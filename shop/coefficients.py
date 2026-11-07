# shop/coefficients.py — country sale-price coefficients (US base = 1.0)
"""Per-country coefficients on top of US sale price.

Display / checkout local amount = US_sale_cents × coefficient × FX(units_per_usd).
Buyer never sees this table. Admin CRUD via /admin/coefficients.
"""
from __future__ import annotations

import json
from typing import Any

# Storefront countries from extras.LOCALES — defaults keep US at 1.0.
# Suggested starters (ops can edit): nearby markets slightly below/above US.
DEFAULTS: dict[str, float] = {
    "US": 1.0,
    "CA": 1.05,
    "GB": 1.08,
    "DE": 1.10,
    "FR": 1.10,
    "ES": 1.05,
    "PT": 1.05,
    "CN": 0.92,
    "TW": 0.95,
    "HK": 0.98,
    "JP": 1.12,
    "MX": 0.90,
    "BR": 0.95,
}

SETTING_KEY = "country_coefficients"


def _clamp(value: float) -> float:
    if value <= 0:
        return 1.0
    if value > 5:
        return 5.0
    return round(value, 4)


def parse_raw(raw: str | None) -> dict[str, float]:
    out = dict(DEFAULTS)
    if not raw:
        return out
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return out
    if not isinstance(data, dict):
        return out
    for code, value in data.items():
        key = str(code or "").strip().upper()
        if not key:
            continue
        try:
            out[key] = _clamp(float(value))
        except (TypeError, ValueError):
            continue
    out.setdefault("US", 1.0)
    return out


def load(conn) -> dict[str, float]:
    row = conn.execute(
        "select value from settings where key = ?", (SETTING_KEY,)
    ).fetchone()
    raw = row["value"] if row else ""
    return parse_raw(raw)


def save(conn, mapping: dict[str, Any]) -> dict[str, float]:
    cleaned: dict[str, float] = {}
    for code, value in (mapping or {}).items():
        key = str(code or "").strip().upper()
        if not key:
            continue
        try:
            cleaned[key] = _clamp(float(value))
        except (TypeError, ValueError):
            continue
    cleaned.setdefault("US", 1.0)
    payload = json.dumps(cleaned, ensure_ascii=False, sort_keys=True)
    conn.execute(
        "insert or replace into settings (key, value) values (?, ?)",
        (SETTING_KEY, payload),
    )
    return cleaned


def coefficient_for(conn, country: str) -> float:
    code = (country or "US").strip().upper() or "US"
    table = load(conn)
    if code in table:
        return float(table[code])
    # Fall back to US base when country not listed.
    return float(table.get("US", 1.0))


def rows_for_admin(conn, countries: tuple[str, ...] | list[str]) -> list[dict]:
    table = load(conn)
    rows = []
    for code in countries:
        key = str(code).upper()
        rows.append(
            {
                "code": key,
                "coefficient": table.get(key, DEFAULTS.get(key, 1.0)),
                "is_base": key == "US",
            }
        )
    # Include any extras saved but not in the default country list.
    known = {str(c).upper() for c in countries}
    for key, value in sorted(table.items()):
        if key not in known:
            rows.append({"code": key, "coefficient": value, "is_base": key == "US"})
    return rows
