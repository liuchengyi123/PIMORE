_JA = {"JP"}
_DE = {"DE", "AT"}
_FR = {"FR"}
_ES = {
    "ES", "MX", "AR", "CO", "CL", "PE", "VE", "EC", "GT", "CU",
    "BO", "DO", "HN", "PY", "SV", "NI", "CR", "PA", "UY", "PR",
}
_PT = {"PT", "BR"}
_ZH_HANS = {"CN", "SG"}
_ZH_HANT = {"TW", "HK", "MO"}

_EUR = {
    "AT", "BE", "HR", "CY", "EE", "FI", "FR", "DE", "GR", "IE",
    "IT", "LV", "LT", "LU", "MT", "NL", "PT", "SK", "SI", "ES",
}
_EU_SHIP = {
    "GB", "IE", "NO", "CH", "IS",
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IT", "LV", "LT", "LU", "MT", "NL", "PL",
    "PT", "RO", "SK", "SI", "ES", "SE",
}


def resolve(country):
    code = (country or "").upper()
    if code in _JA:
        lang = "ja"
    elif code in _DE:
        lang = "de"
    elif code in _FR:
        lang = "fr"
    elif code in _ES:
        lang = "es"
    elif code in _PT:
        lang = "pt"
    elif code in _ZH_HANT:
        lang = "zh-Hant"
    elif code in _ZH_HANS:
        lang = "zh"
    else:
        lang = "en"
    if code == "GB":
        currency = "GBP"
    elif code == "JP":
        currency = "JPY"
    elif code == "BR":
        currency = "BRL"
    elif code == "MX":
        currency = "MXN"
    elif code == "CA":
        currency = "CAD"
    elif code == "TW":
        currency = "TWD"
    elif code == "HK":
        currency = "HKD"
    elif code in {"CN", "MO"}:
        currency = "CNY"
    elif code in _EUR:
        currency = "EUR"
    else:
        currency = "USD"
    return lang, currency


def shipping_tier(country):
    code = (country or "").upper()
    if code == "JP":
        return "JP"
    if code in {"US", "CA"}:
        return "USCA"
    if code in {"MX", "BR"}:
        return "MXBR"
    if code in _EU_SHIP:
        return "EU"
    return "USCA"
