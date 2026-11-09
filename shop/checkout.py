"""Checkout pricing shared by place_order and POST /api/checkout/quote.

Gift fields are three different things. Do not merge them:

gift_sku
    Cookie ``gift_sku`` (set by add-to-cart when ``gift=1``). A catalog line
    that ``priced_lines`` prices at 0 only when qty is 1 and the list price
    is between 50 and 200 cents inclusive. It is not a message and not
    wrapping. Cleared after a successful checkout. The quote prices this
    cookie; a gift_sku in the JSON body is ignored so a client cannot zero
    an arbitrary line.

gift_message
    Note stored on ``orders.gift_message`` (max 200 characters). The HTML
    checkout form still posts it as ``gift``. The quote body field is
    ``gift_message`` (``gift`` is accepted as a fallback). No price effect.
    Never write gift_wrap or gift_sku into this column.

gift_wrap
    Boolean the shopper toggles for wrapping. No fee in this version
    (0 cents) and no orders column. The quote echoes it so the client can
    keep the toggle. It does not change gift_message or gift_sku.
"""

import hashlib
import json
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta, timezone

from shop.address_format import required_keys
from shop.campaigns import price_for
from shop.pricing import quote
from shop.rewards import rebate
from shop.tax import estimate_tax_cents

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


# Legacy orders.speed column. New orders store this one value. It is not a
# shopper choice and it does not change price or the delivery window.
ORDER_SPEED = "standard"

_TRUE_VALUES = {"1", "true", "yes", "on"}


def shipping_cents():
    """Single shipping price. Always 0."""
    return 0


def as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return int(value) != 0
    return str(value or "").strip().lower() in _TRUE_VALUES


def build_quote(promos, *, merchandise_cents, ship_country, units, currency, minor_units, coupon_cents=0, coupon_threshold_cents=0, balance_cents=0, use_balance=False, lucky_off_cents=0):
    # One shipping price: 0. free_shipping_cents=0 also waives any promo table.
    _ = (ship_country, promos.get("free_shipping_cents"), promos.get("shipping"))
    return quote(
        merchandise_cents=merchandise_cents,
        tiers=promos["tiers"],
        coupon_cents=coupon_cents,
        coupon_threshold_cents=coupon_threshold_cents,
        free_shipping_cents=0,
        shipping_cents=shipping_cents(),
        balance_cents=balance_cents,
        use_balance=use_balance,
        units_per_usd=units,
        minor_units=minor_units,
        lucky_off_cents=lucky_off_cents,
    )


def settle_checkout(
    promos,
    *,
    merchandise_cents,
    ship_country,
    region,
    units,
    currency,
    minor_units,
    coupon,
    balance_cents,
    use_balance,
    lucky_off_cents,
):
    """One money path for place_order and the quote API.

    Taxable base is goods after discounts and coupons, plus shipping.
    Shipping is 0. tax_cents is not folded into due_cents (see shop.tax).
    """
    bill = build_quote(
        promos,
        merchandise_cents=merchandise_cents,
        ship_country=ship_country,
        units=units,
        currency=currency,
        minor_units=minor_units,
        coupon_cents=coupon["amount_cents"] if coupon else 0,
        coupon_threshold_cents=coupon["threshold_cents"] if coupon else 0,
        balance_cents=balance_cents,
        use_balance=use_balance,
        lucky_off_cents=lucky_off_cents,
    )
    goods_after = max(0, int(merchandise_cents) - int(bill.discount_cents) - int(bill.coupon_cents))
    taxable = goods_after + int(bill.shipping_cents)
    tax = estimate_tax_cents(taxable, ship_country, region)
    return bill, taxable, tax


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


def coupon_id_from_code(conn, code):
    text = str(code or "").strip()
    if not text:
        return None
    row = conn.execute(
        """
        select id from coupons
        where enabled = 1 and (lower(name) = lower(?) or lower(kind) = lower(?))
        order by id
        limit 1
        """,
        (text, text),
    ).fetchone()
    return int(row["id"]) if row else None


def resolve_coupon_request(conn, coupon_id, coupon_code):
    """Return (coupon_id, requested).

    None means the shopper did not ask. -1 means they asked for something
    that does not resolve, which place_order treats like a bad id and then
    falls through to the best eligible coupon.
    """
    code = str(coupon_code or "").strip()
    raw = "" if coupon_id is None else str(coupon_id).strip()
    asked = bool(raw) or bool(code)
    if raw:
        try:
            return int(coupon_id), True
        except (TypeError, ValueError):
            return -1, True
    if code:
        found = coupon_id_from_code(conn, code)
        return (found if found else -1), True
    return None, asked


def select_coupon(conn, email, merchandise, coupon_id, lucky_off_cents, coupon_requested):
    """Same coupon choice as place_order.

    A live lucky discount suppresses coupons. When the shopper still sent
    one, the quote reports ``coupon_blocked_by_lucky`` and charges no coupon.
    """
    if lucky_off_cents:
        blockers = ["coupon_blocked_by_lucky"] if coupon_requested else []
        return None, blockers
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
    return coupon, []


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


def _available_balance(conn, email):
    if not email:
        return 0
    row = conn.execute(
        "select available_cents from balances where email = ?",
        (email,),
    ).fetchone()
    return int(row["available_cents"]) if row else 0


def _gift_message(value):
    return str(value or "")[:200]


def _parent_need(priced):
    needed = {}
    for line in priced:
        parent = stock_parent(line["sku"])
        needed[parent] = needed.get(parent, 0) + line["qty"]
    return needed


def _short_parent(conn, needed):
    for parent, qty in needed.items():
        row = conn.execute("select stock from products where sku = ?", (parent,)).fetchone()
        if row is None or row["stock"] < qty:
            return parent
    return ""


def _quote_payload(
    *,
    ok,
    currency,
    lines,
    blockers,
    gift_message,
    gift_wrap,
    gift_sku,
    merchandise=0,
    shipping=0,
    discount=0,
    coupon_cents=0,
    tax=0,
    taxable=0,
    balance=0,
    due=0,
    due_local=0,
    coupon_id=None,
    sku="",
):
    body = {
        "ok": bool(ok),
        "subtotal": int(merchandise),
        "merchandise_cents": int(merchandise),
        "shipping_cents": int(shipping),
        "discount_cents": int(discount),
        "coupon_cents": int(coupon_cents),
        "tax_cents": int(tax),
        "taxable_cents": int(taxable),
        # Estimate only. due_cents / total are the amount charged today.
        "tax_estimate": True,
        "tax_included_in_due": False,
        "balance_cents": int(balance),
        "total": int(due),
        "due_cents": int(due),
        "due_local": int(due_local),
        "currency": currency or "USD",
        "lines": lines,
        "blockers": list(blockers),
        "gift_message": _gift_message(gift_message),
        "gift_wrap": bool(gift_wrap),
        "gift_sku": gift_sku or "",
        "coupon_id": int(coupon_id) if coupon_id else None,
    }
    if sku:
        body["sku"] = sku
    return body


def preview_checkout_quote(
    conn,
    promos,
    *,
    lines,
    email="",
    ship_country="",
    region="",
    currency="USD",
    units=1,
    minor_units=2,
    coupon_id=None,
    coupon_code="",
    use_balance=False,
    gift_sku="",
    gift_message="",
    gift_wrap=False,
    returning=False,
    hold=None,
    lucky_off_cents=0,
):
    """Price the cart the way place_order will, without writing an order.

    ``lines`` are the cart cookie lines (same source as POST /checkout).
    ``gift_sku`` is that cookie, not a body field. ``gift_message`` and
    ``gift_wrap`` are echoed and do not change the totals.
    """
    email = (email or "").strip().lower()
    ship_country = (ship_country or "").strip().upper()
    gift_sku = gift_sku or ""
    gift_message = _gift_message(gift_message)
    gift_wrap = as_bool(gift_wrap)
    use_balance = as_bool(use_balance)
    common = dict(
        currency=currency,
        gift_message=gift_message,
        gift_wrap=gift_wrap,
        gift_sku=gift_sku,
    )
    if units is None:
        return _quote_payload(ok=False, lines=[], blockers=["rate"], **common)
    if not lines:
        return _quote_payload(ok=False, lines=[], blockers=["empty"], **common)
    try:
        priced, merchandise = priced_lines(
            conn, lines, gift_sku=gift_sku, email=email, returning=returning, hold=hold
        )
    except CheckoutError as exc:
        return _quote_payload(
            ok=False, lines=[], blockers=[exc.code or "stock"], sku=exc.sku or "", **common
        )
    short = _short_parent(conn, _parent_need(priced))
    if short:
        return _quote_payload(ok=False, lines=[], blockers=["stock"], sku=short, **common)
    requested_id, requested = resolve_coupon_request(conn, coupon_id, coupon_code)
    try:
        coupon, blockers = select_coupon(
            conn, email, merchandise, requested_id, lucky_off_cents, requested
        )
    except CheckoutError as exc:
        return _quote_payload(
            ok=False, lines=[], blockers=[exc.code or "coupon"], sku=exc.sku or "", **common
        )
    available = _available_balance(conn, email) if use_balance else 0
    bill, taxable, tax = settle_checkout(
        promos,
        merchandise_cents=merchandise,
        ship_country=ship_country,
        region=region,
        units=units,
        currency=currency,
        minor_units=minor_units,
        coupon=coupon,
        balance_cents=available,
        use_balance=use_balance,
        lucky_off_cents=lucky_off_cents,
    )
    shown = [
        {
            "sku": line["sku"],
            "qty": line["qty"],
            "price_cents": line["price_cents"],
            "line_cents": int(line["price_cents"]) * int(line["qty"]),
        }
        for line in priced
    ]
    return _quote_payload(
        ok=True,
        lines=shown,
        blockers=blockers,
        merchandise=merchandise,
        shipping=bill.shipping_cents,
        discount=bill.discount_cents,
        coupon_cents=bill.coupon_cents,
        tax=tax,
        taxable=taxable,
        balance=bill.balance_cents,
        due=bill.due_cents,
        due_local=bill.due_local,
        coupon_id=coupon["id"] if coupon else None,
        **common,
    )


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
    lucky_off_cents=0,
    lucky_token="",
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
            missing = [key for key in required_keys(ship_country) if not str(fields[key] or "").strip()]
            if email and "@" not in email and "email" not in missing:
                missing.append("email")
            if missing:
                raise CheckoutError("fields", fields=missing)
            if not lines:
                raise CheckoutError("empty")
            priced, merchandise = priced_lines(
                conn, lines, gift_sku=gift_sku, email=email, returning=returning, hold=hold
            )
            needed = _parent_need(priced)
            short = _short_parent(conn, needed)
            if short:
                raise CheckoutError("stock", sku=short)
            coupon, _coupon_blockers = select_coupon(
                conn,
                email,
                merchandise,
                coupon_id,
                lucky_off_cents,
                bool(coupon_id),
            )
            available = _lock_balance(conn, email) if use_balance else 0
            bill, _taxable, tax = settle_checkout(
                promos,
                merchandise_cents=merchandise,
                ship_country=ship_country,
                region=region,
                units=units,
                currency=currency,
                minor_units=minor_units,
                coupon=coupon,
                balance_cents=available,
                use_balance=use_balance,
                lucky_off_cents=lucky_off_cents,
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
                    shipping_cents, tax_cents, balance_cents, due_cents, due_local,
                    ship_country, ship_name, address, city, region, postal, phone,
                    referrer_email, self_rebate_cents, direct_rebate_cents, created_at
                ) values (?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    submit_id, email, currency, units,
                    merchandise, bill.discount_cents, bill.coupon_cents,
                    coupon["id"] if coupon else None,
                    bill.shipping_cents, tax, bill.balance_cents, bill.due_cents, bill.due_local,
                    ship_country, name.strip(), address.strip(), city.strip(),
                    region.strip(), postal.strip(), phone.strip(),
                    bound, own, direct, datetime.now(timezone.utc).isoformat(),
                ),
            )
            order_id = cursor.lastrowid
            if lucky_off_cents and lucky_token:
                from shop.lucky import consume_spin
                consume_spin(conn, lucky_token, email, order_id)
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
