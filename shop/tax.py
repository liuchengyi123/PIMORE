"""Provisional checkout tax estimates.

Not a compliance engine and not a filing position. Rates are state-level (US)
or country-level placeholders so checkout can show a tax line before a real
tax provider is connected. Combined local / city rates are not included.

Taxable base (merchandise cents, same unit as ``orders.merchandise_cents``):

    goods after tier, lucky, and coupon discounts
    + shipping

Store credit (balance) does not reduce the base. A gift-wrap fee, when an
admin sets one and the shopper turns wrapping on, is added to the charged
due and is not part of this taxable base.

Rates start as the tables below. Ops replace individual cells at ``/admin/tax``
(settings key ``tax_rates``). A missing override keeps the builtin cell.

``tax_cents`` is an estimate stored on the order. It is **not** added to
``due_cents`` / ``due_local``. Those stay the amount charged today, which is
what ``build_quote`` already returns. The quote API echoes the same split
(``tax_included_in_due`` is false) so a later UI can render the line without
changing what the payment gateway captures.

US region ``CA`` is California. Country ``CA`` is Canada (GST only).
US region ``DE`` is Delaware (no state sales tax). Country ``DE`` is Germany.
A country or state missing from the tables estimates as 0, including Japan,
so the existing yen checkout total is unchanged until an admin sets a rate.
"""

import json

# Parts per 100_000. 7.25% = 7250. Half-up in estimate_tax_cents.
_US_STATE_PPM = {
    "AK": 0,
    "AL": 4000,
    "AZ": 5600,
    "CA": 7250,
    "CO": 2900,
    "DE": 0,
    "FL": 6000,
    "GA": 4000,
    "IL": 6250,
    "IN": 7000,
    "KY": 6000,
    "LA": 4450,
    "MA": 6250,
    "MD": 6000,
    "MI": 6000,
    "MN": 6875,
    "MO": 4225,
    "MT": 0,
    "NC": 4750,
    "NH": 0,
    "NJ": 6625,
    "NY": 4000,
    "OH": 5750,
    "OR": 0,
    "PA": 6000,
    "SC": 6000,
    "TN": 7000,
    "TX": 6250,
    "VA": 5300,
    "WA": 6500,
    "WI": 5000,
}

_US_STATE_NAMES = {
    "ALASKA": "AK",
    "ALABAMA": "AL",
    "ARIZONA": "AZ",
    "CALIFORNIA": "CA",
    "COLORADO": "CO",
    "DELAWARE": "DE",
    "FLORIDA": "FL",
    "GEORGIA": "GA",
    "ILLINOIS": "IL",
    "INDIANA": "IN",
    "KENTUCKY": "KY",
    "LOUISIANA": "LA",
    "MASSACHUSETTS": "MA",
    "MARYLAND": "MD",
    "MICHIGAN": "MI",
    "MINNESOTA": "MN",
    "MISSOURI": "MO",
    "MONTANA": "MT",
    "NORTH CAROLINA": "NC",
    "NEW HAMPSHIRE": "NH",
    "NEW JERSEY": "NJ",
    "NEW YORK": "NY",
    "OHIO": "OH",
    "OREGON": "OR",
    "PENNSYLVANIA": "PA",
    "SOUTH CAROLINA": "SC",
    "TENNESSEE": "TN",
    "TEXAS": "TX",
    "VIRGINIA": "VA",
    "WASHINGTON": "WA",
    "WISCONSIN": "WI",
}

# Country code → parts per 100_000. Canada is federal GST only (no PST/HST).
_COUNTRY_PPM = {
    "AT": 20000,
    "AU": 10000,
    "BE": 21000,
    "CA": 5000,
    "CH": 8100,
    "DE": 19000,
    "ES": 21000,
    "FR": 20000,
    "GB": 20000,
    "IE": 23000,
    "IT": 22000,
    "MX": 16000,
    "NL": 21000,
    "NO": 25000,
    "NZ": 15000,
    "PL": 23000,
    "SE": 25000,
    "SG": 9000,
}


def country_code(country):
    letters = "".join(ch for ch in str(country or "").upper() if ch.isalpha())
    return letters[:2]


def us_state_code(region):
    text = " ".join(str(region or "").replace(".", " ").split())
    if not text:
        return ""
    upper = text.upper()
    named = _US_STATE_NAMES.get(upper)
    if named:
        return named
    compact = "".join(ch for ch in upper if ch.isalpha())
    if compact in _US_STATE_PPM:
        return compact
    return ""


def builtin_rate_book():
    """Default tables. Admin overrides in settings replace individual cells."""
    return {"us": dict(_US_STATE_PPM), "country": dict(_COUNTRY_PPM)}


def tax_rate_ppm(country, region, rates=None):
    """Return the provisional rate in parts per 100_000, or 0 when unknown.

    ``rates`` is an optional admin book ``{"us": {"CA": ppm}, "country": {"JP": ppm}}``.
    A present key replaces the builtin cell, including an explicit 0.
    """
    code = country_code(country)
    book = rates if isinstance(rates, dict) else {}
    us_over = book.get("us") if isinstance(book.get("us"), dict) else {}
    country_over = book.get("country") if isinstance(book.get("country"), dict) else {}
    if code == "US":
        state = us_state_code(region)
        if not state:
            return 0
        if state in us_over:
            return int(us_over[state])
        return int(_US_STATE_PPM.get(state, 0))
    if code in country_over:
        return int(country_over[code])
    return int(_COUNTRY_PPM.get(code, 0))


def estimate_tax_cents(taxable_cents, country, region, rates=None):
    """Half-up tax in merchandise cents. 0 when the rate or the base is 0."""
    taxable = max(0, int(taxable_cents or 0))
    ppm = tax_rate_ppm(country, region, rates)
    if taxable <= 0 or ppm <= 0:
        return 0
    return (taxable * ppm + 50_000) // 100_000


def _ppm_map(raw):
    found = {}
    if not isinstance(raw, dict):
        return found
    for key, value in raw.items():
        code = "".join(ch for ch in str(key or "").upper() if ch.isalpha())[:8]
        if not code:
            continue
        try:
            ppm = int(value)
        except (TypeError, ValueError):
            continue
        found[code] = max(0, min(100_000, ppm))
    return found


def load_tax_rates(conn):
    """Admin overrides only. None means every cell uses the builtin table."""
    try:
        row = conn.execute("select value from settings where key = 'tax_rates'").fetchone()
    except Exception:
        return None
    if row is None or not row["value"]:
        return None
    try:
        raw = json.loads(row["value"])
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(raw, dict):
        return None
    book = {"us": _ppm_map(raw.get("us")), "country": _ppm_map(raw.get("country"))}
    if not book["us"] and not book["country"]:
        return None
    return book


def save_tax_rates(conn, book):
    payload = {
        "us": _ppm_map((book or {}).get("us")),
        "country": _ppm_map((book or {}).get("country")),
    }
    encoded = json.dumps(payload, sort_keys=True)
    conn.execute(
        """
        insert into settings (key, value) values ('tax_rates', ?)
        on conflict(key) do update set value = excluded.value
        """,
        (encoded,),
    )


def percent_to_ppm(raw):
    """Parse an admin percent field. None means the field was left blank."""
    text = str(raw or "").strip().replace("%", "").replace(",", "")
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    ppm = int(round(value * 1000))
    return max(0, min(100_000, ppm))


def ppm_to_percent(ppm):
    text = f"{int(ppm) / 1000:.3f}".rstrip("0").rstrip(".")
    return text or "0"
