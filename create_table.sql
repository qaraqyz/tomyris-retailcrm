create table if not exists orders (
  id               integer primary key,
  number           text,
  status           text,
  order_type       text,
  order_method     text,
  first_name       text,
  last_name        text,
  phone            text,
  email            text,
  summ             numeric,
  total_summ       numeric,
  delivery_city    text,
  delivery_address text,
  utm_source       text,
  items            jsonb,
  customer_id      integer,
  site             text,
  created_at       timestamptz,
  status_updated_at timestamptz,
  synced_at        timestamptz default now()
);

-- разрешить insert/upsert через anon key
alter table orders enable row level security;
create policy "allow all" on orders for all using (true) with check (true);
