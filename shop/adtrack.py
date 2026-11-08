# -*- coding: utf-8 -*-
"""Harbor ad platform tracking: click IDs, pixels config, server 回传, link builder."""
from __future__ import annotations

import hashlib
import queue
import re
import json
import os
import threading
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

SEG_PRESETS = [
    ("flash", "闪购通用"),
    ("kitchen", "厨房"),
    ("storage", "收纳"),
    ("cleaning", "清洁"),
    ("bathroom", "卫浴"),
    ("laundry", "洗衣"),
    ("home", "家居百货"),
    ("beauty", "个护美妆"),
    ("pet", "宠物"),
    ("desk", "桌面办公"),
]

# Catalog category + title keywords per seg (EN/ZH). Category match is strongest.
SEG_CATEGORIES = {
    "storage": ["storage"],
    "kitchen": ["kitchen"],
    "cleaning": ["cleaning"],
    "bathroom": [],  # keyword-led (catalog tags sparse)
    "laundry": [],
    "home": ["storage", "kitchen", "desk"],
    "beauty": ["personal"],
    "pet": ["pet"],
    "desk": ["desk", "stationery"],
    "flash": [],
}

SEG_KEYWORDS = {
    "storage": [
        "storage", "organizer", "organiser", "box", "bin", "shelf", "rack", "hook",
        "hanger", "drawer", "cabinet", "basket", "holder", "container", "收纳", "整理",
        "置物", "架子", "挂钩", "箱", "盒",
    ],
    "kitchen": [
        "kitchen", "cook", "cutter", "knife", "spoon", "fork", "bowl", "pot", "pan",
        "chopstick", "garlic", "food", "dish", "cup", "mug", "厨房", "厨", "筷", "碗",
        "刀", "锅", "勺",
    ],
    "cleaning": [
        "clean", "cleaner", "wipe", "brush", "mop", "dustpan", "sponge", "scrub",
        "dust", "garbage", "trash", "清洁", "刷", "拖把", "抹布", "扫",
    ],
    "bathroom": [
        "bath", "bathroom", "toilet", "shower", "soap", "sink", "towel", "washroom",
        "卫浴", "浴室", "马桶", "淋浴", "牙刷", "漱",
    ],
    "laundry": [
        "laundry", "clothes", "hanger", "drying", "clothespin", "washing machine",
        "laundry ball", "衣架", "晾衣", "洗衣", "防缠", "衣夹", "洗衣球",
    ],
    "home": [
        "home", "household", "house", "living", "家居", "家用", "百货",
    ],
    "beauty": [
        "beauty", "cosmetic", "makeup", "skin", "nail", "hair", "facial", "mirror",
        "美妆", "护肤", "化妆", "个护",
    ],
    "pet": ["pet", "cat", "dog", "宠物", "猫", "狗"],
    "desk": ["desk", "office", "pen", "stationery", "办公", "笔", "桌面"],
    "flash": [],
}


def normalize_seg(seg: str) -> str:
    text = _clip(seg, 64).lower()
    if not text:
        return ""
    # allow utm_content values that match presets
    aliases = {
        "organise": "storage",
        "organize": "storage",
        "organizer": "storage",
        "organiser": "storage",
        "收纳": "storage",
        "kitchenware": "kitchen",
        "cook": "kitchen",
        "clean": "cleaning",
        "bath": "bathroom",
        "wash": "laundry",
        "cosmetic": "beauty",
    }
    if text in dict(SEG_PRESETS) or text in SEG_CATEGORIES:
        return text
    return aliases.get(text, text)


def item_text_blob(item_or_row: dict, lang: str = "en") -> str:
    parts = [
        str(item_or_row.get("category") or ""),
        str(item_or_row.get("sku") or ""),
        str(item_or_row.get("name") or ""),
        str(item_or_row.get("campaign_kind") or ""),
    ]
    names = item_or_row.get("names")
    if isinstance(names, str):
        try:
            names = json.loads(names)
        except Exception:
            names = None
    if isinstance(names, dict):
        parts.extend(str(v) for v in names.values() if v)
        parts.append(str(names.get(lang) or ""))
    return " ".join(parts).lower()


def seg_match_score(item_or_row: dict, seg: str, lang: str = "en") -> int:
    """Higher = better match. 0 = no match."""
    seg = normalize_seg(seg)
    if not seg or seg == "flash":
        return 0
    cat = str(item_or_row.get("category") or "").strip().lower()
    blob = item_text_blob(item_or_row, lang)
    score = 0
    cats = SEG_CATEGORIES.get(seg) or []
    keyword_led = seg in {"bathroom", "laundry", "beauty", "home"} and not cats
    if cat and cat == seg:
        score += 100
    elif cat and cat in cats:
        score += 80
    hits = 0
    for kw in SEG_KEYWORDS.get(seg) or []:
        k = (kw or "").lower()
        if k and k in blob:
            hits += 1
            if hits >= 3:
                break
    if hits:
        score += 20 + hits * 15
    elif score == 0 and seg in blob:
        score += 5
    # keyword-led segs need at least one keyword / seg token hit
    if keyword_led and hits == 0 and seg not in blob and score < 100:
        return 0
    return score


CLICK_KEYS = (
    "fbclid",
    "gclid",
    "wbraid",
    "gbraid",
    "ttclid",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
    "seg",
    "acct",
    "adgroup",
    "adset_id",
    "adgroup_id",
    "campaign_id",
    "ad_id",
)

ENV_MAP = {
    "meta_pixel_id": "META_PIXEL_ID",
    "meta_capi_token": "META_CAPI_TOKEN",
    "meta_test_code": "META_TEST_EVENT_CODE",
    "google_aw_id": "GOOGLE_AW_ID",
    "google_measurement_id": "GOOGLE_MEASUREMENT_ID",
    "google_api_secret": "GOOGLE_API_SECRET",
    "tiktok_pixel_id": "TIKTOK_PIXEL_ID",
    "tiktok_access_token": "TIKTOK_ACCESS_TOKEN",
    "tiktok_test_code": "TIKTOK_TEST_EVENT_CODE",
}

SETTING_KEY = "ad_platform"

SCHEMA_EXTRA = """
create table if not exists ad_attribution (
    order_id text primary key,
    payload text not null default "{}",
    created_at text not null default ""
);
create table if not exists ad_event_log (
    id integer primary key,
    created_at text not null,
    platform text not null,
    event_name text not null,
    order_id text not null default "",
    event_id text not null default "",
    ok integer not null default 0,
    detail text not null default "",
    acct text not null default '',
    http_status integer not null default 0
);
create table if not exists ad_funnel (
    id integer primary key,
    created_at text not null,
    day text not null,
    kind text not null,
    seg text not null default "",
    utm_source text not null default "",
    utm_campaign text not null default "",
    sku text not null default "",
    order_id text not null default "",
    visitor text not null default "",
    extra text not null default ""
);
create index if not exists idx_ad_funnel_day_kind on ad_funnel(day, kind);
create index if not exists idx_ad_funnel_seg on ad_funnel(seg, kind);
create table if not exists ad_accounts (
    id integer primary key,
    code text not null unique,
    platform text not null,
    name text not null,
    credentials text not null default "{}",
    send_ratio_pct real not null default 100,
    value_multiplier real not null default 1,
    enabled integer not null default 1,
    is_default integer not null default 0,
    created_at text not null default "",
    updated_at text not null default ""
);
create index if not exists idx_ad_accounts_platform on ad_accounts(platform, enabled);
create table if not exists ad_groups (
    acct text not null,
    adgroup text not null default '',
    platform text not null default '',
    acc integer not null default 0,
    day text not null default '',
    day_orders integer not null default 0,
    ratio_override real,
    target_cpa_override real,
    effective_ratio real,
    reason text not null default '',
    spend real not null default 0,
    prev_spend real not null default 0,
    real_orders integer not null default 0,
    sent_orders integer not null default 0,
    cpa real not null default 0,
    last_adjusted_at text not null default '',
    updated_at text not null default '',
    primary key (acct, adgroup)
);
create index if not exists idx_ad_event_log_lookup on ad_event_log(platform, event_name, event_id);
create index if not exists idx_ad_event_log_created on ad_event_log(created_at);
create table if not exists ad_ratio_history (
    id integer primary key,
    created_at text not null,
    acct text not null,
    adgroup text not null default '',
    ratio real not null default 100,
    reason text not null default '',
    spend real not null default 0,
    real_orders integer not null default 0,
    sent_orders integer not null default 0,
    cpa real not null default 0
);
create table if not exists ad_send_decision (
    order_id text primary key,
    acct text not null default '',
    adgroup text not null default '',
    send integer not null default 1,
    reason text not null default '',
    ratio real not null default 100,
    multiplier real not null default 1,
    created_at text not null default ''
);
"""


def ensure_tables(conn) -> None:
    if getattr(conn, "_ad_tables_ready", False):
        return
    conn.executescript(SCHEMA_EXTRA)
    try:
        cols = set()
        for row in conn.execute("pragma table_info(ad_funnel)").fetchall():
            try:
                cols.add(row["name"])
            except Exception:
                cols.add(row[1])
        if "acct" not in cols:
            conn.execute("alter table ad_funnel add column acct text not null default ''")
    except Exception:
        pass
    try:
        cols = set()
        for row in conn.execute("pragma table_info(ad_event_log)").fetchall():
            try:
                cols.add(row["name"])
            except Exception:
                cols.add(row[1])
        if "acct" not in cols:
            conn.execute("alter table ad_event_log add column acct text not null default ''")
        if "http_status" not in cols:
            conn.execute("alter table ad_event_log add column http_status integer not null default 0")
    except Exception:
        pass
    for name, ddl in (
        ("learning_min", "learning_min integer not null default 50"),
        ("daily_floor", "daily_floor integer not null default 5"),
        ("ratio_min", "ratio_min real not null default 60"),
        ("ratio_max", "ratio_max real not null default 100"),
        ("smart_enabled", "smart_enabled integer not null default 0"),
        ("target_cpa", "target_cpa real not null default 0"),
        ("stoploss_multiple", "stoploss_multiple real not null default 1.5"),
        ("stoploss_hours", "stoploss_hours real not null default 24"),
        ("smart_checked_at", "smart_checked_at text not null default ''"),
    ):
        _add_column(conn, "ad_accounts", name, ddl)
    _add_column(conn, "ad_groups", "stoploss_multiple_override", "stoploss_multiple_override real")
    _add_column(conn, "ad_groups", "stoploss_hours_override", "stoploss_hours_override real")
    _add_column(conn, "ad_groups", "stoploss_since", "stoploss_since text not null default ''")
    _add_column(conn, "ad_groups", "stoploss_active", "stoploss_active integer not null default 0")
    _add_column(conn, "orders", "adgroup", "adgroup text not null default ''")
    _add_column(conn, "orders", "ad_campaign", "ad_campaign text not null default ''")
    _add_column(conn, "orders", "ad_id", "ad_id text not null default ''")
    migrate_legacy_accounts(conn)
    try:
        order_cols = set()
        for row in conn.execute("pragma table_info(orders)").fetchall():
            try:
                order_cols.add(row["name"])
            except Exception:
                order_cols.add(row[1])
        # migrate() may call this before the shop schema creates orders.
        # Stay uncached until the throttle columns are actually present.
        if "adgroup" in order_cols and "ad_id" in order_cols:
            conn._ad_tables_ready = True
    except Exception:
        pass


def _add_column(conn, table: str, name: str, ddl: str) -> None:
    try:
        cols = set()
        for row in conn.execute(f"pragma table_info({table})").fetchall():
            try:
                cols.add(row["name"])
            except Exception:
                cols.add(row[1])
        if cols and name not in cols:
            conn.execute(f"alter table {table} add column {ddl}")
    except Exception:
        return


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _clip(value: Any, n: int = 256) -> str:
    text = str(value or "").strip()
    return text[:n]


def parse_cookie(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    out = {}
    for key in CLICK_KEYS:
        val = _clip(data.get(key), 512)
        if val:
            out[key] = val
    for key in ("fbp", "fbc", "ttp", "event_source_url", "client_ip", "client_ua", "external_id"):
        val = _clip(data.get(key), 512)
        if val:
            out[key] = val
    return out


def pack_cookie(data: dict) -> str:
    clean = {}
    for key, val in (data or {}).items():
        text = _clip(val, 512)
        if text:
            clean[key] = text
    return json.dumps(clean, ensure_ascii=False, separators=(",", ":"))


def clean_platform_id(value: Any) -> str:
    """Keep a real ad id. Leave unsubstituted Meta/TikTok macros empty."""
    text = _clip(value, 80)
    if not text or "{{" in text or "}}" in text or "__" in text:
        return ""
    if not re.fullmatch(r"[A-Za-z0-9_\-]{1,64}", text):
        return ""
    return text


def merge_from_request(existing: dict, params, headers=None) -> dict:
    merged = dict(existing or {})
    for key in CLICK_KEYS:
        val = _clip(params.get(key) if hasattr(params, "get") else "", 512)
        if val:
            merged[key] = val
    # utm_content can seed seg when seg absent
    if not merged.get("seg") and merged.get("utm_content"):
        merged["seg"] = _clip(merged["utm_content"], 64)
    fbclid = merged.get("fbclid")
    # Meta: fbc is fb.1.<unix-ms>.<fbclid>. Never invent one without a real fbclid.
    if fbclid and not _valid_fbc(merged.get("fbc")):
        merged["fbc"] = f"fb.1.{int(time.time() * 1000)}.{fbclid}"
    group = (
        clean_platform_id(merged.get("adset_id"))
        or clean_platform_id(merged.get("adgroup_id"))
        or clean_platform_id(merged.get("adgroup"))
    )
    merged.pop("adset_id", None)
    merged.pop("adgroup_id", None)
    if group:
        merged["adgroup"] = group
    else:
        merged.pop("adgroup", None)
    for key in ("campaign_id", "ad_id"):
        cleaned = clean_platform_id(merged.get(key))
        if cleaned:
            merged[key] = cleaned
        else:
            merged.pop(key, None)
    return merged


_FBC_RE = re.compile(r"^fb\.\d+\.\d{10,13}\.\S+$")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?<!\w)\+?\d[\d\-\s().]{6,}\d")
_TOKEN_RE = re.compile(
    r"((?:access_token|token|authorization|api_secret)(['\"=:\s]+))[^'\"&\s]+",
    re.I,
)
_EAA_RE = re.compile(r"\bEAA[A-Za-z0-9]{8,}")


def _valid_fbc(value: str | None) -> bool:
    text = _clip(value, 512)
    return bool(text and _FBC_RE.match(text))


def canonical_fbc(attrs: dict | None) -> str:
    """Use a stored _fbc, or derive fb.1.<ms>.<fbclid>. Never fabricate without fbclid."""
    attrs = attrs or {}
    fbc = _clip(attrs.get("fbc"), 512)
    if _valid_fbc(fbc):
        return fbc
    fbclid = _clip(attrs.get("fbclid"), 500)
    if not fbclid or any(ch.isspace() for ch in fbclid):
        return ""
    return f"fb.1.{int(time.time() * 1000)}.{fbclid}"


def apply_request_context(attrs, *, cookies=None, client_ip="", user_agent="", external_id=""):
    """Refresh IP / UA and copy browser click cookies. Does not invent fbc."""
    merged = dict(attrs or {})
    cookies = cookies or {}
    fbc = _clip(cookies.get("_fbc"), 512)
    if _valid_fbc(fbc):
        merged["fbc"] = fbc
    for src, dst in (("_fbp", "fbp"), ("_ttp", "ttp")):
        val = _clip(cookies.get(src), 512)
        if val and not merged.get(dst):
            merged[dst] = val
    ip = _clip(client_ip, 64)
    if ip:
        merged["client_ip"] = ip
    ua = _clip(user_agent, 512)
    if ua:
        merged["client_ua"] = ua
    ext = _clip(external_id, 128)
    if ext:
        merged["external_id"] = ext
    return merged


def redact_log(value: str) -> str:
    text = str(value or "")
    text = _EMAIL_RE.sub("[redacted]", text)
    text = _PHONE_RE.sub("[redacted]", text)
    text = _TOKEN_RE.sub(r"\1[redacted]", text)
    text = _EAA_RE.sub("[redacted]", text)
    return text[:180]



PLATFORMS = [
    ("meta", "Meta"),
    ("google", "Google"),
    ("tiktok", "TikTok"),
]

PLATFORM_FIELDS = {
    "meta": [
        ("meta_pixel_id", "Pixel ID", False),
        ("meta_capi_token", "CAPI Access Token", True),
        ("meta_test_code", "Test Event Code", False),
        ("meta_ad_account_id", "广告账户 ID（选填，拉消耗）", False),
    ],
    "google": [
        ("google_aw_id", "Google Ads AW ID", False),
        ("google_measurement_id", "GA4 Measurement ID", False),
        ("google_api_secret", "MP API Secret", True),
    ],
    "tiktok": [
        ("tiktok_pixel_id", "Pixel ID", False),
        ("tiktok_access_token", "Events API Token", True),
        ("tiktok_test_code", "Test Event Code", False),
        ("tiktok_advertiser_id", "广告主 ID（选填，拉消耗）", False),
    ],
}


def _row_dict(row) -> dict:
    if row is None:
        return {}
    try:
        return dict(row)
    except Exception:
        return {}


def _parse_creds(raw) -> dict:
    if isinstance(raw, dict):
        return dict(raw)
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _slug_code(platform: str, name: str, taken: set) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", (name or "acct").lower()).strip("_") or "acct"
    platform = _clip(platform, 16).lower()
    prefix = {"meta": "meta", "google": "gg", "tiktok": "tt"}.get(platform, platform[:2] or "ad")
    candidate = f"{prefix}_{base}"[:40]
    if candidate not in taken:
        return candidate
    n = 2
    while f"{candidate}_{n}" in taken:
        n += 1
    return f"{candidate}_{n}"


def migrate_legacy_accounts(conn) -> None:
    """One-time: turn single global settings/env into one default account per platform."""
    try:
        n = conn.execute("select count(*) as c from ad_accounts").fetchone()
        count = int((n["c"] if n and "c" in n.keys() else n[0]) if n else 0)
    except Exception:
        return
    if count > 0:
        return
    stored = {}
    try:
        row = conn.execute("select value from settings where key = ?", (SETTING_KEY,)).fetchone()
        if row:
            stored = _parse_creds(row["value"] if "value" in row.keys() else row[0])
    except Exception:
        stored = {}
    now = _now()
    for platform, label in PLATFORMS:
        creds = {}
        for key, _title, _secret in PLATFORM_FIELDS[platform]:
            env_name = ENV_MAP.get(key, "")
            val = _clip(os.environ.get(env_name, ""), 2048) or _clip(stored.get(key), 2048)
            if val:
                creds[key] = val
        if not creds and not (
            stored.get("send_ratio_pct") or stored.get("value_multiplier")
        ):
            # still create empty default shell so UI has a tab to edit
            pass
        try:
            ratio = float(stored.get("send_ratio_pct") or os.environ.get("AD_SEND_RATIO_PCT") or 100)
        except ValueError:
            ratio = 100.0
        try:
            mult = float(stored.get("value_multiplier") or os.environ.get("AD_VALUE_MULTIPLIER") or 1)
        except ValueError:
            mult = 1.0
        code = {"meta": "meta_1", "google": "gg_1", "tiktok": "tt_1"}[platform]
        conn.execute(
            "insert into ad_accounts (code, platform, name, credentials, send_ratio_pct, value_multiplier, enabled, is_default, created_at, updated_at) "
            "values (?, ?, ?, ?, ?, ?, 1, 1, ?, ?)",
            (
                code,
                platform,
                f"{label} 默认账户",
                json.dumps(creds, ensure_ascii=False),
                max(0.0, min(100.0, ratio)),
                max(0.0, min(2.0, mult)),
                now,
                now,
            ),
        )


def list_accounts(conn, platform: str | None = None, include_disabled: bool = True) -> list:
    ensure_tables(conn)
    if platform:
        rows = conn.execute(
            "select * from ad_accounts where platform = ? order by is_default desc, id asc",
            (_clip(platform, 16).lower(),),
        ).fetchall()
    else:
        rows = conn.execute(
            "select * from ad_accounts order by platform asc, is_default desc, id asc"
        ).fetchall()
    out = []
    for row in rows:
        item = account_to_dict(row)
        if not include_disabled and not item.get("enabled"):
            continue
        out.append(item)
    return out


def account_to_dict(row) -> dict:
    d = _row_dict(row)
    if not d:
        return {}
    creds = _parse_creds(d.get("credentials"))
    d["credentials"] = creds
    d["enabled"] = bool(int(d.get("enabled") or 0))
    d["is_default"] = bool(int(d.get("is_default") or 0))
    try:
        d["send_ratio_pct"] = float(d.get("send_ratio_pct") if d.get("send_ratio_pct") is not None else 100)
    except (TypeError, ValueError):
        d["send_ratio_pct"] = 100.0
    try:
        d["value_multiplier"] = float(d.get("value_multiplier") if d.get("value_multiplier") is not None else 1)
    except (TypeError, ValueError):
        d["value_multiplier"] = 1.0
    try:
        d["learning_min"] = int(d["learning_min"]) if d.get("learning_min") is not None else 50
    except (TypeError, ValueError, KeyError):
        d["learning_min"] = 50
    try:
        d["daily_floor"] = int(d["daily_floor"]) if d.get("daily_floor") is not None else 5
    except (TypeError, ValueError, KeyError):
        d["daily_floor"] = 5
    try:
        d["ratio_min"] = float(d["ratio_min"]) if d.get("ratio_min") is not None else 60
    except (TypeError, ValueError, KeyError):
        d["ratio_min"] = 60.0
    try:
        d["ratio_max"] = float(d["ratio_max"]) if d.get("ratio_max") is not None else 100
    except (TypeError, ValueError, KeyError):
        d["ratio_max"] = 100.0
    if d["ratio_max"] < d["ratio_min"]:
        d["ratio_max"] = d["ratio_min"]
    d["smart_enabled"] = bool(int(d.get("smart_enabled") or 0))
    try:
        d["target_cpa"] = float(d.get("target_cpa") or 0)
    except (TypeError, ValueError):
        d["target_cpa"] = 0.0
    d["smart_checked_at"] = d.get("smart_checked_at") or ""
    try:
        d["stoploss_multiple"] = float(d["stoploss_multiple"]) if d.get("stoploss_multiple") is not None else 1.5
    except (TypeError, ValueError, KeyError):
        d["stoploss_multiple"] = 1.5
    try:
        d["stoploss_hours"] = float(d["stoploss_hours"]) if d.get("stoploss_hours") is not None else 24
    except (TypeError, ValueError, KeyError):
        d["stoploss_hours"] = 24.0
    d["status"] = account_status(d)
    return d


def account_status(account: dict) -> dict:
    platform = (account.get("platform") or "").lower()
    creds = account.get("credentials") or {}
    pixel = False
    capi = False
    if platform == "meta":
        pixel = bool(creds.get("meta_pixel_id"))
        capi = bool(creds.get("meta_pixel_id") and creds.get("meta_capi_token"))
    elif platform == "google":
        pixel = bool(creds.get("google_aw_id") or creds.get("google_measurement_id"))
        capi = bool(creds.get("google_measurement_id") and creds.get("google_api_secret"))
    elif platform == "tiktok":
        pixel = bool(creds.get("tiktok_pixel_id"))
        capi = bool(creds.get("tiktok_pixel_id") and creds.get("tiktok_access_token"))
    test_code = False
    if platform == "meta":
        test_code = bool(creds.get("meta_test_code"))
    elif platform == "tiktok":
        test_code = bool(creds.get("tiktok_test_code"))
    return {"pixel": pixel, "capi": capi, "platform": platform, "test_code": test_code}


def account_public_view(account: dict | None) -> dict:
    """Launch-page status. No tokens, no raw pixel id."""
    if not account:
        return {}
    creds = account.get("credentials") or {}
    platform = (account.get("platform") or "").lower()
    if platform == "meta":
        pixel = creds.get("meta_pixel_id") or ""
        capi_set = bool(creds.get("meta_capi_token"))
        test_code_set = bool(creds.get("meta_test_code"))
    elif platform == "tiktok":
        pixel = creds.get("tiktok_pixel_id") or ""
        capi_set = bool(creds.get("tiktok_access_token"))
        test_code_set = bool(creds.get("tiktok_test_code"))
    else:
        pixel = creds.get("google_measurement_id") or creds.get("google_aw_id") or ""
        capi_set = bool(creds.get("google_api_secret"))
        test_code_set = False
    return {
        "id": account.get("id"),
        "code": account.get("code") or "",
        "name": account.get("name") or "",
        "platform": platform,
        "platform_label": dict(PLATFORMS).get(platform, platform),
        "enabled": bool(account.get("enabled")),
        "is_default": bool(account.get("is_default")),
        "pixel_masked": mask_secret(pixel) if pixel else "",
        "capi_set": capi_set,
        "test_code_set": test_code_set,
    }


def get_account(conn, account_id: int | None = None, code: str | None = None) -> dict | None:
    ensure_tables(conn)
    row = None
    if account_id:
        row = conn.execute("select * from ad_accounts where id = ?", (int(account_id),)).fetchone()
    elif code:
        row = conn.execute(
            "select * from ad_accounts where code = ?",
            (_clip(code, 64),),
        ).fetchone()
    if not row:
        return None
    return account_to_dict(row)


def get_default_account(conn, platform: str) -> dict | None:
    ensure_tables(conn)
    platform = _clip(platform, 16).lower()
    row = conn.execute(
        "select * from ad_accounts where platform = ? and enabled = 1 and is_default = 1 order by id asc limit 1",
        (platform,),
    ).fetchone()
    if not row:
        row = conn.execute(
            "select * from ad_accounts where platform = ? and enabled = 1 order by id asc limit 1",
            (platform,),
        ).fetchone()
    return account_to_dict(row) if row else None


def resolve_account(conn, acct_code: str | None = None, platform: str | None = None) -> dict | None:
    """Resolve landing/purchase account. Explicit acct wins; else platform default."""
    ensure_tables(conn)
    code = _clip(acct_code, 64)
    if code:
        acct = get_account(conn, code=code)
        if acct and acct.get("enabled"):
            return acct
    if platform:
        return get_default_account(conn, platform)
    return None


def account_to_cfg(account: dict | None) -> dict:
    """Shape expected by send_* helpers + public_pixel_config."""
    cfg = {key: "" for key in ENV_MAP}
    cfg.update(
        {
            "meta_ok": False,
            "meta_capi_ok": False,
            "google_ok": False,
            "google_mp_ok": False,
            "tiktok_ok": False,
            "tiktok_api_ok": False,
            "send_ratio_pct": 100.0,
            "value_multiplier": 1.0,
            "acct": "",
            "account_id": None,
            "account_name": "",
            "platform": "",
        }
    )
    if not account:
        return cfg
    creds = account.get("credentials") or {}
    for key in ENV_MAP:
        cfg[key] = _clip(creds.get(key), 2048)
    platform = (account.get("platform") or "").lower()
    cfg["platform"] = platform
    cfg["acct"] = account.get("code") or ""
    cfg["account_id"] = account.get("id")
    cfg["account_name"] = account.get("name") or ""
    cfg["send_ratio_pct"] = float(account.get("send_ratio_pct") or 100)
    cfg["value_multiplier"] = float(account.get("value_multiplier") or 1)
    cfg["meta_ok"] = bool(cfg.get("meta_pixel_id"))
    cfg["meta_capi_ok"] = bool(cfg.get("meta_pixel_id") and cfg.get("meta_capi_token"))
    cfg["google_ok"] = bool(cfg.get("google_aw_id") or cfg.get("google_measurement_id"))
    cfg["google_mp_ok"] = bool(cfg.get("google_measurement_id") and cfg.get("google_api_secret"))
    cfg["tiktok_ok"] = bool(cfg.get("tiktok_pixel_id"))
    cfg["tiktok_api_ok"] = bool(cfg.get("tiktok_pixel_id") and cfg.get("tiktok_access_token"))
    return cfg


def public_pixels_for_attrs(conn, attrs: dict | None) -> dict:
    """Browser pixels: if acct set, only that account; else merge defaults of all platforms."""
    attrs = attrs or {}
    code = _clip(attrs.get("acct"), 64)
    if code:
        acct = resolve_account(conn, acct_code=code)
        return public_pixel_config(account_to_cfg(acct))
    # legacy / no acct: merge enabled defaults
    merged = public_pixel_config(account_to_cfg(None))
    for platform, _label in PLATFORMS:
        acct = get_default_account(conn, platform)
        if not acct:
            continue
        part = public_pixel_config(account_to_cfg(acct))
        for key, val in part.items():
            if key.endswith("_ok"):
                merged[key] = bool(merged.get(key) or val)
            elif key in {"send_ratio_pct", "value_multiplier"}:
                # keep first default's throttle for browser when no acct
                if merged.get(key) in (None, "", 100, 100.0, 1, 1.0) and val not in (None, ""):
                    merged[key] = val
            elif val and not merged.get(key):
                merged[key] = val
    return merged


def create_account(conn, platform: str, name: str, code: str = "") -> dict:
    ensure_tables(conn)
    platform = _clip(platform, 16).lower()
    if platform not in dict(PLATFORMS):
        raise ValueError("invalid_platform")
    name = _clip(name, 80) or f"{dict(PLATFORMS).get(platform, platform)} 账户"
    taken = {a["code"] for a in list_accounts(conn)}
    code = _clip(code, 40).lower()
    code = re.sub(r"[^a-z0-9_]+", "_", code).strip("_")
    if not code:
        code = _slug_code(platform, name, taken)
    if code in taken:
        raise ValueError("code_taken")
    now = _now()
    # first account on platform becomes default
    existing = list_accounts(conn, platform)
    is_default = 1 if not any(a.get("enabled") for a in existing) else 0
    cur = conn.execute(
        "insert into ad_accounts (code, platform, name, credentials, send_ratio_pct, value_multiplier, enabled, is_default, created_at, updated_at) "
        "values (?, ?, ?, '{}', 100, 1, 1, ?, ?, ?)",
        (code, platform, name, is_default, now, now),
    )
    return get_account(conn, account_id=cur.lastrowid) or get_account(conn, code=code)


def update_account(
    conn,
    account_id: int,
    *,
    name: str | None = None,
    credentials_patch: dict | None = None,
    send_ratio_pct: float | None = None,
    value_multiplier: float | None = None,
    enabled: bool | None = None,
    make_default: bool = False,
    learning_min: int | None = None,
    daily_floor: int | None = None,
    ratio_min: float | None = None,
    ratio_max: float | None = None,
    smart_enabled: bool | None = None,
    target_cpa: float | None = None,
    stoploss_multiple: float | None = None,
    stoploss_hours: float | None = None,
) -> dict | None:
    ensure_tables(conn)
    acct = get_account(conn, account_id=account_id)
    if not acct:
        return None
    creds = dict(acct.get("credentials") or {})
    if credentials_patch:
        for key, _title, is_secret in PLATFORM_FIELDS.get(acct["platform"], []):
            if key not in credentials_patch:
                continue
            raw = _clip(credentials_patch.get(key), 2048)
            if is_secret:
                if raw and raw != "********":
                    creds[key] = raw
                # blank / mask = keep
            else:
                creds[key] = raw
    new_name = _clip(name, 80) if name is not None else acct["name"]
    ratio = acct["send_ratio_pct"] if send_ratio_pct is None else max(0.0, min(100.0, float(send_ratio_pct)))
    mult = acct["value_multiplier"] if value_multiplier is None else max(0.0, min(2.0, float(value_multiplier)))
    en = acct["enabled"] if enabled is None else bool(enabled)
    learn = acct.get("learning_min", 50) if learning_min is None else max(0, min(10000, int(learning_min)))
    floor = acct.get("daily_floor", 5) if daily_floor is None else max(0, min(1000, int(daily_floor)))
    rmin = acct.get("ratio_min", 60) if ratio_min is None else max(0.0, min(100.0, float(ratio_min)))
    rmax = acct.get("ratio_max", 100) if ratio_max is None else max(0.0, min(100.0, float(ratio_max)))
    if rmax < rmin:
        rmax = rmin
    smart = acct.get("smart_enabled", False) if smart_enabled is None else bool(smart_enabled)
    tcpa = acct.get("target_cpa", 0) if target_cpa is None else max(0.0, float(target_cpa))
    sl_mult = acct.get("stoploss_multiple", 1.5) if stoploss_multiple is None else max(1.0, float(stoploss_multiple))
    sl_hours = acct.get("stoploss_hours", 24) if stoploss_hours is None else max(0.0, float(stoploss_hours))
    is_default = 1 if make_default or acct["is_default"] else (1 if acct["is_default"] else 0)
    if make_default:
        conn.execute(
            "update ad_accounts set is_default = 0 where platform = ?",
            (acct["platform"],),
        )
        is_default = 1
    conn.execute(
        "update ad_accounts set name = ?, credentials = ?, send_ratio_pct = ?, value_multiplier = ?, enabled = ?, is_default = ?, "
        "learning_min = ?, daily_floor = ?, ratio_min = ?, ratio_max = ?, smart_enabled = ?, target_cpa = ?, "
        "stoploss_multiple = ?, stoploss_hours = ?, updated_at = ? where id = ?",
        (
            new_name,
            json.dumps(creds, ensure_ascii=False),
            ratio,
            mult,
            1 if en else 0,
            is_default,
            int(learn),
            int(floor),
            float(rmin),
            float(rmax),
            1 if smart else 0,
            float(tcpa),
            float(sl_mult),
            float(sl_hours),
            _now(),
            int(account_id),
        ),
    )
    return get_account(conn, account_id=account_id)


def delete_account(conn, account_id: int) -> bool:
    ensure_tables(conn)
    acct = get_account(conn, account_id=account_id)
    if not acct:
        return False
    conn.execute("delete from ad_accounts where id = ?", (int(account_id),))
    if acct.get("is_default"):
        # promote another enabled account
        other = get_default_account(conn, acct["platform"])
        if other:
            conn.execute(
                "update ad_accounts set is_default = 1 where id = ?",
                (other["id"],),
            )
    return True


def accounts_by_platform(conn) -> dict:
    grouped = {p: [] for p, _ in PLATFORMS}
    for acct in list_accounts(conn, include_disabled=True):
        grouped.setdefault(acct["platform"], []).append(acct)
    return grouped


def load_stored_config(conn) -> dict:
    ensure_tables(conn)
    row = conn.execute("select value from settings where key = ?", (SETTING_KEY,)).fetchone()
    if not row:
        return {}
    try:
        data = json.loads(row["value"] or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def save_stored_config(conn, data: dict) -> None:
    ensure_tables(conn)
    conn.execute(
        "insert into settings (key, value) values (?, ?) on conflict(key) do update set value = excluded.value",
        (SETTING_KEY, json.dumps(data, ensure_ascii=False)),
    )


def load_config(conn) -> dict:
    """Env wins over empty; admin-stored fills gaps. Secrets may live in either place."""
    stored = load_stored_config(conn)
    cfg = {}
    for key, env_name in ENV_MAP.items():
        env_val = _clip(os.environ.get(env_name, ""), 2048)
        stored_val = _clip(stored.get(key), 2048)
        cfg[key] = env_val or stored_val
        cfg[f"{key}_from_env"] = bool(env_val)
    cfg["meta_ok"] = bool(cfg.get("meta_pixel_id"))
    cfg["meta_capi_ok"] = bool(cfg.get("meta_pixel_id") and cfg.get("meta_capi_token"))
    cfg["google_ok"] = bool(cfg.get("google_aw_id") or cfg.get("google_measurement_id"))
    cfg["google_mp_ok"] = bool(cfg.get("google_measurement_id") and cfg.get("google_api_secret"))
    cfg["tiktok_ok"] = bool(cfg.get("tiktok_pixel_id"))
    cfg["tiktok_api_ok"] = bool(cfg.get("tiktok_pixel_id") and cfg.get("tiktok_access_token"))
    # 扣量：回传比例 + 金额系数（env 可覆盖）
    ratio_env = os.environ.get("AD_SEND_RATIO_PCT", "").strip()
    mult_env = os.environ.get("AD_VALUE_MULTIPLIER", "").strip()
    ratio_raw = ratio_env or stored.get("send_ratio_pct") or "100"
    mult_raw = mult_env or stored.get("value_multiplier") or "1"
    try:
        ratio = float(ratio_raw)
    except ValueError:
        ratio = 100.0
    try:
        mult = float(mult_raw)
    except ValueError:
        mult = 1.0
    cfg["send_ratio_pct"] = max(0.0, min(100.0, ratio))
    cfg["value_multiplier"] = max(0.0, min(2.0, mult))
    cfg["send_ratio_pct_from_env"] = bool(ratio_env)
    cfg["value_multiplier_from_env"] = bool(mult_env)
    return cfg


def mask_secret(value: str, keep: int = 4) -> str:
    text = _clip(value, 2048)
    if not text:
        return ""
    if len(text) <= keep * 2:
        return "*" * len(text)
    return text[:keep] + "…" + text[-keep:]


def public_pixel_config(cfg: dict) -> dict:
    return {
        "meta_pixel_id": cfg.get("meta_pixel_id") or "",
        "google_aw_id": cfg.get("google_aw_id") or "",
        "google_measurement_id": cfg.get("google_measurement_id") or "",
        "tiktok_pixel_id": cfg.get("tiktok_pixel_id") or "",
        "meta_ok": bool(cfg.get("meta_ok")),
        "google_ok": bool(cfg.get("google_ok")),
        "tiktok_ok": bool(cfg.get("tiktok_ok")),
        "send_ratio_pct": float(cfg.get("send_ratio_pct") or 100),
        "value_multiplier": float(cfg.get("value_multiplier") or 1),
    }


def status_cards(cfg: dict) -> list:
    return [
        {
            "id": "meta",
            "name": "Meta (Facebook)",
            "pixel": bool(cfg.get("meta_pixel_id")),
            "capi": bool(cfg.get("meta_capi_ok")),
            "note": "Pixel + CAPI token for Purchase 回传",
        },
        {
            "id": "google",
            "name": "Google Ads / GA4",
            "pixel": bool(cfg.get("google_ok")),
            "capi": bool(cfg.get("google_mp_ok")),
            "note": "AW ID for gtag; Measurement ID + API secret for server MP",
        },
        {
            "id": "tiktok",
            "name": "TikTok",
            "pixel": bool(cfg.get("tiktok_pixel_id")),
            "capi": bool(cfg.get("tiktok_api_ok")),
            "note": "Pixel ID + Events API access token",
        },
    ]


def save_attribution(conn, order_id: str, attrs: dict) -> None:
    ensure_tables(conn)
    oid = str(order_id or "").strip()
    if not oid:
        return
    payload = pack_cookie(attrs or {})
    conn.execute(
        "insert into ad_attribution (order_id, payload, created_at) values (?, ?, ?) "
        "on conflict(order_id) do update set payload = excluded.payload",
        (oid, payload, _now()),
    )
    try:
        stamp_order_ads(conn, oid, attrs or {})
    except Exception:
        return


def load_attribution(conn, order_id: str) -> dict:
    ensure_tables(conn)
    row = conn.execute(
        "select payload from ad_attribution where order_id = ?",
        (str(order_id or ""),),
    ).fetchone()
    if not row:
        return {}
    return parse_cookie(row["payload"])


def log_event(
    conn,
    platform: str,
    event_name: str,
    order_id: str,
    event_id: str,
    ok: bool,
    detail: str = "",
    acct: str = "",
    http_status: int = 0,
) -> None:
    ensure_tables(conn)
    try:
        status = int(http_status or 0)
    except (TypeError, ValueError):
        status = 0
    result = conn.execute(
        "insert into ad_event_log (created_at, platform, event_name, order_id, event_id, ok, detail, acct, http_status) "
        "values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            _now(),
            _clip(platform, 32),
            _clip(event_name, 64),
            _clip(order_id, 64),
            _clip(event_id, 128),
            1 if ok else 0,
            redact_log(detail),
            _clip(acct, 64),
            status,
        ),
    )
    # keep last ~500
    conn.execute(
        "delete from ad_event_log where id not in (select id from ad_event_log order by id desc limit 500)"
    )
    try:
        return int(result.lastrowid or 0)
    except (TypeError, ValueError):
        return 0


def _shanghai(iso: str) -> str:
    text = str(iso or "")
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return text


def recent_logs(conn, limit: int = 40) -> list:
    ensure_tables(conn)
    rows = conn.execute(
        "select * from ad_event_log order by id desc limit ?",
        (max(1, min(int(limit or 40), 200)),),
    ).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        item["detail"] = redact_log(item.get("detail") or "")
        item["created_at_sh"] = _shanghai(item.get("created_at") or "")
        item["acct"] = item.get("acct") or ""
        try:
            item["http_status"] = int(item.get("http_status") or 0)
        except (TypeError, ValueError):
            item["http_status"] = 0
        out.append(item)
    return out


def event_already_ok(conn, platform: str, event_name: str, event_id: str) -> bool:
    ensure_tables(conn)
    if not event_id:
        return False
    row = conn.execute(
        "select 1 from ad_event_log where platform = ? and event_name = ? and event_id = ? and ok = 1 limit 1",
        (_clip(platform, 32), _clip(event_name, 64), _clip(event_id, 128)),
    ).fetchone()
    return row is not None


def build_creative_url(base: str, country: str = "US", seg: str = "", utm: dict | None = None, acct: str = "") -> str:
    base = (base or "/lp/ship").strip() or "/lp/ship"
    if not base.startswith("http") and not base.startswith("/"):
        base = "/" + base
    query = {}
    if country:
        query["country"] = country
    if seg:
        query["seg"] = seg
    if acct:
        query["acct"] = _clip(acct, 64)
    utm = utm or {}
    for key in ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"):
        val = _clip(utm.get(key), 128)
        if val:
            query[key] = val
    if "utm_content" not in query and seg:
        query["utm_content"] = seg
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}{urlencode(query)}" if query else base


def _http_json(url: str, payload: dict, headers: dict | None = None, timeout: int = 12) -> tuple[bool, int, str]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            status = int(getattr(resp, "status", 200) or 200)
            return True, status, redact_log(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace") if exc.fp else str(exc)
        return False, int(exc.code or 0), redact_log(raw)
    except Exception as exc:  # noqa: BLE001
        return False, 0, redact_log(str(exc))


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hash_email(email: str) -> str:
    text = (email or "").strip().lower()
    if "@" not in text:
        return ""
    return _sha256(text)


def _phone_digits(phone: str, country: str = "") -> str:
    digits = re.sub(r"\D", "", phone or "")
    digits = digits.lstrip("0")
    if not digits:
        return ""
    if country.upper() == "US" and len(digits) == 10:
        digits = "1" + digits
    return digits


def _hash_phone_meta(phone: str, country: str = "") -> str:
    """Meta: digits only, country code, no plus, then SHA256."""
    digits = _phone_digits(phone, country)
    if not digits:
        return ""
    return _sha256(digits)


def _hash_phone_tiktok(phone: str, country: str = "") -> str:
    """TikTok: SHA256 of E.164, keeping the leading +."""
    digits = _phone_digits(phone, country)
    if not digits:
        return ""
    return _sha256("+" + digits)


def _hash_external(value: str) -> str:
    text = (value or "").strip().lower()
    if not text:
        return ""
    return _sha256(text)


def new_event_id(prefix: str) -> str:
    clean = re.sub(r"[^a-z0-9]+", "", (prefix or "ev").lower())[:12] or "ev"
    return f"{clean}_{uuid.uuid4().hex[:16]}"


def encode_pixel_queue(existing_raw: str, event: dict | None) -> str:
    events = []
    raw = urllib.parse.unquote(existing_raw or "")
    try:
        data = json.loads(raw) if raw else []
        if isinstance(data, list):
            events = [item for item in data if isinstance(item, dict)]
        elif isinstance(data, dict):
            events = [data]
    except json.JSONDecodeError:
        events = []
    if event and event.get("name"):
        events.append(
            {
                "name": event.get("name"),
                "event_id": event.get("event_id") or "",
                "custom": bool(event.get("custom")),
                "params": event.get("params") or {},
            }
        )
    return json.dumps(events[-6:], ensure_ascii=False, separators=(",", ":"))


def _browser_params(value, currency, content_ids, contents, search_string) -> dict:
    params = {}
    if value is not None:
        params["value"] = round(float(value), 2)
        params["currency"] = (currency or "USD").upper()
    ids = [str(item) for item in (content_ids or []) if item]
    safe_contents = []
    for item in contents or []:
        if not isinstance(item, dict):
            continue
        cid = str(item.get("id") or item.get("content_id") or "")
        if not cid:
            continue
        try:
            qty = int(item.get("quantity") or 1)
        except (TypeError, ValueError):
            qty = 1
        try:
            price = round(float(item.get("item_price") if item.get("item_price") is not None else item.get("price") or 0), 2)
        except (TypeError, ValueError):
            price = 0.0
        safe_contents.append(
            {
                "id": cid,
                "content_id": cid,
                "quantity": qty,
                "item_price": price,
                "price": price,
            }
        )
        if cid not in ids:
            ids.append(cid)
    if ids:
        params["content_ids"] = ids
        params["content_type"] = "product"
    if safe_contents:
        params["contents"] = safe_contents
        params["content_type"] = "product"
    if search_string:
        params["search_string"] = _clip(search_string, 200)
    return params


def purchase_event_id(order_id: str) -> str:
    return f"purchase_{order_id}"


def _order_value_currency(order: dict) -> tuple[float, str]:
    cents = int(order.get("due_cents") or 0)
    currency = str(order.get("currency") or "USD").upper()
    return round(cents / 100.0, 2), currency



def should_send_conversion(order_id: str, send_ratio_pct: float) -> bool:
    """Deterministic keep/drop for 扣量. Same order_id always same decision."""
    pct = max(0.0, min(100.0, float(send_ratio_pct if send_ratio_pct is not None else 100)))
    if pct >= 100.0:
        return True
    if pct <= 0.0:
        return False
    digest = hashlib.sha256(f"harbor_throttle:{order_id}".encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 10000  # 0..9999
    return bucket < int(round(pct * 100))


def apply_value_multiplier(order: dict, multiplier: float) -> dict:
    out = dict(order or {})
    try:
        mult = max(0.0, min(2.0, float(multiplier)))
    except (TypeError, ValueError):
        mult = 1.0
    cents = int(out.get("due_cents") or 0)
    out["due_cents"] = int(round(cents * mult))
    out["_value_multiplier"] = mult
    return out


def record_funnel(
    conn,
    kind: str,
    *,
    seg: str = "",
    utm_source: str = "",
    utm_campaign: str = "",
    sku: str = "",
    order_id: str = "",
    visitor: str = "",
    extra: str = "",
    acct: str = "",
) -> None:
    ensure_tables(conn)
    kind = _clip(kind, 32).lower()
    if kind not in {"land", "deal_click", "purchase"}:
        return
    now = _now()
    day = now[:10]
    conn.execute(
        "insert into ad_funnel (created_at, day, kind, seg, utm_source, utm_campaign, sku, order_id, visitor, extra, acct) "
        "values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            now,
            day,
            kind,
            _clip(normalize_seg(seg) or seg, 64),
            _clip(utm_source, 64),
            _clip(utm_campaign, 128),
            _clip(sku, 128),
            _clip(order_id, 64),
            _clip(visitor, 128),
            _clip(extra, 500),
            _clip(acct, 64),
        ),
    )
    # retain ~30d roughly by trimming old rows when large
    try:
        n = conn.execute("select count(*) as c from ad_funnel").fetchone()["c"]
        if int(n or 0) > 50000:
            conn.execute(
                "delete from ad_funnel where id in (select id from ad_funnel order by id asc limit 5000)"
            )
    except Exception:
        pass


def funnel_stats(conn, days: int = 14) -> dict:
    """Aggregate land / deal_click / purchase for admin."""
    ensure_tables(conn)
    days = max(1, min(int(days or 14), 60))
    rows = conn.execute(
        "select day, kind, seg, utm_source, acct, count(*) as c from ad_funnel "
        "where day >= date('now', ?) group by day, kind, seg, utm_source, acct "
        "order by day desc, c desc",
        (f"-{days} days",),
    ).fetchall()
    by_day = {}
    by_seg = {}
    by_source = {}
    by_acct = {}
    totals = {"land": 0, "deal_click": 0, "purchase": 0}
    for row in rows:
        d = dict(row)
        kind = d["kind"]
        c = int(d["c"] or 0)
        totals[kind] = totals.get(kind, 0) + c
        day = d["day"]
        by_day.setdefault(day, {"land": 0, "deal_click": 0, "purchase": 0})
        by_day[day][kind] = by_day[day].get(kind, 0) + c
        seg = d["seg"] or "(none)"
        by_seg.setdefault(seg, {"land": 0, "deal_click": 0, "purchase": 0})
        by_seg[seg][kind] = by_seg[seg].get(kind, 0) + c
        src = d["utm_source"] or "(none)"
        by_source.setdefault(src, {"land": 0, "deal_click": 0, "purchase": 0})
        by_source[src][kind] = by_source[src].get(kind, 0) + c
        ac = d.get("acct") or "(none)"
        by_acct.setdefault(ac, {"land": 0, "deal_click": 0, "purchase": 0})
        by_acct[ac][kind] = by_acct[ac].get(kind, 0) + c
    day_rows = [{"day": k, **v} for k, v in sorted(by_day.items(), reverse=True)]
    seg_rows = [
        {"seg": k, **v, "cvr": (round(100.0 * v.get("purchase", 0) / v["land"], 1) if v.get("land") else 0)}
        for k, v in sorted(by_seg.items(), key=lambda kv: kv[1].get("land", 0), reverse=True)
    ]
    source_rows = [
        {"utm_source": k, **v}
        for k, v in sorted(by_source.items(), key=lambda kv: kv[1].get("land", 0), reverse=True)
    ]
    acct_rows = [
        {"acct": k, **v}
        for k, v in sorted(by_acct.items(), key=lambda kv: kv[1].get("land", 0), reverse=True)
    ]
    return {
        "days": days,
        "totals": totals,
        "by_day": day_rows[:days],
        "by_seg": seg_rows[:30],
        "by_source": source_rows[:20],
        "by_acct": acct_rows[:30],
    }


def _meta_contents(contents: list) -> list:
    out = []
    for item in contents or []:
        if not isinstance(item, dict):
            continue
        cid = str(item.get("id") or item.get("content_id") or "")
        if not cid:
            continue
        try:
            qty = int(item.get("quantity") or 1)
        except (TypeError, ValueError):
            qty = 1
        try:
            price = round(float(item.get("item_price") if item.get("item_price") is not None else item.get("price") or 0), 2)
        except (TypeError, ValueError):
            price = 0.0
        out.append({"id": cid, "quantity": qty, "item_price": price})
    return out


def _tiktok_contents(contents: list) -> list:
    out = []
    for item in contents or []:
        if not isinstance(item, dict):
            continue
        cid = str(item.get("content_id") or item.get("id") or "")
        if not cid:
            continue
        try:
            qty = int(item.get("quantity") or 1)
        except (TypeError, ValueError):
            qty = 1
        try:
            price = round(float(item.get("price") if item.get("price") is not None else item.get("item_price") or 0), 2)
        except (TypeError, ValueError):
            price = 0.0
        out.append({"content_id": cid, "price": price, "quantity": qty})
    return out


def send_meta_event(
    cfg: dict,
    event_name: str,
    order: dict | None,
    attrs: dict,
    event_id: str,
    value: float | None = None,
    currency: str = "USD",
    source_url: str = "",
    content_ids: list | None = None,
    contents: list | None = None,
    search_string: str = "",
    phone: str = "",
    phone_country: str = "",
    external_id: str = "",
    timeout: int = 12,
) -> tuple[bool, int, str]:
    pixel = cfg.get("meta_pixel_id") or ""
    token = cfg.get("meta_capi_token") or ""
    if not pixel or not token:
        return False, 0, "meta_not_configured"
    attrs = attrs or {}
    user = {}
    email_hash = _hash_email((order or {}).get("email") or "")
    if email_hash:
        user["em"] = [email_hash]
    phone_hash = _hash_phone_meta(phone or (order or {}).get("phone") or "", phone_country or (order or {}).get("ship_country") or "")
    if phone_hash:
        user["ph"] = [phone_hash]
    ext = _hash_external(external_id or attrs.get("external_id") or "")
    if ext:
        user["external_id"] = [ext]
    if attrs.get("client_ip"):
        user["client_ip_address"] = _clip(attrs.get("client_ip"), 64)
    if attrs.get("client_ua"):
        user["client_user_agent"] = _clip(attrs.get("client_ua"), 512)
    if attrs.get("fbp"):
        user["fbp"] = attrs["fbp"]
    fbc = canonical_fbc(attrs)
    if fbc:
        user["fbc"] = fbc
    custom = {}
    if value is not None:
        custom["value"] = round(float(value), 2)
        custom["currency"] = (currency or "USD").upper()
    ids = [str(item) for item in (content_ids or []) if item]
    meta_contents = _meta_contents(contents or [])
    if not ids and meta_contents:
        ids = [item["id"] for item in meta_contents]
    if ids:
        custom["content_ids"] = ids
        custom["content_type"] = "product"
    if meta_contents:
        custom["contents"] = meta_contents
        custom["content_type"] = "product"
    if search_string:
        custom["search_string"] = _clip(search_string, 200)
    event = {
        "event_name": event_name,
        "event_time": int(time.time()),
        "event_id": event_id,
        "action_source": "website",
        "user_data": user,
        "custom_data": custom,
    }
    page = source_url or attrs.get("event_source_url") or ""
    if page:
        event["event_source_url"] = page
    payload = {"data": [event]}
    test_code = cfg.get("meta_test_code") or ""
    if test_code:
        payload["test_event_code"] = test_code
    url = f"https://graph.facebook.com/v19.0/{pixel}/events?access_token={urllib.parse.quote(token)}"
    ok, status, detail = _http_json(url, payload, timeout=timeout)
    return ok, status, redact_log(detail)


def send_meta_purchase(cfg: dict, order: dict, attrs: dict, event_id: str, event_source_url: str = "") -> tuple[bool, int, str]:
    value, currency = _order_value_currency(order)
    return send_meta_event(
        cfg,
        "Purchase",
        order,
        attrs,
        event_id,
        value=value,
        currency=currency,
        source_url=event_source_url,
        phone=(order or {}).get("phone") or "",
        phone_country=(order or {}).get("ship_country") or "",
    )


def send_google_mp_purchase(cfg: dict, order: dict, attrs: dict, event_id: str, timeout: int = 12) -> tuple[bool, int, str]:
    mid = cfg.get("google_measurement_id") or ""
    secret = cfg.get("google_api_secret") or ""
    if not mid or not secret:
        return False, 0, "google_mp_not_configured"
    value, currency = _order_value_currency(order)
    client_id = attrs.get("gclid") or attrs.get("wbraid") or attrs.get("gbraid") or f"harbor.{order.get('id')}"
    cid = hashlib.sha256(str(client_id).encode()).hexdigest()
    cid = f"{int(cid[:8], 16)}.{int(cid[8:16], 16)}"
    params = {
        "name": "purchase",
        "params": {
            "transaction_id": str(order.get("id") or ""),
            "value": value,
            "currency": currency,
            "engagement_time_msec": 1,
        },
    }
    if attrs.get("gclid"):
        params["params"]["gclid"] = attrs["gclid"]
    payload = {
        "client_id": cid,
        "events": [params],
    }
    url = f"https://www.google-analytics.com/mp/collect?measurement_id={urllib.parse.quote(mid)}&api_secret={urllib.parse.quote(secret)}"
    ok, status, detail = _http_json(url, payload, timeout=timeout)
    return ok, status, redact_log(detail)


def send_tiktok_event(
    cfg: dict,
    event_name: str,
    order: dict | None,
    attrs: dict,
    event_id: str,
    value: float | None = None,
    currency: str = "USD",
    source_url: str = "",
    content_ids: list | None = None,
    contents: list | None = None,
    search_string: str = "",
    phone: str = "",
    phone_country: str = "",
    external_id: str = "",
    timeout: int = 12,
) -> tuple[bool, int, str]:
    pixel = cfg.get("tiktok_pixel_id") or ""
    token = cfg.get("tiktok_access_token") or ""
    if not pixel or not token:
        return False, 0, "tiktok_not_configured"
    attrs = attrs or {}
    user = {}
    if attrs.get("ttclid"):
        user["ttclid"] = attrs["ttclid"]
    if attrs.get("ttp"):
        user["ttp"] = attrs["ttp"]
    if attrs.get("client_ip"):
        user["ip"] = _clip(attrs.get("client_ip"), 64)
    if attrs.get("client_ua"):
        user["user_agent"] = _clip(attrs.get("client_ua"), 512)
    email_hash = _hash_email((order or {}).get("email") or "")
    if email_hash:
        user["email"] = email_hash
    phone_hash = _hash_phone_tiktok(phone or (order or {}).get("phone") or "", phone_country or (order or {}).get("ship_country") or "")
    if phone_hash:
        user["phone"] = phone_hash
    ext = _hash_external(external_id or attrs.get("external_id") or "")
    if ext:
        user["external_id"] = ext
    properties = {}
    tt_contents = _tiktok_contents(contents or [])
    ids = [str(item) for item in (content_ids or []) if item]
    if not ids and tt_contents:
        ids = [item["content_id"] for item in tt_contents]
    if ids or tt_contents:
        properties["content_type"] = "product"
    if ids:
        properties["content_ids"] = ids
    if tt_contents:
        properties["contents"] = tt_contents
    if value is not None:
        properties["value"] = round(float(value), 2)
        properties["currency"] = (currency or "USD").upper()
    if search_string:
        properties["search_string"] = _clip(search_string, 200)
    data = {
        "event": event_name,
        "event_time": int(time.time()),
        "event_id": event_id,
        "user": user,
        "page": {"url": source_url or attrs.get("event_source_url") or ""},
        "properties": properties,
    }
    payload = {
        "event_source": "web",
        "event_source_id": pixel,
        "data": [data],
    }
    test_code = cfg.get("tiktok_test_code") or ""
    if test_code:
        payload["test_event_code"] = test_code
    ok, status, detail = _http_json(
        "https://business-api.tiktok.com/open_api/v1.3/event/track/",
        payload,
        headers={"Access-Token": token},
        timeout=timeout,
    )
    return ok, status, redact_log(detail)


def send_tiktok_purchase(cfg: dict, order: dict, attrs: dict, event_id: str, source_url: str = "") -> tuple[bool, int, str]:
    value, currency = _order_value_currency(order)
    return send_tiktok_event(
        cfg,
        "Purchase",
        order,
        attrs,
        event_id,
        value=value,
        currency=currency,
        source_url=source_url,
        phone=(order or {}).get("phone") or "",
        phone_country=(order or {}).get("ship_country") or "",
    )


def accounts_for_event(conn, attrs: dict | None, *, fallback_all: bool = False) -> list:
    """Selected acct wins. Otherwise the platform implied by utm_source, else nothing."""
    ensure_tables(conn)
    attrs = attrs or {}
    code = _clip(attrs.get("acct"), 64)
    if code:
        acct = resolve_account(conn, acct_code=code)
        return [acct] if acct else []
    source = _clip(attrs.get("utm_source"), 64).lower()
    platform = {
        "meta": "meta",
        "facebook": "meta",
        "fb": "meta",
        "instagram": "meta",
        "ig": "meta",
        "tiktok": "tiktok",
        "tt": "tiktok",
        "google": "google",
    }.get(source, "")
    if platform:
        acct = get_default_account(conn, platform)
        return [acct] if acct else []
    if not fallback_all:
        return []
    found = []
    for name, _label in PLATFORMS:
        acct = get_default_account(conn, name)
        if acct:
            found.append(acct)
    return found


_POSTBACK_QUEUE = queue.Queue(maxsize=8192)
_POSTBACK_STARTED = False
_POSTBACK_LOCK = threading.Lock()
_POSTBACK_INFLIGHT = set()
_POSTBACK_INFLIGHT_LOCK = threading.Lock()
_POSTBACK_TIMEOUT = 3


def start_postback_workers(count=2):
    """One or two daemon threads send Meta/TikTok/Google off the request path."""
    global _POSTBACK_STARTED
    with _POSTBACK_LOCK:
        if _POSTBACK_STARTED:
            return
        width = max(1, min(2, int(count or 1)))
        for index in range(width):
            threading.Thread(target=_postback_worker, name=f"ad-postback-{index}", daemon=True).start()
        _POSTBACK_STARTED = True


def drain_postbacks(timeout=2.0) -> bool:
    start_postback_workers()
    deadline = time.monotonic() + float(timeout)
    while time.monotonic() < deadline:
        if _POSTBACK_QUEUE.unfinished_tasks == 0:
            return True
        time.sleep(0.01)
    return _POSTBACK_QUEUE.unfinished_tasks == 0


def _claim_postback(platform, event_name, event_id) -> bool:
    key = (_clip(platform, 32), _clip(event_name, 64), _clip(event_id, 128))
    with _POSTBACK_INFLIGHT_LOCK:
        if key in _POSTBACK_INFLIGHT:
            return False
        _POSTBACK_INFLIGHT.add(key)
        return True


def _release_postback(platform, event_name, event_id) -> None:
    key = (_clip(platform, 32), _clip(event_name, 64), _clip(event_id, 128))
    with _POSTBACK_INFLIGHT_LOCK:
        _POSTBACK_INFLIGHT.discard(key)


def _mark_event(conn, row_id, ok, detail, http_status) -> None:
    try:
        status = int(http_status or 0)
    except (TypeError, ValueError):
        status = 0
    if not row_id:
        return
    conn.execute(
        "update ad_event_log set ok = ?, detail = ?, http_status = ? where id = ?",
        (1 if ok else 0, redact_log(detail), status, int(row_id)),
    )


def _dispatch_postback(job) -> tuple[bool, int, str]:
    cfg = job["cfg"]
    timeout = _POSTBACK_TIMEOUT
    platform = job["platform"]
    if platform == "meta":
        return send_meta_event(
            cfg,
            job["event_name"],
            job["order"] or None,
            job["attrs"],
            job["event_id"],
            value=job["value"],
            currency=job["currency"],
            source_url=job["source_url"],
            content_ids=job["content_ids"],
            contents=job["contents"],
            search_string=job["search_string"],
            phone=job["phone"],
            phone_country=job["phone_country"],
            external_id=job["external_id"],
            timeout=timeout,
        )
    if platform == "tiktok":
        return send_tiktok_event(
            cfg,
            job["event_name"],
            job["order"] or None,
            job["attrs"],
            job["event_id"],
            value=job["value"],
            currency=job["currency"],
            source_url=job["source_url"],
            content_ids=job["content_ids"],
            contents=job["contents"],
            search_string=job["search_string"],
            phone=job["phone"],
            phone_country=job["phone_country"],
            external_id=job["external_id"],
            timeout=timeout,
        )
    if platform == "google":
        return send_google_mp_purchase(cfg, job["order"], job["attrs"], job["event_id"], timeout=timeout)
    return False, 0, "unknown_platform"


def _deliver_postback(job) -> None:
    delays = (0.0, 0.4, 1.2)
    ok, status, detail = False, 0, "no_attempt"
    try:
        for delay in delays:
            if delay:
                time.sleep(delay)
            try:
                ok, status, detail = _dispatch_postback(job)
            except Exception as exc:  # noqa: BLE001
                ok, status, detail = False, 0, redact_log(str(exc))
            if ok:
                break
            try:
                code = int(status or 0)
            except (TypeError, ValueError):
                code = 0
            if 400 <= code < 500:
                break
        _mark_event(job["conn"], job["row_id"], ok, detail, status)
    finally:
        _release_postback(job["platform"], job["log_name"], job["event_id"])


def _postback_worker() -> None:
    while True:
        job = _POSTBACK_QUEUE.get()
        try:
            _deliver_postback(job)
        except Exception:
            try:
                _release_postback(job.get("platform"), job.get("log_name"), job.get("event_id"))
            except Exception:
                pass
        finally:
            _POSTBACK_QUEUE.task_done()


def _enqueue_postback(job) -> bool:
    start_postback_workers()
    try:
        _POSTBACK_QUEUE.put_nowait(job)
        return True
    except queue.Full:
        return False


def track_server_event(
    conn,
    *,
    event_name: str,
    event_id: str,
    attrs: dict | None = None,
    source_url: str = "",
    value: float | None = None,
    currency: str = "USD",
    content_ids: list | None = None,
    contents: list | None = None,
    search_string: str = "",
    email: str = "",
    phone: str = "",
    phone_country: str = "",
    external_id: str = "",
    order: dict | None = None,
    order_id: str = "",
    idempotent: bool = False,
    fallback_all: bool = False,
) -> dict:
    """Send one server event for the attributed account. Returns the browser pixel payload."""
    ensure_tables(conn)
    attrs = dict(attrs or {})
    event_name = _clip(event_name, 64) or "PageView"
    event_id = _clip(event_id, 128) or new_event_id(event_name.lower())
    order = dict(order or {})
    if email and not order.get("email"):
        order["email"] = email
    if phone and not order.get("phone"):
        order["phone"] = phone
    if phone_country and not order.get("ship_country"):
        order["ship_country"] = phone_country
    oid = _clip(order_id or order.get("id") or "", 64)
    params = _browser_params(value, currency, content_ids, contents, search_string)
    browser = {
        "name": event_name,
        "event_id": event_id,
        "custom": event_name == "EnterStore",
        "params": params,
    }
    targets = accounts_for_event(conn, attrs, fallback_all=fallback_all)
    if not targets:
        # Unconfigured traffic is not a conversion. Skip the log write.
        return browser
    for acct in targets:
        cfg = account_to_cfg(acct)
        platform = cfg.get("platform") or acct.get("platform") or ""
        code = acct.get("code") or ""
        send_value = value
        if event_name == "Purchase":
            # Decide and store before enqueue so the browser pixel matches the server.
            decision = decide_purchase(conn, oid, attrs)
            browser["send"] = bool(decision.get("send"))
            decided_acct = decision.get("acct") or ""
            if decided_acct and code and decided_acct != code:
                continue
            if not decision.get("send"):
                if decision.get("fresh"):
                    log_event(
                        conn,
                        platform or "throttle",
                        event_name,
                        oid,
                        event_id,
                        False,
                        f"skipped_throttle {decision.get('reason') or ''} ratio={decision.get('ratio')}",
                        acct=code or decided_acct,
                        http_status=0,
                    )
                continue
            try:
                mult = max(0.0, min(2.0, float(decision.get("multiplier") if decision.get("multiplier") is not None else cfg.get("value_multiplier") or 1)))
            except (TypeError, ValueError):
                mult = 1.0
            if send_value is not None:
                send_value = round(float(send_value) * mult, 2)
        log_name = event_name
        if platform == "meta":
            if not cfg.get("meta_capi_ok"):
                continue
        elif platform == "tiktok":
            if not cfg.get("tiktok_api_ok"):
                continue
        elif platform == "google" and event_name == "Purchase":
            if not cfg.get("google_mp_ok"):
                continue
            log_name = "purchase"
        else:
            continue
        if idempotent and (
            event_already_ok(conn, platform, event_name, event_id)
            or (log_name != event_name and event_already_ok(conn, platform, log_name, event_id))
        ):
            continue
        if not _claim_postback(platform, log_name, event_id):
            continue
        row_id = log_event(
            conn, platform, log_name, oid, event_id, False, "queued", acct=code, http_status=0
        )
        job = {
            "conn": conn,
            "platform": platform,
            "log_name": log_name,
            "cfg": dict(cfg),
            "event_name": event_name,
            "order": dict(order or {}),
            "attrs": dict(attrs),
            "event_id": event_id,
            "value": send_value,
            "currency": currency,
            "source_url": source_url,
            "content_ids": list(content_ids or []),
            "contents": [dict(item) if isinstance(item, dict) else item for item in (contents or [])],
            "search_string": search_string,
            "phone": phone,
            "phone_country": phone_country,
            "external_id": external_id,
            "row_id": row_id,
            "acct": code,
        }
        if not _enqueue_postback(job):
            _mark_event(conn, row_id, False, "queue_full", 0)
            _release_postback(platform, log_name, event_id)
    return browser


def notify_purchase(conn, order: dict, attrs: dict | None = None, event_source_url: str = "") -> list:
    """Fire server Purchase once for a paid order. Same event_id on every retry."""
    ensure_tables(conn)
    order = dict(order or {})
    oid = str(order.get("id") or "")
    if not oid:
        return []
    attrs = dict(attrs or load_attribution(conn, oid) or {})
    event_id = purchase_event_id(oid)
    acct_code = _clip(attrs.get("acct"), 64)
    try:
        record_funnel(
            conn,
            "purchase",
            seg=attrs.get("seg") or attrs.get("utm_content") or "",
            utm_source=attrs.get("utm_source") or "",
            utm_campaign=attrs.get("utm_campaign") or "",
            order_id=oid,
            extra=f"due_cents={order.get('due_cents') or 0}",
            acct=acct_code,
        )
    except Exception:
        pass
    contents = []
    content_ids = []
    try:
        rows = conn.execute(
            "select sku, qty, price_cents from order_lines where order_id = ?",
            (oid,),
        ).fetchall()
        for row in rows:
            sku = str(row["sku"] if hasattr(row, "keys") else row[0])
            qty = int(row["qty"] if hasattr(row, "keys") else row[2])
            cents = int(row["price_cents"] if hasattr(row, "keys") else row[1])
            price = round(cents / 100.0, 2)
            content_ids.append(sku)
            contents.append(
                {"id": sku, "content_id": sku, "quantity": qty, "item_price": price, "price": price}
            )
    except Exception:
        contents = []
        content_ids = []
    value, currency = _order_value_currency(order)
    had_acct = bool(acct_code)
    track_server_event(
        conn,
        event_name="Purchase",
        event_id=event_id,
        attrs=attrs,
        source_url=event_source_url or attrs.get("event_source_url") or "",
        value=value,
        currency=currency,
        content_ids=content_ids,
        contents=contents,
        email=order.get("email") or "",
        phone=order.get("phone") or "",
        phone_country=order.get("ship_country") or "",
        external_id=attrs.get("external_id") or "",
        order=order,
        order_id=oid,
        idempotent=True,
        fallback_all=not had_acct,
    )
    return [("logged", True, event_id)]


def send_test_event(conn, platform: str = "", account_id: int | None = None) -> tuple[bool, str]:
    ensure_tables(conn)
    acct = get_account(conn, account_id=account_id) if account_id else None
    if not acct and platform:
        acct = get_default_account(conn, platform)
    cfg = account_to_cfg(acct) if acct else load_config(conn)
    platform = (acct.get("platform") if acct else platform or "").strip().lower()
    fake_order = {"id": f"test_{int(time.time())}", "due_cents": 100, "currency": "USD", "email": "", "phone": ""}
    attrs = {"client_ip": "127.0.0.1", "client_ua": "HarborTest"}
    event_id = f"test_{platform}_{int(time.time())}"
    code = (acct or {}).get("code") or ""
    if platform == "meta":
        ok, status, detail = send_meta_event(cfg, "PageView", None, attrs, event_id, source_url="https://linkiip.com/")
        log_event(conn, "meta", "PageView", fake_order["id"], event_id, ok, detail, acct=code, http_status=status)
        return ok, detail
    if platform == "google":
        ok, status, detail = send_google_mp_purchase(cfg, fake_order, attrs, event_id)
        log_event(conn, "google", "purchase", fake_order["id"], event_id, ok, detail, acct=code, http_status=status)
        return ok, detail
    if platform == "tiktok":
        ok, status, detail = send_tiktok_event(cfg, "PageView", None, attrs, event_id, source_url="https://linkiip.com/")
        log_event(conn, "tiktok", "PageView", fake_order["id"], event_id, ok, detail, acct=code, http_status=status)
        return ok, detail
    return False, "unknown_platform"


_DECIDE_LOCK = threading.Lock()
_SMART_STARTED = False


def _shanghai_day(now=None) -> str:
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")


def clamp_ratio(ratio, lo, hi) -> float:
    try:
        low = max(0.0, min(100.0, float(lo)))
    except (TypeError, ValueError):
        low = 60.0
    try:
        high = max(0.0, min(100.0, float(hi)))
    except (TypeError, ValueError):
        high = 100.0
    if high < low:
        high = low
    try:
        value = float(ratio)
    except (TypeError, ValueError):
        value = high
    return max(low, min(high, value))


def bresenham_step(acc: int, ratio: int) -> tuple[int, bool]:
    """Even spread: ratio 70 sends exactly 7 of every 10 and 70 of 100."""
    nxt = int(acc) + int(ratio)
    if nxt >= 100:
        return nxt - 100, True
    return nxt, False


def spread_sends(ratio: int, count: int, acc: int = 0) -> list[bool]:
    out = []
    for _ in range(max(0, int(count))):
        acc, send = bresenham_step(acc, int(ratio))
        out.append(send)
    return out


def stamp_order_ads(conn, order_id: str, attrs: dict) -> None:
    ensure_tables(conn)
    oid = str(order_id or "").strip()
    if not oid:
        return
    attrs = attrs or {}
    try:
        conn.execute(
            "update orders set adgroup = ?, ad_campaign = ?, ad_id = ? where id = ?",
            (
                clean_platform_id(attrs.get("adgroup")),
                clean_platform_id(attrs.get("campaign_id")),
                clean_platform_id(attrs.get("ad_id")),
                oid,
            ),
        )
    except Exception:
        return


def _decision_from_row(row, fresh: bool) -> dict:
    data = _row_dict(row)
    return {
        "order_id": str(data.get("order_id") or ""),
        "acct": data.get("acct") or "",
        "adgroup": data.get("adgroup") or "",
        "send": bool(int(data.get("send") or 0)),
        "reason": data.get("reason") or "",
        "ratio": float(data.get("ratio") or 100),
        "multiplier": float(data.get("multiplier") if data.get("multiplier") is not None else 1),
        "fresh": fresh,
    }


def load_send_decision(conn, order_id: str) -> dict | None:
    row = conn.execute(
        "select * from ad_send_decision where order_id = ?",
        (str(order_id or ""),),
    ).fetchone()
    if not row:
        return None
    return _decision_from_row(row, False)


def _prior_purchases(conn, acct: str, adgroup: str, now) -> int:
    since = (now - timedelta_days(7)).replace(microsecond=0).isoformat()
    row = conn.execute(
        "select count(*) as c from ad_send_decision where acct = ? and adgroup = ? and created_at >= ?",
        (acct, adgroup, since),
    ).fetchone()
    if not row:
        return 0
    try:
        return int(row["c"] if "c" in row.keys() else row[0])
    except Exception:
        return int(row[0])


def timedelta_days(days: int):
    from datetime import timedelta
    return timedelta(days=days)


def decide_purchase(conn, order_id: str, attrs: dict | None = None, now=None) -> dict:
    """One stored send/drop per order. Retries return the same decision."""
    ensure_tables(conn)
    oid = str(order_id or "").strip()
    attrs = dict(attrs or {})
    if not oid:
        return {"send": True, "reason": "no_order", "acct": "", "adgroup": "", "ratio": 100, "multiplier": 1, "fresh": False}
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    with _DECIDE_LOCK:
        try:
            existing = load_send_decision(conn, oid)
            if existing:
                return existing
            acct = resolve_account(conn, acct_code=_clip(attrs.get("acct"), 64)) if attrs.get("acct") else None
            if acct is None:
                found = accounts_for_event(conn, attrs, fallback_all=False)
                acct = found[0] if found else None
            if acct is None:
                return {
                    "send": True,
                    "reason": "no_account",
                    "acct": "",
                    "adgroup": clean_platform_id(attrs.get("adgroup")),
                    "ratio": 100.0,
                    "multiplier": 1.0,
                    "fresh": True,
                }
            code = acct.get("code") or ""
            group = clean_platform_id(attrs.get("adgroup"))
            lo = float(acct.get("ratio_min") if acct.get("ratio_min") is not None else 60)
            hi = float(acct.get("ratio_max") if acct.get("ratio_max") is not None else 100)
            raw_base = 100 if acct.get("send_ratio_pct") is None else acct.get("send_ratio_pct")
            grow = conn.execute(
                "select * from ad_groups where acct = ? and adgroup = ?",
                (code, group),
            ).fetchone()
            grow = _row_dict(grow) if grow else {}
            if grow.get("ratio_override") is not None:
                raw_base = grow.get("ratio_override")
            if acct.get("smart_enabled"):
                current = clamp_ratio(raw_base, lo, hi)
                if grow.get("effective_ratio") is not None:
                    current = clamp_ratio(grow.get("effective_ratio"), lo, hi)
            else:
                # Smart off: bounds and target CPA do not apply. Group ratio override is that group's base.
                try:
                    current = max(0.0, min(100.0, float(raw_base)))
                except (TypeError, ValueError):
                    current = 100.0
            prior = _prior_purchases(conn, code, group, moment)
            learn_at = int(acct.get("learning_min") if acct.get("learning_min") is not None else 50)
            floor_n = int(acct.get("daily_floor") if acct.get("daily_floor") is not None else 5)
            day = _shanghai_day(moment)
            acc = int(grow.get("acc") or 0)
            if (grow.get("day") or "") != day:
                day_orders = 0
            else:
                day_orders = int(grow.get("day_orders") or 0)
            if prior < learn_at:
                acc, _natural = bresenham_step(acc, 100)
                send, reason, used = True, "learning", 100.0
            elif day_orders < floor_n:
                acc, _natural = bresenham_step(acc, 100)
                send, reason, used = True, "floor", 100.0
            else:
                used_int = int(round(current))
                acc, send = bresenham_step(acc, used_int)
                reason, used = ("ratio" if send else "drop"), float(used_int)
            day_orders += 1
            mult = float(acct.get("value_multiplier") or 1)
            conn.execute(
                "insert into ad_send_decision (order_id, acct, adgroup, send, reason, ratio, multiplier, created_at) "
                "values (?, ?, ?, ?, ?, ?, ?, ?)",
                (oid, code, group, 1 if send else 0, reason, used, mult, moment.replace(microsecond=0).isoformat()),
            )
            conn.execute(
                "insert into ad_groups (acct, adgroup, platform, acc, day, day_orders, updated_at) "
                "values (?, ?, ?, ?, ?, ?, ?) "
                "on conflict(acct, adgroup) do update set platform = excluded.platform, acc = excluded.acc, "
                "day = excluded.day, day_orders = excluded.day_orders, updated_at = excluded.updated_at",
                (code, group, acct.get("platform") or "", acc, day, day_orders, _now()),
            )
            return {
                "send": send,
                "reason": reason,
                "acct": code,
                "adgroup": group,
                "ratio": used,
                "multiplier": mult,
                "fresh": True,
            }
        except Exception:
            existing = load_send_decision(conn, oid)
            if existing:
                return existing
            raise


def list_ad_groups(conn, acct_code: str) -> list:
    ensure_tables(conn)
    rows = conn.execute(
        "select * from ad_groups where acct = ? order by real_orders desc, adgroup asc",
        (_clip(acct_code, 64),),
    ).fetchall()
    return [_row_dict(row) for row in rows]


def list_ratio_history(conn, acct_code: str, limit: int = 30) -> list:
    ensure_tables(conn)
    rows = conn.execute(
        "select * from ad_ratio_history where acct = ? order by id desc limit ?",
        (_clip(acct_code, 64), max(1, min(int(limit or 30), 100))),
    ).fetchall()
    out = []
    for row in rows:
        item = _row_dict(row)
        item["created_at_sh"] = _shanghai(item.get("created_at") or "")
        out.append(item)
    return out


STOPLOSS_REASON = "止损：真实CPA持续超标"


def save_group_override(
    conn,
    acct_code: str,
    adgroup: str,
    ratio_override,
    target_cpa_override,
    platform: str = "",
    stoploss_multiple_override=None,
    stoploss_hours_override=None,
) -> None:
    ensure_tables(conn)
    code = _clip(acct_code, 64)
    group = clean_platform_id(adgroup)
    if not code:
        return
    ratio = None if ratio_override in (None, "") else max(0.0, min(100.0, float(ratio_override)))
    tcpa = None if target_cpa_override in (None, "") else max(0.0, float(target_cpa_override))
    sl_mult = None if stoploss_multiple_override in (None, "") else max(1.0, float(stoploss_multiple_override))
    sl_hours = None if stoploss_hours_override in (None, "") else max(0.0, float(stoploss_hours_override))
    conn.execute(
        "insert into ad_groups (acct, adgroup, platform, updated_at, ratio_override, target_cpa_override, "
        "stoploss_multiple_override, stoploss_hours_override) values (?, ?, ?, ?, ?, ?, ?, ?) "
        "on conflict(acct, adgroup) do update set ratio_override = excluded.ratio_override, "
        "target_cpa_override = excluded.target_cpa_override, "
        "stoploss_multiple_override = excluded.stoploss_multiple_override, "
        "stoploss_hours_override = excluded.stoploss_hours_override, updated_at = excluded.updated_at",
        (code, group, _clip(platform, 16), _now(), ratio, tcpa, sl_mult, sl_hours),
    )


def evaluate_stoploss(since: str, now, actual_cpa, target, multiple, hours) -> tuple[bool, str, bool]:
    """Return (active, since, hold). Hold freezes the ratio; active marks the red row.

    The clock starts the first time real CPA is above target × multiple.
    Hold begins only after that clock has run for `hours`. CPA at or under
    the line clears the clock.
    """
    try:
        line = float(target) * float(multiple)
        limit = float(hours)
    except (TypeError, ValueError):
        return False, "", False
    if float(target or 0) <= 0 or actual_cpa is None or line <= 0:
        return False, since or "", False
    if float(actual_cpa) <= line:
        return False, "", False
    text = (since or "").strip()
    if not text:
        text = now.replace(microsecond=0).isoformat()
    try:
        started = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
    except ValueError:
        started = now
        text = now.replace(microsecond=0).isoformat()
    elapsed = (now - started).total_seconds() / 3600.0
    if elapsed + 1e-9 >= limit:
        return True, text, True
    return False, text, False


def propose_ratio(current, base, target_cpa, actual_cpa, spend, prev_spend, lo, hi) -> tuple[float, str]:
    """Step 5 or 10 points. Near the target, walk back toward the base ratio."""
    current = clamp_ratio(current, lo, hi)
    base = clamp_ratio(base, lo, hi)
    try:
        target = float(target_cpa or 0)
    except (TypeError, ValueError):
        target = 0.0
    if target <= 0 or actual_cpa is None:
        return base, "no_target_keep_base"
    try:
        spend_now = float(spend or 0)
        spend_prev = float(prev_spend or 0)
    except (TypeError, ValueError):
        spend_now, spend_prev = 0.0, 0.0
    falling = spend_prev > 0 and spend_now < spend_prev * 0.7
    rel = float(actual_cpa) / target if target else 1
    if falling or rel > 1.15:
        step = 10 if (rel > 1.4 or (falling and rel > 1)) else 5
        return clamp_ratio(current + step, lo, hi), ("step_up_spend" if falling and rel <= 1.15 else "step_up_cpa")
    if rel < 0.85:
        step = 10 if rel < 0.6 else 5
        return clamp_ratio(current - step, lo, hi), "step_down"
    gap = current - base
    if abs(gap) <= 5:
        return base, "near_target"
    step = 10 if abs(gap) >= 10 else 5
    if gap > 0:
        return clamp_ratio(current - step, lo, hi), "near_target"
    return clamp_ratio(current + step, lo, hi), "near_target"


def _http_get(url: str, headers: dict | None = None, timeout: int = 12) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(getattr(resp, "status", 200) or 200), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace") if exc.fp else str(exc)
        return int(exc.code or 0), raw
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc)


def fetch_meta_spend(token: str, adset_id: str) -> tuple[float | None, str]:
    if not token:
        return None, "no_token"
    if not adset_id:
        return None, "no_adgroup"
    url = (
        f"https://graph.facebook.com/v19.0/{urllib.parse.quote(adset_id)}/insights"
        f"?fields=spend&date_preset=last_7d&access_token={urllib.parse.quote(token)}"
    )
    status, raw = _http_get(url)
    if status != 200:
        return None, redact_log(f"meta_http_{status}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None, "meta_bad_json"
    spend = 0.0
    for row in data.get("data") or []:
        try:
            spend += float(row.get("spend") or 0)
        except (TypeError, ValueError):
            continue
    return spend, ""


def fetch_tiktok_spend(token: str, advertiser_id: str, adgroup_id: str, now=None) -> tuple[float | None, str]:
    if not token:
        return None, "no_token"
    if not advertiser_id:
        return None, "no_advertiser_id"
    if not adgroup_id:
        return None, "no_adgroup"
    moment = now or datetime.now(timezone.utc)
    end = moment.astimezone(ZoneInfo("Asia/Shanghai")).date()
    start = end - timedelta_days(6)
    query = urllib.parse.urlencode(
        {
            "advertiser_id": advertiser_id,
            "service_type": "AUCTION",
            "report_type": "BASIC",
            "data_level": "AUCTION_ADGROUP",
            "dimensions": json.dumps(["adgroup_id"]),
            "metrics": json.dumps(["spend"]),
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "filtering": json.dumps(
                [{"field_name": "adgroup_ids", "filter_type": "IN", "filter_value": json.dumps([adgroup_id])}]
            ),
            "page": 1,
            "page_size": 20,
        }
    )
    status, raw = _http_get(
        "https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/?" + query,
        headers={"Access-Token": token},
    )
    if status != 200:
        return None, redact_log(f"tiktok_http_{status}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None, "tiktok_bad_json"
    if int((data or {}).get("code") or 0) not in {0}:
        return None, "tiktok_api_error"
    spend = 0.0
    for row in ((data.get("data") or {}).get("list") or []):
        metrics = row.get("metrics") or {}
        try:
            spend += float(metrics.get("spend") or 0)
        except (TypeError, ValueError):
            continue
    return spend, ""


def _record_ratio(conn, acct, adgroup, ratio, reason, spend, real_orders, sent_orders, cpa) -> None:
    conn.execute(
        "insert into ad_ratio_history (created_at, acct, adgroup, ratio, reason, spend, real_orders, sent_orders, cpa) "
        "values (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (_now(), acct, adgroup, float(ratio), _clip(reason, 80), float(spend or 0), int(real_orders or 0), int(sent_orders or 0), float(cpa or 0)),
    )


def run_smart_ratios(conn, fetch=None, now=None) -> list:
    """Adjust each smart account's ad-group ratio. Failures keep the base ratio and are logged."""
    ensure_tables(conn)
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    notes = []
    for acct in list_accounts(conn):
        if not acct.get("smart_enabled"):
            continue
        checked = acct.get("smart_checked_at") or ""
        if checked:
            try:
                prev = datetime.fromisoformat(checked.replace("Z", "+00:00"))
                if prev.tzinfo is None:
                    prev = prev.replace(tzinfo=timezone.utc)
                if (moment - prev).total_seconds() < 6 * 3600:
                    continue
            except ValueError:
                pass
        code = acct.get("code") or ""
        groups = list_ad_groups(conn, code)
        if not any(clean_platform_id(g.get("adgroup")) for g in groups):
            groups.append({"acct": code, "adgroup": "", "effective_ratio": None, "ratio_override": None, "prev_spend": 0, "last_adjusted_at": ""})
        creds = acct.get("credentials") or {}
        platform = acct.get("platform") or ""
        lo = acct.get("ratio_min", 60)
        hi = acct.get("ratio_max", 100)
        for group in groups:
            adgroup = clean_platform_id(group.get("adgroup")) if group.get("adgroup") else ""
            base_raw = group.get("ratio_override") if group.get("ratio_override") is not None else acct.get("send_ratio_pct")
            base = clamp_ratio(100 if base_raw is None else base_raw, lo, hi)
            current = clamp_ratio(group.get("effective_ratio") if group.get("effective_ratio") is not None else base, lo, hi)
            real = _prior_purchases(conn, code, adgroup, moment)
            sent_row = conn.execute(
                "select count(*) as c from ad_send_decision where acct = ? and adgroup = ? and send = 1 and created_at >= ?",
                (code, adgroup, (moment - timedelta_days(7)).replace(microsecond=0).isoformat()),
            ).fetchone()
            sent = int(sent_row["c"] if sent_row and "c" in sent_row.keys() else (sent_row[0] if sent_row else 0))
            token = creds.get("meta_capi_token") if platform == "meta" else creds.get("tiktok_access_token")
            spend, err = (None, "no_token")
            if fetch is not None:
                try:
                    spend, err = fetch(acct, adgroup)
                except Exception as exc:  # noqa: BLE001
                    spend, err = None, redact_log(str(exc))
            elif platform == "meta":
                spend, err = fetch_meta_spend(token or "", adgroup)
            elif platform == "tiktok":
                spend, err = fetch_tiktok_spend(token or "", creds.get("tiktok_advertiser_id") or "", adgroup, moment)
            else:
                err = "unsupported_platform"
            sl_mult = group.get("stoploss_multiple_override")
            if sl_mult is None:
                sl_mult = acct.get("stoploss_multiple") if acct.get("stoploss_multiple") is not None else 1.5
            sl_hours = group.get("stoploss_hours_override")
            if sl_hours is None:
                sl_hours = acct.get("stoploss_hours") if acct.get("stoploss_hours") is not None else 24
            sl_since = group.get("stoploss_since") or ""
            sl_active = bool(int(group.get("stoploss_active") or 0))
            hold = False
            if err or spend is None:
                if sl_active:
                    reason = STOPLOSS_REASON
                    new_ratio = current
                    hold = True
                else:
                    reason = err or "fetch_failed"
                    new_ratio = base
            else:
                if real <= 0:
                    actual = None if float(spend or 0) <= 0 else float(spend) * 1000
                else:
                    actual = float(spend) / real
                target = group.get("target_cpa_override")
                if target is None:
                    target = acct.get("target_cpa") or 0
                sl_active, sl_since, hold = evaluate_stoploss(sl_since, moment, actual, target, sl_mult, sl_hours)
                if hold:
                    new_ratio = current
                    reason = STOPLOSS_REASON
                else:
                    new_ratio, reason = propose_ratio(current, base, target, actual, spend, group.get("prev_spend") or 0, lo, hi)
                    if real <= 0 and float(spend or 0) > 0:
                        reason = "step_up_cpa" if new_ratio >= current else reason
            last = group.get("last_adjusted_at") or ""
            changed = abs(float(new_ratio) - float(current)) >= 0.5
            recent = False
            if last:
                try:
                    prev = datetime.fromisoformat(last.replace("Z", "+00:00"))
                    if prev.tzinfo is None:
                        prev = prev.replace(tzinfo=timezone.utc)
                    recent = (moment - prev).total_seconds() < 6 * 3600
                except ValueError:
                    recent = False
            if err or spend is None or hold:
                recent = False
            if changed and recent and not hold:
                new_ratio = current
                reason = "held_" + reason
            cpa = (float(spend) / real) if (spend is not None and real > 0) else 0.0
            conn.execute(
                "insert into ad_groups (acct, adgroup, platform, effective_ratio, reason, spend, prev_spend, real_orders, sent_orders, cpa, last_adjusted_at, updated_at, stoploss_since, stoploss_active) "
                "values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "on conflict(acct, adgroup) do update set platform = excluded.platform, effective_ratio = excluded.effective_ratio, "
                "reason = excluded.reason, prev_spend = ad_groups.spend, spend = excluded.spend, real_orders = excluded.real_orders, "
                "sent_orders = excluded.sent_orders, cpa = excluded.cpa, "
                "stoploss_since = excluded.stoploss_since, stoploss_active = excluded.stoploss_active, "
                "last_adjusted_at = case when abs(excluded.effective_ratio - coalesce(ad_groups.effective_ratio, excluded.effective_ratio)) >= 0.5 "
                "then excluded.last_adjusted_at else ad_groups.last_adjusted_at end, updated_at = excluded.updated_at",
                (
                    code,
                    adgroup,
                    platform,
                    float(new_ratio),
                    _clip(reason, 80),
                    float(spend or 0),
                    float(spend or 0),
                    int(real),
                    int(sent),
                    float(cpa or 0),
                    moment.replace(microsecond=0).isoformat() if changed and not recent else (last or ""),
                    _now(),
                    sl_since or "",
                    1 if sl_active else 0,
                ),
            )
            _record_ratio(conn, code, adgroup, new_ratio, reason, spend or 0, real, sent, cpa)
            notes.append({"acct": code, "adgroup": adgroup, "ratio": new_ratio, "reason": reason})
        conn.execute("update ad_accounts set smart_checked_at = ? where code = ?", (moment.replace(microsecond=0).isoformat(), code))
    return notes


def start_smart_job(conn, db_path) -> None:
    global _SMART_STARTED
    if _SMART_STARTED or str(db_path or "") == ":memory:":
        return
    _SMART_STARTED = True

    def loop():
        while True:
            time.sleep(6 * 3600)
            try:
                run_smart_ratios(conn)
            except Exception:
                continue

    threading.Thread(target=loop, name="ad-smart-ratio", daemon=True).start()
