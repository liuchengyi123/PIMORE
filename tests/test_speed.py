import threading
import time

from fastapi.testclient import TestClient
from PIL import Image

from shop.adtrack import drain_postbacks, ensure_tables, track_server_event
from shop.app import create_app
from shop.db import connect, migrate
from shop.images import card_image, drain_fits


def _client():
    return TestClient(create_app(units_per_usd=150, db_path=":memory:"))


def test_postback_enqueue_returns_before_the_network(monkeypatch):
    started = threading.Event()
    release = threading.Event()

    def slow(url, payload, headers=None, timeout=12):
        started.set()
        assert timeout <= 3
        release.wait(2)
        return True, 200, "ok"

    monkeypatch.setattr("shop.adtrack._http_json", slow)
    client = _client()
    db = client.app.state.db
    ensure_tables(db)
    from shop.adtrack import create_account, update_account

    acct = create_account(db, "meta", "meta_home", "meta_home")
    update_account(
        db,
        acct["id"],
        credentials_patch={
            "meta_pixel_id": "111122223333",
            "meta_capi_token": "EAAsecret-token",
            "meta_test_code": "TEST123",
        },
        send_ratio_pct=100,
        learning_min=0,
        daily_floor=0,
    )
    started_at = time.perf_counter()
    browser = track_server_event(
        db,
        event_name="PageView",
        event_id="pv_speed_1",
        attrs={"acct": "meta_home", "utm_source": "meta"},
    )
    elapsed = time.perf_counter() - started_at
    assert elapsed < 0.25
    assert browser["event_id"] == "pv_speed_1"
    queued = db.execute(
        "select ok, detail from ad_event_log where event_id = 'pv_speed_1'"
    ).fetchone()
    assert queued is not None
    assert queued["ok"] == 0
    assert started.wait(1)
    release.set()
    assert drain_postbacks(timeout=3)
    done = db.execute(
        "select ok, http_status, detail from ad_event_log where event_id = 'pv_speed_1'"
    ).fetchone()
    assert done["ok"] == 1
    assert done["http_status"] == 200
    assert "queued" not in (done["detail"] or "")


def test_no_account_does_not_write_a_log_row():
    client = _client()
    db = client.app.state.db
    track_server_event(db, event_name="PageView", event_id="pv_none", attrs={})
    count = db.execute("select count(*) as c from ad_event_log").fetchone()["c"]
    assert count == 0


def test_home_pool_is_reused(monkeypatch):
    import shop.app as appmod

    calls = {"n": 0}
    real = appmod.main_urls

    def wrapped(*args, **kwargs):
        calls["n"] += 1
        return real(*args, **kwargs)

    monkeypatch.setattr(appmod, "main_urls", wrapped)
    client = _client()
    first = client.get("/?country=US")
    assert first.status_code == 200
    filled = calls["n"]
    assert filled > 0
    second = client.get("/?country=US")
    assert second.status_code == 200
    assert calls["n"] == filled


def test_fitted_image_miss_does_not_call_pil_on_the_request_thread(tmp_path, monkeypatch):
    import shop.images as images

    folder = tmp_path / "static" / "catalog" / "sku1"
    folder.mkdir(parents=True)
    Image.new("RGB", (1600, 900), (10, 20, 30)).save(folder / "0.jpg", quality=95)
    caller = threading.get_ident()
    seen = []
    real = images._fit_bytes

    def wrapped(data, edge, quality):
        seen.append(threading.get_ident())
        time.sleep(0.2)
        return real(data, edge, quality)

    monkeypatch.setattr(images, "_fit_bytes", wrapped)
    started = time.perf_counter()
    url = card_image("/static/catalog/sku1/0.jpg", tmp_path)
    elapsed = time.perf_counter() - started
    assert url == "/static/catalog/sku1/0.jpg"
    assert elapsed < 0.15
    assert drain_fits(timeout=3)
    assert seen and seen[0] != caller
    assert card_image("/static/catalog/sku1/0.jpg", tmp_path) == "/static/catalog/sku1/fit/0.jpg"


def test_empty_cart_renders_at_most_12_cards():
    client = _client()
    page = client.get("/cart?country=US")
    assert page.status_code == 200
    cards = page.text.count('class="card"')
    sheets = page.text.count('class="sheet-item"')
    assert cards <= 12
    assert sheets == 0
    assert cards + sheets <= 12


def test_storefront_skips_gen_task_progress(monkeypatch):
    def boom(conn):
        raise AssertionError("task_progress on a storefront page")

    monkeypatch.setattr("shop.app.task_progress", boom)
    monkeypatch.setattr("shop.app.sku_task_progress", boom)
    client = _client()
    assert client.get("/?country=US").status_code == 200
    assert client.get("/cart?country=US").status_code == 200
    assert client.get("/p/sink-strainer?country=US").status_code == 200


def test_hot_indexes_and_ensure_tables_are_idempotent(tmp_path):
    conn = connect(str(tmp_path / "shop.db"))
    migrate(conn)
    ensure_tables(conn)
    ensure_tables(conn)
    names = {row["name"] for row in conn.execute("select name from sqlite_master where type = 'index'").fetchall()}
    for needed in (
        "reviews_sku",
        "questions_sku",
        "order_lines_order_id",
        "idx_ad_event_log_lookup",
        "idx_ad_event_log_created",
        "gen_tasks_status",
        "sku_gen_tasks_status",
    ):
        assert needed in names
