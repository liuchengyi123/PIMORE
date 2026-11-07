# -*- coding: utf-8 -*-
"""Harbor ad platform tracking: click IDs, pixels config, server 回传, link builder."""
from __future__ import annotations

import hashlib
import re
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

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
    detail text not null default ""
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
"""


def ensure_tables(conn) -> None:
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
    migrate_legacy_accounts(conn)


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
    for key in ("fbp", "fbc", "ttp", "event_source_url"):
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
    if fbclid and not merged.get("fbc"):
        merged["fbc"] = f"fb.1.{int(time.time())}.{fbclid}"
    return merged



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
    ],
    "google": [
        ("google_aw_id", "Google Ads AW ID", False),
        ("google_measurement_id", "GA4 Measurement ID", False),
        ("google_api_secret", "MP API Secret", True),
    ],
    "tiktok": [
        ("tiktok_pixel_id", "Pixel ID", False),
        ("tiktok_access_token", "Events API Token", True),
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
    return {"pixel": pixel, "capi": capi, "platform": platform}


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
    is_default = 1 if make_default or acct["is_default"] else (1 if acct["is_default"] else 0)
    if make_default:
        conn.execute(
            "update ad_accounts set is_default = 0 where platform = ?",
            (acct["platform"],),
        )
        is_default = 1
    conn.execute(
        "update ad_accounts set name = ?, credentials = ?, send_ratio_pct = ?, value_multiplier = ?, enabled = ?, is_default = ?, updated_at = ? where id = ?",
        (
            new_name,
            json.dumps(creds, ensure_ascii=False),
            ratio,
            mult,
            1 if en else 0,
            is_default,
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


def load_attribution(conn, order_id: str) -> dict:
    ensure_tables(conn)
    row = conn.execute(
        "select payload from ad_attribution where order_id = ?",
        (str(order_id or ""),),
    ).fetchone()
    if not row:
        return {}
    return parse_cookie(row["payload"])


def log_event(conn, platform: str, event_name: str, order_id: str, event_id: str, ok: bool, detail: str = "") -> None:
    ensure_tables(conn)
    conn.execute(
        "insert into ad_event_log (created_at, platform, event_name, order_id, event_id, ok, detail) values (?, ?, ?, ?, ?, ?, ?)",
        (_now(), _clip(platform, 32), _clip(event_name, 64), _clip(order_id, 64), _clip(event_id, 128), 1 if ok else 0, _clip(detail, 500)),
    )
    # keep last ~500
    conn.execute(
        "delete from ad_event_log where id not in (select id from ad_event_log order by id desc limit 500)"
    )


def recent_logs(conn, limit: int = 40) -> list:
    ensure_tables(conn)
    rows = conn.execute(
        "select * from ad_event_log order by id desc limit ?",
        (max(1, min(int(limit or 40), 200)),),
    ).fetchall()
    return [dict(row) for row in rows]


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


def _http_json(url: str, payload: dict, headers: dict | None = None, timeout: int = 12) -> tuple[bool, str]:
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
            return True, raw[:400]
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace") if exc.fp else str(exc)
        return False, f"HTTP {exc.code}: {raw[:300]}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)[:300]


def _hash_email(email: str) -> str:
    text = (email or "").strip().lower()
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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


def send_meta_purchase(cfg: dict, order: dict, attrs: dict, event_id: str, event_source_url: str = "") -> tuple[bool, str]:
    pixel = cfg.get("meta_pixel_id") or ""
    token = cfg.get("meta_capi_token") or ""
    if not pixel or not token:
        return False, "meta_not_configured"
    value, currency = _order_value_currency(order)
    user = {}
    email_hash = _hash_email(order.get("email") or "")
    if email_hash:
        user["em"] = [email_hash]
    if attrs.get("fbp"):
        user["fbp"] = attrs["fbp"]
    if attrs.get("fbc"):
        user["fbc"] = attrs["fbc"]
    elif attrs.get("fbclid"):
        user["fbc"] = f"fb.1.{int(time.time())}.{attrs['fbclid']}"
    event = {
        "event_name": "Purchase",
        "event_time": int(time.time()),
        "event_id": event_id,
        "action_source": "website",
        "user_data": user,
        "custom_data": {
            "currency": currency,
            "value": value,
            "order_id": str(order.get("id") or ""),
        },
    }
    if event_source_url or attrs.get("event_source_url"):
        event["event_source_url"] = event_source_url or attrs.get("event_source_url")
    payload = {"data": [event]}
    test_code = cfg.get("meta_test_code") or ""
    if test_code:
        payload["test_event_code"] = test_code
    url = f"https://graph.facebook.com/v19.0/{pixel}/events?access_token={urllib.parse.quote(token)}"
    return _http_json(url, payload)


def send_meta_event(cfg: dict, event_name: str, order: dict | None, attrs: dict, event_id: str, value: float | None = None, currency: str = "USD", source_url: str = "") -> tuple[bool, str]:
    pixel = cfg.get("meta_pixel_id") or ""
    token = cfg.get("meta_capi_token") or ""
    if not pixel or not token:
        return False, "meta_not_configured"
    user = {}
    if order:
        email_hash = _hash_email(order.get("email") or "")
        if email_hash:
            user["em"] = [email_hash]
    if attrs.get("fbp"):
        user["fbp"] = attrs["fbp"]
    if attrs.get("fbc"):
        user["fbc"] = attrs["fbc"]
    elif attrs.get("fbclid"):
        user["fbc"] = f"fb.1.{int(time.time())}.{attrs['fbclid']}"
    custom = {}
    if value is not None:
        custom["value"] = value
        custom["currency"] = currency
    if order and order.get("id"):
        custom["order_id"] = str(order["id"])
    event = {
        "event_name": event_name,
        "event_time": int(time.time()),
        "event_id": event_id,
        "action_source": "website",
        "user_data": user,
        "custom_data": custom,
    }
    if source_url or attrs.get("event_source_url"):
        event["event_source_url"] = source_url or attrs.get("event_source_url")
    payload = {"data": [event]}
    test_code = cfg.get("meta_test_code") or ""
    if test_code:
        payload["test_event_code"] = test_code
    url = f"https://graph.facebook.com/v19.0/{pixel}/events?access_token={urllib.parse.quote(token)}"
    return _http_json(url, payload)


def send_google_mp_purchase(cfg: dict, order: dict, attrs: dict, event_id: str) -> tuple[bool, str]:
    mid = cfg.get("google_measurement_id") or ""
    secret = cfg.get("google_api_secret") or ""
    if not mid or not secret:
        return False, "google_mp_not_configured"
    value, currency = _order_value_currency(order)
    client_id = attrs.get("gclid") or attrs.get("wbraid") or attrs.get("gbraid") or f"harbor.{order.get('id')}"
    # GA4 MP client_id format: random.random — use stable hash
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
    return _http_json(url, payload)


def send_tiktok_purchase(cfg: dict, order: dict, attrs: dict, event_id: str, source_url: str = "") -> tuple[bool, str]:
    pixel = cfg.get("tiktok_pixel_id") or ""
    token = cfg.get("tiktok_access_token") or ""
    if not pixel or not token:
        return False, "tiktok_not_configured"
    value, currency = _order_value_currency(order)
    email_hash = _hash_email(order.get("email") or "")
    user = {}
    if email_hash:
        user["email"] = email_hash
    if attrs.get("ttclid"):
        user["ttclid"] = attrs["ttclid"]
    if attrs.get("ttp"):
        user["ttp"] = attrs["ttp"]
    payload = {
        "event_source": "web",
        "event_source_id": pixel,
        "data": [
            {
                "event": "CompletePayment",
                "event_time": int(time.time()),
                "event_id": event_id,
                "user": user,
                "properties": {
                    "currency": currency,
                    "value": value,
                    "content_type": "product",
                },
                "page": {"url": source_url or attrs.get("event_source_url") or ""},
            }
        ],
    }
    return _http_json(
        "https://business-api.tiktok.com/open_api/v1.3/event/track/",
        payload,
        headers={"Access-Token": token},
    )


def notify_purchase(conn, order: dict, attrs: dict | None = None, event_source_url: str = "") -> list:
    """Fire server 回传 for a paid order using the attributed ad account (acct)."""
    ensure_tables(conn)
    order = dict(order or {})
    oid = str(order.get("id") or "")
    if not oid:
        return []
    attrs = dict(attrs or load_attribution(conn, oid) or {})
    event_id = purchase_event_id(oid)
    results = []
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

    # Build list of accounts to notify: explicit acct OR each platform default
    targets = []
    if acct_code:
        acct = resolve_account(conn, acct_code=acct_code)
        if acct:
            targets.append(acct)
    else:
        for platform, _label in PLATFORMS:
            acct = get_default_account(conn, platform)
            if acct:
                targets.append(acct)
        # legacy fallback to env/settings blob if no accounts rows somehow
        if not targets:
            targets.append({"platform": "legacy", "credentials": {}, "code": "", "name": "legacy",
                            "send_ratio_pct": 100, "value_multiplier": 1, "enabled": True,
                            **{"_legacy_cfg": load_config(conn)}})

    if not targets:
        log_event(conn, "throttle", "Purchase", oid, event_id, False, "skipped_no_account")
        return [("none", False, "no_account")]

    for acct in targets:
        if acct.get("_legacy_cfg"):
            cfg = acct["_legacy_cfg"]
            platform = "legacy"
            code = ""
        else:
            cfg = account_to_cfg(acct)
            platform = cfg.get("platform") or acct.get("platform") or ""
            code = acct.get("code") or ""
        ratio = float(cfg.get("send_ratio_pct") or 100)
        mult = float(cfg.get("value_multiplier") or 1)
        # per-account deterministic throttle (include acct code)
        throttle_key = f"{code}:{oid}" if code else oid
        if not should_send_conversion(throttle_key, ratio):
            log_event(
                conn,
                platform or "throttle",
                "Purchase",
                oid,
                event_id,
                False,
                f"skipped_throttle acct={code or '-'} ratio={ratio} mult={mult}",
            )
            results.append((platform or "throttle", False, "skipped_throttle"))
            continue
        send_order = apply_value_multiplier(order, mult)
        tag = f"acct={code or '-'}"

        if platform in {"meta", "legacy"} and cfg.get("meta_capi_ok"):
            ok, detail = send_meta_purchase(cfg, send_order, attrs, event_id, event_source_url)
            log_event(conn, "meta", "Purchase", oid, event_id, ok, (detail if not ok else f"ok {tag} mult={mult}"))
            results.append(("meta", ok, detail))
        elif platform == "meta":
            log_event(conn, "meta", "Purchase", oid, event_id, False, f"skipped_no_keys {tag}")

        if platform in {"google", "legacy"} and cfg.get("google_mp_ok"):
            ok, detail = send_google_mp_purchase(cfg, send_order, attrs, event_id)
            log_event(conn, "google", "purchase", oid, event_id, ok, (detail if not ok else f"ok {tag} mult={mult}"))
            results.append(("google", ok, detail))
        elif platform == "google":
            log_event(conn, "google", "purchase", oid, event_id, False, f"skipped_no_keys {tag}")

        if platform in {"tiktok", "legacy"} and cfg.get("tiktok_api_ok"):
            ok, detail = send_tiktok_purchase(cfg, send_order, attrs, event_id, event_source_url)
            log_event(conn, "tiktok", "CompletePayment", oid, event_id, ok, (detail if not ok else f"ok {tag} mult={mult}"))
            results.append(("tiktok", ok, detail))
        elif platform == "tiktok":
            log_event(conn, "tiktok", "CompletePayment", oid, event_id, False, f"skipped_no_keys {tag}")

    return results



def send_test_event(conn, platform: str = "", account_id: int | None = None) -> tuple[bool, str]:
    ensure_tables(conn)
    acct = get_account(conn, account_id=account_id) if account_id else None
    if not acct and platform:
        acct = get_default_account(conn, platform)
    cfg = account_to_cfg(acct) if acct else load_config(conn)
    platform = (acct.get("platform") if acct else platform or "").strip().lower()
    fake_order = {"id": f"test_{int(time.time())}", "due_cents": 100, "currency": "USD", "email": ""}
    attrs = {}
    event_id = f"test_{platform}_{int(time.time())}"
    tag = f"acct={(acct or {}).get('code') or '-'}"
    if platform == "meta":
        ok, detail = send_meta_event(cfg, "PageView", None, attrs, event_id, source_url="https://linkiip.com/")
        log_event(conn, "meta", "PageView", fake_order["id"], event_id, ok, detail if not ok else f"test_ok {tag}")
        return ok, detail
    if platform == "google":
        ok, detail = send_google_mp_purchase(cfg, fake_order, attrs, event_id)
        log_event(conn, "google", "purchase", fake_order["id"], event_id, ok, detail if not ok else f"test_ok {tag}")
        return ok, detail
    if platform == "tiktok":
        ok, detail = send_tiktok_purchase(cfg, fake_order, attrs, event_id, "https://linkiip.com/")
        log_event(conn, "tiktok", "CompletePayment", fake_order["id"], event_id, ok, detail if not ok else f"test_ok {tag}")
        return ok, detail
    return False, "unknown_platform"
