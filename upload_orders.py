import json
import urllib.request
import urllib.parse
import time

API_KEY = "lU2gcKVfoscEeL3fi6wRRJqCBZ7p8ahJ"
BASE_URL = "https://zaqcount2.retailcrm.ru/api/v5"
SITE = "zaqcount2"

with open("mock_orders.json", "r", encoding="utf-8") as f:
    orders = json.load(f)

success = 0
failed = 0

for i, order in enumerate(orders, 1):
    order["orderType"] = "main"
    payload = urllib.parse.urlencode({
        "apiKey": API_KEY,
        "site": SITE,
        "order": json.dumps(order, ensure_ascii=False)
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/orders/create",
        data=payload,
        method="POST"
    )
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            if body.get("success"):
                print(f"[{i}/50] OK — заказ #{body.get('id')} ({order['firstName']} {order['lastName']})")
                success += 1
            else:
                print(f"[{i}/50] ОШИБКА — {body.get('errorMsg', body)}")
                failed += 1
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            err = json.loads(body)
            print(f"[{i}/50] ОШИБКА {e.code} — {err.get('errorMsg','')} | {err.get('errors','')}")
        except Exception:
            print(f"[{i}/50] ОШИБКА {e.code} — {body[:200]}")
        failed += 1
    except Exception as e:
        print(f"[{i}/50] ИСКЛЮЧЕНИЕ — {e}")
        failed += 1

    time.sleep(0.3)  # небольшая пауза, чтобы не превысить rate limit

print(f"\nГотово: {success} успешно, {failed} с ошибкой.")
