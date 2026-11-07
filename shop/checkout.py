import hashlib
import json
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta, timezone

from shop.campaigns import price_for
from shop.locale import shipping_tier
from shop.pricing import quote
from shop.rewards import rebate

_LOCKS = {}
_LOCKS_GUARD = threading.Lock()
REQUIRED = ("email", "name", "address", "city", "region", "postal", "ship_country", "phone")


class CheckoutError(Exception):
    def __init__(self, code, sku=None, fields=None):
        self.code = code
        self.sku = sku
        self.fields = fields or []


class Outbox:
    def __init__(self):
        self.messages = []

    def send(self, to, subject, body):
        self.messages.append({"to": to, "subject": subject, "body": body})


def email_lock(email):
    with _LOCKS_GUARD:
        lock = _LOCKS.get(email)
        if lock is None:
            lock = threading.Lock()
            _LOCKS[email] = lock
        return lock


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 20_000).hex()
    return f"{salt}${digest}"


def verify_password(password, stored):
    if not stored or "$" not in stored:
        return False
    salt, digest = stored.split("$", 1)
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 20_000).hex()
    return secrets.compare_digest(check, digest)


def load_lines(raw):
    lines = []
    for part in (raw or "").split(","):
        if ":" not in part:
            continue
        sku, qty = part.split(":", 1)
        try:
            count = int(qty)
        except ValueError:
            continue
        sku = sku.strip()
        if sku and count > 0:
            lines.append({"sku": sku, "qty": count})
    return lines


def dump_lines(lines):
    return ",".join(f"{line['sku']}:{line['qty']}" for line in lines)


def stock_parent(code):
    parent, sep, _offer = str(code or "").partition("~")
    return parent if sep else str(code or "")


def merge_line(lines, sku, qty):
    updated = []
    found = False
    for line in lines:
        if line["sku"] == sku:
            updated.append({"sku": sku, "qty": line["qty"] + qty})
            found = True
        else:
            updated.append(line)
    if not found:
        updated.append({"sku": sku, "qty": qty})
    return updated


def build_quote(promos, *, merchandise_cents, ship_country, units, currency, minor_units, coupon_cents=0, coupon_threshold_cents=0, balance_cents=0, use_balance=False):
    return quote(
        merchandise_cents=merchandise_cents,
        tiers=promos["tiers"],
        coupon_cents=coupon_cents,
        coupon_threshold_cents=coupon_threshold_cents,
        free_shipping_cents=0,
        shipping_cents=0,
        balance_cents=balance_cents,
        use_balance=use_balance,
        units_per_usd=units,
        minor_units=minor_units,
    )


def live_offers(row):
    try:
        raw = json.loads(row["offers"] or "[]") if "offers" in row.keys() else []
    except (json.JSONDecodeError, TypeError):
        raw = []
    return [item for item in raw if item.get("id") and not item.get("hold")]


def cheapest_live_offer(row):
    offers = live_offers(row)
    if not offers:
        return None
    return min(offers, key=lambda item: int(item.get("price_cents") or 0))


def find_sellable(conn, code):
    parent, sep, offer_id = str(code or "").partition("~")
    row = conn.execute("select * from products where sku = ?", (parent,)).fetchone()
    if row is None or int(row["published"] or 0) != 1:
        return None
    price = int(row["price_cents"] or 0)
    label = ""
    image = row["image_url"] if "image_url" in row.keys() else ""
    code_out = str(code or "")
    if sep:
        try:
            offers = json.loads(row["offers"] or "[]")
        except json.JSONDecodeError:
            offers = []
        offer = next((item for item in offers if item.get("id") == offer_id), None)
        if offer is None or offer.get("hold"):
            return None
        price = int(offer["price_cents"])
        label = offer.get("label") or ""
        image = offer.get("image") or image
    else:
        # Never sell the phantom products.price_cents when SKUs exist:
        # use the cheapest live offer, or refuse if every offer is held.
        try:
            raw = json.loads(row["offers"] or "[]") if "offers" in row.keys() else []
        except json.JSONDecodeError:
            raw = []
        if raw:
            offer = cheapest_live_offer(row)
            if offer is None:
                price = int(row["price_cents"] or 0)
                if price <= 0:
                    return None
            else:
                price = int(offer["price_cents"])
                label = offer.get("label") or ""
                image = offer.get("image") or image
                code_out = f"{parent}~{offer.get('id')}"
    return {
        "code": code_out,
        "parent": parent,
        "row": row,
        "price_cents": price,
        "label": label,
        "image": image,
        "stock": row["stock"],
    }


def priced_lines(conn, lines, gift_sku="", email="", returning=False, hold=None):
    priced = []
    merchandise = 0
    gift_sku = gift_sku or ""
    for line in lines:
        sold = find_sellable(conn, line["sku"])
        if sold is None:
            raise CheckoutError("stock", sku=line["sku"])
        qty = int(line["qty"])
        unit = int(sold["price_cents"])
        special, item_id = price_for(
            conn, sold["code"], email, lines, qty, returning=returning, hold=hold
        )
        applied = item_id if special is not None else 0
        if special is not None:
            unit = special
        if gift_sku and sold["code"] == gift_sku and qty == 1 and 50 <= int(sold["price_cents"]) <= 200:
            unit = 0
            applied = 0
        priced.append({
            "sku": sold["code"],
            "qty": qty,
            "price_cents": unit,
            "stock": sold["stock"],
            "campaign_item_id": applied,
        })
        merchandise += unit * qty
    return priced, merchandise


def allowed_coupon(conn, email, merchandise, coupon_id):
    if not coupon_id:
        return None
    coupon = conn.execute("select * from coupons where id = ? and enabled = 1", (coupon_id,)).fetchone()
    if coupon is None or merchandise < coupon["threshold_cents"]:
        raise CheckoutError("coupon")
    if coupon["kind"] == "public":
        return coupon
    if coupon["kind"] == "first":
        existing = conn.execute(
            "select count(*) as n from orders where email = ? and status != 'cancelled'",
            (email,),
        ).fetchone()["n"]
        if existing:
            raise CheckoutError("coupon")
        return coupon
    granted = conn.execute(
        "select 1 as ok from coupon_grants where email = ? and coupon_id = ?",
        (email, coupon["id"]),
    ).fetchone()
    if granted is None:
        raise CheckoutError("coupon")
    return coupon


def best_coupon(coupons):
    if not coupons:
        return None
    return max(
        coupons,
        key=lambda row: (int(row["amount_cents"]), -int(row["threshold_cents"]), -int(row["id"])),
    )


def list_coupons(conn, email, merchandise):
    rows = conn.execute("select * from coupons where enabled = 1").fetchall()
    open_orders = 0
    if email:
        open_orders = conn.execute(
            "select count(*) as n from orders where email = ? and status != 'cancelled'",
            (email,),
        ).fetchone()["n"]
    found = []
    for coupon in rows:
        if merchandise < coupon["threshold_cents"]:
            continue
        if coupon["kind"] == "public":
            found.append(coupon)
        elif coupon["kind"] == "first" and open_orders == 0:
            found.append(coupon)
        elif coupon["kind"] not in {"public", "first"}:
            granted = conn.execute(
                "select 1 as ok from coupon_grants where email = ? and coupon_id = ?",
                (email, coupon["id"]),
            ).fetchone()
            if granted:
                found.append(coupon)
    return found


def _lock_balance(conn, email):
    conn.execute(
        """
        insert into balances (email, available_cents) values (?, 0)
        on conflict(email) do update set available_cents = available_cents
        """,
        (email,),
    )
    return conn.execute(
        "select available_cents from balances where email = ?",
        (email,),
    ).fetchone()["available_cents"]


def _bind_referrer(conn, email, referrer):
    conn.execute(
        "insert into accounts (email, password_hash, referrer_email) values (?, null, null) on conflict(email) do nothing",
        (email,),
    )
    if not referrer or referrer == email:
        current = conn.execute("select referrer_email from accounts where email = ?", (email,)).fetchone()
        return current["referrer_email"] if current and current["referrer_email"] != email else None
    known = conn.execute("select email from accounts where email = ?", (referrer,)).fetchone()
    current = conn.execute("select referrer_email from accounts where email = ?", (email,)).fetchone()
    bound = current["referrer_email"] if current else None
    if bound:
        return None if bound == email else bound
    if known is None:
        return None
    conn.execute("update accounts set referrer_email = ? where email = ?", (referrer, email))
    return referrer


def place_order(
    conn,
    promos,
    outbox,
    *,
    lines,
    submit_id,
    email,
    name,
    address,
    city,
    region,
    postal,
    ship_country,
    phone,
    currency,
    units,
    minor_units,
    use_balance,
    coupon_id,
    referrer,
    gift_sku="",
    returning=False,
    hold=None,
):
    email = (email or "").strip().lower()
    ship_country = (ship_country or "").strip().upper()
    referrer = (referrer or "").strip().lower() or None
    fields = {
        "email": email,
        "name": name,
        "address": address,
        "city": city,
        "region": region,
        "postal": postal,
        "ship_country": ship_country,
        "phone": phone,
    }
    with email_lock(email or "anonymous"):
        conn.execute("BEGIN IMMEDIATE")
        try:
            if submit_id:
                existing = conn.execute(
                    "select id from orders where submit_id = ?",
                    (submit_id,),
                ).fetchone()
                if existing:
                    conn.rollback()
                    return existing["id"]
            missing = [key for key in REQUIRED if not str(fields[key] or "").strip()]
            if email and "@" not in email and "email" not in missing:
                missing.append("email")
            if missing:
                raise CheckoutError("fields", fields=missing)
            if not lines:
                raise CheckoutError("empty")
            priced, merchandise = priced_lines(
                conn, lines, gift_sku=gift_sku, email=email, returning=returning, hold=hold
            )
            needed = {}
            for line in priced:
                parent = stock_parent(line["sku"])
                needed[parent] = needed.get(parent, 0) + line["qty"]
            for parent, qty in needed.items():
                row = conn.execute("select stock from products where sku = ?", (parent,)).fetchone()
                if row is None or row["stock"] < qty:
                    raise CheckoutError("stock", sku=parent)
            eligible = list_coupons(conn, email, merchandise)
            coupon = None
            if coupon_id:
                try:
                    coupon = allowed_coupon(conn, email, merchandise, coupon_id)
                except CheckoutError as exc:
                    if exc.code != "coupon":
                        raise
                    coupon = None
            if coupon is None:
                coupon = best_coupon(eligible)
            available = _lock_balance(conn, email) if use_balance else 0
            bill = build_quote(
                promos,
                merchandise_cents=merchandise,
                ship_country=ship_country,
                units=units,
                currency=currency,
                minor_units=minor_units,
                coupon_cents=coupon["amount_cents"] if coupon else 0,
                coupon_threshold_cents=coupon["threshold_cents"] if coupon else 0,
                balance_cents=available,
                use_balance=use_balance,
            )
            bound = _bind_referrer(conn, email, referrer)
            base = max(0, merchandise - bill.discount_cents - bill.coupon_cents)
            own, direct = rebate(
                base_cents=base,
                self_rate=promos["self_rate"],
                direct_rate=promos["direct_rate"],
                referrer=bound,
                buyer=email,
            )
            for line in priced:
                item_id = int(line.get("campaign_item_id") or 0)
                if not item_id:
                    continue
                conn.execute(
                    "update campaign_items set stock = stock - ? where id = ? and stock >= ?",
                    (line["qty"], item_id, line["qty"]),
                )
                changed = conn.execute("select changes() as n").fetchone()["n"]
                if changed != 1:
                    raise CheckoutError("stock", sku=stock_parent(line["sku"]))
            for parent, qty in needed.items():
                conn.execute(
                    "update products set stock = stock - ? where sku = ?",
                    (qty, parent),
                )
            if bill.balance_cents:
                conn.execute(
                    "update balances set available_cents = available_cents - ? where email = ?",
                    (bill.balance_cents, email),
                )
            cursor = conn.execute(
                """
                insert into orders (
                    submit_id, email, status, currency, units_per_usd,
                    merchandise_cents, discount_cents, coupon_cents, coupon_id,
                    shipping_cents, balance_cents, due_cents, due_local,
                    ship_country, ship_name, address, city, region, postal, phone,
                    referrer_email, self_rebate_cents, direct_rebate_cents, created_at
                ) values (?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    submit_id, email, currency, units,
                    merchandise, bill.discount_cents, bill.coupon_cents,
                    coupon["id"] if coupon else None,
                    bill.shipping_cents, bill.balance_cents, bill.due_cents, bill.due_local,
                    ship_country, name.strip(), address.strip(), city.strip(),
                    region.strip(), postal.strip(), phone.strip(),
                    bound, own, direct, datetime.now(timezone.utc).isoformat(),
                ),
            )
            order_id = cursor.lastrowid
            for line in priced:
                conn.execute(
                    """
                    insert into order_lines (order_id, sku, price_cents, qty, campaign_item_id)
                    values (?, ?, ?, ?, ?)
                    """,
                    (order_id, line["sku"], line["price_cents"], line["qty"], int(line.get("campaign_item_id") or 0)),
                )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback()
            existing = conn.execute(
                "select id from orders where submit_id = ?",
                (submit_id,),
            ).fetchone()
            if existing:
                return existing["id"]
            raise
        except Exception:
            conn.rollback()
            raise
    outbox.send(
        email,
        "Order",
        f"order {order_id} {bill.due_local} {currency}",
    )
    return order_id


def cancel_order(conn, order_id):
    conn.execute("BEGIN IMMEDIATE")
    try:
        order = conn.execute("select * from orders where id = ?", (order_id,)).fetchone()
        if order is None or order["status"] != "pending":
            conn.rollback()
            return False
        lines = conn.execute(
            "select sku, qty, campaign_item_id from order_lines where order_id = ?",
            (order_id,),
        ).fetchall()
        for line in lines:
            conn.execute(
                "update products set stock = stock + ? where sku = ?",
                (line["qty"], stock_parent(line["sku"])),
            )
            if line["campaign_item_id"]:
                conn.execute(
                    "update campaign_items set stock = stock + ? where id = ?",
                    (line["qty"], line["campaign_item_id"]),
                )
        if order["balance_cents"]:
            conn.execute(
                "update balances set available_cents = available_cents + ? where email = ?",
                (order["balance_cents"], order["email"]),
            )
        conn.execute(
            """
            update orders
            set status = 'cancelled', self_rebate_cents = 0, direct_rebate_cents = 0
            where id = ?
            """,
            (order_id,),
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise



def expire_pending_orders(conn, minutes=30, now=None):
    """Cancel unpaid pending orders older than minutes and release stock."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=int(minutes))
    rows = conn.execute(
        "select id, created_at from orders where status = 'pending'"
    ).fetchall()
    cancelled = []
    for row in rows:
        raw = (row["created_at"] or "").strip()
        if not raw:
            continue
        try:
            created = datetime.fromisoformat(raw)
        except ValueError:
            continue
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created > cutoff:
            continue
        if cancel_order(conn, row["id"]):
            cancelled.append(row["id"])
    return cancelled

def issue_reset(conn, outbox, email, now=None):
    email = (email or "").strip().lower()
    account = conn.execute("select email from accounts where email = ?", (email,)).fetchone()
    if account is None:
        return None
    now = now or datetime.now(timezone.utc)
    token = secrets.token_urlsafe(24)
    expires = (now + timedelta(minutes=30)).isoformat()
    conn.execute(
        "insert into password_resets (token, email, expires_at) values (?, ?, ?)",
        (token, email, expires),
    )
    outbox.send(email, "Reset", f"/reset-password?token={token}")
    return token


def apply_reset(conn, token, password, now=None):
    now = now or datetime.now(timezone.utc)
    row = conn.execute("select * from password_resets where token = ?", (token,)).fetchone()
    if row is None:
        return False
    expires = datetime.fromisoformat(row["expires_at"])
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= now:
        return False
    conn.execute(
        "update accounts set password_hash = ? where email = ?",
        (hash_password(password), row["email"]),
    )
    conn.execute("delete from password_resets where token = ?", (token,))
    return True
