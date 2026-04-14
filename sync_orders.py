"""
Синхронизация заказов: RetailCRM → Supabase
Запуск: python3 sync_orders.py
"""

import json
import urllib.request
import urllib.parse
import urllib.error

# ── настройки ──────────────────────────────────────────────────────────────
RETAILCRM_URL = "https://zaqcount2.retailcrm.ru/api/v5"
RETAILCRM_KEY = "lU2gcKVfoscEeL3fi6wRRJqCBZ7p8ahJ"
RETAILCRM_SITE = "zaqcount2"

SUPABASE_URL  = "https://plifwqwdkkfjwyuriglj.supabase.co"
SUPABASE_KEY  = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBsaWZ3cXdka2tmand5dXJpZ2xqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYxMDAyMjgsImV4cCI6MjA5MTY3NjIyOH0.KgLLtyqpg9NVkm6ukB2qakNWq5RVuGBxKE7GvedQp6I"
# ───────────────────────────────────────────────────────────────────────────


def fetch_orders_page(page: int) -> dict:
    params = urllib.parse.urlencode({
        "apiKey": RETAILCRM_KEY,
        "site":   RETAILCRM_SITE,
        "limit":  100,
        "page":   page,
    })
    req = urllib.request.Request(f"{RETAILCRM_URL}/orders?{params}")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def fetch_all_orders() -> list[dict]:
    orders = []
    page = 1
    while True:
        data        = fetch_orders_page(page)
        batch       = data.get("orders", [])
        pagination  = data.get("pagination", {})
        orders.extend(batch)
        print(f"  страница {page}: получено {len(batch)} заказов "
              f"(всего {pagination.get('totalCount', '?')})")
        if page >= pagination.get("totalPageCount", 1):
            break
        page += 1
    return orders


def transform(order: dict) -> dict:
    items = [
        {
            "id":          item.get("id"),
            "product":     item.get("offer", {}).get("displayName"),
            "quantity":    item.get("quantity"),
            "price":       item.get("initialPrice"),
            "total":       item.get("initialPrice", 0) * item.get("quantity", 1),
        }
        for item in order.get("items", [])
    ]

    custom_fields = order.get("customFields", {})
    utm = custom_fields.get("utm_source") if isinstance(custom_fields, dict) else None

    delivery = order.get("delivery", {})
    address  = delivery.get("address", {})

    return {
        "id":               order["id"],
        "number":           order.get("number"),
        "status":           order.get("status"),
        "order_type":       order.get("orderType"),
        "order_method":     order.get("orderMethod"),
        "first_name":       order.get("firstName"),
        "last_name":        order.get("lastName"),
        "phone":            order.get("phone"),
        "email":            order.get("email"),
        "summ":             order.get("summ"),
        "total_summ":       order.get("totalSumm"),
        "delivery_city":    address.get("city"),
        "delivery_address": address.get("text"),
        "utm_source":       utm,
        "items":            items,
        "customer_id":      order.get("customer", {}).get("id"),
        "site":             order.get("site"),
        "created_at":       order.get("createdAt"),
        "status_updated_at": order.get("statusUpdatedAt"),
    }


def upsert_to_supabase(rows: list[dict]) -> None:
    url  = f"{SUPABASE_URL}/rest/v1/orders"
    body = json.dumps(rows, ensure_ascii=False).encode("utf-8")
    req  = urllib.request.Request(url, data=body, method="POST")
    req.add_header("apikey",       SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer",       "resolution=merge-duplicates")

    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status
    except urllib.error.HTTPError as e:
        body_err = e.read().decode("utf-8")
        raise RuntimeError(f"Supabase {e.code}: {body_err}") from e


def main():
    print("1. Забираем заказы из RetailCRM...")
    orders = fetch_all_orders()
    print(f"   итого: {len(orders)} заказов\n")

    print("2. Трансформируем...")
    rows = [transform(o) for o in orders]

    print("3. Загружаем в Supabase (upsert)...")
    # загружаем пачками по 50, чтобы не упереться в лимит запроса
    batch_size = 50
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        upsert_to_supabase(batch)
        print(f"   upsert {i + 1}–{i + len(batch)} — OK")

    print(f"\nГотово. {len(rows)} заказов синхронизировано.")


if __name__ == "__main__":
    main()
