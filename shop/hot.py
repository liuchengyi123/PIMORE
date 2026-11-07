import json
import re
import time
from datetime import date, timedelta
from html import unescape

import httpx

from shop.locale import resolve
from shop.markets import LABELS, MARKETS

DOMAINS = {
    "US": "www.amazon.com",
    "CA": "www.amazon.ca",
    "GB": "www.amazon.co.uk",
    "DE": "www.amazon.de",
    "FR": "www.amazon.fr",
    "ES": "www.amazon.es",
    "BR": "www.amazon.com.br",
    "MX": "www.amazon.com.mx",
    "JP": "www.amazon.co.jp",
}
PATHS = (
    "/gp/bestsellers/kitchen",
    "/gp/bestsellers/home-garden",
    "/gp/bestsellers/hpc",
    "/gp/bestsellers/pet-supplies",
)
LANG_HEADER = {
    "US": "en-US,en;q=0.9",
    "CA": "en-CA,en;q=0.9",
    "GB": "en-GB,en;q=0.9",
    "DE": "de-DE,de;q=0.9",
    "FR": "fr-FR,fr;q=0.9",
    "ES": "es-ES,es;q=0.9",
    "BR": "pt-BR,pt;q=0.9",
    "MX": "es-MX,es;q=0.9",
    "JP": "ja-JP,ja;q=0.9",
}
STOP = {
    "with", "from", "that", "this", "your", "pack", "size", "inch", "inches",
    "piece", "pieces", "count", "black", "white", "large", "small", "home",
    "kitchen", "bathroom", "bedroom", "amazon", "basics", "premium", "heavy",
    "duty", "stainless", "steel", "plastic", "rubber", "soft", "hard",
    "und", "mit", "fur", "für", "der", "die", "das", "ein", "eine",
    "pour", "avec", "dans", "les", "des", "une",
    "para", "con", "los", "las", "una", "del",
    "para", "com", "uma", "dos", "das",
}
FOLD = {
    "stopper": "stop",
    "organiser": "organizer",
    "organisers": "organizer",
    "organizers": "organizer",
}


def stale(conn, today=None):
    today = today or date.today()
    rows = conn.execute(
        "select country, min(fetched_at) as day from hot_titles group by country"
    ).fetchall()
    found = {row["country"]: row["day"] for row in rows}
    for country in DOMAINS:
        day = found.get(country)
        if not day:
            return True
        try:
            fetched = date.fromisoformat(str(day)[:10])
        except ValueError:
            return True
        if fetched < today - timedelta(days=7):
            return True
    return False


def parse_titles(html):
    found = []
    seen = set()
    pattern = re.compile(r'class="[^"]*p13n-sc-css-line-clamp[^"]*"[^>]*>(.*?)</', re.I | re.S)
    for match in pattern.finditer(html or ""):
        text = unescape(re.sub(r"<[^>]+>", " ", match.group(1)))
        text = " ".join(text.split())
        key = text.casefold()
        if len(text) < 12 or key in seen:
            continue
        if "out of 5 stars" in key or text.startswith("$"):
            continue
        seen.add(key)
        found.append(text)
        if len(found) >= 30:
            break
    return found


def refresh_titles(conn, fetch=None, today=None):
    today = (today or date.today()).isoformat()
    fetch = fetch or _fetch
    saved = 0
    have = {
        row["country"]
        for row in conn.execute(
            "select country, count(*) as n from hot_titles group by country"
        ).fetchall()
        if row["n"] >= 8
    }
    for country, domain in DOMAINS.items():
        if country in have:
            continue
        titles = []
        for path in PATHS:
            try:
                html = fetch(f"https://{domain}{path}", LANG_HEADER[country])
            except Exception:
                continue
            titles.extend(parse_titles(html))
            time.sleep(0.6)
        unique = list(dict.fromkeys(titles))
        if len(unique) < 8:
            continue
        conn.execute("delete from hot_titles where country = ?", (country,))
        for title in unique:
            conn.execute(
                "insert into hot_titles (country, title, fetched_at) values (?, ?, ?)",
                (country, title, today),
            )
        saved += 1
    return saved


def _fetch(url, language):
    response = httpx.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": language,
        },
        timeout=25,
        follow_redirects=True,
    )
    response.raise_for_status()
    return response.text


def _fold(token):
    token = FOLD.get(token, token)
    if len(token) > 4 and token.endswith("s") and not token.endswith("ss") and token[-2] != "e":
        token = FOLD.get(token[:-1], token[:-1])
    return token


def _profile(text):
    words = [
        _fold(token)
        for token in re.findall(r"[a-z0-9\u00c0-\u024f]{4,}", str(text or "").casefold())
    ]
    tokens = {token for token in words if token not in STOP}
    bigrams = {
        f"{left} {right}"
        for left, right in zip(words, words[1:])
        if left not in STOP and right not in STOP
    }
    cjk = set(re.findall(r"[\u3040-\u30ff\u4e00-\u9fff]{3,}", str(text or "")))
    return tokens, bigrams, cjk


def _product_text(row, lang):
    try:
        names = json.loads(row.get("names") or "{}")
    except json.JSONDecodeError:
        names = {}
    if not isinstance(names, dict):
        names = {}
    return " ".join(str(names.get(key) or "") for key in (lang, "en"))


def match_score(product_text, hot_profiles):
    tokens, bigrams, cjk = _profile(product_text)
    best = 0
    for hot_tokens, hot_bigrams, hot_cjk, raw in hot_profiles:
        shared = bigrams & hot_bigrams
        long_words = {token for token in tokens & hot_tokens if len(token) >= 12}
        if shared:
            best = max(best, 2 + len(shared))
        elif long_words:
            best = max(best, 2)
        elif any(len(chunk) >= 4 and chunk in raw for chunk in cjk):
            best = max(best, 3)
        elif any(len(piece) >= 4 and piece in product_text for piece in hot_cjk):
            best = max(best, 3)
    return best


def build_scores(rows, titles_by_country):
    scores = {}
    for country, titles in titles_by_country.items():
        lang = resolve(country)[0]
        profiles = []
        for title in titles:
            tokens, bigrams, cjk = _profile(title)
            profiles.append((tokens, bigrams, cjk, title))
        bucket = {}
        for row in rows:
            score = match_score(_product_text(row, lang), profiles)
            if score:
                bucket[row["sku"]] = score
        scores[country] = bucket
    return scores


def hot_line(scores, ready):
    if not ready:
        return "热销同款　还没有"
    counts = []
    for code in MARKETS:
        if code not in DOMAINS:
            continue
        counts.append(f"{LABELS[code]} {len((scores or {}).get(code) or {})}")
    body = "　".join(counts)
    if not any(len((scores or {}).get(code) or {}) for code in DOMAINS):
        return "热销同款　这一周没有对上"
    return f"热销同款　{body}"
