import os

from fastapi.testclient import TestClient

from shop.app import create_app
from shop.translate import fill_languages


def test_other_languages_are_translated_from_english():
    seen = []

    def translate(text, source, target):
        seen.append((source, target, text))
        return text

    result = fill_languages({"name": "不锈钢沥水架 30厘米"}, translate)
    assert result["name"]["en"] == "stainless steel dish rack 30cm"
    later = [row for row in seen if row[1] != "en"]
    assert {row[0] for row in later} == {"en"}
    assert {row[1] for row in later} == {"es", "de", "fr", "pt", "ja"}
    assert all("沥" not in row[2] and "厘米" not in row[2] for row in later)
    assert all(result["name"][lang] == "stainless steel dish rack 30cm" for lang in ("es", "de", "fr", "pt", "ja"))


def test_import_does_not_publish_chinese_without_a_key(monkeypatch):
    monkeypatch.delenv("DEEPL_AUTH_KEY", raising=False)
    from shop.staff import save_staff

    client = TestClient(create_app(units_per_usd=150, db_path=":memory:"))
    save_staff(client.app.state.db, "admin", "secret", "admin")
    client.post("/admin/login", data={"username": "admin", "password": "secret"}, follow_redirects=False)
    response = client.post(
        "/admin/catalog",
        data={"sku": "zh-rack", "category": "kitchen", "price_cents": "1200", "name_zh": "沥水架"},
        follow_redirects=False,
    )
    assert response.status_code == 400
    saved = client.app.state.db.execute("select sku from products where sku = 'zh-rack'").fetchone()
    assert saved is None
