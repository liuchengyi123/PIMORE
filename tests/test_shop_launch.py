import asyncio
import os

import httpx
import pytest
from fastapi.testclient import TestClient

from shop.app import create_app

BUYER = {
    "email": "buyer@example.com",
    "name": "A Buyer",
    "address": "1 Road",
    "city": "Austin",
    "region": "TX",
    "postal": "73301",
    "phone": "5551212",
}


@pytest.fixture()
def client():
    return TestClient(create_app(units_per_usd=150, db_path=":memory:"))


def as_admin(client):
    from shop.staff import save_staff

    save_staff(client.app.state.db, "admin", "secret", "admin")
    client.post("/admin/login", data={"username": "admin", "password": "secret"}, follow_redirects=False)


def test_admin_edits_drop_the_catalog_cache(client):
    db = client.app.state.db
    cache = client.app.state.cache
    first = client.get("/?country=US")
    assert "$12.00" in first.text
    assert "shop:catalog" in cache.values
    db.execute("update products set price_cents = 1 where sku = 'drain-rack'")
    cached = client.get("/?country=US")
    assert "$12.00" in cached.text
    denied = client.post("/admin/products/drain-rack", data={"price_cents": "1"}, follow_redirects=False)
    assert denied.status_code == 401
    as_admin(client)
    try:
        client.post("/admin/products/drain-rack", data={"price_cents": "1"}, follow_redirects=False)
        client.post("/admin/promos", data={"free_shipping_cents": "10000"}, follow_redirects=False)
        coupon = db.execute("select id from coupons where kind = 'public'").fetchone()["id"]
        client.post(f"/admin/coupons/{coupon}/disable", follow_redirects=False)
    finally:
        os.environ.pop("ADMIN_PASSWORD", None)
    assert cache.deleted.count("shop:catalog") >= 3
    assert "shop:catalog" not in cache.values
    fresh = client.get("/?country=US")
    assert "$0.01" in fresh.text


def test_empty_ad_slots_are_omitted_and_checkout_never_has_one(client):
    home = client.get("/?country=US")
    assert "data-ad" not in home.text
    checkout = client.get("/checkout?country=US")
    assert "data-ad" not in checkout.text
    as_admin(client)
    try:
        client.post(
            "/admin/ads",
            data={
                "slot": "announcement",
                "lang": "en",
                "body": "Ships this week",
                "image_url": "",
                "href": "",
            },
            follow_redirects=False,
        )
        client.post(
            "/admin/ads",
            data={
                "slot": "hero",
                "lang": "en",
                "image_url": "https://cdn.example/hero.jpg",
                "href": "https://example.com/guide",
                "body": "",
            },
            follow_redirects=False,
        )
        client.post(
            "/admin/ads",
            data={
                "slot": "sponsored",
                "lang": "ja",
                "href": "drain-rack",
                "image_url": "",
                "body": "",
            },
            follow_redirects=False,
        )
    finally:
        os.environ.pop("ADMIN_PASSWORD", None)
    japan = client.get("/?country=JP")
    assert 'data-ad="hero"' in japan.text
    assert "スポンサー" in japan.text
    listed = client.get("/c/kitchen?country=JP")
    assert "スポンサー" in listed.text
    still = client.get("/checkout?country=JP")
    assert "data-ad" not in still.text
    payment = client.get("/payment?country=JP")
    assert "data-ad" not in payment.text


def test_advantage_model_cannot_write_reviews(client):
    calls = []

    def model(**kwargs):
        calls.append(kwargs)
        return ["Solid handle", "Listed size", "Listed weight", "Photo matches"]

    app = create_app(units_per_usd=150, db_path=":memory:", advantage_model=model)
    tool = TestClient(app)
    before = tool.app.state.db.execute("select count(*) as n from reviews").fetchone()["n"]
    from shop.staff import save_staff

    save_staff(tool.app.state.db, "admin", "secret", "admin")
    try:
        tool.post("/admin/login", data={"username": "admin", "password": "secret"}, follow_redirects=False)
        saved = tool.post("/admin/products/drain-rack/advantages", follow_redirects=False)
    finally:
        os.environ.pop("ADMIN_PASSWORD", None)
    assert saved.status_code == 303
    assert set(calls[0]) == {"name", "category", "material", "size", "weight"}
    page = tool.get("/p/drain-rack?country=US")
    assert "Solid handle" in page.text
    assert page.text.count('class="advantage"') == 4
    after = tool.app.state.db.execute("select count(*) as n from reviews").fetchone()["n"]
    assert after == before


def test_pwa_caches_static_files_only(client):
    script = client.get("/sw.js")
    assert script.status_code == 200
    assert "/static/" in script.text
    assert "checkout" not in script.text
    manifest = client.get("/manifest.webmanifest")
    assert manifest.status_code == 200
    assert manifest.json()["start_url"] == "/"
    product = client.get("/p/drain-rack?country=US")
    assert product.headers["cache-control"] == "no-store"


def test_browse_load_and_duplicate_submit():
    app = create_app(units_per_usd=150, db_path=":memory:")

    async def run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://shop") as http:
            async def hit(path):
                response = await http.get(path)
                return response.status_code == 200

            home = await asyncio.gather(*[hit("/?country=US") for _ in range(500)])
            product = await asyncio.gather(*[hit("/p/drain-rack?country=US") for _ in range(500)])
            payload = dict(BUYER)
            payload.update(ship_country="US", submit_id="once", coupon_id="")

            async def submit():
                response = await http.post(
                    "/checkout?country=US",
                    data=payload,
                    cookies={"cart": "note-holder:1"},
                    follow_redirects=True,
                )
                return response.status_code

            codes = await asyncio.gather(submit(), submit())
            return home, product, codes

    home, product, codes = asyncio.run(run())
    assert sum(home) / 500 >= 0.99
    assert sum(product) / 500 >= 0.99
    assert codes == [200, 200]
    orders = app.state.db.execute("select count(*) as n from orders").fetchone()["n"]
    stock = app.state.db.execute(
        "select stock from products where sku = 'note-holder'"
    ).fetchone()["stock"]
    assert orders == 1
    assert stock == 99
