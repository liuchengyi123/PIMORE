import ipaddress
import os
import re

import httpx

_POSTAL_COUNTRIES = {"US", "GB", "CA", "DE", "FR", "ES", "PT", "BR", "MX", "JP"}


def postal_fields(body):
    places = body.get("places") if isinstance(body, dict) else None
    if not places:
        return {}
    place = places[0]
    return {
        "city": place.get("place name") or "",
        "region": place.get("state abbreviation") or place.get("state") or "",
    }


# House number follows the street in these countries. Elsewhere it leads.
_NUMBER_AFTER = {
    "DE", "AT", "NL", "CH", "BE", "PL", "CZ", "IT", "ES", "SE", "NO", "DK", "FI",
    "JP", "CN", "KR", "TW", "BR",
}
# These forms keep the number, or the district, in its own box.
_SPLIT_NUMBER = {"BR", "MX", "NL"}
_SPLIT_DISTRICT = {"BR", "MX", "CN", "TW", "HK", "MO"}


def here_fields(body):
    address = body.get("address") if isinstance(body, dict) else None
    if not isinstance(address, dict):
        return {}
    country = (address.get("country_code") or "").upper()
    city = address.get("city") or address.get("town") or address.get("village") or address.get("hamlet") or ""
    region = address.get("state") or address.get("province") or address.get("county") or ""
    road = address.get("road") or ""
    number = address.get("house_number") or ""
    district = (
        address.get("suburb")
        or address.get("neighbourhood")
        or address.get("quarter")
        or address.get("city_district")
        or ""
    )
    if country in _SPLIT_NUMBER:
        line = road
    elif country in _NUMBER_AFTER:
        line = " ".join(part for part in (road, number) if part)
        number = ""
    else:
        line = " ".join(part for part in (number, road) if part)
        number = ""
    if country not in _SPLIT_DISTRICT:
        district = ""
    return {
        "city": city,
        "region": region,
        "postal": address.get("postcode") or "",
        "country": country,
        "line": line,
        "number": number,
        "district": district,
    }


def lookup_postal(country, code):
    country = (country or "").strip().upper()[:2]
    code = re.sub(r"[^A-Za-z0-9 -]", "", code or "")[:12].strip()
    if country not in _POSTAL_COUNTRIES or len(code) < 2:
        return {}
    try:
        response = httpx.get(
            f"https://api.zippopotam.us/{country.lower()}/{code.replace(' ', '')}",
            timeout=6,
            headers={"User-Agent": "HarborShop/1.0"},
        )
        if response.status_code != 200:
            return {}
        return postal_fields(response.json())
    except Exception:
        return {}


def lookup_here(lat, lon):
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return {}
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return {}
    try:
        response = httpx.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json", "addressdetails": 1},
            timeout=6,
            headers={"User-Agent": "HarborShop/1.0"},
        )
        if response.status_code != 200:
            return {}
        return here_fields(response.json())
    except Exception:
        return {}


_LANG_COUNTRY = {
    "zh": "CN",
    "ja": "JP",
    "de": "DE",
    "fr": "FR",
    "es": "ES",
    "pt": "BR",
    "en": "US",
}


def accept_language_country(header):
    """Map Accept-Language to a store country. Language follows country elsewhere."""
    raw = (header or "").strip()
    if not raw:
        return ""
    for part in raw.split(","):
        tag = part.split(";", 1)[0].strip().lower().replace("_", "-")
        if not tag:
            continue
        primary = tag.split("-", 1)[0]
        # Prefer region when present: zh-TW → TW, zh-HK → HK, zh-CN → CN
        if len(tag) >= 5 and tag[2] == "-":
            region = tag.split("-", 1)[1].upper()[:2]
            if region.isalpha():
                return region
        if primary in _LANG_COUNTRY:
            return _LANG_COUNTRY[primary]
    return ""


_reader = None
_reader_ready = False


def _db_paths():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    return [
        os.environ.get("GEOLITE2_PATH", ""),
        os.path.join(root, "data", "dbip-country-lite.mmdb"),
        "/opt/harbor/data/dbip-country-lite.mmdb",
    ]


def _database():
    global _reader, _reader_ready
    if _reader_ready:
        return _reader
    _reader_ready = True
    try:
        import maxminddb
    except Exception:
        return None
    for path in _db_paths():
        if not path or not os.path.isfile(path):
            continue
        try:
            _reader = maxminddb.open_database(path)
            return _reader
        except Exception:
            continue
    return None


def _public_ip(host):
    text = str(host or "").split("%", 1)[0].strip()
    if not text:
        return ""
    try:
        ip = ipaddress.ip_address(text)
    except ValueError:
        return ""
    if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local or ip.is_unspecified:
        return ""
    return str(ip)


def client_ip(request):
    """Public client address. Proxy-rewritten client.host wins over a spoofable header."""
    host = request.client.host if getattr(request, "client", None) else ""
    public = _public_ip(host)
    if public:
        return public
    forwarded = str(request.headers.get("x-forwarded-for") or "").split(",", 1)[0].strip()
    public = _public_ip(forwarded)
    if public:
        return public
    return _public_ip(request.headers.get("x-real-ip") or "")


def lookup_country(ip):
    """ISO country from the IP database. Empty when the address is not a public IP."""
    public = _public_ip(ip)
    if not public:
        return ""
    reader = _database()
    if reader is None:
        return ""
    try:
        record = reader.get(public) or {}
    except Exception:
        return ""
    country = record.get("country") if isinstance(record, dict) else None
    code = str((country or {}).get("iso_code") or "").upper()[:2]
    if len(code) == 2 and code.isalpha():
        return code
    return ""


def country_for(request):
    """Store country follows the visitor IP. Language never selects the currency.

    A public address is authoritative, including when the URL still says
    ?country= or an old locale cookie is present. Localhost may pass ?country=
    so the shop can be previewed. Accept-Language is not a country.
    """
    code = lookup_country(client_ip(request))
    if code:
        return code
    if not client_ip(request):
        query = str(request.query_params.get("country") or "").strip().upper()[:2]
        if len(query) == 2 and query.isalpha():
            return query
    return "US"
