"""Match a typed or pasted address against the town library.

The library is regions and towns for the countries in divisions.json, plus
every Chinese province, city, and district. It does not contain street names.
A street that is not a town stays whatever the shopper typed.
"""
import re
import threading

from shop.cn_areas import cities as cn_city_names
from shop.cn_areas import districts as cn_district_names
from shop.cn_areas import provinces as cn_province_names
from shop.divisions import divisions

_LOCK = threading.Lock()
_BOOKS = None

_POSTAL = {
    "US": r"\b\d{5}(?:-\d{4})?\b",
    "CA": r"\b[A-Za-z]\d[A-Za-z][ -]?\d[A-Za-z]\d\b",
    "GB": r"\b[A-Za-z]{1,2}\d[A-Za-z\d]?\s*\d[A-Za-z]{2}\b",
    "JP": r"\b\d{3}-?\d{4}\b",
    "BR": r"\b\d{5}-?\d{3}\b",
    "PT": r"\b\d{4}-\d{3}\b",
    "NL": r"\b\d{4}\s?[A-Za-z]{2}\b",
    "CN": r"(?<!\d)\d{6}(?!\d)",
    "DE": r"\b\d{5}\b",
    "FR": r"\b\d{5}\b",
    "ES": r"\b\d{5}\b",
    "IT": r"\b\d{5}\b",
    "AU": r"\b\d{4}\b",
    "KR": r"\b\d{5}\b",
}


def _books():
    global _BOOKS
    if _BOOKS is not None:
        return _BOOKS
    with _LOCK:
        if _BOOKS is not None:
            return _BOOKS
        books = {}
        for country, block in divisions().items():
            regions = []
            cities = []
            for region in block["regions"]:
                regions.append({"code": region["code"], "name": region["name"], "en": region["name"]})
                for city in region["cities"]:
                    cities.append({
                        "city": city,
                        "en": city,
                        "region": region["code"],
                        "region_name": region["name"],
                        "region_en": region["name"],
                    })
            books[country] = {"regions": regions, "cities": cities, "districts": []}
        cn_regions = [{"code": name, "name": name, "en": name} for name in cn_province_names()]
        cn_cities = []
        cn_districts = []
        for province in cn_province_names():
            for city in cn_city_names(province):
                cn_cities.append({
                    "city": city,
                    "en": city,
                    "region": province,
                    "region_name": province,
                    "region_en": province,
                })
                for name in cn_district_names(province, city):
                    cn_districts.append({"city": city, "name": name, "en": name})
        books["CN"] = {"regions": cn_regions, "cities": cn_cities, "districts": cn_districts}
        _BOOKS = books
        return _BOOKS


def _book(country):
    return _books().get((country or "").strip().upper()[:2]) or {"regions": [], "cities": [], "districts": []}


def suggest_places(country, query, region="", lang="", limit=8):
    """Towns whose name starts with, or contains, what the shopper typed."""
    text = (query or "").strip()
    folded = text.casefold()
    shortest = 1 if any("\u4e00" <= ch <= "\u9fff" for ch in text) else 2
    if len(folded) < shortest:
        return []
    book = _book(country)
    region_filter = (region or "").strip().casefold()
    zh = str(lang or "").lower().startswith("zh")
    hits = []
    for row in book["cities"]:
        if region_filter and region_filter not in {
            row["region"].casefold(),
            row["region_name"].casefold(),
            row["region_en"].casefold(),
        }:
            continue
        keys = [row["city"].casefold(), row["en"].casefold()]
        rank = None
        for key in keys:
            if not key:
                continue
            if key.startswith(folded):
                rank = 0
                break
            if folded in key:
                rank = 1
        if rank is None:
            continue
        city_label = row["city"] if zh or not row["en"] else row["en"]
        region_label = row["region_name"] if zh or not row["region_en"] else row["region_en"]
        hits.append((rank, len(row["city"]), city_label.casefold(), {
            "city": row["city"],
            "region": row["region"],
            "region_name": row["region_name"],
            "label": f"{city_label}, {region_label}",
        }))
    hits.sort(key=lambda item: (item[0], item[1], item[2]))
    out = []
    seen = set()
    for _, _, _, row in hits:
        key = (row["city"], row["region"])
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
        if len(out) >= limit:
            break
    return out


def _take_pattern(pattern, text):
    if not pattern:
        return "", text
    match = re.search(pattern, text, flags=re.I)
    if not match:
        return "", text
    found = match.group(0)
    return found.strip(), (text[:match.start()] + " " + text[match.end():]).strip()


def _take_phone(text):
    match = re.search(r"(?<!\d)(?:\+\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-])?\d[\d\s()-]{6,}\d(?!\d)", text)
    if not match:
        return "", text
    found = match.group(0).strip()
    digits = re.sub(r"\D", "", found)
    if len(digits) < 8:
        return "", text
    return found, (text[:match.start()] + " " + text[match.end():]).strip()


def _region_hit(book, text):
    folded = text.casefold()
    best = None
    for region in book["regions"]:
        for needle in (region["name"], region.get("en") or ""):
            if len(needle) < 3:
                continue
            if needle.casefold() in folded and (best is None or len(needle) > len(best[0])):
                best = (needle, region)
        code = region["code"]
        if re.search(rf"(?<![A-Za-z]){re.escape(code)}(?![A-Za-z])", text):
            if best is None or len(code) > len(best[0]):
                best = (code, region)
    return best


def _city_hit(book, text, region_code=""):
    folded = text.casefold()
    best = None
    for row in book["cities"]:
        if region_code and row["region"] != region_code:
            continue
        for needle in (row["city"], row["en"]):
            if len(needle) < 3 or needle.casefold() not in folded:
                continue
            if best is None or len(needle) > len(best[0]):
                best = (needle, row)
    return best


def _district_hit(book, city, text):
    folded = text.casefold()
    best = None
    for row in book["districts"]:
        if row["city"] != city:
            continue
        for needle in (row["name"], row["en"]):
            if len(needle) < 2 or needle.casefold() not in folded:
                continue
            if best is None or len(needle) > len(best[0]):
                best = (needle, row["name"])
    return best


def _take_name(text):
    stripped = text.strip()
    han = re.match(r"^[\u4e00-\u9fff]{2,4}(?=[^\u4e00-\u9fff]|$)", stripped)
    if han:
        return han.group(0), stripped[han.end():].strip()
    latin = re.match(r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b", stripped)
    if latin and re.search(r"\d", stripped[latin.end():]):
        return latin.group(1), stripped[latin.end():].strip()
    return "", stripped


def read_address(country, text):
    """Split a pasted block into the fields this country uses. Streets stay as typed."""
    country = (country or "").strip().upper()[:2]
    work = re.sub(r"\s+", " ", (text or "").strip())
    postal, work = _take_pattern(_POSTAL.get(country, ""), work)
    phone, work = _take_phone(work)
    book = _book(country)
    region_found = _region_hit(book, work)
    region_code = region_found[1]["code"] if region_found else ""
    city_found = _city_hit(book, work, region_code) or _city_hit(book, work, "")
    city = ""
    if city_found:
        needle, row = city_found
        city = row["city"]
        region_code = row["region"]
        work = re.sub(re.escape(needle), " ", work, count=1, flags=re.I)
        for alias in (row["region_name"], row["region_en"], row["region"]):
            if alias and alias.casefold() in work.casefold():
                work = re.sub(re.escape(alias), " ", work, count=1, flags=re.I)
                break
    elif region_found:
        needle, region = region_found
        region_code = region["code"]
        work = re.sub(re.escape(needle), " ", work, count=1, flags=re.I)
    district = ""
    district_found = _district_hit(book, city, work) if city else None
    if district_found:
        district = district_found[1]
        work = re.sub(re.escape(district_found[0]), " ", work, count=1, flags=re.I)
    name, work = _take_name(work)
    line = re.sub(r"\s+", " ", work).strip(" ,，、。.")
    return {
        "name": name,
        "phone": re.sub(r"\s+", " ", phone).strip(),
        "postal": postal,
        "region": region_code,
        "city": city,
        "district": district,
        "line": line,
    }
