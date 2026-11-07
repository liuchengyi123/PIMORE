from shop.db import connect
from shop.seed import seed


def test_seed_has_36_products_and_known_prices():
    db = connect()
    seed(db)
    rows = db.execute("select count(*) as n from products").fetchone()["n"]
    assert rows == 36
    rack = db.execute(
        "select price_cents, stock from products where sku='drain-rack'"
    ).fetchone()
    assert rack["price_cents"] == 1200
    assert rack["stock"] == 100
    clip = db.execute(
        "select price_cents from products where sku='binder-clip'"
    ).fetchone()
    assert clip["price_cents"] == 300
