"""Provisional checkout tax estimates.

Not a compliance engine and not a filing position. Rates are state-level (US)
or country-level placeholders so checkout can show a tax line before a real
tax provider is connected. Combined local / city rates are not included.

Taxable base (merchandise cents, same unit as ``orders.merchandise_cents``):

    goods after tier, lucky, and coupon discounts
    + shipping

Store credit (balance) does not reduce the base. ``gift_wrap`` is not a charge
and is not taxed on its own.

``tax_cents`` is an estimate stored on the order. It is **not** added to
``due_cents`` / ``due_local``. Those stay the amount charged today, which is
what ``build_quote`` already returns. The quote API echoes the same split
(``tax_included_in_due`` is false) so a later UI can render the line without
changing what the payment gateway captures.

US region ``CA`` is California. Country ``CA`` is Canada (GST only).
US region ``DE`` is Delaware (no state sales tax). Country ``DE`` is Germany.
A country or state missing from the tables estimates as 0, including Japan,
so the existing yen checkout total is unchanged.
"""

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


def tax_rate_ppm(country, region):
    """Return the provisional rate in parts per 100_000, or 0 when unknown."""
    code = country_code(country)
    if code == "US":
        state = us_state_code(region)
        if not state:
            return 0
        return int(_US_STATE_PPM.get(state, 0))
    return int(_COUNTRY_PPM.get(code, 0))


def estimate_tax_cents(taxable_cents, country, region):
    """Half-up tax in merchandise cents. 0 when the rate or the base is 0."""
    taxable = max(0, int(taxable_cents or 0))
    ppm = tax_rate_ppm(country, region)
    if taxable <= 0 or ppm <= 0:
        return 0
    return (taxable * ppm + 50_000) // 100_000
