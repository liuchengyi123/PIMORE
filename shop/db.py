import sqlite3
import threading


class _Result:
    def __init__(self, rows, lastrowid):
        self._rows = rows
        self._index = 0
        self.lastrowid = lastrowid

    def fetchone(self):
        if self._index >= len(self._rows):
            return None
        row = self._rows[self._index]
        self._index += 1
        return row

    def fetchall(self):
        rows = self._rows[self._index:]
        self._index = len(self._rows)
        return rows


class Connection:
    def __init__(self, conn):
        self._conn = conn
        self._lock = threading.Lock()

    def execute(self, sql, parameters=()):
        with self._lock:
            cursor = self._conn.execute(sql, parameters)
            return _Result(cursor.fetchall(), cursor.lastrowid)

    def executemany(self, sql, seq):
        with self._lock:
            cursor = self._conn.executemany(sql, seq)
            return _Result(cursor.fetchall(), cursor.lastrowid)

    def executescript(self, script):
        with self._lock:
            return self._conn.executescript(script)

    def commit(self):
        with self._lock:
            return self._conn.commit()

    def rollback(self):
        with self._lock:
            return self._conn.rollback()


SCHEMA = """
create table if not exists products (
    sku text primary key,
    category text not null,
    price_cents integer not null,
    stock integer not null,
    names text not null,
    bullets text not null,
    description text not null,
    specs text not null,
    source_zh text not null default '',
    listing text not null default '',
    published integer not null default 1,
    original_cents integer not null default 0,
    offers text not null default '[]',
    uploaded_at text not null default '',
    subcategory text not null default ''
);
create index if not exists products_published on products (published);
create table if not exists rates (
    currency text not null,
    hour text not null,
    units_per_usd real not null,
    primary key (currency, hour)
);
create table if not exists accounts (
    email text primary key,
    password_hash text,
    referrer_email text
);
create table if not exists balances (
    email text primary key,
    available_cents integer not null
);
create table if not exists orders (
    id integer primary key,
    submit_id text unique,
    email text not null,
    status text not null,
    currency text not null,
    units_per_usd real not null,
    merchandise_cents integer not null default 0,
    discount_cents integer not null default 0,
    coupon_cents integer not null default 0,
    coupon_id integer,
    shipping_cents integer not null default 0,
    balance_cents integer not null default 0,
    due_cents integer not null,
    due_local integer not null,
    ship_country text not null default '',
    ship_name text not null default '',
    address text not null default '',
    city text not null default '',
    region text not null default '',
    postal text not null default '',
    phone text not null default '',
    referrer_email text,
    self_rebate_cents integer not null default 0,
    direct_rebate_cents integer not null default 0,
    carrier text not null default '',
    tracking text not null default '',
    created_at text not null default ''
);
create table if not exists order_lines (
    order_id integer not null,
    sku text not null,
    price_cents integer not null,
    qty integer not null,
    bought integer not null default 0,
    campaign_item_id integer not null default 0
);
create table if not exists campaigns (
    id integer primary key,
    kind text not null,
    enabled integer not null default 0,
    title text not null default '',
    rules text not null default '',
    image_url text not null default '',
    starts_at text not null default '',
    ends_at text not null default ''
);
create table if not exists campaign_items (
    id integer primary key,
    campaign_id integer not null,
    sku text not null,
    price_cents integer not null,
    stock integer not null default 0,
    unique (campaign_id, sku)
);
create table if not exists coupons (
    id integer primary key,
    name text not null,
    kind text not null,
    threshold_cents integer not null,
    amount_cents integer not null,
    enabled integer not null
);
create table if not exists coupon_grants (
    id integer primary key,
    email text not null,
    coupon_id integer not null,
    day text not null,
    unique (email, coupon_id, day)
);
create table if not exists promos (
    key text primary key,
    value text not null
);
create table if not exists ads (
    slot text not null,
    lang text not null,
    image_url text,
    href text,
    body text,
    primary key (slot, lang)
);
create table if not exists reviews (
    id integer primary key,
    sku text not null,
    email text not null,
    rating integer not null,
    body text not null,
    unique (email, sku)
);
create table if not exists referrals (
    email text primary key,
    code text not null
);
create table if not exists password_resets (
    token text primary key,
    email text not null,
    expires_at text not null
);
create table if not exists sessions (
    token text primary key,
    email text not null
);
create table if not exists withdrawals (
    id integer primary key,
    email text not null,
    amount_cents integer not null,
    payout_account text not null,
    status text not null
);
create table if not exists stock_alerts (
    id integer primary key,
    sku text not null,
    email text not null,
    country text not null default 'US',
    offer text not null default '',
    created_at text not null default (datetime('now')),
    unique(sku, email, offer)
);
create table if not exists questions (

    id integer primary key,
    sku text not null,
    email text not null,
    body text not null,
    answer text not null default ''
);
create table if not exists addresses (
    id integer primary key,
    email text not null,
    name text not null,
    address text not null,
    city text not null,
    region text not null,
    postal text not null,
    ship_country text not null,
    phone text not null
);
create table if not exists returns (
    id integer primary key,
    order_id integer not null,
    email text not null,
    reason text not null,
    status text not null
);
create table if not exists cs_rooms (
    id text primary key,
    visitor_id text not null,
    email text not null default '',
    status text not null default 'open',
    current_sku text not null default '',
    current_name text not null default '',
    current_image text not null default '',
    current_price text not null default '',
    history_json text not null default '[]',
    created_at text not null,
    updated_at text not null,
    last_user_at text not null default '',
    last_staff_at text not null default '',
    unread_staff integer not null default 0,
    unread_user integer not null default 0
);
create table if not exists cs_messages (
    id integer primary key,
    room_id text not null,
    role text not null,
    body text not null,
    created_at text not null,
    staff_user text not null default ''
);
create index if not exists cs_messages_room on cs_messages (room_id, id);
create index if not exists cs_rooms_updated on cs_rooms (updated_at desc);
create table if not exists messages (
    id integer primary key,
    email text not null,
    body text not null
);
create table if not exists pay_methods (
    id integer primary key,
    email text not null,
    brand text not null,
    last4 text not null
);
create table if not exists clicks (
    id integer primary key,
    email text not null,
    sku text not null,
    weight integer not null
);
create table if not exists visits (
    id integer primary key,
    day text not null,
    kind text not null,
    sku text not null default '',
    country text not null default '',
    lang text not null default '',
    visitor text not null default '',
    cents integer not null default 0,
    qty integer not null default 0
);
create index if not exists visits_day on visits (day, kind);
create index if not exists clicks_email on clicks (email, id desc);
create table if not exists staff (
    username text primary key,
    password_hash text not null,
    role text not null,
    enabled integer not null default 1
);
create table if not exists staff_sessions (
    token text primary key,
    username text not null
);
create table if not exists settings (
    key text primary key,
    value text not null
);
create table if not exists ad_attribution (
    order_id text primary key,
    payload text not null default "{}",
    created_at text not null default ""
);
create table if not exists ad_event_log (
    id integer primary key,
    created_at text not null,
    platform text not null,
    event_name text not null,
    order_id text not null default "",
    event_id text not null default "",
    ok integer not null default 0,
    detail text not null default ""
);
create table if not exists hot_titles (
    country text not null,
    title text not null,
    fetched_at text not null,
    primary key (country, title)
);
"""


def connect(path=":memory:"):
    conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")
    if path != ":memory:":
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-20000")
    return Connection(conn)


def _column_names(conn, table):
    return {row["name"] for row in conn.execute(f"pragma table_info({table})").fetchall()}


def migrate(conn):
    try:
        from shop.adtrack import ensure_tables
        ensure_tables(conn)
    except Exception:
        pass
    try:
        from shop.support import ensure_cs_tables
        ensure_cs_tables(conn)
    except Exception:
        pass
    # ensure stock_alerts (Notify me)
    conn.execute(
        """create table if not exists stock_alerts (
        id integer primary key,
        sku text not null,
        email text not null,
        country text not null default 'US',
        offer text not null default '',
        created_at text not null default (datetime('now')),
        unique(sku, email, offer)
        )"""
    )
    conn.executescript(SCHEMA)
    orders = _column_names(conn, "orders")
    for column, ddl in (
        ("gift_message", "alter table orders add column gift_message text not null default ''"),
        ("pay_method", "alter table orders add column pay_method text not null default 'card'"),
        ("speed", "alter table orders add column speed text not null default 'standard'"),
        ("refund_reason", "alter table orders add column refund_reason text not null default ''"),
    ):
        if column not in orders:
            conn.execute(ddl)
    withdrawals_cols = _column_names(conn, "withdrawals")
    if "payout_note" not in withdrawals_cols:
        conn.execute("alter table withdrawals add column payout_note text not null default ''")
    products = _column_names(conn, "products")
    if "image_url" not in products:
        conn.execute("alter table products add column image_url text not null default ''")
    if "source_zh" not in products:
        conn.execute("alter table products add column source_zh text not null default ''")
    if "listing" not in products:
        conn.execute("alter table products add column listing text not null default ''")
    if "published" not in products:
        conn.execute("alter table products add column published integer not null default 1")
    if "original_cents" not in products:
        conn.execute("alter table products add column original_cents integer not null default 0")
    if "offers" not in products:
        conn.execute("alter table products add column offers text not null default '[]'")
    if "uploaded_at" not in products:
        conn.execute("alter table products add column uploaded_at text not null default ''")
    if "subcategory" not in products:
        conn.execute("alter table products add column subcategory text not null default ''")
    if "markets" not in products:
        conn.execute("alter table products add column markets text not null default ''")
    if "markets_lock" not in products:
        conn.execute("alter table products add column markets_lock integer not null default 0")
    if "gen_at" not in products:
        conn.execute("alter table products add column gen_at text not null default ''")
    conn.execute(
        """
        create table if not exists gen_tasks (
            sku text primary key,
            status text not null,
            worker text not null default '',
            error text not null default ''
        )
        """
    )
    task_cols = _column_names(conn, "gen_tasks")
    if "touched" not in task_cols:
        conn.execute("alter table gen_tasks add column touched real not null default 0")
    conn.execute(
        """
        create table if not exists sku_gen_tasks (
            id text primary key,
            product_sku text not null default '',
            image text not null default '',
            status text not null,
            worker text not null default '',
            error text not null default '',
            touched real not null default 0
        )
        """
    )
    sku_task_cols = _column_names(conn, "sku_gen_tasks")
    # Migrate legacy product-level queue (sku PK, no image column) -> image-level.
    if "id" not in sku_task_cols and "sku" in sku_task_cols:
        conn.execute("alter table sku_gen_tasks rename to sku_gen_tasks_legacy")
        conn.execute(
            """
            create table sku_gen_tasks (
                id text primary key,
                product_sku text not null default '',
                image text not null default '',
                status text not null,
                worker text not null default '',
                error text not null default '',
                touched real not null default 0
            )
            """
        )
        conn.execute("drop table sku_gen_tasks_legacy")
        sku_task_cols = _column_names(conn, "sku_gen_tasks")
    if "product_sku" not in sku_task_cols:
        conn.execute("alter table sku_gen_tasks add column product_sku text not null default ''")
    if "image" not in sku_task_cols:
        conn.execute("alter table sku_gen_tasks add column image text not null default ''")
    if "touched" not in sku_task_cols:
        conn.execute("alter table sku_gen_tasks add column touched real not null default 0")
    lines = _column_names(conn, "order_lines")
    if "bought" not in lines:
        conn.execute("alter table order_lines add column bought integer not null default 0")
    if "campaign_item_id" not in lines:
        conn.execute("alter table order_lines add column campaign_item_id integer not null default 0")
    orders_cols = _column_names(conn, "orders")
    if "created_at" not in orders_cols:
        conn.execute("alter table orders add column created_at text not null default ''")

    conn.execute(
        """
        create table if not exists stripe_sessions (
            order_id integer primary key,
            amount integer not null,
            currency text not null,
            session_id text not null default '',
            payment_intent text not null default ''
        )
        """
    )
    conn.commit()
