"""Pre-pay 10% spin and one free-order coupon per customer.

The spin always awards the configured percent. The six slices are presentation.
The free-order row is unique per email and is created only for the customer's
latest paid order at the moment they smash. Later paid orders do not open a
second coupon; they count toward the five stamps when they clear the amount.
"""

import json
import secrets
from datetime import datetime, timedelta, timezone

KEY = "lucky_draw"
DEFAULTS = {
    "enabled": 1,
    "percent": 10,
    "hours": 6,
    "browse_minutes": 3,
    "stamps_needed": 5,
    "window_days": 60,
    "return_days": 30,
}


def ensure(conn):
    conn.execute(
        """
        create table if not exists lucky_spins (
            token text primary key,
            email text not null default '',
            percent integer not null,
            won_at text not null,
            expires_at text not null,
            order_id integer not null default 0,
            browse_kept integer not null default 0,
            pay_kept integer not null default 0
        )
        """
    )
    conn.execute(
        """
        create table if not exists lucky_frees (
            email text primary key,
            order_id integer not null,
            amount_cents integer not null,
            stamps integer not null default 0,
            status text not null,
            created_at text not null,
            deadline_at text not null,
            hold_until text not null default '',
            reminded integer not null default 0
        )
        """
    )
    conn.execute(
        """
        create table if not exists lucky_stamps (
            id integer primary key,
            owner_email text not null,
            source text not null,
            friend_email text not null default '',
            order_id integer not null,
            created_at text not null,
            unique(owner_email, order_id)
        )
        """
    )
    conn.execute("create index if not exists lucky_spins_email on lucky_spins (email)")
    conn.execute("create index if not exists lucky_stamps_owner on lucky_stamps (owner_email)")


def utcnow():
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(text):
    raw = str(text or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        found = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if found.tzinfo is None:
        found = found.replace(tzinfo=timezone.utc)
    return found.astimezone(timezone.utc).replace(microsecond=0)


def _clip(value, low, high, fallback):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(low, min(high, number))


def load_settings(conn):
    ensure(conn)
    row = conn.execute("select value from settings where key = ?", (KEY,)).fetchone()
    found = dict(DEFAULTS)
    if row is not None:
        try:
            raw = json.loads(row["value"] or "{}")
        except (json.JSONDecodeError, TypeError):
            raw = {}
        if isinstance(raw, dict):
            found.update(raw)
    found["enabled"] = 1 if int(found.get("enabled") or 0) else 0
    found["percent"] = _clip(found.get("percent"), 1, 90, DEFAULTS["percent"])
    found["hours"] = _clip(found.get("hours"), 1, 72, DEFAULTS["hours"])
    found["browse_minutes"] = _clip(found.get("browse_minutes"), 1, 120, DEFAULTS["browse_minutes"])
    found["stamps_needed"] = _clip(found.get("stamps_needed"), 1, 20, DEFAULTS["stamps_needed"])
    found["window_days"] = _clip(found.get("window_days"), 1, 365, DEFAULTS["window_days"])
    found["return_days"] = _clip(found.get("return_days"), 0, 120, DEFAULTS["return_days"])
    return found


def save_settings(conn, raw):
    current = load_settings(conn)
    current["enabled"] = 1 if str(raw.get("enabled") or "") in {"1", "on", "true"} else 0
    for key, low, high in (
        ("percent", 1, 90),
        ("hours", 1, 72),
        ("browse_minutes", 1, 120),
        ("stamps_needed", 1, 20),
        ("window_days", 1, 365),
        ("return_days", 0, 120),
    ):
        current[key] = _clip(raw.get(key), low, high, current[key])
    conn.execute(
        "insert into settings (key, value) values (?, ?) on conflict(key) do update set value = excluded.value",
        (KEY, json.dumps(current)),
    )
    return current


def paid_goods(order):
    return max(
        0,
        int(order["merchandise_cents"] or 0)
        - int(order["discount_cents"] or 0)
        - int(order["coupon_cents"] or 0),
    )


def _email(value):
    return str(value or "").strip().lower()


def actor_email(conn, token, buyer):
    """Prefer the signed-in shopper. A guest keeps the email bound at checkout."""
    ensure(conn)
    buyer = _email(buyer)
    row = _spin_row(conn, token)
    bound = _email(row["email"]) if row is not None else ""
    if buyer and bound and buyer != bound:
        return buyer
    return buyer or bound


def _spin_row(conn, token):
    token = str(token or "").strip()
    if not token:
        return None
    return conn.execute("select * from lucky_spins where token = ?", (token,)).fetchone()


def _email_spin(conn, email):
    email = _email(email)
    if not email:
        return None
    return conn.execute(
        "select * from lucky_spins where email = ? order by won_at desc limit 1",
        (email,),
    ).fetchone()


def lookup_off(conn, token, email, merchandise_cents, now=None):
    """Uncapped percent off, only while the spin is unused and unexpired."""
    settings = load_settings(conn)
    if not settings["enabled"]:
        return 0
    row = _spin_row(conn, token)
    if row is None or int(row["order_id"] or 0):
        return 0
    moment = now or utcnow()
    expires = parse_iso(row["expires_at"])
    if expires is None or expires <= moment:
        return 0
    bound = _email(row["email"])
    buyer = _email(email)
    if bound and buyer and bound != buyer:
        return 0
    if buyer and _email_spin(conn, buyer) and _email_spin(conn, buyer)["token"] != row["token"]:
        return 0
    goods = max(0, int(merchandise_cents or 0))
    return goods * int(row["percent"]) // 100


def spin(conn, token, email="", now=None):
    settings = load_settings(conn)
    moment = now or utcnow()
    buyer = _email(email)
    if not settings["enabled"]:
        return ""
    existing = _spin_row(conn, token)
    if existing is not None:
        return existing["token"]
    if buyer and _email_spin(conn, buyer) is not None:
        return ""
    fresh = secrets.token_urlsafe(18)
    expires = moment + timedelta(hours=settings["hours"])
    conn.execute(
        """
        insert into lucky_spins (token, email, percent, won_at, expires_at)
        values (?, ?, ?, ?, ?)
        """,
        (fresh, buyer, settings["percent"], iso(moment), iso(expires)),
    )
    return fresh


def consume_spin(conn, token, email, order_id):
    row = _spin_row(conn, token)
    if row is None or int(row["order_id"] or 0):
        return False
    conn.execute(
        "update lucky_spins set email = ?, order_id = ? where token = ? and order_id = 0",
        (_email(email), int(order_id), row["token"]),
    )
    return True


def mark_kept(conn, token, kind):
    column = "browse_kept" if kind == "browse" else "pay_kept" if kind == "pay" else ""
    if not column:
        return False
    row = _spin_row(conn, token)
    if row is None or int(row[column] or 0):
        return False
    conn.execute(f"update lucky_spins set {column} = 1 where token = ?", (row["token"],))
    return True


def _free(conn, email):
    email = _email(email)
    if not email:
        return None
    return conn.execute("select * from lucky_frees where email = ?", (email,)).fetchone()


def latest_paid_id(conn, email):
    email = _email(email)
    if not email:
        return 0
    row = conn.execute(
        """
        select id from orders
        where email = ? and status in ('paid', 'shipped')
        order by id desc limit 1
        """,
        (email,),
    ).fetchone()
    return int(row["id"]) if row else 0


def smash(conn, email, order_id, now=None):
    """Create the one free-order row, only for this person's latest paid order."""
    settings = load_settings(conn)
    buyer = _email(email)
    moment = now or utcnow()
    if not settings["enabled"] or not buyer:
        return {"ok": False, "code": "disabled"}
    order = conn.execute("select * from orders where id = ?", (int(order_id),)).fetchone()
    if order is None or _email(order["email"]) != buyer or order["status"] not in {"paid", "shipped"}:
        return {"ok": False, "code": "no_order"}
    latest = latest_paid_id(conn, buyer)
    if int(order["id"]) != latest:
        return {"ok": False, "code": "not_latest"}
    current = _free(conn, buyer)
    if current is not None:
        if current["status"] == "open" and int(current["order_id"]) == int(order["id"]):
            return {"ok": True, "code": "already", "free": _public_free(current, settings)}
        return {"ok": False, "code": "already"}
    amount = paid_goods(order)
    deadline = moment + timedelta(days=settings["window_days"])
    conn.execute(
        """
        insert into lucky_frees (
            email, order_id, amount_cents, stamps, status, created_at, deadline_at
        ) values (?, ?, ?, 0, 'open', ?, ?)
        """,
        (buyer, int(order["id"]), amount, iso(moment), iso(deadline)),
    )
    created = _free(conn, buyer)
    return {"ok": True, "code": "won", "free": _public_free(created, settings)}


def _public_free(row, settings):
    if row is None:
        return None
    return {
        "email": row["email"],
        "order_id": int(row["order_id"]),
        "amount_cents": int(row["amount_cents"]),
        "stamps": int(row["stamps"] or 0),
        "needed": int(settings["stamps_needed"]),
        "status": row["status"],
        "created_at": row["created_at"],
        "deadline_at": row["deadline_at"],
        "hold_until": row["hold_until"] or "",
        "window_days": int(settings["window_days"]),
        "return_days": int(settings["return_days"]),
    }


def _recount(conn, email, settings, moment):
    row = _free(conn, email)
    if row is None or row["status"] != "open":
        return
    count = conn.execute(
        "select count(*) as n from lucky_stamps where owner_email = ?",
        (email,),
    ).fetchone()["n"]
    conn.execute("update lucky_frees set stamps = ? where email = ?", (int(count), email))
    deadline = parse_iso(row["deadline_at"])
    if deadline is not None and moment > deadline:
        return
    if int(count) >= int(settings["stamps_needed"]):
        hold = moment + timedelta(days=int(settings["return_days"]))
        conn.execute(
            """
            update lucky_frees
            set status = 'held', hold_until = ?
            where email = ? and status = 'open'
            """,
            (iso(hold), email),
        )


def _add_stamp(conn, owner, source, friend, order_id, moment):
    try:
        conn.execute(
            """
            insert into lucky_stamps (owner_email, source, friend_email, order_id, created_at)
            values (?, ?, ?, ?, ?)
            """,
            (owner, source, friend, int(order_id), iso(moment)),
        )
        return True
    except Exception:
        return False


def _retarget(conn, buyer, order, moment, settings):
    """Keep the single coupon on this person's latest paid order."""
    row = _free(conn, buyer)
    if row is None or row["status"] != "open":
        return False
    if int(order["id"]) <= int(row["order_id"]):
        return False
    new_amount = paid_goods(order)
    if new_amount <= 0:
        return False
    previous = conn.execute("select * from orders where id = ?", (row["order_id"],)).fetchone()
    if previous is not None and paid_goods(previous) >= new_amount:
        _add_stamp(conn, buyer, "self", "", previous["id"], moment)
    conn.execute(
        """
        update lucky_frees
        set order_id = ?, amount_cents = ?
        where email = ? and status = 'open'
        """,
        (int(order["id"]), new_amount, buyer),
    )
    _recount(conn, buyer, settings, moment)
    return True


def _stamp_open(conn, owner, order, moment):
    row = _free(conn, owner)
    if row is None or row["status"] != "open":
        return None
    deadline = parse_iso(row["deadline_at"])
    if deadline is not None and moment > deadline:
        return None
    if int(order["id"]) == int(row["order_id"]):
        return None
    if paid_goods(order) < int(row["amount_cents"]):
        return None
    return row


def on_paid(conn, order_id, now=None):
    ensure(conn)
    settings = load_settings(conn)
    moment = now or utcnow()
    sweep(conn, moment)
    order = conn.execute("select * from orders where id = ?", (int(order_id),)).fetchone()
    if order is None or order["status"] not in {"paid", "shipped"}:
        settle(conn, moment)
        return
    buyer = _email(order["email"])
    referrer = _email(order["referrer_email"])
    _retarget(conn, buyer, order, moment, settings)
    if referrer and referrer != buyer:
        host = _stamp_open(conn, referrer, order, moment)
        if host is not None:
            taken = conn.execute(
                """
                select id from lucky_stamps
                where owner_email = ? and source = 'friend' and friend_email = ?
                """,
                (referrer, buyer),
            ).fetchone()
            if taken is None:
                _add_stamp(conn, referrer, "friend", buyer, order["id"], moment)
                _recount(conn, referrer, settings, moment)
    own = _stamp_open(conn, buyer, order, moment)
    if own is not None:
        _add_stamp(conn, buyer, "self", "", order["id"], moment)
        _recount(conn, buyer, settings, moment)
    settle(conn, moment)


def on_refund(conn, order_id, now=None):
    ensure(conn)
    moment = now or utcnow()
    order = conn.execute("select * from orders where id = ?", (int(order_id),)).fetchone()
    if order is None:
        return
    buyer = _email(order["email"])
    owned = _free(conn, buyer)
    if owned is not None and int(owned["order_id"]) == int(order["id"]) and owned["status"] in {"open", "held"}:
        conn.execute("update lucky_frees set status = 'void' where email = ?", (buyer,))
    stamps = conn.execute(
        "select owner_email from lucky_stamps where order_id = ?",
        (int(order_id),),
    ).fetchall()
    if stamps:
        conn.execute("delete from lucky_stamps where order_id = ?", (int(order_id),))
        settings = load_settings(conn)
        for stamp in stamps:
            owner = stamp["owner_email"]
            row = _free(conn, owner)
            if row is None:
                continue
            count = conn.execute(
                "select count(*) as n from lucky_stamps where owner_email = ?",
                (owner,),
            ).fetchone()["n"]
            if row["status"] == "held" and int(count) < int(settings["stamps_needed"]):
                conn.execute(
                    "update lucky_frees set stamps = ?, status = 'open', hold_until = '' where email = ?",
                    (int(count), owner),
                )
            elif row["status"] == "open":
                conn.execute(
                    "update lucky_frees set stamps = ? where email = ?",
                    (int(count), owner),
                )
    sweep(conn, moment)


def sweep(conn, now=None):
    moment = now or utcnow()
    conn.execute(
        """
        update lucky_frees set status = 'void'
        where status = 'open' and deadline_at < ?
        """,
        (iso(moment),),
    )


def _credit(conn, email, cents):
    cents = int(cents or 0)
    if not email or cents <= 0:
        return
    conn.execute(
        """
        insert into balances (email, available_cents) values (?, ?)
        on conflict(email) do update set available_cents = available_cents + excluded.available_cents
        """,
        (email, cents),
    )


def settle(conn, now=None):
    moment = now or utcnow()
    sweep(conn, moment)
    due = conn.execute(
        """
        select * from lucky_frees
        where status = 'held' and hold_until != '' and hold_until <= ?
        """,
        (iso(moment),),
    ).fetchall()
    for row in due:
        order = conn.execute("select status from orders where id = ?", (row["order_id"],)).fetchone()
        if order is None or order["status"] not in {"paid", "shipped"}:
            conn.execute("update lucky_frees set status = 'void' where email = ? and status = 'held'", (row["email"],))
            continue
        latest = latest_paid_id(conn, row["email"])
        # Stamps are newer orders on purpose. Payout still requires the bound
        # order to be a real paid order. A second free coupon is never created.
        if not latest:
            continue
        conn.execute(
            "update lucky_frees set status = 'paid' where email = ? and status = 'held'",
            (row["email"],),
        )
        changed = conn.execute("select changes() as n").fetchone()["n"]
        if changed == 1:
            _credit(conn, row["email"], row["amount_cents"])


def void_free(conn, email):
    email = _email(email)
    row = _free(conn, email)
    if row is None or row["status"] not in {"open", "held"}:
        return False
    conn.execute("update lucky_frees set status = 'void' where email = ?", (email,))
    return True


def snapshot(conn, token, email, now=None):
    settings = load_settings(conn)
    moment = now or utcnow()
    sweep(conn, moment)
    settle(conn, moment)
    buyer = _email(email)
    row = _spin_row(conn, token)
    if row is None and buyer:
        row = _email_spin(conn, buyer)
    spin_out = None
    if row is not None:
        expires = parse_iso(row["expires_at"])
        left = int((expires - moment).total_seconds()) if expires else 0
        spin_out = {
            "percent": int(row["percent"]),
            "expires_at": row["expires_at"],
            "seconds_left": max(0, left),
            "used": bool(int(row["order_id"] or 0)),
            "browse_kept": int(row["browse_kept"] or 0),
            "pay_kept": int(row["pay_kept"] or 0),
            "live": left > 0 and not int(row["order_id"] or 0),
        }
    offer = bool(settings["enabled"]) and row is None and not (buyer and _email_spin(conn, buyer))
    free_row = _free(conn, buyer)
    egg = None
    if settings["enabled"] and buyer and free_row is None:
        latest = latest_paid_id(conn, buyer)
        if latest:
            egg = {"order_id": latest}
    return {
        "enabled": bool(settings["enabled"]),
        "percent": settings["percent"],
        "hours": settings["hours"],
        "browse_minutes": settings["browse_minutes"],
        "stamps_needed": settings["stamps_needed"],
        "window_days": settings["window_days"],
        "return_days": settings["return_days"],
        "offer_spin": offer,
        "spin": spin_out,
        "free": _public_free(free_row, settings),
        "egg": egg,
    }


def _due_soon(deadline):
    moment = parse_iso(deadline)
    if moment is None:
        return False
    left = (moment - utcnow()).total_seconds()
    return 0 < left <= 10 * 24 * 3600


def admin_rows(conn):
    settings = load_settings(conn)
    sweep(conn)
    settle(conn)
    frees = []
    rows = conn.execute("select * from lucky_frees order by created_at desc limit 200").fetchall()
    for row in rows:
        latest = latest_paid_id(conn, row["email"])
        stamps = conn.execute(
            """
            select source, friend_email, order_id, created_at
            from lucky_stamps where owner_email = ? order by id
            """,
            (row["email"],),
        ).fetchall()
        frees.append(
            {
                "email": row["email"],
                "order_id": int(row["order_id"]),
                "amount_cents": int(row["amount_cents"]),
                "stamps": int(row["stamps"] or 0),
                "needed": settings["stamps_needed"],
                "status": row["status"],
                "created_at": row["created_at"],
                "deadline_at": row["deadline_at"],
                "hold_until": row["hold_until"] or "",
                "still_latest": int(row["order_id"]) == latest,
                "latest_order_id": latest,
                "stamp_rows": [dict(item) for item in stamps],
                "remind": row["status"] == "open" and int(row["stamps"] or 0) < settings["stamps_needed"] and _due_soon(row["deadline_at"]),
            }
        )
    spins = conn.execute(
        "select * from lucky_spins order by won_at desc limit 50"
    ).fetchall()
    return settings, frees, spins
