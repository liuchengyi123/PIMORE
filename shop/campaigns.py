from datetime import datetime, timedelta, timezone


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def _parse(ts):
    text = (ts or "").strip()
    if not text:
        return None
    if len(text) == 16:
        text += ":00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _parent(code):
    return str(code or "").split("~", 1)[0]


def is_live(row, now=None):
    now = now or _now()
    if not int(row["enabled"] or 0):
        return False
    start = _parse(row["starts_at"])
    end = _parse(row["ends_at"])
    if start and now < start:
        return False
    if end and now >= end:
        return False
    return True


def active_campaign(conn, kind, now=None):
    now = now or _now()
    rows = conn.execute(
        "select * from campaigns where kind = ? order by id desc",
        (kind,),
    ).fetchall()
    for row in rows:
        if is_live(row, now):
            return row
    return None


def items_for(conn, campaign_id):
    return conn.execute(
        "select * from campaign_items where campaign_id = ? and stock > 0 order by id",
        (campaign_id,),
    ).fetchall()


def buyer_is_new(conn, email):
    email = (email or "").strip().lower()
    if not email:
        return True
    paid = conn.execute(
        """
        select count(*) as n from orders
        where email = ? and status in ('paid', 'shipped')
        """,
        (email,),
    ).fetchone()["n"]
    return paid == 0


def half_cents(price_cents):
    price = int(price_cents)
    if price <= 1:
        return price
    return price // 2


def parse_hold(raw, now=None):
    now = now or _now()
    parts = str(raw or "").split("|")
    if len(parts) != 3 or not parts[0]:
        return None
    ends = _parse(parts[2])
    if ends is None:
        return None
    try:
        price_cents = int(parts[1])
    except ValueError:
        return None
    return {
        "sku": parts[0],
        "price_cents": price_cents,
        "ends_at": ends.isoformat(),
        "alive": now < ends,
    }


def pack_hold(sku, price_cents, ends_at):
    return f"{sku}|{int(price_cents)}|{ends_at}"


def newcomer_kept(conn, lines, now=None):
    camp = active_campaign(conn, "newcomer", now)
    if camp is None:
        return None
    specials = {row["sku"]: row for row in items_for(conn, camp["id"])}
    for line in lines or []:
        parent = _parent(line.get("sku"))
        row = specials.get(parent)
        if row is not None:
            return {"sku": parent, "price_cents": int(row["price_cents"])}
    return None


def _offer(conn, sku, qty, hold_sku, hold_price, newcomer, seckill_id):
    # Flash / newcomer specials are limit 1 at the promo price.
    qty = int(qty or 1)
    if qty != 1:
        return None
    if hold_sku and sku == hold_sku:
        return int(hold_price), 0
    row = newcomer.get(sku)
    if row is not None and int(row["stock"]) >= 1:
        return int(row["price_cents"]), int(row["id"])
    if seckill_id:
        found = conn.execute(
            """
            select * from campaign_items
            where campaign_id = ? and sku = ? and stock >= 1
            """,
            (seckill_id, sku),
        ).fetchone()
        if found is not None:
            return int(found["price_cents"]), int(found["id"])
    return None


def price_for(conn, code, email, lines, qty=1, returning=False, hold=None):
    parent = _parent(code)
    now = _now()
    fresh = (not returning) and buyer_is_new(conn, email)
    held = bool(hold) and fresh
    hold_sku = ""
    hold_price = 0
    if held and hold.get("alive"):
        hold_sku = hold["sku"]
        hold_price = hold["price_cents"]
    newcomer = {}
    if fresh and not held:
        camp = active_campaign(conn, "newcomer", now)
        if camp:
            newcomer = {row["sku"]: row for row in items_for(conn, camp["id"])}
    seckill = active_campaign(conn, "seckill", now)
    seckill_id = seckill["id"] if seckill else None

    def offer(sku, count):
        return _offer(conn, sku, count, hold_sku, hold_price, newcomer, seckill_id)

    if hold_sku:
        owner = hold_sku
    else:
        owner = None
        for line in lines:
            other = _parent(line.get("sku"))
            if offer(other, line.get("qty") or 1):
                owner = other
                break
    if owner and owner != parent:
        return None, None
    found = offer(parent, qty)
    if found:
        return found
    return None, None


def next_coupon_goal(conn, email, merchandise):
    email = (email or "").strip().lower()
    open_orders = 0
    if email:
        open_orders = conn.execute(
            "select count(*) as n from orders where email = ? and status != 'cancelled'",
            (email,),
        ).fetchone()["n"]
    best = None
    rows = conn.execute("select * from coupons where enabled = 1").fetchall()
    for coupon in rows:
        threshold = int(coupon["threshold_cents"])
        if threshold <= merchandise:
            continue
        kind = coupon["kind"]
        if kind == "public":
            allowed = True
        elif kind == "first":
            allowed = open_orders == 0
        elif email:
            allowed = conn.execute(
                "select 1 as ok from coupon_grants where email = ? and coupon_id = ?",
                (email, coupon["id"]),
            ).fetchone() is not None
        else:
            allowed = False
        if not allowed:
            continue
        if best is None or threshold < best[0]:
            best = (threshold, int(coupon["amount_cents"]))
    return best


def ensure_campaigns(conn):
    if conn.execute("select count(*) as n from campaigns").fetchone()["n"]:
        return
    now = _now()
    end = (now + timedelta(hours=36)).isoformat()
    cursor = conn.execute(
        """
        insert into campaigns (kind, enabled, title, rules, starts_at, ends_at)
        values ('seckill', 1, 'Ends soon', ?, ?, ?)
        """,
        (
            "The price on this page lasts until the clock hits zero. When it does, this price stops.",
            now.isoformat(),
            end,
        ),
    )
    seckill_id = cursor.lastrowid
    cursor = conn.execute(
        """
        insert into campaigns (kind, enabled, title, rules, starts_at, ends_at)
        values ('newcomer', 1, 'New here', ?, '', '')
        """,
        (
            "One item at this price. The moment it is in your cart, every other item here goes back to the regular price. After your first paid order, this price is gone.",
        ),
    )
    newcomer_id = cursor.lastrowid
    rows = conn.execute(
        """
        select sku, price_cents from products
        where published = 1 and stock > 0
          and sku not in ('binder-clip', 'drain-rack', 'note-holder', 'toy-ball')
        order by price_cents asc, sku asc
        limit 8
        """
    ).fetchall()
    for row in rows[:4]:
        price = max(100, int(row["price_cents"] * 70 / 100))
        conn.execute(
            "insert into campaign_items (campaign_id, sku, price_cents, stock) values (?, ?, ?, 40)",
            (seckill_id, row["sku"], price),
        )
    for row in rows[4:8]:
        price = max(100, int(row["price_cents"] * 50 / 100))
        conn.execute(
            "insert into campaign_items (campaign_id, sku, price_cents, stock) values (?, ?, ?, 20)",
            (newcomer_id, row["sku"], price),
        )


def campaign_special_possible(conn, code, email, lines, qty=1, returning=False, hold=None):
    """True when this line could have had a flash/newcomer price but did not (limit / owner)."""
    special, _item = price_for(conn, code, email, lines, qty=qty, returning=returning, hold=hold)
    if special is not None:
        return False
    parent = _parent(code)
    now = _now()
    fresh = (not returning) and buyer_is_new(conn, email)
    held = bool(hold) and fresh and hold.get("alive")
    if held and hold.get("sku") == parent and int(qty or 1) != 1:
        return True
    if held and hold.get("sku") and hold.get("sku") != parent:
        return True
    if fresh and not held:
        camp = active_campaign(conn, "newcomer", now)
        if camp:
            rows = {row["sku"]: row for row in items_for(conn, camp["id"])}
            if parent in rows and int(qty or 1) != 1:
                return True
            if parent in rows:
                # another newcomer already owns the slot
                for line in lines or []:
                    other = _parent(line.get("sku"))
                    if other != parent and other in rows:
                        return True
    seckill = active_campaign(conn, "seckill", now)
    if seckill:
        found = conn.execute(
            "select 1 as ok from campaign_items where campaign_id = ? and sku = ? and stock > 0",
            (seckill["id"], parent),
        ).fetchone()
        if found is not None and int(qty or 1) != 1:
            return True
    return False
