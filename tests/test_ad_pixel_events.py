import hashlib
import json
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from shop.adtrack import (
    _hash_phone_meta,
    _hash_phone_tiktok,
    bresenham_step,
    clean_platform_id,
    create_account,
    decide_purchase,
    drain_postbacks,
    ensure_tables,
    evaluate_stoploss,
    merge_from_request,
    propose_ratio,
    run_smart_ratios,
    send_meta_event,
    send_tiktok_event,
    spread_sends,
    update_account,
)
from shop.app import create_app
from shop.pay import mark_paid
from shop.staff import save_staff
from tests.test_shop_pay import BUYER


def _client():
    return TestClient(create_app(units_per_usd=150, db_path=":memory:"))


def _login(client):
    save_staff(client.app.state.db, "admin", "secret-pass", "admin")
    entered = client.post(
        "/admin/login",
        data={"username": "admin", "password": "secret-pass"},
        follow_redirects=False,
    )
    assert entered.status_code == 303


def _account(db, platform="meta", code="meta_home", **throttle):
    ensure_tables(db)
    acct = create_account(db, platform, code, code)
    creds = {
        "meta_pixel_id": "111122223333",
        "meta_capi_token": "EAAsecret-token",
        "meta_test_code": "TEST123",
    }
    if platform == "tiktok":
        creds = {
            "tiktok_pixel_id": "CPIXEL99",
            "tiktok_access_token": "tt-secret",
            "tiktok_test_code": "TTTEST",
        }
    update_account(
        db,
        acct["id"],
        credentials_patch=creds,
        send_ratio_pct=throttle.get("send_ratio_pct", 100),
        learning_min=throttle.get("learning_min", 0),
        daily_floor=throttle.get("daily_floor", 0),
        ratio_min=throttle.get("ratio_min", 0),
        ratio_max=throttle.get("ratio_max", 100),
        smart_enabled=throttle.get("smart_enabled", False),
        target_cpa=throttle.get("target_cpa", 0),
        value_multiplier=throttle.get("value_multiplier", 1),
        stoploss_multiple=throttle.get("stoploss_multiple", 1.5),
        stoploss_hours=throttle.get("stoploss_hours", 24),
    )
    return acct


def test_launch_page_shows_account_pixel_status_without_inputs():
    client = _client()
    _login(client)
    db = client.app.state.db
    _account(db, code="meta_home")
    _account(db, code="meta_beauty")
    page = client.get("/admin/launch?platform=meta&acct=meta_beauty")
    assert page.status_code == 200
    assert 'name="meta_pixel_id"' not in page.text
    assert 'name="meta_capi_token"' not in page.text
    assert 'name="tiktok_access_token"' not in page.text
    assert "受众差很多" in page.text
    assert "1111" in page.text and "3333" in page.text
    assert "已设置" in page.text
    assert "/admin/traffic?platform=meta&amp;acct=meta_beauty" in page.text
    assert "meta_home" in page.text and "meta_beauty" in page.text


def test_launch_link_includes_platform_adgroup_macros():
    client = _client()
    _login(client)
    meta = client.post(
        "/admin/launch",
        data={
            "template": "dense_flash",
            "category": "kitchen",
            "skin": "kitchen",
            "platform": "meta",
            "utm_source": "meta",
            "utm_medium": "paid",
            "country": "US",
            "acct": "",
        },
    )
    assert "adset_id={{adset.id}}" in meta.text
    assert "campaign_id={{campaign.id}}" in meta.text
    assert "ad_id={{ad.id}}" in meta.text
    tiktok = client.post(
        "/admin/launch",
        data={
            "template": "dense_flash",
            "category": "kitchen",
            "skin": "kitchen",
            "platform": "tiktok",
            "utm_source": "tiktok",
            "utm_medium": "paid",
            "country": "US",
        },
    )
    assert "adgroup_id=__AID__" in tiktok.text
    assert "ad_id=__CID__" in tiktok.text


def test_fbc_comes_only_from_fbclid_and_phone_hashes_differ():
    blank = merge_from_request({}, {"utm_source": "meta"})
    assert "fbc" not in blank
    merged = merge_from_request({}, {"fbclid": "IwAR123", "adset_id": "{{adset.id}}", "ad_id": "9988"})
    assert merged["fbc"].startswith("fb.1.")
    assert merged["fbc"].endswith(".IwAR123")
    assert len(merged["fbc"].split(".")[2]) >= 13
    assert "adgroup" not in merged
    assert merged["ad_id"] == "9988"
    assert clean_platform_id("__AID__") == ""
    assert clean_platform_id("{{adset.id}}") == ""
    phone = "+1 (415) 555-2671"
    assert _hash_phone_tiktok(phone, "US") == hashlib.sha256(b"+14155552671").hexdigest()
    assert _hash_phone_meta(phone, "US") == hashlib.sha256(b"14155552671").hexdigest()
    assert _hash_phone_tiktok(phone, "US") != _hash_phone_meta(phone, "US")


def test_server_payloads_share_event_id_and_put_test_code_at_root(monkeypatch):
    seen = {}

    def fake(url, payload, headers=None, timeout=12):
        seen["url"] = url
        seen["payload"] = payload
        seen["headers"] = headers or {}
        return False, 400, "bad token user@example.com +14155552671"

    monkeypatch.setattr("shop.adtrack._http_json", fake)
    cfg = {
        "meta_pixel_id": "111",
        "meta_capi_token": "EAAsecret",
        "meta_test_code": "TEST123",
    }
    ok, status, detail = send_meta_event(
        cfg,
        "AddToCart",
        {"email": "Buyer@Example.com", "phone": "+14155552671", "ship_country": "US"},
        {"fbp": "fb.1.1.1", "fbclid": "IwAR123", "client_ip": "1.2.3.4", "client_ua": "TestUA", "external_id": "vid"},
        "atc_1",
        value=12.5,
        currency="USD",
        source_url="https://linkiip.com/p/sku",
        content_ids=["sku"],
        contents=[{"id": "sku", "quantity": 1, "item_price": 12.5}],
    )
    assert ok is False and status == 400
    assert "user@example.com" not in detail
    assert "14155552671" not in detail
    body = seen["payload"]
    assert body["test_event_code"] == "TEST123"
    event = body["data"][0]
    assert event["event_name"] == "AddToCart"
    assert event["event_id"] == "atc_1"
    assert event["action_source"] == "website"
    assert event["event_source_url"].endswith("/p/sku")
    assert event["user_data"]["client_ip_address"] == "1.2.3.4"
    assert event["user_data"]["fbp"] == "fb.1.1.1"
    assert event["user_data"]["fbc"].endswith(".IwAR123")
    assert event["user_data"]["em"] == [hashlib.sha256(b"buyer@example.com").hexdigest()]
    assert event["custom_data"]["content_ids"] == ["sku"]
    assert event["custom_data"]["contents"][0]["id"] == "sku"
    assert "access_token=" in seen["url"]
    cfg = {
        "tiktok_pixel_id": "PX",
        "tiktok_access_token": "tt-secret",
        "tiktok_test_code": "TTTEST",
    }
    send_tiktok_event(
        cfg,
        "Purchase",
        {"email": "buyer@example.com", "phone": "+14155552671", "ship_country": "US"},
        {"ttclid": "tt1", "ttp": "ttp1", "client_ip": "1.2.3.4", "client_ua": "TestUA", "external_id": "vid"},
        "purchase_9",
        value=9,
        currency="USD",
        source_url="https://linkiip.com/orders/9",
        contents=[{"content_id": "sku", "price": 9, "quantity": 1}],
        search_string="",
    )
    body = seen["payload"]
    assert seen["headers"]["Access-Token"] == "tt-secret"
    assert body["event_source"] == "web"
    assert body["event_source_id"] == "PX"
    assert body["test_event_code"] == "TTTEST"
    row = body["data"][0]
    assert row["event"] == "Purchase"
    assert row["event_id"] == "purchase_9"
    assert row["user"]["phone"] == hashlib.sha256(b"+14155552671").hexdigest()
    assert row["user"]["ttclid"] == "tt1"
    assert row["properties"]["contents"][0]["content_id"] == "sku"
    assert "CompletePayment" not in json.dumps(body)


def test_funnel_events_log_from_lp_through_checkout(monkeypatch):
    monkeypatch.setattr("shop.adtrack._http_json", lambda *a, **k: (False, 400, "nope"))
    client = _client()
    _login(client)
    db = client.app.state.db
    _account(db, code="meta_home")
    made = client.post(
        "/admin/launch",
        data={
            "template": "dense_flash",
            "category": "kitchen",
            "skin": "kitchen",
            "platform": "meta",
            "utm_source": "meta",
            "utm_medium": "paid",
            "utm_campaign": "home",
            "country": "US",
            "acct": "meta_home",
        },
    )
    assert made.status_code == 200
    row = db.execute("select code from ad_launch_links order by id desc limit 1").fetchone()
    lp = client.get(f"/lp/ad/{row['code']}?acct=meta_home&utm_source=meta&adset_id=555&campaign_id=77&ad_id=88")
    assert lp.status_code == 200
    assert "ad_enter=1" in lp.text
    assert "fbq(" in lp.text or "PageView" in lp.text
    enter = client.get("/c/kitchen?country=US&ad_enter=1&eid=enter_abc12345")
    assert enter.status_code == 200
    product = client.get("/p/sink-strainer?country=US")
    assert product.status_code == 200
    added = client.post("/cart/add", data={"sku": "sink-strainer", "qty": "1", "country": "US", "ajax": "1"})
    assert added.status_code == 200
    assert added.json()["ad_event"]["name"] == "AddToCart"
    assert added.json()["ad_event"]["event_id"]
    checkout = client.get("/checkout?country=US")
    assert checkout.status_code == 200
    assert drain_postbacks(timeout=3)
    names = [
        item["event_name"]
        for item in db.execute("select event_name from ad_event_log order by id asc").fetchall()
    ]
    assert names[:5] == ["PageView", "EnterStore", "ViewContent", "AddToCart", "InitiateCheckout"]
    acct_col = db.execute("select acct, http_status from ad_event_log where event_name = 'PageView'").fetchone()
    assert acct_col["acct"] == "meta_home"
    assert acct_col["http_status"] == 400
    wish = client.post(
        "/wishlist",
        data={"sku": "sink-strainer", "country": "US", "ajax": "1"},
        headers={"X-Harbor-Ajax": "1"},
    )
    assert wish.json()["wished"] is True
    assert wish.json()["ad_event"]["name"] == "AddToWishlist"
    found = client.get("/search?country=US&q=strainer")
    assert found.status_code == 200
    assert drain_postbacks(timeout=3)
    names = [item["event_name"] for item in db.execute("select event_name from ad_event_log").fetchall()]
    assert "Search" in names
    assert "AddToWishlist" in names
    assert "Purchase" not in names
    order = db.execute("select adgroup, ad_campaign, ad_id from orders").fetchone()
    # no order yet
    assert order is None
    client.post(
        "/checkout?country=US",
        data={
            **BUYER,
            "ship_country": "US",
            "submit_id": "payinfo-1",
            "coupon_id": "",
            "pay_method": "stripe",
        },
    )
    stamped = db.execute("select adgroup, ad_campaign, ad_id, status from orders").fetchone()
    assert stamped["adgroup"] == "555"
    assert stamped["ad_campaign"] == "77"
    assert stamped["ad_id"] == "88"
    assert stamped["status"] == "pending"
    assert drain_postbacks(timeout=3)
    logged = [item["event_name"] for item in db.execute(
        "select event_name from ad_event_log where event_name = 'AddPaymentInfo'"
    ).fetchall()]
    assert logged == ["AddPaymentInfo"]
    assert "Purchase" not in [
        item["event_name"] for item in db.execute("select event_name from ad_event_log").fetchall()
    ]


def test_ratio_is_exact_idempotent_and_respects_guards():
    assert spread_sends(70, 10).count(True) == 7
    assert spread_sends(70, 100).count(True) == 70
    acc = 0
    sends = []
    for _ in range(10):
        acc, send = bresenham_step(acc, 70)
        sends.append(send)
    assert sends.count(True) == 7
    assert sends[0] is False and sends[-1] is True

    client = _client()
    db = client.app.state.db
    _account(db, code="meta_home", send_ratio_pct=70, learning_min=0, daily_floor=0, ratio_min=0, ratio_max=100)
    attrs = {"acct": "meta_home", "adgroup": "555"}
    flags = []
    for index in range(10):
        flags.append(decide_purchase(db, f"o{index}", attrs)["send"])
    assert flags.count(True) == 7
    again = decide_purchase(db, "o0", attrs)
    assert again["send"] is flags[0]
    assert again["fresh"] is False
    assert db.execute("select count(*) as c from ad_send_decision").fetchone()["c"] == 10

    _account(db, code="meta_learn", send_ratio_pct=0, learning_min=50, daily_floor=0, ratio_min=0)
    learned = [decide_purchase(db, f"l{i}", {"acct": "meta_learn", "adgroup": "9"})["reason"] for i in range(3)]
    assert learned == ["learning", "learning", "learning"]

    _account(db, code="meta_floor", send_ratio_pct=0, learning_min=0, daily_floor=2, ratio_min=0)
    reasons = [decide_purchase(db, f"f{i}", {"acct": "meta_floor", "adgroup": ""})["reason"] for i in range(4)]
    assert reasons[:2] == ["floor", "floor"]
    assert reasons[2:] == ["drop", "drop"]


def test_dropped_purchase_skips_browser_and_server(monkeypatch):
    monkeypatch.setattr("shop.adtrack._http_json", lambda *a, **k: (True, 200, "ok"))
    client = _client()
    db = client.app.state.db
    _account(db, code="meta_home", send_ratio_pct=0, learning_min=0, daily_floor=0, ratio_min=0, ratio_max=100)
    client.get("/?acct=meta_home&adset_id=555&utm_source=meta")
    client.post("/cart/add", data={"sku": "note-holder", "qty": "1", "country": "US", "next": "/cart"})
    client.post(
        "/checkout?country=US",
        data={**BUYER, "ship_country": "US", "submit_id": "drop-1", "coupon_id": "", "pay_method": "stripe"},
    )
    order = db.execute("select * from orders order by id desc").fetchone()
    assert mark_paid(db, order["id"]) is True
    page = client.get(f"/orders/{order['id']}")
    assert page.status_code == 200
    assert 'data-ad-send="0"' in page.text
    assert 'data-paid="1"' in page.text
    row = db.execute(
        "select send, reason from ad_send_decision where order_id = ?",
        (str(order["id"]),),
    ).fetchone()
    assert row["send"] == 0
    logged = db.execute(
        "select event_name, ok, detail from ad_event_log where event_name = 'Purchase'"
    ).fetchone()
    assert logged["ok"] == 0
    assert "skipped_throttle" in logged["detail"]
    again = client.get(f"/orders/{order['id']}")
    assert again.status_code == 200
    assert db.execute("select count(*) as c from ad_event_log where event_name = 'Purchase'").fetchone()["c"] == 1


def test_smart_ratio_steps_and_keeps_base_when_fetch_fails():
    low, _ = propose_ratio(70, 70, 10, 4, 40, 40, 60, 100)
    assert low == 60
    high, reason = propose_ratio(70, 70, 10, 20, 80, 100, 60, 100)
    assert high == 80
    assert reason == "step_up_cpa"
    near, why = propose_ratio(90, 70, 10, 10, 50, 50, 60, 100)
    assert why == "near_target"
    assert near == 80

    client = _client()
    db = client.app.state.db
    _account(db, code="meta_home", send_ratio_pct=80, learning_min=0, daily_floor=0, ratio_min=60, ratio_max=100, smart_enabled=True, target_cpa=10)
    decide_purchase(db, "s1", {"acct": "meta_home", "adgroup": "555"})

    def fetch_ok(acct, adgroup):
        return 4.0, ""

    notes = run_smart_ratios(db, fetch=fetch_ok)
    assert notes
    group = db.execute("select effective_ratio, reason, spend, real_orders from ad_groups where adgroup = '555'").fetchone()
    assert group["effective_ratio"] == 70
    assert group["reason"] == "step_down"
    assert group["real_orders"] == 1
    assert group["spend"] == 4

    def fetch_fail(acct, adgroup):
        return None, "no_token"

    db.execute("update ad_accounts set smart_checked_at = ''")
    run_smart_ratios(db, fetch=fetch_fail)
    group = db.execute("select effective_ratio, reason from ad_groups where adgroup = '555'").fetchone()
    assert group["effective_ratio"] == 80
    assert group["reason"] == "no_token"
    history = db.execute("select reason from ad_ratio_history order by id desc limit 1").fetchone()
    assert history["reason"] == "no_token"


def test_smart_off_uses_base_ratio_without_bounds():
    client = _client()
    db = client.app.state.db
    _account(
        db,
        code="meta_home",
        send_ratio_pct=50,
        learning_min=0,
        daily_floor=0,
        ratio_min=60,
        ratio_max=100,
        smart_enabled=False,
    )
    flags = [decide_purchase(db, f"b{i}", {"acct": "meta_home", "adgroup": "555"})["send"] for i in range(10)]
    assert flags.count(True) == 5


def test_stoploss_holds_ratio_then_clears_when_cpa_recovers():
    started = datetime(2026, 11, 1, tzinfo=timezone.utc)
    active, since, hold = evaluate_stoploss("", started, 20, 8, 1.5, 24)
    assert hold is False and active is False and since
    active, since, hold = evaluate_stoploss(since, started + timedelta(hours=24), 20, 8, 1.5, 24)
    assert active is True and hold is True
    active, since, hold = evaluate_stoploss(since, started + timedelta(hours=48), 8, 8, 1.5, 24)
    assert active is False and hold is False and since == ""

    client = _client()
    db = client.app.state.db
    _account(
        db,
        code="meta_home",
        send_ratio_pct=70,
        learning_min=0,
        daily_floor=0,
        ratio_min=60,
        ratio_max=100,
        smart_enabled=True,
        target_cpa=8,
        stoploss_multiple=1.5,
        stoploss_hours=24,
    )
    decide_purchase(db, "hot-1", {"acct": "meta_home", "adgroup": "555"})

    def hot(_acct, _adgroup):
        return 20.0, ""

    run_smart_ratios(db, fetch=hot, now=started)
    row = db.execute(
        "select effective_ratio, reason, stoploss_active, stoploss_since from ad_groups where adgroup = '555'"
    ).fetchone()
    assert row["stoploss_active"] == 0
    assert row["reason"] == "step_up_cpa"
    held = row["effective_ratio"]
    db.execute("update ad_accounts set smart_checked_at = ''")
    run_smart_ratios(db, fetch=hot, now=started + timedelta(hours=24))
    row = db.execute(
        "select effective_ratio, reason, stoploss_active from ad_groups where adgroup = '555'"
    ).fetchone()
    assert row["stoploss_active"] == 1
    assert row["reason"] == "止损：真实CPA持续超标"
    assert row["effective_ratio"] == held
    assert db.execute("select reason from ad_ratio_history order by id desc limit 1").fetchone()["reason"] == "止损：真实CPA持续超标"
    db.execute("update ad_accounts set smart_checked_at = ''")
    run_smart_ratios(db, fetch=lambda _a, _g: (8.0, ""), now=started + timedelta(hours=30))
    row = db.execute("select stoploss_active, reason, stoploss_since from ad_groups where adgroup = '555'").fetchone()
    assert row["stoploss_active"] == 0
    assert row["stoploss_since"] == ""
    assert row["reason"] != "止损：真实CPA持续超标"


def test_traffic_page_explains_each_throttle_rule():
    client = _client()
    _login(client)
    page = client.get("/admin/traffic?platform=meta")
    assert page.status_code == 200
    for text in (
        "扣量规则说明",
        "真实 CPA",
        "平台看到的 CPA",
        "智能关",
        "止损倍数",
        "止损时长",
        "学习期",
        "每日保底",
        "浏览器 Purchase",
        "漏斗仍按全额",
    ):
        assert text in page.text
    launch = client.get("/admin/launch")
    assert "打码后的值" in launch.text
    assert "测试事件" in launch.text


def test_existing_sqlite_gets_throttle_columns(tmp_path):
    import sqlite3

    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("create table ad_accounts (id integer primary key, code text, platform text, name text, credentials text, send_ratio_pct real, value_multiplier real, enabled integer, is_default integer, created_at text, updated_at text)")
    conn.execute("create table orders (id integer primary key, email text)")
    conn.execute("create table ad_event_log (id integer primary key, created_at text, platform text, event_name text, order_id text, event_id text, ok integer, detail text)")
    conn.execute("create table ad_funnel (id integer primary key, created_at text, day text, kind text, seg text, utm_source text, utm_campaign text, sku text, order_id text, visitor text, extra text)")
    conn.execute("create table settings (key text primary key, value text)")
    ensure_tables(conn)
    cols = {row["name"] for row in conn.execute("pragma table_info(ad_accounts)")}
    assert {"learning_min", "daily_floor", "ratio_min", "ratio_max", "smart_enabled", "target_cpa", "stoploss_multiple", "stoploss_hours"} <= cols
    order_cols = {row["name"] for row in conn.execute("pragma table_info(orders)")}
    assert "adgroup" in order_cols
    log_cols = {row["name"] for row in conn.execute("pragma table_info(ad_event_log)")}
    assert "http_status" in log_cols and "acct" in log_cols
