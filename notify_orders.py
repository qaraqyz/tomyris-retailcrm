"""
Мониторинг заказов RetailCRM → уведомление в Telegram если сумма > 50 000 ₸
Запуск: python3 notify_orders.py
Для автозапуска добавить в cron: */5 * * * * python3 /path/to/notify_orders.py
"""

import json
import urllib.request
import urllib.parse
import urllib.error
import os

# ── настройки ──────────────────────────────────────────────────────────────
RETAILCRM_URL  = "https://zaqcount2.retailcrm.ru/api/v5"
RETAILCRM_KEY  = "lU2gcKVfoscEeL3fi6wRRJqCBZ7p8ahJ"
RETAILCRM_SITE = "zaqcount2"

SUPABASE_URL = "https://plifwqwdkkfjwyuriglj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBsaWZ3cXdka2tmand5dXJpZ2xqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYxMDAyMjgsImV4cCI6MjA5MTY3NjIyOH0.KgLLtyqpg9NVkm6ukB2qakNWq5RVuGBxKE7GvedQp6I"

TG_TOKEN   = "8616255409:AAHTFNE_HI8h238XzIJLLas2kDWcWT8vzyc"
TG_CHAT_ID = "1085936541"

THRESHOLD  = 50_000   # ₸
STATE_FILE = os.path.join(os.path.dirname(__file__), ".last_order_id")
# ───────────────────────────────────────────────────────────────────────────


def get_last_seen_id() -> int:
    """Читаем последний обработанный ID заказа из файла."""
    try:
        with open(STATE_FILE) as f:
            return int(f.read().strip())
    except Exception:
        return 0


def save_last_seen_id(order_id: int) -> None:
    with open(STATE_FILE, "w") as f:
        f.write(str(order_id))


def fetch_recent_orders() -> list[dict]:
    """Получаем последнюю страницу заказов из RetailCRM."""
    params = urllib.parse.urlencode({
        "apiKey": RETAILCRM_KEY,
        "site":   RETAILCRM_SITE,
        "limit":  100,
        "page":   1,
    })
    req = urllib.request.Request(f"{RETAILCRM_URL}/orders?{params}")
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode())
    return data.get("orders", [])


def send_telegram(text: str) -> None:
    payload = json.dumps({"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        data=payload,
    )
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10) as r:
        resp = json.loads(r.read().decode())
    if not resp.get("ok"):
        raise RuntimeError(f"Telegram error: {resp}")


def format_items(items: list[dict]) -> str:
    lines = []
    for item in items:
        lines.append(f"  • {item.get('offer', {}).get('displayName', '—')} × {item.get('quantity', 1)}")
    return "\n".join(lines) if lines else "  —"


def main():
    last_id = get_last_seen_id()
    orders  = fetch_recent_orders()

    # сортируем по id, берём только новые
    new_orders = sorted(
        [o for o in orders if o["id"] > last_id],
        key=lambda o: o["id"]
    )

    if not new_orders:
        print("Новых заказов нет.")
        return

    notified = 0
    max_id   = last_id

    for order in new_orders:
        max_id = max(max_id, order["id"])
        summ   = order.get("totalSumm", 0) or order.get("summ", 0)

        if summ > THRESHOLD:
            items_text = format_items(order.get("items", []))
            text = (
                f"🔔 <b>Крупный заказ #{order['number']}</b>\n\n"
                f"👤 {order.get('firstName', '')} {order.get('lastName', '')}\n"
                f"📞 {order.get('phone', '—')}\n"
                f"📍 {order.get('delivery', {}).get('address', {}).get('city', '—')}\n\n"
                f"🛍 Состав:\n{items_text}\n\n"
                f"💰 <b>Сумма: {summ:,.0f} ₸</b>"
            )
            send_telegram(text)
            print(f"Отправлено уведомление: заказ #{order['number']} — {summ:,.0f} ₸")
            notified += 1
        else:
            print(f"Заказ #{order['number']} — {summ:,.0f} ₸ (ниже порога, пропущен)")

    save_last_seen_id(max_id)
    print(f"\nОбработано {len(new_orders)} новых заказов, отправлено {notified} уведомлений.")


if __name__ == "__main__":
    main()
