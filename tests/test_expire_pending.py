from datetime import datetime, timedelta, timezone

from shop.checkout import expire_pending_orders, place_order, Outbox
from shop.db import connect
from shop.seed import seed


PROMOS = {
    "free_shipping_cents": 3900,
    "tiers": [[3000, 400], [6000, 800]],
    "shipping": {"USCA": 600, "EU": 800, "JP": 700, "MXBR": 900},
    "self_rate": 0.05,
    "direct_rate": 0.1,
}


def _place(conn, submit_id, qty=2):
    return place_order(
        conn,
        PROMOS,
        Outbox(),
        lines=[{"sku": "oil-sprayer", "qty": qty}],
        submit_id=submit_id,
        email="buyer@example.com",
        name="Buyer",
        address="1 St",
        city="Austin",
        region="TX",
        postal="78701",
        ship_country="US",
        phone="15551212",
        currency="USD",
        units=1.0,
        minor_units=2,
        use_balance=False,
        coupon_id=None,
        referrer="",
    )


def test_expire_pending_releases_stock(tmp_path):
    conn = connect(str(tmp_path / "shop.sqlite"))
    seed(conn)
    before = conn.execute("select stock from products where sku='oil-sprayer'").fetchone()["stock"]
    order_id = _place(conn, "s1", qty=2)
    assert conn.execute("select stock from products where sku='oil-sprayer'").fetchone()["stock"] == before - 2
    order = conn.execute("select status, created_at from orders where id=?", (order_id,)).fetchone()
    assert order["status"] == "pending"
    assert order["created_at"]
    old = (datetime.now(timezone.utc) - timedelta(minutes=45)).isoformat()
    conn.execute("update orders set created_at=? where id=?", (old, order_id))
    conn.commit()
    assert expire_pending_orders(conn, minutes=30) == [order_id]
    assert conn.execute("select status from orders where id=?", (order_id,)).fetchone()["status"] == "cancelled"
    assert conn.execute("select stock from products where sku='oil-sprayer'").fetchone()["stock"] == before


def test_expire_skips_fresh_pending(tmp_path):
    conn = connect(str(tmp_path / "shop.sqlite"))
    seed(conn)
    before = conn.execute("select stock from products where sku='oil-sprayer'").fetchone()["stock"]
    order_id = _place(conn, "s2", qty=1)
    assert expire_pending_orders(conn, minutes=30) == []
    assert conn.execute("select status from orders where id=?", (order_id,)).fetchone()["status"] == "pending"
    assert conn.execute("select stock from products where sku='oil-sprayer'").fetchone()["stock"] == before - 1
