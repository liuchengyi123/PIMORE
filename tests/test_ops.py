import pytest
from fastapi.testclient import TestClient

from shop.app import create_app
from shop.i18n import UI
from shop.ops import board, note_paid
from shop.staff import save_staff


@pytest.fixture()
def client():
    return TestClient(create_app(units_per_usd=150, db_path=":memory:"))


def test_board_counts_visits_in_each_language_and_hides_from_guests(client):
    denied = client.get("/admin/stats")
    assert denied.status_code == 401
    assert client.get("/?country=DE").status_code == 200
    assert client.get("/p/drain-rack?country=ES").status_code == 200
    added = client.post(
        "/cart/add",
        data={"sku": "drain-rack", "qty": "2", "country": "FR"},
        follow_redirects=False,
    )
    assert added.status_code == 303
    conn = client.app.state.db
    order_id = conn.execute(
        """
        insert into orders (
            submit_id, email, status, currency, units_per_usd, due_cents, due_local, ship_country
        ) values ('ops-1', 'buyer@harbor.test', 'pending', 'USD', 1, 1200, 1200, 'JP')
        """
    ).lastrowid
    conn.execute(
        "insert into order_lines (order_id, sku, price_cents, qty) values (?, 'drain-rack', 1200, 1)",
        (order_id,),
    )
    order = conn.execute("select * from orders where id = ?", (order_id,)).fetchone()
    conn.execute("update orders set status = 'paid' where id = ?", (order_id,))
    note_paid(conn, order)
    data = board(conn, 1)
    assert data["pages"] >= 2
    assert data["visitors"] >= 1
    assert data["products"] >= 1
    assert data["carts"] == 1
    assert data["paid_orders"] == 1
    assert data["paid_cents"] == 1200
    assert data["life_paid"] == 1
    assert data["life_cents"] == 1200
    langs = {row["code"] for row in data["langs"]}
    assert {"de", "es"} <= langs
    item = next(row for row in data["items"] if row["sku"] == "drain-rack")
    assert item["views"] >= 1
    assert item["carts"] == 2
    assert item["sold"] == 1
    sold = next(row for row in data["sold"] if row["sku"] == "drain-rack")
    assert sold["qty"] == 1
    save_staff(conn, "admin", "secret-pass", "admin")
    client.post("/admin/login", data={"username": "admin", "password": "secret-pass"})
    page = client.get("/admin/stats?days=1")
    assert page.status_code == 200
    assert "数据" in page.text
    assert "德语" in page.text
    assert "西语" in page.text
    assert "drain-rack" in page.text
    assert "$12.00" in page.text
    home = client.get("/")
    assert 'class="mall-cats"' not in home.text
    spanish = client.get("/?country=ES")
    assert "Seguir viendo" in spanish.text
    assert "Para ti" in spanish.text
    for code in ("en", "es", "de", "fr", "pt", "ja"):
        assert UI[code]["recent"]
        assert UI[code]["for_you"]
