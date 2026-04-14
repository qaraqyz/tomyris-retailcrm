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

def load_env(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(__file__), ".env")
    env = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return env

_env = load_env()

RETAILCRM_URL  = os.getenv("RETAILCRM_URL",  _env.get("RETAILCRM_URL"))
RETAILCRM_KEY  = os.getenv("RETAILCRM_KEY",  _env.get("RETAILCRM_KEY"))
RETAILCRM_SITE = os.getenv("RETAILCRM_SITE", _env.get("RETAILCRM_SITE"))
TG_TOKEN       = os.getenv("TG_TOKEN",       _env.get("TG_TOKEN"))
TG_CHAT_ID     = os.getenv("TG_CHAT_ID",     _env.get("TG_CHAT_ID"))

THRESHOLD  = 50_000
STATE_FILE = os.path.join(os.path.dirname(__file__), ".last_order_id")


def get_last_seen_id() -> int:
    try:
        with open(STATE_FILE) as f:
            return int(f.read().strip())
    except Exception:
        return 0


def save_last_seen_id(order_id: int) -> None:
    with open(STATE_FILE, "w") as f:
        f.write(str(order_id))


def fetch_recent_orders() -> list[dict]:
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
    lines = [
        f"  • {item.get('offer', {}).get('displayName', '—')} × {item.get('quantity', 1)}"
        for item in items
    ]
    return "\n".join(lines) if lines else "  —"


def main():
    last_id = get_last_seen_id()
    orders  = fetch_recent_orders()

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
