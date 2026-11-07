from shop.app import create_app
from fastapi.testclient import TestClient


def test_titles_canonical_and_private_pages():
    client = TestClient(create_app(units_per_usd=150, db_path=":memory:"))
    home = client.get("/")
    assert home.status_code == 200
    assert "<title>The small goods a house actually uses | Harbor</title>" in home.text
    assert 'rel="canonical" href="https://linkiip.com/"' in home.text
    assert "hreflang=\"de\" href=\"https://linkiip.com/de/\"" in home.text
    assert 'content="index, follow"' in home.text

    german = client.get("/?country=DE")
    assert "<title>Die kleinen Dinge, die ein Haushalt wirklich braucht | Harbor</title>" in german.text
    assert 'rel="canonical" href="https://linkiip.com/de/"' in german.text

    product = client.get("/p/drain-rack")
    assert "<title>Dish rack | Harbor</title>" in product.text
    assert 'rel="canonical" href="https://linkiip.com/p/drain-rack"' in product.text
    assert '"@type": "Product"' in product.text
    assert "Dish rack" in product.text

    prefixed = client.get("/de/p/drain-rack?country=US")
    assert "<title>Geschirrständer | Harbor</title>" in prefixed.text
    assert "$12.00" in prefixed.text
    assert 'rel="canonical" href="https://linkiip.com/de/p/drain-rack"' in prefixed.text

    kitchen = client.get("/c/kitchen")
    assert "<title>Kitchen | Harbor</title>" in kitchen.text
    assert 'rel="canonical" href="https://linkiip.com/c/kitchen"' in kitchen.text
    assert "breadcrumb" in kitchen.text

    cart = client.get("/cart")
    assert 'content="noindex, follow"' in cart.text
    assert "hreflang" not in cart.text

    japan = client.get("/p/drain-rack?country=JP")
    assert 'content="noindex, follow"' in japan.text
    assert 'rel="canonical" href="https://linkiip.com/p/drain-rack"' in japan.text

    robots = client.get("/robots.txt")
    assert "Disallow: /cart" in robots.text
    assert "Sitemap:" not in robots.text

    probe = client.get("/.env")
    assert probe.status_code == 404
    assert probe.content == b""
    assert "harbor_vid" not in probe.headers.get("set-cookie", "")
    assert client.get("/.git/config").status_code == 404
    assert client.get("/wp-admin/install.php").status_code == 404

    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200
    assert "https://linkiip.com/c/kitchen" in sitemap.text
    assert "https://linkiip.com/de/c/kitchen" in sitemap.text
    assert "drain-rack" not in sitemap.text
