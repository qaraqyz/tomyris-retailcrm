Перед каждым проектом я сначала пишу подробное ТЗ с чеклистом, чтобы клауди делал каждый этап отдельно и можно было контролировать каждый его шаг. Единственная проблема была в том что клауди 
написал все api ключи в сам код, а не вывел его в отдельный env файл.

Сам промт:

# ТЗ: Интеграция RetailCRM → Supabase → Дашборд TOMYRIS

## Цель проекта

Настроить автоматическую синхронизацию заказов из RetailCRM в базу данных Supabase,
визуализировать аналитику на брендовом дашборде и получать Telegram-уведомления
о крупных заказах в реальном времени.

---

## Стек

| Слой | Технология |
|---|---|
| CRM | RetailCRM API v5 |
| База данных | Supabase (PostgreSQL + REST API) |
| Фронтенд | Vanilla HTML + Chart.js |
| Хостинг | Vercel (static) |
| Уведомления | Telegram Bot API |
| Язык скриптов | Python 3.9+ (без сторонних библиотек) |
| Репозиторий | GitHub |

---

## Этап 1 — Загрузка тестовых заказов в RetailCRM

### Цель
Загрузить 50 mock-заказов из `mock_orders.json` в RetailCRM через API.

### Требования
- Читать заказы из `mock_orders.json`
- Перед отправкой подставить корректный `orderType` из справочника CRM (`/reference/order-types`)
- Передавать параметр `site` при каждом запросе
- Соблюдать паузу между запросами (0.3 с) чтобы не превысить rate limit
- Выводить результат каждого заказа: успех с ID или текст ошибки

### Эндпоинты
- `GET /api/v5/reference/order-types` — получить доступные типы заказов
- `GET /api/v5/reference/sites` — получить код сайта
- `POST /api/v5/orders/create` — создать заказ

### Результат
Скрипт `upload_orders.py`. Все 50 заказов созданы в CRM.

---

## Этап 2 — Создание таблицы в Supabase

### Цель
Подготовить структуру БД для хранения заказов.

### Схема таблицы `orders`

```sql
create table if not exists orders (
  id                integer primary key,
  number            text,
  status            text,
  order_type        text,
  order_method      text,
  first_name        text,
  last_name         text,
  phone             text,
  email             text,
  summ              numeric,
  total_summ        numeric,
  delivery_city     text,
  delivery_address  text,
  utm_source        text,
  items             jsonb,
  customer_id       integer,
  site              text,
  created_at        timestamptz,
  status_updated_at timestamptz,
  synced_at         timestamptz default now()
);
```

### Требования
- Включить Row Level Security (RLS)
- Добавить политику `allow all` для доступа через anon key
- SQL выполняется вручную через Supabase SQL Editor

### Результат
Файл `create_table.sql`. Таблица создана и доступна через REST API.

---

## Этап 3 — Синхронизация RetailCRM → Supabase

### Цель
Написать скрипт, который забирает все заказы из RetailCRM и кладёт их в Supabase.

### Требования
- Постраничная загрузка из RetailCRM (лимит 100, все страницы)
- Трансформация полей: вложенные объекты (`delivery.address`, `items`, `customer`) → плоская структура
- Поле `items` хранится как JSONB (массив объектов с `product`, `quantity`, `price`, `total`)
- Upsert в Supabase: при повторном запуске обновлять существующие записи, не дублировать
- Загрузка пачками по 50 записей

### Трансформация ключевых полей

```
order.delivery.address.city  → delivery_city
order.delivery.address.text  → delivery_address
order.customFields.utm_source → utm_source
order.items[].offer.displayName → items[].product
```

### Результат
Скрипт `sync_orders.py`. 50 заказов синхронизированы в Supabase.

---

## Этап 4 — Дашборд TOMYRIS

### Цель
Одностраничный дашборд с аналитикой заказов в фирменном стиле бренда TOMYRIS.

### Дизайн
- Цвета: чёрный фон `#0a0a0a`, розовые акценты `#f0a0b8 → #8c2040`, белый текст
- Шрифты: Cormorant Garamond (заголовки, KPI) + Inter (интерфейс)
- Стиль: минималистичный, люксовый, без лишних элементов

### Блоки

#### KPI-карточки (3 штуки)
- Всего заказов
- Общая выручка (розовый акцент)
- Средний чек

#### Графики (4 штуки)
| График | Тип | Данные |
|---|---|---|
| Выручка по городам | Bar | `delivery_city` + `total_summ` |
| Топ-5 продуктов | Horizontal bar | `items[].product` + `quantity` |
| Позиции в заказе | Bar | кол-во `items` на заказ |
| Заказы по городам | Doughnut | `delivery_city` + count |

### Технические требования
- Данные тянутся напрямую из Supabase REST API при загрузке страницы
- Никакого бэкенда — только статический HTML
- Chart.js 4.x через CDN
- Кастомные тултипы в фирменном стиле
- Деплой на Vercel

### Результат
Файл `dashboard/index.html` + `dashboard/vercel.json`. Задеплоено на Vercel.

---

## Этап 5 — Telegram-уведомления

### Цель
Автоматически уведомлять в Telegram о новых заказах на сумму больше 50 000 ₸.

### Требования
- Сравнивать новые заказы с последним обработанным ID (хранится в `.last_order_id`)
- Отправлять уведомление только если `total_summ > 50 000`
- Формат сообщения: имя клиента, телефон, город, состав заказа, итоговая сумма
- Запускаться автоматически каждые 5 минут через cron
- Логи писать в `/tmp/notify_orders.log`

### Формат уведомления
```
🔔 Крупный заказ #90A

👤 Феруза Юсупова
📞 +77090123450
📍 Алматы

🛍 Состав:
  • Утягивающий комбидресс Nova Slim × 1
  • Утягивающее боди Nova Body × 1

💰 Сумма: 81 000 ₸
```

### Cron
```
*/5 * * * * python3 /path/to/notify_orders.py >> /tmp/notify_orders.log 2>&1
```

### Результат
Скрипт `notify_orders.py`. Cron настроен, уведомления приходят.

---

## Этап 6 — GitHub

### Требования
- Репозиторий публичный: `tomyris-retailcrm`
- Все API-ключи вынесены в `.env` — файл добавлен в `.gitignore`
- В репо есть `.env.example` с пустыми значениями для онбординга
- В репо есть `docs/ai/tz.md` — текущее ТЗ

### Структура репозитория
```
tomyris-retailcrm/
├── .env.example          # шаблон переменных окружения
├── .gitignore
├── mock_orders.json      # 50 тестовых заказов
├── upload_orders.py      # Этап 1: загрузка в RetailCRM
├── create_table.sql      # Этап 2: схема таблицы Supabase
├── sync_orders.py        # Этап 3: синхронизация → Supabase
├── notify_orders.py      # Этап 5: Telegram-уведомления
├── dashboard/
│   ├── index.html        # Этап 4: дашборд TOMYRIS
│   └── vercel.json
└── docs/
    └── ai/
        └── tz.md         # этот документ
```

---

## Переменные окружения (`.env`)

```env
RETAILCRM_URL=https://yourshop.retailcrm.ru/api/v5
RETAILCRM_KEY=your_retailcrm_api_key
RETAILCRM_SITE=your_site_code

SUPABASE_URL=https://your_project.supabase.co
SUPABASE_KEY=your_supabase_anon_key

TG_TOKEN=your_telegram_bot_token
TG_CHAT_ID=your_telegram_chat_id
```

---

## Архитектура

```
RetailCRM API
     │
     ├── upload_orders.py   → загрузка mock-заказов (разово)
     │
     ├── sync_orders.py     → полная синхронизация в Supabase (по требованию)
     │
     └── notify_orders.py   → мониторинг новых заказов > 50 000 ₸ (cron каждые 5 мин)
                                        │
                                   Telegram Bot
                   
Supabase
  └── таблица orders
            │
      dashboard/index.html → Vercel (статика, данные при загрузке)
```

---

## Чеклист выполнения

- [x] Загрузить 50 заказов в RetailCRM
- [x] Создать таблицу `orders` в Supabase
- [x] Написать и запустить `sync_orders.py`
- [x] Создать и задеплоить дашборд на Vercel
- [x] Настроить Telegram-уведомления
- [x] Вынести секреты в `.env`
- [x] Запушить в GitHub
