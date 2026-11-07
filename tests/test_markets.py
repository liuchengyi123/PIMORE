import json

from shop.markets import judge_batch, parsed, push_line, rank


def test_unknown_stays_forward_and_a_miss_goes_back():
    assert rank({"markets": ""}, "US") == 0
    flagged = json.dumps({"US": False, "CA": False, "GB": False, "DE": False, "FR": False, "ES": False, "PT": False, "BR": False, "MX": False, "JP": True})
    assert rank({"markets": flagged}, "US") == 1
    assert rank({"markets": flagged}, "JP") == 0


def test_string_false_is_not_treated_as_yes():
    assert parsed('{"US": "false", "CA": "true", "GB": false, "DE": false, "FR": false, "ES": false, "PT": false, "BR": false, "MX": false, "JP": false}')["US"] is False
    assert parsed('{"US": "false", "CA": "true", "GB": false, "DE": false, "FR": false, "ES": false, "PT": false, "BR": false, "MX": false, "JP": false}')["CA"] is True


def test_one_reply_without_sku_still_binds():
    body = json.dumps({code: code == "JP" for code in ("US", "CA", "GB", "DE", "FR", "ES", "PT", "BR", "MX", "JP")})

    def complete(prompt):
        assert "筷子" in prompt
        return body

    found = judge_batch([{"sku": "bowl", "title": "陶瓷筷子", "description": ""}], complete)
    assert found["bowl"]["JP"] is True
    assert found["bowl"]["US"] is False


def test_table_reply_keeps_only_known_skus():
    def complete(prompt):
        assert "不要重复标题" in prompt
        assert "陶瓷筷子" in prompt
        return "bowl,0,0,0,0,0,0,0,0,0,1\nnope,1,1,1,1,1,1,1,1,1,1\n"

    found = judge_batch([{"sku": "bowl", "title": "陶瓷筷子"}], complete)
    assert list(found) == ["bowl"]
    assert found["bowl"]["JP"] is True
    assert found["bowl"]["US"] is False


def test_push_line_counts_only_judged_stock(tmp_path):
    import sqlite3

    from shop.db import migrate

    conn = sqlite3.connect(tmp_path / "shop.sqlite")
    conn.row_factory = sqlite3.Row
    migrate(conn)
    yes = json.dumps({code: True for code in ("US", "CA", "GB", "DE", "FR", "ES", "PT", "BR", "MX", "JP")})
    no = json.dumps({code: code == "JP" for code in ("US", "CA", "GB", "DE", "FR", "ES", "PT", "BR", "MX", "JP")})
    conn.execute(
        "insert into products (sku, category, price_cents, stock, names, bullets, description, specs, published, markets) values (?, ?, ?, ?, '{}', '[]', '{}', '{}', 1, ?)",
        ("a", "kitchen", 100, 2, yes),
    )
    conn.execute(
        "insert into products (sku, category, price_cents, stock, names, bullets, description, specs, published, markets) values (?, ?, ?, ?, '{}', '[]', '{}', '{}', 1, ?)",
        ("b", "kitchen", 100, 2, no),
    )
    conn.commit()
    line = push_line(conn)
    assert line.startswith("主推款")
    assert "美国 1" in line
    assert "日本 2" in line
