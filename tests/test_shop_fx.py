from datetime import datetime, timezone

import pytest

from shop.fx import NoRate, RateBook, fetch_rates


def test_same_hour_fetches_once():
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        return {"JPY": 150}

    book = RateBook(fetch)
    now = datetime(2026, 11, 2, 3, 15, tzinfo=timezone.utc)
    first = book.rate_for("JPY", now)
    second = book.rate_for("JPY", now.replace(minute=40))
    assert first.units_per_usd == 150
    assert first.stale is False
    assert second.units_per_usd == 150
    assert calls["n"] == 1


def test_failure_without_history_raises():
    def fetch():
        raise RuntimeError("down")

    book = RateBook(fetch)
    now = datetime(2026, 11, 2, 3, tzinfo=timezone.utc)
    with pytest.raises(NoRate):
        book.rate_for("JPY", now)


def test_failure_uses_previous_hour():
    state = {"ok": True}

    def fetch():
        if not state["ok"]:
            raise RuntimeError("down")
        return {"JPY": 150}

    book = RateBook(fetch)
    first_hour = datetime(2026, 11, 2, 3, tzinfo=timezone.utc)
    assert book.rate_for("JPY", first_hour).stale is False
    state["ok"] = False
    next_hour = datetime(2026, 11, 2, 4, tzinfo=timezone.utc)
    stale = book.rate_for("JPY", next_hour)
    assert stale.units_per_usd == 150
    assert stale.stale is True


def test_one_response_covers_every_currency():
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        return {"JPY": 150, "EUR": 0.9}

    book = RateBook(fetch)
    now = datetime(2026, 11, 2, 3, tzinfo=timezone.utc)
    assert book.rate_for("JPY", now).units_per_usd == 150
    assert book.rate_for("EUR", now).units_per_usd == 0.9
    assert calls["n"] == 1


def test_backup_rate_is_used_when_frankfurter_times_out():
    def primary():
        raise TimeoutError("slow")

    def backup():
        return {"JPY": 157.25, "EUR": 0.89}

    assert fetch_rates(primary, backup)["JPY"] == 157.25


def test_usd_does_not_fetch():
    def fetch():
        raise AssertionError("should not fetch")

    book = RateBook(fetch)
    now = datetime(2026, 11, 2, 3, tzinfo=timezone.utc)
    assert book.rate_for("USD", now).units_per_usd == 1
