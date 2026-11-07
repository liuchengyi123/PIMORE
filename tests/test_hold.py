from fastapi.testclient import TestClient

from shop.app import create_app
from shop.checkout import priced_lines


def _client():
    return TestClient(create_app(units_per_usd=150, db_path=":memory:"))


def _newcomer(db):
    return db.execute(
        """
        select ci.sku, ci.price_cents, p.price_cents as regular
        from campaign_items ci
        join campaigns c on c.id = ci.campaign_id
        join products p on p.sku = ci.sku
        where c.kind = 'newcomer'
        order by ci.id
        """
    ).fetchall()


def test_leave_offers_the_cheapest_viewed_item_at_half_price():
    client = _client()
    page = client.get("/", cookies={"history": "desk-organizer,toy-ball"})
    assert 'data-sku="toy-ball"' in page.text
    assert "Half price, only for you" in page.text
    locked = client.post(
        "/hold",
        data={"sku": "desk-organizer"},
        cookies={"history": "desk-organizer,toy-ball"},
    )
    body = locked.json()
    assert body["sku"] == "toy-ball"
    assert body["kept"] is False
    assert body["price_cents"] == 200
    again = client.post("/hold", data={"sku": "binder-clip"}, cookies={"history": "binder-clip"})
    assert again.json()["sku"] == "toy-ball"
    home = client.get("/")
    assert 'id="pop-hold"' not in home.text
    fresh = client.get("/new")
    assert fresh.text.count('class="deal"') == 1
    assert "/p/toy-ball" in fresh.text
    priced, _total = priced_lines(
        client.app.state.db,
        [{"sku": "toy-ball", "qty": 1}],
        hold={"sku": "toy-ball", "price_cents": 200, "alive": True},
    )
    assert priced[0]["price_cents"] == 200


def test_leave_keeps_the_newcomer_item_already_in_the_cart():
    client = _client()
    db = client.app.state.db
    kept = _newcomer(db)[0]
    other = _newcomer(db)[1]
    page = client.get(
        "/",
        cookies={"cart": f"{kept['sku']}:1", "history": "toy-ball"},
    )
    assert f'data-sku="{kept["sku"]}"' in page.text
    assert "This price stays on this item" in page.text
    assert 'data-sku="toy-ball"' not in page.text
    locked = client.post(
        "/hold",
        data={"sku": "toy-ball"},
        cookies={"cart": f"{kept['sku']}:1", "history": "toy-ball"},
    )
    body = locked.json()
    assert body["sku"] == kept["sku"]
    assert body["kept"] is True
    assert body["price_cents"] == kept["price_cents"]
    assert body["price_cents"] != kept["regular"]
    hold = {"sku": body["sku"], "price_cents": body["price_cents"], "alive": True}
    priced, _total = priced_lines(db, [{"sku": kept["sku"], "qty": 1}], hold=hold)
    assert priced[0]["price_cents"] == kept["price_cents"]
    other_line, _total = priced_lines(db, [{"sku": other["sku"], "qty": 1}], hold=hold)
    assert other_line[0]["price_cents"] == other["regular"]
