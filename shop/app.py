import asyncio
import json
import queue
import time
import os
import re
import secrets
import hashlib
import random
import shutil
import tempfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from shop.mobile_api import mount_mobile_api
from fastapi.templating import Jinja2Templates

from shop.ads import load_ads, sponsored_skus
from shop.adtrack import (
    SEG_PRESETS,
    PLATFORMS,
    PLATFORM_FIELDS,
    build_creative_url,
    load_config as load_ad_config,
    load_stored_config,
    save_stored_config,
    mask_secret,
    merge_from_request,
    pack_cookie as pack_ad_cookie,
    parse_cookie as parse_ad_cookie,
    public_pixel_config,
    public_pixels_for_attrs,
    recent_logs as recent_ad_logs,
    save_attribution,
    send_test_event,
    status_cards as ad_status_cards,
    ensure_tables as ensure_ad_tables,
    normalize_seg,
    seg_match_score,
    record_funnel,
    funnel_stats,
    should_send_conversion,
    list_accounts,
    get_account,
    get_default_account,
    resolve_account,
    account_to_cfg,
    accounts_by_platform,
    create_account,
    update_account,
    delete_account,
)
from shop.lp_links import (
    create_link as create_lp_link,
    get_by_code as get_lp_link,
    list_recent as list_lp_links,
    preview_path as lp_preview_path,
)
from shop.lp_modules import (
    IMPULSE_MAX_CENTS,
    IMPULSE_MIN_CENTS,
    SKINS as LP_SKINS,
    TEMPLATES as LP_TEMPLATES,
    LpChoiceError,
    band_groups,
    resolve_module,
)
from shop.alibaba import (
    AlibabaFormatError,
    apply_intercept_rules,
    apply_prices,
    detail_image_urls,
    group_rows,
    hold_reason,
    parse_percent,
    parse_rate,
    parse_sheet,
    sku_price,
)
from shop.advantages import generate_advantages
from shop.cache import open_cache
from shop.seo import (
    OPEN_LANGS,
    absolute,
    first_sentence,
    hreflang_links,
    indexable_product,
    is_private,
    page_title,
    public_url,
    strip_prefix,
)

from shop.campaigns import (
    active_campaign,
    buyer_is_new,
    campaign_special_possible,
    half_cents,
    items_for,
    newcomer_kept,
    pack_hold,
    parse_hold,
    price_for,
)
from shop.checkout import (
    CheckoutError,
    Outbox,
    apply_reset,
    build_quote,
    cancel_order,
    dump_lines,
    find_sellable,
    hash_password,
    issue_reset,
    best_coupon,
    list_coupons,
    load_lines,
    merge_line,
    _bind_referrer,
    place_order,
    verify_password,
    live_offers,
    cheapest_live_offer,
)
from shop.db import connect
from shop.extras import (
    COLORS,
    LOCALES,
    bump_interest,
    bump_taste,
    delivery_span,
    read_interest,
    read_taste,
    read_notes,
    read_skus,
    write_notes,
    write_skus,
)
from shop.fx import NoRate, Rate, RateBook, fetch_rates, load_rates, remember_rates
from shop.image_translate import (
    IMAGE_LANGS,
    ImageAuthError,
    ImageTranslateError,
    image_has_cjk,
    language_file,
    pending_images,
    stamp_missing_uploads,
    storefront_image,
)
from shop.gen_connect import LinkError, open_gpu, parse_ssh
from shop.image_gen import (
    DEFAULT_GEN_API_MODEL,
    DEFAULT_GEN_API_URL,
    DEFAULT_GEN_API_WORKERS,
    MAX_GEN_API_WORKERS,
    ApiEditor,
    CommerceImageClient,
    GenError,
    HttpEditor,
    claim_sku_task,
    claim_task,
    enqueue,
    enqueue_sku,
    enqueue_sku_shots,
    finish_sku_task,
    finish_task,
    generate_product,
    generate_one_sku_shot,
    generate_sku_shots,
    generate_story,
    has_pending_sku_shot,
    list_pending_sku_shot_units,
    count_pending_sku_shots,
    main_urls,
    missing_story_slots,
    has_pending_shot,
    pending_rows,
    plan_product,
    plan_queue,
    plan_sku_product,
    plan_sku_queue,
    release_abandoned,
    release_abandoned_sku,
    source_url,
    sku_task_progress,
    story_urls,
    task_progress,
)
from shop.images import card_image, phone_image, save_image_bytes, save_remote_image
from shop.package import PackageError, describe_preview, is_jushuitan_sheet, preview_sheets, read_package
from shop.net import outbound_proxy, remembered_proxy
from shop.ops import board, product_interest_count, record
from shop.translate import LANGS, fill_from_english, fill_languages, has_cjk, translate_fields, translator_from_env
from shop.writer import CURSOR_LANES, ai_from_env, ai_pair, cursor_product, prepare_cursor_lanes, supplier_link
from shop.address_format import compose_street, formats_for, label_lines
from shop.divisions import city_choices, country_choices, region_choices
from shop.geo import country_for, lookup_here, lookup_postal
from shop.coefficients import coefficient_for, load as load_coefficients, rows_for_admin as coefficient_rows, save as save_coefficients, DEFAULTS as COEF_DEFAULTS
from shop.interest import account_weights, merge_weights, note_click
from shop.i18n import CATEGORIES, UI
from shop.locale import resolve, shipping_tier
from shop.pay import (
    LianLianCheckout,
    MemoryStripe,
    PayPalCheckout,
    StripeCheckout,
    StripeError,
    add_review,
    ensure_code,
    grant_templates,
    handle_event,
    mark_paid,
    refund_order,
    request_withdrawal,
    ship_order,
    utc_day,
)
from shop.markets import judge_batch, judge_one, push_line, rank
from shop.hot import build_scores, hot_line, refresh_titles, stale
from shop.pricing import quote
from shop.seed import seed
from shop.support import mount_support, ensure_cs_tables, push_open_room_cart
from shop.staff import (
    authenticate,
    clean_username,
    is_admin_role,
    reset_staff_password,
    save_staff,
    set_staff_enabled,
    staff_from_token,
    start_session,
)
from shop.admin_money import cents_to_dollars_str, dollars_to_cents, format_usd
from shop.suggest import BROWSE_SHARE, blend_order, category_weights, choose, diverse_order, fit_add, for_you, personal_order, ranked_choose, ranked_for_you
from shop.taxonomy import CHILDREN, HOME_FACE, ZH, children, known, labels_for

ROOT = Path(__file__).resolve().parent


def _ai_parts(pair):
    if not pair:
        return None, None, None
    if len(pair) == 2:
        writer, translator = pair
        return writer, translator, None
    writer, translator, complete = pair
    return writer, translator, complete


def _secret_text(env_name, file_name):
    path = os.environ.get(file_name, "").strip()
    if path:
        return Path(path).read_text(encoding="utf-8")
    return os.environ.get(env_name, "").replace("\\n", "\n").strip()
MINOR = {"JPY": 0, "USD": 2, "EUR": 2, "GBP": 2, "BRL": 2, "MXN": 2, "CAD": 2, "CNY": 2, "TWD": 2, "HKD": 2}
SYMBOL = {"USD": "$", "EUR": "€", "GBP": "£", "BRL": "R$", "MXN": "MX$", "CAD": "CA$", "JPY": "円", "CNY": "¥", "TWD": "NT$", "HKD": "HK$"}
SORTS = {
    "featured": "rowid asc",
    "price_asc": "price_cents asc",
    "price_desc": "price_cents desc",
    "newest": "rowid desc",
}


class FixedBook:
    def __init__(self, units):
        self.units = units

    def rate_for(self, currency, now):
        if currency == "USD":
            return Rate(1.0, False)
        return Rate(self.units, False)


def href(path, country):
    join = "&" if "?" in path else "?"
    return f"{path}{join}country={country}"


def _public_h5_origin(request):
    """Keep the Vite dev address on localhost. Public pages use this site."""
    raw = (os.environ.get("HARBOR_H5_ORIGIN") or "").rstrip("/")
    host = ""
    try:
        host = (request.headers.get("x-forwarded-host") or request.url.hostname or "")
        host = host.split(",")[0].strip().lower().split(":")[0]
    except Exception:
        host = ""
    if host in {"127.0.0.1", "localhost"}:
        return raw
    if "127.0.0.1" in raw or "localhost" in raw.lower():
        return ""
    return raw


def _breadcrumb(crumbs):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": index, "name": name, "item": url}
            for index, (name, url) in enumerate(crumbs, 1)
        ],
    }


def _xml(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _seo_label(path, text):
    bare = strip_prefix(path)
    named = {
        "/": text["hero_title"],
        "/categories": text["departments"],
        "/policies/shipping": text["shipping_policy"],
        "/policies/privacy": text["privacy"],
        "/contact": text["contact"],
    }
    if bare in named:
        return named[bare]
    parts = [part for part in bare.split("/") if part]
    if parts and parts[0] == "c" and len(parts) > 1:
        return text["categories"].get(parts[1], "")
    return ""


def safe_next(raw):
    text = str(raw or "/cart")
    path = text.split("?")[0]
    if path == "/cart":
        return "/cart?bundle=1" if "bundle=1" in text else "/cart"
    if path == "/checkout" or path.startswith("/p/") or path.startswith("/lp/"):
        return path
    return "/cart"


def format_money(amount, currency):
    if currency == "JPY":
        return f"{amount:,}円"
    return f"{SYMBOL.get(currency, '')}{amount / 100:,.2f}"


def goods_local(cents, units, currency):
    shown = quote(
        merchandise_cents=cents,
        tiers=[],
        coupon_cents=0,
        coupon_threshold_cents=1,
        free_shipping_cents=10**12,
        shipping_cents=0,
        balance_cents=0,
        use_balance=False,
        units_per_usd=units,
        minor_units=MINOR.get(currency, 2),
    )
    return shown.due_local


def _plain_name(value):
    if isinstance(value, dict):
        for key in ("name", "zh", "en"):
            found = _plain_name(value.get(key))
            if found:
                return found
        return ""
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if not text:
        return ""
    if text[0] in "{[":
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return text
        return _plain_name(parsed)
    return text



def catalog_lang_hint(request):
    """App/API language hint: query hl, X-Harbor-Lang, cookie harbor_hl."""
    try:
        q = (request.query_params.get("hl") or "").strip()
    except Exception:
        q = ""
    try:
        header = (request.headers.get("x-harbor-lang") or request.headers.get("X-Harbor-Lang") or "").strip()
    except Exception:
        header = ""
    try:
        cookie = (request.cookies.get("harbor_hl") or "").strip()
    except Exception:
        cookie = ""
    return q or header or cookie or ""



def normalize_ui_lang(raw):
    """Map request language tags to a UI dict key (zh/zh-Hant/en/es/de/fr/pt/ja)."""
    key = str(raw or "").replace("_", "-").strip().lower()
    if not key:
        return ""
    if key.startswith("zh"):
        # Traditional: zh-Hant / zh-TW / zh-HK / zh-MO
        rest = key[2:].lstrip("-")
        if rest.startswith("hant") or rest in {"tw", "hk", "mo"} or key in {"zh-hant", "zh-tw", "zh-hk", "zh-mo"}:
            return "zh-Hant"
        return "zh"
    # Exact UI keys (e.g. zh-Hant) after lowercasing need rematch
    for ui_key in UI:
        if ui_key.lower() == key:
            return ui_key
    code = key.split("-", 1)[0]
    if code in UI:
        return code
    return ""


def ui_lang_hint(request):
    """Explicit UI language only: lang/hl query, harbor_hl cookie, X-Harbor-Lang.

    Accept-Language is intentionally ignored so language follows the selected
    country (US stays English even on a Chinese browser).
    """
    raw = ""
    try:
        raw = (request.query_params.get("lang") or request.query_params.get("hl") or "").strip()
    except Exception:
        raw = ""
    if not raw:
        try:
            raw = (request.cookies.get("harbor_hl") or request.cookies.get("harbor_lang") or "").strip()
        except Exception:
            raw = ""
    if not raw:
        try:
            raw = (request.headers.get("x-harbor-lang") or request.headers.get("X-Harbor-Lang") or "").strip()
        except Exception:
            raw = ""
    return normalize_ui_lang(raw)


def accept_ui_lang(header):
    """First Accept-Language tag that maps to a storefront UI language."""
    raw = str(header or "").strip()
    if not raw:
        return ""
    for part in raw.split(","):
        code = normalize_ui_lang(part.split(";", 1)[0].strip())
        if code and code in UI:
            return code
    return ""


def ui_lang_for(request, country_lang):
    """Manual choice, otherwise the IP country's language.

    Explicit ``?lang=`` / ``?hl=`` and the ``harbor_hl`` cookie are a manual
    choice. Accept-Language never overrides the country default. Currency
    stays on the IP country and is not read here.
    """
    raw = ""
    try:
        raw = (request.query_params.get("lang") or request.query_params.get("hl") or "").strip()
    except Exception:
        raw = ""
    hinted = normalize_ui_lang(raw)
    if hinted and hinted in UI:
        return hinted
    try:
        saved = normalize_ui_lang(request.cookies.get("harbor_hl") or "")
    except Exception:
        saved = ""
    if saved and saved in UI:
        return saved
    if country_lang in UI:
        return country_lang
    return "en"


def prefer_zh_copy(request_or_hint):
    """True when App asks for Chinese original product copy (not OPEN_LANGS SEO)."""
    if request_or_hint is None:
        return False
    if hasattr(request_or_hint, "query_params"):
        raw = catalog_lang_hint(request_or_hint)
    else:
        raw = str(request_or_hint or "")
    key = raw.replace("_", "-").strip().lower()
    if not key:
        return False
    if key in {"zh", "zh-hans", "zh-hant", "zh-cn", "zh-tw", "zh-hk", "zh-mo", "zh-sg"}:
        return True
    return key.startswith("zh-") or key.startswith("zh_")


def _product_label(source_zh, names, sku):
    return _plain_name(source_zh) or _plain_name(names) or sku


def _has_cjk(text):
    """Han, kana, or hangul. Latin storefronts must not show these."""
    for ch in str(text or ""):
        code = ord(ch)
        if (
            0x3400 <= code <= 0x4DBF
            or 0x4E00 <= code <= 0x9FFF
            or 0xF900 <= code <= 0xFAFF
            or 0x3040 <= code <= 0x30FF
            or 0x31F0 <= code <= 0x31FF
            or 0xAC00 <= code <= 0xD7AF
        ):
            return True
    return False


def _lang_allows_cjk(lang):
    key = str(lang or "")
    # zh* is Chinese. Japanese titles use kanji and kana, so ja keeps them.
    # Every other language drops CJK and falls back to English, then sku.
    return key == "ja" or key.startswith("zh")


def localized_copy(value, lang, fallback="", source_zh=""):
    """Pick product copy: names[lang] → names[en] → fallback.

    ``source_zh`` is used only when lang is zh*. A non-zh/ja candidate that
    still contains CJK is skipped, so an English page cannot show a Chinese
    title that was stored under ``en`` or only in ``source_zh``.
    """
    lang = str(lang or "en")
    names = {}
    bare = ""
    if isinstance(value, dict):
        names = value
    elif isinstance(value, str):
        text = value.strip()
        if text[:1] in "{[":
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                names = parsed
            else:
                bare = text
        else:
            bare = text
    else:
        bare = _plain_name(value)

    def accept(raw):
        text = _plain_name(raw)
        if not text:
            return ""
        if not _lang_allows_cjk(lang) and _has_cjk(text):
            return ""
        return text

    if str(lang).startswith("zh"):
        zh = accept(source_zh)
        if zh:
            return zh
    if names:
        picked = accept(names.get(lang))
        if picked:
            return picked
        if lang != "en":
            picked = accept(names.get("en"))
            if picked:
                return picked
        return fallback
    return accept(bare) or fallback


def load_promos(conn):
    rows = conn.execute("select key, value from promos").fetchall()
    data = {row["key"]: json.loads(row["value"]) for row in rows}
    data["tiers"] = [tuple(pair) for pair in data["tiers"]]
    return data


GUARANTEE_DEFAULTS = {
    "late_delivery_credit_cents": 500,
    "return_days": 30,
    "checkout_min_cents": 1500,  # $15. Stored settings override this.
}


def load_guarantees(conn):
    row = conn.execute("select value from settings where key = 'platform_guarantees'").fetchone()
    data = dict(GUARANTEE_DEFAULTS)
    if row and row["value"]:
        try:
            raw = json.loads(row["value"])
        except json.JSONDecodeError:
            raw = {}
        if isinstance(raw, dict):
            for key in GUARANTEE_DEFAULTS:
                if key not in raw:
                    continue
                try:
                    data[key] = int(raw[key])
                except (TypeError, ValueError):
                    continue
    data["late_delivery_credit_cents"] = max(0, min(50000, int(data["late_delivery_credit_cents"])))
    data["return_days"] = max(0, min(365, int(data["return_days"])))
    data["checkout_min_cents"] = max(0, min(10**7, int(data["checkout_min_cents"])))
    return data


def save_guarantees(conn, data):
    payload = {
        "late_delivery_credit_cents": int(data.get("late_delivery_credit_cents", GUARANTEE_DEFAULTS["late_delivery_credit_cents"])),
        "return_days": int(data.get("return_days", GUARANTEE_DEFAULTS["return_days"])),
        "checkout_min_cents": int(data.get("checkout_min_cents", GUARANTEE_DEFAULTS["checkout_min_cents"])),
    }
    conn.execute(
        "insert into settings (key, value) values ('platform_guarantees', ?) on conflict(key) do update set value = excluded.value",
        (json.dumps(payload),),
    )
    return payload


def checkout_quote(conn, country, units, currency):
    promos = load_promos(conn)
    tier = shipping_tier(country)
    return quote(
        merchandise_cents=0,
        tiers=promos["tiers"],
        coupon_cents=0,
        coupon_threshold_cents=0,
        free_shipping_cents=0,
        shipping_cents=0,
        balance_cents=0,
        use_balance=False,
        units_per_usd=units,
        minor_units=MINOR.get(currency, 2),
    )


def _local_pictures(raw, key):
    try:
        listing = json.loads(raw or "")
    except json.JSONDecodeError:
        return []
    if not isinstance(listing, dict):
        return []
    pictures = []
    for picture in listing.get(key) or []:
        if isinstance(picture, str) and picture.startswith("/static/"):
            pictures.append(picture)
    return pictures


def stored_detail_images(raw):
    return _local_pictures(raw, "detail_images")


def stored_gallery(raw):
    return _local_pictures(raw, "gallery")


def _plant_package_images(item, save_held=False):
    folder = ROOT / "static" / "catalog" / item["sku"]
    gallery = []
    for index, data in enumerate(item.pop("mains", []) or []):
        saved = save_image_bytes(data, folder, index, max_bytes=None)
        if saved and saved not in gallery:
            gallery.append(saved)
    item["listing"]["gallery"] = gallery
    details = []
    for index, data in enumerate(item.pop("details", []) or []):
        saved = save_image_bytes(data, folder, f"d{index}", max_bytes=None)
        if saved and saved not in details:
            details.append(saved)
    item["listing"]["detail_images"] = details
    for index, offer in enumerate(item.get("offers") or []):
        data = offer.get("image")
        if offer.get("hold") and not save_held:
            offer["image"] = ""
            continue
        if isinstance(data, (bytes, bytearray)):
            saved = save_image_bytes(data, folder, f"c{index}", max_bytes=None)
            offer["image"] = saved or (gallery[0] if gallery else "")
    if gallery and not item.get("image_url"):
        item["image_url"] = gallery[0]


def fill_saved_product_images(conn, item):
    """Put package photos on a sku that is already in the catalog.

    Titles, prices, and published stay as they are. Language folders such as
    catalog/sku/en are not touched.
    """
    sku = item.get("sku") or ""
    if not sku:
        return False
    row = conn.execute(
        "select image_url, listing, offers from products where sku = ?",
        (sku,),
    ).fetchone()
    if row is None:
        return False
    has_bytes = any(
        isinstance(offer.get("image"), (bytes, bytearray)) and offer.get("image")
        for offer in item.get("offers") or []
    )
    if not (item.get("mains") or item.get("details") or has_bytes):
        return False
    _plant_package_images(item, save_held=True)
    gallery = list((item.get("listing") or {}).get("gallery") or [])
    details = list((item.get("listing") or {}).get("detail_images") or [])
    image_url = item.get("image_url") or row["image_url"] or (gallery[0] if gallery else "")
    try:
        offers = json.loads(row["offers"] or "[]")
    except json.JSONDecodeError:
        offers = []
    incoming = []
    by_id = {}
    for offer in item.get("offers") or []:
        image = offer.get("image") if isinstance(offer, dict) else ""
        if not isinstance(image, str) or not image.startswith("/static/"):
            image = ""
        incoming.append(image)
        if isinstance(offer, dict) and offer.get("id") and image:
            by_id[str(offer["id"])] = image
    if isinstance(offers, list):
        for index, offer in enumerate(offers):
            if not isinstance(offer, dict):
                continue
            image = by_id.get(str(offer.get("id") or ""))
            if not image and index < len(incoming):
                image = incoming[index]
            if image:
                offer["image"] = image
    else:
        offers = []
    conn.execute(
        """
        update products
        set image_url = ?,
            offers = ?,
            listing = case
                when json_valid(listing) then json_set(
                    listing,
                    '$.gallery', json(?),
                    '$.detail_images', json(?)
                )
                else listing
            end
        where sku = ?
        """,
        (
            image_url,
            json.dumps(offers, ensure_ascii=False),
            json.dumps(gallery, ensure_ascii=False),
            json.dumps(details, ensure_ascii=False),
            sku,
        ),
    )
    return bool(gallery or details or image_url)




def strike_factor(key):
    """Stable 1.80–2.20 multiplier. Same product keeps the same list price."""
    n = 2166136261
    for ch in str(key or "x"):
        n ^= ord(ch)
        n = (n * 16777619) & 0xFFFFFFFF
    return (180 + (n % 41)) / 100.0


def strike_list_cents(sale, key):
    sale = int(sale or 0)
    if sale <= 0:
        return 0
    listed = int(sale * strike_factor(key) + 0.5)
    if listed <= sale:
        listed = sale + 1
    return listed


def sale_list_cents(row):
    """Return (sale_cents, list_cents). List is sale times 1.80–2.20, stable per SKU."""
    offer = cheapest_live_offer(row)
    sku = row["sku"] if "sku" in row.keys() else ""
    if offer is not None:
        sale = int(offer.get("price_cents") or 0)
        key = f"{sku}~{offer.get('id') or ''}"
    else:
        sale = int(row["price_cents"] or 0)
        key = sku
    return sale, strike_list_cents(sale, key)



def line_sale_list_cents(row, line_sku):
    """Sale/list cents for a cart line (parent~offerId uses that offer, else cheapest)."""
    parent, sep, oid = str(line_sku or "").partition("~")
    sku = row["sku"] if "sku" in row.keys() else parent
    if sep and oid:
        for offer in live_offers(row):
            if str(offer.get("id") or "") == str(oid):
                sale = int(offer.get("price_cents") or 0)
                return sale, strike_list_cents(sale, f"{sku}~{oid}")
    return sale_list_cents(row)


def catalog_file_exists(url, root):
    text = str(url or "").strip()
    if not text.startswith("/static/"):
        return bool(text)
    path = Path(root) / "static" / text[len("/static/"):]
    return path.is_file()


def resolve_catalog_image(url, row, lang, root):
    """Use url when the file exists; else product image_url / generated main / any on-disk shot / svg."""
    sku = ""
    fallbacks = []
    if url:
        fallbacks.append(str(url))
    if row is not None:
        sku = str(row["sku"] if "sku" in row.keys() else "")
        img = ""
        if "image_url" in row.keys() and row["image_url"]:
            img = str(row["image_url"])
        if img:
            fallbacks.append(img)
        if sku:
            try:
                mains = list(main_urls(sku, lang, root) or [])
            except Exception:
                mains = []
            if not mains and lang != "en":
                try:
                    mains = list(main_urls(sku, "en", root) or [])
                except Exception:
                    mains = []
            fallbacks.extend(mains)
            # Any existing catalog file for this SKU (s0/c1/etc.) before SVG placeholder.
            folder = Path(root) / "static" / "catalog" / sku
            if folder.is_dir():
                for path in sorted(folder.glob("*.jpg")) + sorted(folder.glob("*.png")) + sorted(folder.glob("*.webp")):
                    fallbacks.append(f"/static/catalog/{sku}/{path.name}")
                for sub in ("en/main", f"{lang}/main"):
                    subdir = folder / sub
                    if subdir.is_dir():
                        for path in sorted(subdir.glob("*.jpg")):
                            fallbacks.append(f"/static/catalog/{sku}/{sub}/{path.name}")
            fallbacks.append(f"/static/products/{sku}.svg")
    seen = set()
    for cand in fallbacks:
        cand = str(cand or "").strip()
        if not cand or cand in seen:
            continue
        seen.add(cand)
        if cand.startswith("/static/"):
            if catalog_file_exists(cand, root):
                if "/catalog/" in cand and "/products/" not in cand:
                    try:
                        return storefront_image(cand, lang, root)
                    except Exception:
                        return cand
                return cand
        elif cand.startswith("http://") or cand.startswith("https://"):
            return cand
    # Last resort: SVG path even if missing (browser may 404 less harshly than broken jpg)
    if sku:
        return f"/static/products/{sku}.svg"
    return ""


def format_off_pct(sale_cents, list_cents):
    """Percent off vs list, only when list > sale. One decimal when needed."""
    if not (list_cents > sale_cents > 0):
        return ""
    pct = (list_cents - sale_cents) * 100.0 / list_cents
    if abs(pct - round(pct)) < 0.05:
        return str(int(round(pct)))
    return f"{pct:.1f}"


def deal_ends_iso(conn):
    """Prefer live seckill ends_at; else end of current UTC day (deal clock)."""
    now = datetime.now(timezone.utc)
    camp = None
    try:
        camp = active_campaign(conn, "seckill")
    except Exception:
        camp = None
    if camp is not None:
        ends = camp["ends_at"] if "ends_at" in camp.keys() else None
        if ends:
            try:
                dt = datetime.fromisoformat(str(ends).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt > now:
                    return dt.isoformat()
            except ValueError:
                pass
    end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    if end <= now:
        end = end + timedelta(days=1)
    return end.isoformat()


def offer_view(row, ctx):
    original_cents = row["original_cents"] if "original_cents" in row.keys() else 0
    raw = []
    if "offers" in row.keys() and row["offers"]:
        try:
            raw = json.loads(row["offers"])
        except json.JSONDecodeError:
            raw = []

    def money_of(cents):
        if ctx["units"] is None or not cents:
            return ""
        return format_money(goods_local(cents, ctx["units"], ctx["currency"]), ctx["currency"])

    offers = []
    for offer in raw:
        if offer.get("hold"):
            continue
        label = offer.get("label") or ""
        offer_lang = ctx.get("lang") or "en"
        if str(offer_lang).startswith("zh") and (offer.get("source_label") or "").strip():
            text = str(offer.get("source_label") or "").strip()
        else:
            text = localized_copy(label, offer_lang, fallback="")
        if not text:
            text = str(offer.get("id") or "")
        sale = int(offer.get("price_cents") or 0)
        listed = strike_list_cents(sale, f"{row['sku'] if 'sku' in row.keys() else ''}~{offer.get('id') or ''}")
        save_cents = (listed - sale) if listed > sale else 0
        offers.append({
            "id": offer.get("id") or "",
            "label": text,
            "price": money_of(sale),
            "original": money_of(listed) if listed and listed > sale else "",
            "save": money_of(save_cents) if save_cents else "",
            "higher": listed > sale,
            "off_pct": format_off_pct(sale, listed) if listed > sale else "",
            "image": offer.get("image") or "",
            "generated": 1 if offer.get("generated") else 0,
        })
    pictures = []
    for offer in offers:
        if offer["image"] and offer["image"] not in pictures:
            pictures.append(offer["image"])
    sale_cents, list_cents = sale_list_cents(row)
    if list_cents > sale_cents > 0:
        original = money_of(list_cents)
        higher = True
        off_pct = format_off_pct(sale_cents, list_cents)
    elif original_cents and original_cents != (sale_cents or int(row["price_cents"] or 0)):
        original = money_of(original_cents)
        higher = original_cents > (sale_cents or int(row["price_cents"] or 0))
        off_pct = format_off_pct(sale_cents or int(row["price_cents"] or 0), original_cents) if higher else ""
    else:
        original = ""
        higher = False
        off_pct = ""
    # Enrich offers with off_pct for PDP switcher
    for offer in offers:
        # recompute from money strings is hard; leave; JS uses data-off-pct from template
        pass
    return {
        "offers": offers if len(offers) > 1 or any(item["label"] for item in offers) else [],
        "has_skus": bool(raw),
        "original": original,
        "higher": higher,
        "off_pct": off_pct,
        "images": pictures,
    }



class HarborLangCookie:
    """Persist lang/hl query onto harbor_hl for all HTML responses (not only render())."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        # Ad landing pages never record a manual language choice.
        if str(scope.get("path") or "").startswith("/lp/ad"):
            await self.app(scope, receive, send)
            return
        qs = scope.get("query_string") or b""
        try:
            from urllib.parse import parse_qs
            params = parse_qs(qs.decode("latin-1"))
            raw = (params.get("lang") or params.get("hl") or [""])[0]
        except Exception:
            raw = ""
        code = normalize_ui_lang(raw) if raw else ""
        if not code or code not in UI:
            await self.app(scope, receive, send)
            return

        async def send_wrap(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                # avoid duplicating if already set
                if not any(k.lower() == b"set-cookie" and b"harbor_hl=" in v for k, v in headers):
                    cookie = f"harbor_hl={code}; Max-Age=31536000; Path=/; SameSite=lax".encode()
                    headers.append((b"set-cookie", cookie))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_wrap)


class LangPrefix:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope.get("path") or "/"
            for code in ("de", "es"):
                head = f"/{code}"
                if path == head or path.startswith(head + "/"):
                    rest = path[len(head):] or "/"
                    scope = dict(scope)
                    scope["path"] = rest
                    scope["raw_path"] = rest.encode()
                    state = dict(scope.get("state") or {})
                    state["seo_lang"] = code
                    scope["state"] = state
                    break
        await self.app(scope, receive, send)



def _load_dotenv():
    for path in (Path(__file__).resolve().parent / ".env", Path(__file__).resolve().parents[1] / ".env"):
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if not key or key in os.environ:
                continue
            value = value.strip().strip('"').strip("'")
            os.environ[key] = value


def create_app(*, units_per_usd=None, db_path=None, book=None, cache=None, advantage_model=None, translator=None, writer=None, image_fetch=None, image_client=None, gen_editors=None, gen_connector=None):
    _load_dotenv()
    app = FastAPI()

    class LoginRequired(Exception):
        pass

    @app.exception_handler(LoginRequired)
    async def admin_login_required(request: Request, exc: LoginRequired):
        return RedirectResponse("/admin/login", status_code=303)
    app.add_middleware(GZipMiddleware, minimum_size=800)
    app.add_middleware(LangPrefix)
    app.add_middleware(HarborLangCookie)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    db_path = db_path or os.environ.get("SHOP_DB", ":memory:")
    conn = connect(db_path)
    if db_path and db_path != ":memory:":
        preview_root = Path(db_path).resolve().parent / "catalog-preview"
    else:
        preview_root = Path(tempfile.mkdtemp(prefix="harbor-preview-"))
    preview_root.mkdir(parents=True, exist_ok=True)
    seed(conn)
    stamp_missing_uploads(conn, ROOT / "static" / "catalog", date.today().isoformat())
    app.state.db = conn
    app.state.image_client = image_client
    app.state.gen_editors = gen_editors
    app.state.gen_connector = gen_connector
    app.state.outbox = Outbox()

    def saved_or_env(key, env_name="", default=""):
        row = conn.execute("select value from settings where key = ?", (key,)).fetchone()
        if row is not None and str(row["value"] or "").strip():
            return str(row["value"]).strip()
        if env_name:
            found = os.environ.get(env_name, "").strip()
            if found:
                return found
        return default

    def save_setting(key, value):
        conn.execute(
            "insert into settings (key, value) values (?, ?) on conflict(key) do update set value = excluded.value",
            (key, value),
        )

    def apply_checkout():
        paypal_id = saved_or_env("paypal_client_id", "PAYPAL_CLIENT_ID")
        paypal_secret = saved_or_env("paypal_client_secret", "PAYPAL_CLIENT_SECRET")
        paypal_hook = saved_or_env("paypal_webhook_id", "PAYPAL_WEBHOOK_ID")
        paypal_live = saved_or_env("paypal_env", "PAYPAL_ENV", "sandbox").lower() == "live"
        ll_merchant = saved_or_env("lianlian_merchant_id", "LIANLIAN_MERCHANT_ID")
        ll_sub = saved_or_env("lianlian_sub_merchant_id", "LIANLIAN_SUB_MERCHANT_ID")
        ll_private = saved_or_env("lianlian_private_key") or _secret_text("LIANLIAN_PRIVATE_KEY", "LIANLIAN_PRIVATE_KEY_FILE")
        ll_public = saved_or_env("lianlian_public_key") or _secret_text("LIANLIAN_PUBLIC_KEY", "LIANLIAN_PUBLIC_KEY_FILE")
        ll_live = saved_or_env("lianlian_env", "LIANLIAN_ENV", "sandbox").lower() == "live"
        ll_country = saved_or_env("lianlian_country", "LIANLIAN_COUNTRY", "CN") or "CN"
        stripe_secret = saved_or_env("stripe_secret_key", "STRIPE_SECRET_KEY")
        stripe_hook = saved_or_env("stripe_webhook_secret", "STRIPE_WEBHOOK_SECRET")
        paypal_ready = bool(paypal_id and paypal_secret)
        lianlian_ready = bool(ll_merchant and ll_sub and ll_private)
        stripe_ready = bool(stripe_secret)
        stored = conn.execute("select value from settings where key = ?", ("pay_providers",)).fetchone()
        if stored is not None:
            enabled = [part for part in str(stored["value"] or "").split(",") if part in {"paypal", "lianlian", "stripe"}]
        else:
            legacy = saved_or_env("pay_provider", "PAY_PROVIDER", "auto").lower()
            if legacy in {"paypal", "lianlian", "stripe"}:
                enabled = [legacy]
            else:
                enabled = [
                    name for name, ready in (
                        ("paypal", paypal_ready),
                        ("lianlian", lianlian_ready),
                        ("stripe", stripe_ready),
                    ) if ready
                ]
        gateways = {}
        if "paypal" in enabled and paypal_ready:
            gateways["paypal"] = PayPalCheckout(conn, paypal_id, paypal_secret, paypal_hook, sandbox=not paypal_live)
        if "lianlian" in enabled and lianlian_ready:
            gateways["lianlian"] = LianLianCheckout(
                conn, ll_merchant, ll_sub, ll_private, ll_public,
                sandbox=not ll_live, country=ll_country,
            )
        if "stripe" in enabled and stripe_ready:
            gateways["stripe"] = StripeCheckout(conn, stripe_secret, stripe_hook)
        app.state.gateways = gateways
        app.state.stripe = next(iter(gateways.values()), None) or MemoryStripe()
        shown = [name for name in ("paypal", "lianlian", "stripe") if name in gateways]
        app.state.pay_status = {
            "provider": ",".join(enabled),
            "enabled": enabled,
            "shown": shown,
            "active": shown[0] if shown else "none",
            "paypal_live": paypal_live,
            "paypal_ready": paypal_ready,
            "lianlian_ready": lianlian_ready,
            "stripe_ready": stripe_ready,
        }
        return app.state.pay_status

    apply_checkout()
    app.state.cache = cache or open_cache()
    app.state.memo = {}
    app.state.catalog_token = 0
    app.state.hot = {}
    app.state.hot_token = 0
    app.state.hot_ready = False
    app.state.advantage_model = advantage_model
    complete = None
    if writer is None and translator is None:
        writer, translator, complete = _ai_parts(ai_from_env())
    app.state.writer = writer
    app.state.translator = translator
    app.state.complete = complete
    app.state.image_fetch = image_fetch
    job_lock = threading.Lock()

    def blank_job(kind=""):
        return {
            "running": False,
            "kind": kind,
            "phase": "",
            "done": 0,
            "total": 0,
            "label": "",
            "error": "",
            "url": "",
            "workers": 0,
            "result": {"imported": 0, "held": 0, "skipped": 0, "published": 0, "failed": 0, "price_held": 0},
        }

    def _job_settings_key(kind):
        if kind == "upload":
            return "catalog_upload_job"
        if kind == "translate":
            return "catalog_translate_job"
        return "catalog_job"

    def persist_kind_job(kind, snapshot):
        conn.execute(
            "insert into settings (key, value) values (?, ?) on conflict(key) do update set value = excluded.value",
            (_job_settings_key(kind), json.dumps(snapshot, ensure_ascii=False)),
        )

    def _merge_saved_job(job, saved):
        if not isinstance(saved, dict):
            return job
        for key in job:
            if key in saved and key != "result":
                job[key] = saved[key]
        if isinstance(saved.get("result"), dict):
            for key in job["result"]:
                if key in saved["result"]:
                    job["result"][key] = saved["result"][key]
            for key, value in saved["result"].items():
                if key not in job["result"]:
                    job["result"][key] = value
        return job

    def load_kind_job(kind):
        job = blank_job(kind)
        row = conn.execute(
            "select value from settings where key = ?",
            (_job_settings_key(kind),),
        ).fetchone()
        if not row and kind in {"upload", "translate"}:
            # one-time migrate from legacy single catalog_job
            legacy = conn.execute("select value from settings where key = 'catalog_job'").fetchone()
            if legacy:
                try:
                    saved = json.loads(legacy["value"])
                except json.JSONDecodeError:
                    saved = None
                if isinstance(saved, dict) and str(saved.get("kind") or "") == kind:
                    row = legacy
        if row:
            try:
                saved = json.loads(row["value"])
            except json.JSONDecodeError:
                saved = None
            _merge_saved_job(job, saved)
        if job["running"]:
            job["running"] = False
            job["workers"] = 0
            if not job["error"]:
                if kind == "translate":
                    job["error"] = "上次翻译中断了。已经译好的还在，可以再点一次。"
                else:
                    job["error"] = "上次上传中断了。已经保存的商品还在，可以再点一次。"
            persist_kind_job(kind, job)
        job["kind"] = kind
        return job

    app.state.upload_job = load_kind_job("upload")
    app.state.translate_job = load_kind_job("translate")

    def _job_bucket(kind):
        if kind == "translate":
            return "translate_job"
        return "upload_job"

    def kind_job_update(job_kind, **kwargs):
        with job_lock:
            # Call sites often pass kind=...; never let it collide with job_kind.
            kwargs.pop("kind", None)
            bucket = getattr(app.state, _job_bucket(job_kind))
            bucket.update(kwargs)
            bucket["kind"] = job_kind
            snapshot = json.loads(json.dumps(bucket))
            persist_kind_job(job_kind, snapshot)

    def kind_job_read(job_kind):
        with job_lock:
            bucket = getattr(app.state, _job_bucket(job_kind))
            return json.loads(json.dumps(bucket))

    def kind_job_busy(job_kind):
        with job_lock:
            bucket = getattr(app.state, _job_bucket(job_kind))
            return bool(bucket["running"])

    def upload_job_update(**kwargs):
        kwargs.pop("kind", None)
        kind_job_update("upload", **kwargs)

    def translate_job_update(**kwargs):
        kwargs.pop("kind", None)
        kind_job_update("translate", **kwargs)

    def upload_job_read():
        return kind_job_read("upload")

    def translate_job_read():
        return kind_job_read("translate")

    def upload_job_busy():
        return kind_job_busy("upload")

    def translate_job_busy():
        return kind_job_busy("translate")

    def job_read():
        # Compatibility: prefer a running job, else newest non-empty translate/upload snapshot.
        upload = upload_job_read()
        translate = translate_job_read()
        if upload.get("running"):
            primary = dict(upload)
        elif translate.get("running"):
            primary = dict(translate)
        elif translate.get("result", {}).get("published") or translate.get("result", {}).get("failed") or translate.get("error"):
            primary = dict(translate)
        else:
            primary = dict(upload)
        primary["jobs"] = {"upload": upload, "translate": translate}
        primary["upload"] = upload
        primary["translate"] = translate
        primary["any_running"] = bool(upload.get("running") or translate.get("running"))
        return primary

    def job_busy():
        # Legacy helper — true only when BOTH cannot accept new work of that same type.
        # Prefer upload_job_busy / translate_job_busy at call sites.
        return upload_job_busy() or translate_job_busy()

    def pending_part_uploads():
        root = preview_root / "parts"
        items = []
        if not root.is_dir():
            return items
        for folder in sorted(root.iterdir()):
            if not folder.is_dir() or not re.fullmatch(r"[0-9a-f]{16}", folder.name):
                continue
            total = 0
            total_path = folder / "total"
            if total_path.is_file():
                try:
                    total = int(total_path.read_text(encoding="utf-8").strip())
                except ValueError:
                    total = 0
            received = []
            for path in folder.glob("*.part"):
                try:
                    received.append(int(path.stem))
                except ValueError:
                    pass
            received = sorted(set(received))
            meta = {}
            meta_path = folder / "meta.json"
            if meta_path.is_file():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except Exception:
                    meta = {}
            items.append({
                "upload_id": folder.name,
                "filename": meta.get("filename") or "",
                "size": meta.get("size") or 0,
                "total": total or meta.get("total") or 0,
                "received": len(received),
                "complete": bool(total) and len(received) >= total,
            })
        return items

    image_lock = threading.Lock()

    def blank_image_job():
        return {
            "running": False,
            "lang": "",
            "done": 0,
            "total": 0,
            "label": "",
            "error": "",
            "date_from": "",
            "date_to": "",
            "result": {"translated": 0, "failed": 0, "skipped": 0, "products": 0, "kind": ""},
        }

    def persist_image_job(snapshot):
        conn.execute(
            "insert into settings (key, value) values ('image_job', ?) on conflict(key) do update set value = excluded.value",
            (json.dumps(snapshot, ensure_ascii=False),),
        )

    def load_image_job():
        job = blank_image_job()
        row = conn.execute("select value from settings where key = 'image_job'").fetchone()
        if not row:
            return job
        try:
            saved = json.loads(row["value"])
        except json.JSONDecodeError:
            return job
        if isinstance(saved, dict):
            for key in job:
                if key in saved and key != "result":
                    job[key] = saved[key]
            if isinstance(saved.get("result"), dict):
                for key in job["result"]:
                    if key in saved["result"]:
                        job["result"][key] = saved["result"][key]
        if job["running"]:
            job["running"] = False
            if not job["error"]:
                job["error"] = "上次出图中断了。已经有主图和详情的商品不会再出。要接着出就点「继续未译的图」。"
            persist_image_job(job)
        return job

    app.state.image_job = load_image_job()

    def image_job_update(**kwargs):
        with image_lock:
            app.state.image_job.update(kwargs)
            persist_image_job(json.loads(json.dumps(app.state.image_job)))

    def image_job_read():
        with image_lock:
            return json.loads(json.dumps(app.state.image_job))

    def image_job_busy():
        with image_lock:
            return bool(app.state.image_job["running"])

    def gen_is_paused():
        return setting("gen_paused") == "1"

    def gen_job_read():
        progress = task_progress(conn)
        progress["paused"] = gen_is_paused()
        if progress["paused"] and not progress["active"]:
            progress["running"] = False
        return progress

    def image_account():
        key = setting("image_key")
        return {
            "saved": bool(key),
            "tail": key[-4:] if len(key) >= 4 else "",
            "workspace": setting("image_workspace"),
        }

    def gen_api_account():
        key = setting("gen_api_key")
        url = setting("gen_api_url") or DEFAULT_GEN_API_URL
        model = setting("gen_api_model") or DEFAULT_GEN_API_MODEL
        workers_raw = setting("gen_api_workers")
        try:
            workers = int(workers_raw or DEFAULT_GEN_API_WORKERS)
        except ValueError:
            workers = DEFAULT_GEN_API_WORKERS
        workers = max(1, min(MAX_GEN_API_WORKERS, workers))
        return {
            "saved": bool(key),
            "tail": key[-4:] if len(key) >= 4 else "",
            "url": url,
            "model": model,
            "workers": workers,
        }

    def pull(url, sku, index):
        if str(url or "").startswith("/static/catalog/"):
            return url
        if not url:
            return ""
        if app.state.image_fetch is not None:
            saved = app.state.image_fetch(url, sku, index) or ""
        else:
            saved = save_remote_image(url, ROOT / "static" / "catalog" / sku, index)
        return saved if str(saved).startswith("/static/catalog/") else ""
    if book is not None:
        app.state.book = book
    elif units_per_usd is not None:
        app.state.book = FixedBook(units_per_usd)
    else:
        def fetch_live():
            data = fetch_rates()
            hour_key = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")
            remember_rates(conn, data, hour_key)
            return data

        book = RateBook(fetch_live)
        hour_key = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")
        last, current = load_rates(conn, hour_key)
        book.last.update(last)
        for code, units in current.items():
            book.saved[(code, hour_key)] = units
        app.state.book = book
    templates = Jinja2Templates(directory=str(ROOT / "templates"))

    def _tojson(value):
        from markupsafe import Markup
        return Markup(json.dumps(value, ensure_ascii=False).replace("<", "\\u003c"))

    templates.env.filters["tojson"] = _tojson
    templates.env.globals["href"] = href
    templates.env.globals["format_money"] = format_money
    app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")

    def _h5_dist():
        raw = (os.environ.get("HARBOR_H5_DIST") or "").strip()
        candidates = []
        if raw:
            candidates.append(Path(raw))
        candidates.append(Path("/opt/harbor/harbor-web/dist"))
        candidates.append(ROOT.parent / "harbor-web" / "dist")
        for item in candidates:
            if item and (item / "index.html").is_file():
                return item
        return None

    h5_dist = _h5_dist()
    if h5_dist is not None:
        h5_assets = h5_dist / "assets"
        if h5_assets.is_dir():
            app.mount("/assets", StaticFiles(directory=str(h5_assets)), name="harbor_h5_assets")

        @app.get("/chat", include_in_schema=False)
        @app.get("/chat/{rest:path}", include_in_schema=False)
        async def harbor_h5_chat(rest: str = ""):
            return FileResponse(h5_dist / "index.html")

    def _storefront(path):
        if path.startswith("/admin") or path.startswith("/lookup") or path.startswith("/stripe"):
            return False
        return path not in {
            "/sw.js",
            "/manifest.webmanifest",
            "/apple-touch-icon.png",
            "/apple-touch-icon-precomposed.png",
            "/offline",
        }

    def _see(request, path, vid):
        try:
            country = country_for(request)
            lang, _currency = resolve(country)
            record(conn, "page", country=country, lang=lang, visitor=vid)
            if path.startswith("/p/"):
                sku = path[3:].strip("/")
                if sku and "/" not in sku:
                    record(conn, "product", sku=sku, country=country, lang=lang, visitor=vid)
        except Exception:
            return

    def _track(request, kind, sku="", qty=1, cents=0, country=""):
        try:
            picked = country or country_for(request)
            lang, _currency = resolve(picked)
            record(
                conn,
                kind,
                sku=sku,
                country=picked,
                lang=lang,
                visitor=getattr(request.state, "visitor", "") or request.cookies.get("harbor_vid", ""),
                cents=cents,
                qty=qty,
            )
        except Exception:
            return

    def _probe_path(path: str) -> bool:
        lower = (path or "/").split("?", 1)[0].lower()
        if lower.startswith("/.well-known/"):
            return False
        if any(part.startswith(".") for part in lower.split("/") if part):
            return True
        if lower.startswith((
            "/wp-admin", "/wp-login", "/wp-json", "/xmlrpc.php",
            "/phpmyadmin", "/pma", "/adminer",
        )) or "/phpinfo" in lower:
            return True
        return lower.endswith((
            ".php", ".asp", ".aspx", ".cgi", ".env", ".sql", ".bak", ".swp", ".old", ".orig",
        ))

    @app.middleware("http")
    async def priced_pages(request: Request, call_next):
        if _probe_path(request.url.path):
            return Response(status_code=404, content=b"", media_type="text/plain")
        request.state.visitor = request.cookies.get("harbor_vid") or secrets.token_hex(8)
        existing_ad = parse_ad_cookie(request.cookies.get("harbor_ad"))
        incoming_ad = merge_from_request(existing_ad, request.query_params)
        # Merge browser-set fbp/ttp from cookie jar if present in query (rare) — primary via JS later.
        request.state.ad_attrs = incoming_ad
        response = await call_next(request)
        path = request.url.path
        if path.startswith("/static") or path in {"/sw.js", "/manifest.webmanifest", "/apple-touch-icon.png", "/apple-touch-icon-precomposed.png", "/offline"}:
            if path in {"/sw.js", "/manifest.webmanifest", "/offline"}:
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                if path == "/sw.js":
                    response.headers["Service-Worker-Allowed"] = "/"
            elif path.startswith("/static/catalog/") or path.startswith("/static/products/"):
                response.headers["Cache-Control"] = "public, max-age=604800"
            elif path.startswith("/static/"):
                # icons / css / js may be version-queried; keep a day but allow revalidate
                response.headers["Cache-Control"] = "public, max-age=86400, must-revalidate"
            return response
        response.headers["Cache-Control"] = "no-store"
        vid = request.cookies.get("harbor_vid") or getattr(request.state, "visitor", "")
        if not request.cookies.get("harbor_vid") and vid:
            response.set_cookie(
                "harbor_vid", vid, max_age=31536000, httponly=True, samesite="lax", path="/"
            )
        # Persist ad click IDs / UTM / seg for checkout attribution (90 days).
        try:
            attrs = getattr(request.state, "ad_attrs", None) or {}
            if attrs and pack_ad_cookie(attrs) != (request.cookies.get("harbor_ad") or ""):
                response.set_cookie(
                    "harbor_ad",
                    pack_ad_cookie(attrs),
                    max_age=90 * 86400,
                    httponly=False,
                    samesite="lax",
                    path="/",
                )
        except Exception:
            pass
        if request.method == "GET" and response.status_code == 200 and _storefront(path):
            media = response.headers.get("content-type", "")
            if "text/html" in media:
                _see(request, path, vid)
        return response

    @app.get("/manifest.webmanifest")
    def manifest():
        return JSONResponse(
            {
                "id": "/?source=pwa",
                "name": "Harbor",
                "short_name": "Harbor",
                "description": "Harbor — cross-border household finds, free-shipping packs, and daily check-ins.",
                "start_url": "/?source=pwa",
                "scope": "/",
                "display": "standalone",
                "display_override": ["standalone", "minimal-ui"],
                "orientation": "portrait-primary",
                "background_color": "#1E4D3B",
                "theme_color": "#1E4D3B",
                "lang": "en",
                "dir": "ltr",
                "categories": ["shopping", "lifestyle"],
                "icons": [
                    {"src": "/static/harbor-icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
                    {"src": "/static/harbor-icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
                    {"src": "/static/harbor-icon-maskable-192.png", "sizes": "192x192", "type": "image/png", "purpose": "maskable"},
                    {"src": "/static/harbor-icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
                ],
                "screenshots": [
                    {
                        "src": "/static/harbor-shot-narrow.png",
                        "sizes": "1080x1920",
                        "type": "image/png",
                        "form_factor": "narrow",
                        "label": "Harbor shop",
                    },
                    {
                        "src": "/static/harbor-shot-wide.png",
                        "sizes": "1920x1080",
                        "type": "image/png",
                        "form_factor": "wide",
                        "label": "Harbor desktop",
                    },
                ],
                "shortcuts": [
                    {"name": "Cart", "short_name": "Cart", "url": "/cart?source=pwa", "icons": [{"src": "/static/harbor-icon-192.png", "sizes": "192x192"}]},
                    {"name": "Check-in", "short_name": "Check-in", "url": "/check-in?source=pwa", "icons": [{"src": "/static/harbor-icon-192.png", "sizes": "192x192"}]},
                    {"name": "Account", "short_name": "Account", "url": "/account?source=pwa", "icons": [{"src": "/static/harbor-icon-192.png", "sizes": "192x192"}]},
                ],
            },
            media_type="application/manifest+json",
            headers={"Cache-Control": "no-cache"},
        )

    @app.get("/apple-touch-icon.png")
    @app.get("/apple-touch-icon-precomposed.png")
    def apple_touch_icon():
        return FileResponse(ROOT / "static" / "harbor-apple-touch-180.png", media_type="image/png")

    @app.get("/sw.js")
    def service_worker():
        return FileResponse(
            ROOT / "static" / "sw.js",
            media_type="application/javascript; charset=utf-8",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Service-Worker-Allowed": "/",
            },
        )

    @app.get("/offline", response_class=HTMLResponse)
    def offline_page():
        return FileResponse(ROOT / "static" / "offline.html", media_type="text/html; charset=utf-8")

    def cached_guarantees():
        hit = app.state.memo.get("guarantees")
        if isinstance(hit, dict):
            return hit
        data = load_guarantees(conn)
        app.state.memo["guarantees"] = data
        return data

    def rec_salt(request):
        # Stable for this browser's taste. Page 2 must continue page 1.
        crumb = (
            (request.cookies.get("interest") or "")
            + "|"
            + (request.cookies.get("history") or "")
            + "|"
            + (request.cookies.get("taste") or "")
            + "|"
            + (request.cookies.get("buyer_session") or "")
        )
        n = 0x9E3779B9
        for ch in crumb:
            n = (n * 33 + ord(ch)) & 0xFFFFFFFF
        return n

    def scarcity_left(sku, stock):
        stock = int(stock or 0)
        if 1 <= stock <= 9:
            return stock, False
        day = time.strftime("%Y-%m-%d", time.gmtime())
        digest = hashlib.md5(f"{sku}:{day}".encode("utf-8")).hexdigest()
        show = (int(digest[8:10], 16) % 100) < 38
        if not show or stock <= 0:
            return 0, False
        return (int(digest[:8], 16) % 9) + 1, True

    def interest_profile(request, by_sku=None, cart_skus=None):
        email = buyer_email(request) or ""
        account = account_weights(conn, email)
        guest = read_interest(request.cookies.get("interest"))
        history = read_skus(request.cookies.get("history"), 24)
        return merge_weights(
            account,
            guest,
            history=history,
            cart_skus=cart_skus or [],
            by_sku=by_sku,
        )

    def cached_promos():
        hit = app.state.memo.get("promos")
        if hit is not None:
            return hit
        data = load_promos(conn)
        app.state.memo["promos"] = data
        return data

    def cached_ads(lang):
        key = f"ads:{lang}"
        hit = app.state.memo.get(key)
        if hit is not None:
            return hit
        data = load_ads(conn, lang)
        app.state.memo[key] = data
        return data

    def public_visitor(request):
        if request.cookies.get("buyer_session"):
            return False
        if request.cookies.get("harbor_bought") == "1":
            return False
        if (request.cookies.get("history") or "").strip():
            return False
        if (request.cookies.get("harbor_hold") or "").strip():
            return False
        return not (request.cookies.get("cart") or "").strip()

    def cached_public(request, key):
        if not public_visitor(request):
            return None
        hit = app.state.memo.get(key)
        if not isinstance(hit, tuple):
            return None
        saved_at, html = hit
        if time.monotonic() - saved_at > 30:
            return None
        return HTMLResponse(html)

    def store_public(request, key, template_name, ctx):
        html = templates.env.get_template(template_name).render(ctx)
        if public_visitor(request):
            app.state.memo[key] = (time.monotonic(), html)
        return HTMLResponse(html)

    def _checked_today(email):
        if not email:
            return False
        return conn.execute(
            """
            select 1 from coupon_grants g
            join coupons c on c.id = g.coupon_id
            where g.email = ? and c.kind = 'checkin' and g.day = ?
            """,
            (email, utc_day()),
        ).fetchone() is not None

    def hold_choice(request, by_sku, lines, prefer_sku=""):
        """Pick a leave-offer SKU tied to PDP / history / cart gap — never a random cheapest orphan."""
        kept = newcomer_kept(conn, lines)
        if kept:
            row = by_sku.get(kept["sku"])
            if row is not None and int(row.get("stock") or 0) > 0:
                return row, int(kept["price_cents"]), True

        def usable(sku):
            row = by_sku.get(sku)
            if row is None or int(row.get("stock") or 0) <= 0:
                return None
            return row

        prefer = str(prefer_sku or getattr(request.state, "hold_extra", "") or "").strip()
        bare_now = strip_prefix(request.url.path)
        current = ""
        if bare_now.startswith("/p/"):
            current = bare_now[3:].split("/", 1)[0]
        if not prefer and current:
            prefer = current

        cart_parents = []
        for line in lines or []:
            parent = str(line.get("sku") or "").split("~", 1)[0]
            if parent and parent not in cart_parents:
                cart_parents.append(parent)

        seen = read_skus(request.cookies.get("history"))
        # Most-recent first: current PDP, then history (already recent-first in cookie).
        ordered = []
        for sku in [prefer, current, *seen, *cart_parents]:
            if sku and sku not in ordered:
                ordered.append(sku)

        # 1) Exact preferred / current PDP product.
        for sku in (prefer, current):
            row = usable(sku)
            if row is not None:
                return row, half_cents(row["price_cents"]), False

        # 2) Same-category companion from recent history (skip items already in cart when possible).
        anchor = usable(prefer) or usable(current) or next((usable(s) for s in seen if usable(s)), None)
        anchor_cat = (anchor.get("category") if anchor else "") or ""
        if anchor_cat:
            for sku in ordered:
                if sku == (anchor.get("sku") if anchor else ""):
                    continue
                row = usable(sku)
                if row is None:
                    continue
                if str(row.get("category") or "") != anchor_cat:
                    continue
                if row["sku"] in cart_parents and len(ordered) > 2:
                    continue
                return row, half_cents(row["price_cents"]), False

        # 3) Cart free-ship filler: cheapest stocked item from history/category that shrinks the gap.
        promos = cached_promos()
        free_cents = int(promos.get("free_shipping_cents") or 0)
        merchandise = 0
        for line in lines or []:
            parent = str(line.get("sku") or "").split("~", 1)[0]
            row = by_sku.get(parent) or by_sku.get(line.get("sku"))
            if row is not None:
                unit_cents, _ = line_sale_list_cents(row, line.get("sku"))
                merchandise += int(unit_cents) * int(line.get("qty") or 1)
        # Shipping is always free in quote; do not use free_shipping threshold for fillers.
        if False and free_cents and 0 < merchandise < free_cents:
            need = free_cents - merchandise
            fillers = []
            for sku in ordered:
                row = usable(sku)
                if row is None or row["sku"] in cart_parents:
                    continue
                price = int(row["price_cents"])
                # Prefer items that help close the gap without huge overshoot.
                score = abs(price - need) if price <= need * 2 else price
                fillers.append((score, price, row["sku"], row))
            if not fillers:
                # Fall back to same-category catalog fillers near the gap.
                for row in by_sku.values():
                    if int(row.get("stock") or 0) <= 0:
                        continue
                    if anchor_cat and str(row.get("category") or "") != anchor_cat:
                        continue
                    if row["sku"] in cart_parents:
                        continue
                    price = int(row["price_cents"])
                    if price <= 0:
                        continue
                    score = abs(price - need) if price <= need * 2 else price
                    fillers.append((score, price, row["sku"], row))
            if fillers:
                fillers.sort(key=lambda item: (item[0], item[1], item[2]))
                row = fillers[0][3]
                return row, half_cents(row["price_cents"]), False

        # 4) Most recently viewed in-stock product (not global cheapest).
        for sku in ordered:
            row = usable(sku)
            if row is not None:
                return row, half_cents(row["price_cents"]), False
        return None, 0, False

    def view(request):
        country = country_for(request)
        lang, currency = resolve(country)
        coef = 1.0
        forced = getattr(request.state, "seo_lang", None)
        if forced in OPEN_LANGS:
            lang = forced
        # Manual ?lang= / ?hl= or harbor_hl wins. Otherwise keep the IP language.
        # Accept-Language is not consulted. Currency stays on country.
        lang = ui_lang_for(request, lang)
        now = datetime.now(timezone.utc)
        try:
            rate = app.state.book.rate_for(currency, now)
            units = rate.units_per_usd
            coef = coefficient_for(conn, country)
            if coef != 1.0:
                units = float(units) * float(coef)
            stale = rate.stale
            no_rate = False
        except NoRate:
            units = None
            coef = coefficient_for(conn, country)
            stale = False
            no_rate = True
        promos = cached_promos()
        cart_count = sum(line["qty"] for line in load_lines(request.cookies.get("cart")))
        prefer_zh = prefer_zh_copy(request) or str(lang).startswith("zh")
        ua = (request.headers.get("user-agent") or "").lower()
        is_mobile = (
            "mobile" in ua
            or "android" in ua
            or "iphone" in ua
            or "ipod" in ua
            or "webos" in ua
            or "blackberry" in ua
        ) and "ipad" not in ua
        ctx = {
            "request": request,
            "t": UI.get(lang) or UI["en"],
            "lang": lang,
            "prefer_zh": prefer_zh,
            "is_mobile": is_mobile,
            "country": country,
            "currency": currency,
            "units": units,
            "coefficient": coef,
            "stale": stale,
            "no_rate": no_rate,
            "promos": promos,
            "categories": CATEGORIES,
            "home_face": HOME_FACE,
            "child_map": CHILDREN,
            "child_labels": labels_for(lang),
            "ads": cached_ads(lang),
            "ad_pixels": public_pixels_for_attrs(conn, getattr(request.state, "ad_attrs", None) or parse_ad_cookie(request.cookies.get("harbor_ad"))),
            "ad_attrs": getattr(request.state, "ad_attrs", None)
            or parse_ad_cookie(request.cookies.get("harbor_ad")),
            "cart_count": cart_count,
            "signed_in": bool(buyer_email(request)),
            "checked_today": _checked_today(buyer_email(request)),
            "harbor_notice": (request.cookies.get("harbor_notice") or "").strip(),
            "h5_origin": _public_h5_origin(request),
            "ship_countries": country_choices(),
            "address_formats": formats_for(lang),
        }
        text = UI[lang]
        if units is None:
            free_ship = "—"
            deal = ""
            deal_more = ""
        else:
            free_ship = format_money(
                goods_local(promos["free_shipping_cents"], units, currency),
                currency,
            )
            if promos["tiers"]:
                low, high = promos["tiers"][0], promos["tiers"][-1]
                deal = text["deal_line"].format(
                    over=format_money(goods_local(low[0], units, currency), currency),
                    save=format_money(goods_local(low[1], units, currency), currency),
                )
                deal_more = text["deal_line"].format(
                    over=format_money(goods_local(high[0], units, currency), currency),
                    save=format_money(goods_local(high[1], units, currency), currency),
                )
            else:
                deal = ""
                deal_more = ""
        ctx["deal_line"] = deal
        ctx["deal_more"] = deal_more
        ctx["ship_fee_text"] = "—" if units is None else format_money(0, currency)
        ctx["leave_offer"] = None
        ctx["gift_offer"] = None
        ctx["hold"] = parse_hold(request.cookies.get("harbor_hold"))
        ctx["cart_needs_ship"] = False
        lines = load_lines(request.cookies.get("cart"))
        if lines:
            try:
                by_sku = catalog_index()
            except Exception:
                by_sku = {}
        else:
            by_sku = {}
        merchandise = 0
        for line in lines:
            parent = line["sku"].split("~", 1)[0]
            row = by_sku.get(parent) or by_sku.get(line["sku"])
            if row is not None:
                unit_cents, _list_cents = line_sale_list_cents(row, line["sku"])
                merchandise += int(unit_cents) * int(line["qty"])
        ctx["cart_cents"] = merchandise
        ctx["cart_needs_ship"] = False
        cart_rail = []
        list_merchandise = 0
        sale_merchandise = 0
        for line in lines[:8]:
            parent = line["sku"].split("~", 1)[0]
            row = by_sku.get(parent) or by_sku.get(line["sku"])
            if row is None:
                continue
            names = json.loads(row["names"])
            unit_cents, list_cents = line_sale_list_cents(row, line["sku"])
            qty = int(line["qty"])
            sale_merchandise += unit_cents * qty
            list_merchandise += (list_cents if list_cents > unit_cents else unit_cents) * qty
            image = (row["image_url"] if "image_url" in row.keys() and row["image_url"] else "") or f"/static/products/{row['sku']}.svg"
            image = card_image(listing_photo(parent, lang, image), ROOT)
            if units is None or not unit_cents:
                price_text = "—"
            else:
                price_text = format_money(goods_local(unit_cents, units, currency), currency)
            cart_rail.append({
                "sku": line["sku"],
                "product_sku": parent,
                "name": names.get(lang) or names.get("en") or parent,
                "qty": qty,
                "price": price_text,
                "image": image,
            })
        # Also count remaining cart lines beyond rail preview for savings totals
        for line in lines[8:]:
            parent = line["sku"].split("~", 1)[0]
            row = by_sku.get(parent) or by_sku.get(line["sku"])
            if row is None:
                continue
            unit_cents, list_cents = line_sale_list_cents(row, line["sku"])
            qty = int(line["qty"])
            sale_merchandise += unit_cents * qty
            list_merchandise += (list_cents if list_cents > unit_cents else unit_cents) * qty
        ctx["cart_rail"] = cart_rail
        save_cents = max(0, list_merchandise - sale_merchandise)
        off_pct = format_off_pct(sale_merchandise, list_merchandise) if save_cents else ""
        ctx["cart_save_cents"] = save_cents
        ctx["cart_off_pct"] = off_pct
        ctx["cart_deal_ends"] = deal_ends_iso(conn) if (save_cents and merchandise > 0) else ""
        if units is None:
            ctx["cart_subtotal_text"] = "—"
            ctx["cart_save_text"] = ""
        else:
            # Prefer offer-based sale sum for rail total when available
            show_cents = sale_merchandise if sale_merchandise else merchandise
            ctx["cart_subtotal_text"] = format_money(goods_local(show_cents, units, currency), currency)
            ctx["cart_save_text"] = (
                format_money(goods_local(save_cents, units, currency), currency) if save_cents else ""
            )
        ctx["cart_ship_progress"] = 0
        # Quote always charges $0 shipping — treat as always-free for UI.
        ctx["cart_ship_met"] = bool(merchandise > 0)
        ctx["free_ship_policy"] = True
        ctx["always_free_shipping"] = True
        guarantees = cached_guarantees()
        ctx["guarantees"] = guarantees
        late_cents = int(guarantees.get("late_delivery_credit_cents") or 0)
        return_days = int(guarantees.get("return_days") or 30)
        if units is not None and late_cents:
            ctx["late_credit_text"] = format_money(goods_local(late_cents, units, currency), currency)
        elif late_cents:
            ctx["late_credit_text"] = f"${late_cents / 100:.2f}"
        else:
            ctx["late_credit_text"] = ""
        ctx["return_days"] = return_days
        # Keep returns_window live from platform policy (not hard-coded 30 in copy alone).
        if "returns_window_fmt" in text:
            ctx["t"] = dict(text)
            ctx["t"]["returns_window"] = text["returns_window_fmt"].format(days=return_days)
        elif "{days}" in str(text.get("returns_window") or ""):
            ctx["t"] = dict(text)
            ctx["t"]["returns_window"] = text["returns_window"].format(days=return_days)
        ctx["checkout_min_cents"] = int(guarantees.get("checkout_min_cents") or 0)
        min_cents = ctx["checkout_min_cents"]
        # Shipping is always free in build_quote — never advertise a false free-shipping threshold.
        if units is None:
            ctx["promise_line"] = ""
        else:
            ctx["promise_line"] = text.get("free_ship_badge") or text.get("free_shipping") or ""
        ctx["cart_gap"] = ""
        ctx["cart_gap_role"] = ""
        if units is not None and merchandise > 0 and min_cents and merchandise < min_cents:
            ctx["cart_gap_role"] = "min"
            pattern = text.get("gap_min") or "Add {amount} to check out"
            ctx["cart_gap"] = pattern.format(
                amount=format_money(goods_local(min_cents - merchandise, units, currency), currency)
            )
            ctx["cart_ship_progress"] = min(100, int(merchandise * 100 / min_cents))
            # Shipping still free; progress bar is toward checkout minimum only.
            ctx["cart_ship_met"] = True
        elif units is not None and merchandise > 0:
            ctx["cart_ship_met"] = True
            if min_cents and merchandise >= min_cents:
                ctx["cart_ship_progress"] = 100
            tiers = sorted(
                (int(threshold), int(save))
                for threshold, save in (promos.get("tiers") or [])
            )
            next_tier = next(((t, s) for t, s in tiers if merchandise < t), None)
            if next_tier is not None:
                threshold, save = next_tier
                ctx["cart_gap_role"] = "spend"
                ctx["cart_gap"] = text["gap_deal"].format(
                    amount=format_money(
                        goods_local(threshold - merchandise, units, currency),
                        currency,
                    ),
                    save=format_money(goods_local(save, units, currency), currency),
                )
            else:
                ctx["cart_gap_role"] = "done"
                save = tiers[-1][1] if tiers else 0
                ctx["cart_gap"] = (
                    text["gap_done"].format(
                        save=format_money(goods_local(save, units, currency), currency)
                    )
                    if save
                    else text["gap_free"]
                )
        fresh = buyer_is_new(conn, buyer_email(request) or "") and request.cookies.get("harbor_bought") != "1"
        bare_path = strip_prefix(request.url.path)
        on_lp = bare_path.startswith("/lp/")
        on_pdp = bare_path.startswith("/p/")
        # Prefetch leave offer for exit-intent (never embed on PDP/LP — mid-browse must not see it).
        if fresh and ctx["hold"] is None and not on_lp and not on_pdp:
            chosen, sale, kept = hold_choice(request, by_sku, lines)
            if chosen is not None:
                names = json.loads(chosen["names"])
                image = chosen.get("image_url") or f"/static/products/{chosen['sku']}.svg"
                ctx["leave_offer"] = {
                    "sku": chosen["sku"],
                    "name": names.get(lang) or names.get("en") or chosen["sku"],
                    "original": "—"
                    if units is None
                    else format_money(goods_local(int(chosen["price_cents"]), units, currency), currency),
                    "price": "—"
                    if units is None
                    else format_money(goods_local(sale, units, currency), currency),
                    "stock": int(chosen["stock"]),
                    "image": storefront_image(image, lang, ROOT),
                    "kept": kept,
                }
        
        try:
            shelf_rows = catalog_list_rows()
        except Exception:
            shelf_rows = list(by_sku.values()) if by_sku else []
        stocked = [row for row in shelf_rows if int(row["stock"] or 0) > 0]
        near = [item for item in stocked if 80 <= int(item["price_cents"]) <= 150]
        if not near:
            near = sorted(stocked, key=lambda item: abs(int(item["price_cents"]) - 100))[:1]
        if near:
            gift = min(near, key=lambda item: (abs(int(item["price_cents"]) - 100), int(item["price_cents"])))
            gift_names = json.loads(gift["names"])
            gift_image = gift.get("image_url") or f"/static/products/{gift['sku']}.svg"
            ctx["gift_offer"] = {
                "sku": gift["sku"],
                "name": gift_names.get(lang) or gift_names.get("en") or gift["sku"],
                "price": "—"
                if units is None
                else format_money(goods_local(int(gift["price_cents"]), units, currency), currency),
                "image": storefront_image(gift_image, lang, ROOT),
            }
        bare = strip_prefix(request.url.path)
        opened = lang in OPEN_LANGS and not is_private(bare)
        label = _seo_label(bare, text)
        ctx["seo_title"] = page_title(label) if label else "Harbor"
        ctx["seo_description"] = first_sentence(text["hero_body"] if bare in {"/", "/categories"} else "")
        if bare.startswith("/c/") and label:
            ctx["seo_description"] = first_sentence(text["shop_category"].format(name=label))
        ctx["seo_robots"] = "index, follow" if opened else "noindex, follow"
        ctx["seo_canonical"] = public_url(bare, lang if lang in OPEN_LANGS else "en")
        ctx["seo_hreflang"] = hreflang_links(bare) if opened else []
        ctx["seo_image"] = ""
        ctx["seo_jsonld"] = []
        # Account flyout + mega HOT: recent history + hottest categories (real heat only).
        recent_views = []
        for sku in read_skus(request.cookies.get("history"))[:8]:
            row = by_sku.get(sku)
            if row is None:
                continue
            try:
                recent_views.append(present_card(row, ctx))
            except Exception:
                continue
        ctx["recent_views"] = recent_views
        hot_map = app.state.hot.get(country) or {}
        hot_cats = set()
        for sku, score in sorted(hot_map.items(), key=lambda kv: -int(kv[1] or 0))[:40]:
            if int(score or 0) <= 0:
                continue
            row = by_sku.get(sku)
            if row is not None and row.get("category"):
                hot_cats.add(row["category"])
        ctx["hot_cats"] = hot_cats
        word = ""
        hint_tab = "recommended"
        if recent_views:
            word = " ".join(str(recent_views[0].get("name") or "").split())
            if len(word) > 18:
                parts = word.split()
                word = parts[0] if parts and 2 <= len(parts[0]) <= 18 else word[:8]
            cat = recent_views[0].get("category") or ""
            if cat in CATEGORIES:
                hint_tab = cat
        ctx["gap_keyword"] = word
        ctx["gap_tab"] = hint_tab
        return ctx

    _CATALOG_SLIM_COLS = (
        "sku",
        "category",
        "subcategory",
        "price_cents",
        "original_cents",
        "stock",
        "names",
        "image_url",
        "source_zh",
        "published",
        "offers",
    )
    _CATALOG_FAT_KEYS = (
        "description",
        "bullets",
        "specs",
        "listing",
        "markets",
        "markets_lock",
        "gen_at",
        "uploaded_at",
    )

    def _compact_list_row(row):
        """Card/home row: drop fat blobs; keep sale price without full offers JSON."""
        item = {key: row[key] for key in row.keys() if key not in _CATALOG_FAT_KEYS}
        try:
            offer = cheapest_live_offer(item)
        except Exception:
            offer = None
        if offer is not None:
            sale = int(offer.get("price_cents") or item.get("price_cents") or 0)
            item["price_cents"] = sale
            item["offers"] = json.dumps(
                [
                    {
                        "id": offer.get("id") or "a",
                        "price_cents": sale,
                        "label": offer.get("label") or {},
                        "image": offer.get("image") or "",
                    }
                ],
                ensure_ascii=False,
            )
        else:
            item["offers"] = "[]"
        return item

    def catalog_rows():
        """Full published catalog (includes offers/listing/description). Prefer catalog_list_rows for shelves."""
        cached = app.state.cache.get("shop:catalog")
        if cached is not None:
            return cached
        rows = [
            dict(row)
            for row in conn.execute(
                "select * from products where published = 1 order by rowid"
            ).fetchall()
        ]
        app.state.catalog_token += 1
        app.state.cache.set("shop:catalog", rows)
        app.state.cache.set("shop:catalog-index", {row["sku"]: row for row in rows})
        return rows

    def catalog_list_rows():
        """Slim published catalog for home/list/api cards — no description/listing blobs."""
        cached = app.state.cache.get("shop:catalog-slim")
        if cached is not None:
            return cached
        cols = ", ".join(_CATALOG_SLIM_COLS)
        rows = [
            _compact_list_row(dict(row))
            for row in conn.execute(
                f"select {cols} from products where published = 1 order by rowid"
            ).fetchall()
        ]
        app.state.catalog_token += 1
        app.state.cache.set("shop:catalog-slim", rows)
        return rows

    def catalog_index():
        cached = app.state.cache.get("shop:catalog-index")
        if cached is not None:
            return cached
        index = {row["sku"]: row for row in catalog_rows()}
        app.state.cache.set("shop:catalog-index", index)
        return index

    def forget_public():
        app.state.memo.clear()

    def forget_catalog():
        app.state.cache.delete("shop:catalog")
        app.state.cache.delete("shop:catalog-slim")
        app.state.cache.delete("shop:catalog-index")
        forget_public()

    def heat(row, country):
        return int((app.state.hot.get(country) or {}).get(row["sku"], 0))

    def reload_hot():
        grouped = {}
        for row in conn.execute("select country, title from hot_titles").fetchall():
            grouped.setdefault(row["country"], []).append(row["title"])
        app.state.hot_ready = bool(grouped)
        app.state.hot = build_scores(catalog_list_rows(), grouped)
        app.state.hot_token += 1
        forget_public()

    def present(row, ctx):
        names = json.loads(row["names"])
        offer = cheapest_live_offer(row)
        if offer is not None:
            cents = int(offer.get("price_cents") or 0)
        else:
            # No live offer (none, or every offer held): the product price is the sale price.
            cents = int(row["price_cents"] or 0)
        ship_cents = 0  # quote always free shipping
        free = True
        if ctx["units"] is None:
            price = "—"
            shipping = "—"
        elif not cents:
            price = "—"
            shipping = format_money(0, ctx["currency"]) if ctx["units"] is not None else "—"
        else:
            price = format_money(goods_local(cents, ctx["units"], ctx["currency"]), ctx["currency"])
            shipping = format_money(0, ctx["currency"])
        raw_specs = json.loads(row["specs"])

        copy_lang = ctx.get("lang") or "en"
        source_zh = row["source_zh"] if "source_zh" in row.keys() else ""

        def spec_text(key):
            return localized_copy(raw_specs.get(key) or "", copy_lang, fallback="")

        display_name = localized_copy(names, copy_lang, fallback=row["sku"], source_zh=source_zh)
        item = {
            "sku": row["sku"],
            "category": row["category"],
            "name": display_name,
            "price": price,
            "price_cents": cents,
            "stock": row["stock"],
            "shipping": shipping,
            "free_shipping": free,
            "description": localized_copy(
                json.loads(row["description"]) if row["description"] else {},
                copy_lang,
                fallback=display_name,
            ),
            "specs": {
                "material": spec_text("material"),
                "size": spec_text("size"),
                "weight": spec_text("weight"),
            },
            "image": (row["image_url"] if "image_url" in row.keys() and row["image_url"] else "")
            or f"/static/products/{row['sku']}.svg",
            "detail_images": stored_detail_images(row["listing"]) if "listing" in row.keys() else [],
            "images": stored_gallery(row["listing"]) if "listing" in row.keys() else [],
        }
        item["image"] = resolve_catalog_image(item["image"], row, ctx["lang"], ROOT) or item["image"]
        shots = list(item["images"])
        if item["image"] and item["image"] not in shots:
            shots.insert(0, item["image"])
        extra = offer_view(row, ctx)
        # Fall back missing offer packshots to product image / main.
        fixed_offers = []
        for offer in extra.get("offers") or []:
            shot = resolve_catalog_image(offer.get("image") or "", row, ctx["lang"], ROOT)
            offer = dict(offer)
            offer["image"] = shot or item["image"]
            fixed_offers.append(offer)
        extra["offers"] = fixed_offers
        offer_images = {picture for picture in extra.pop("images") if picture and catalog_file_exists(picture, ROOT)}
        # SKU photos stay in the picker. The gallery only keeps pictures that are not a SKU shot.
        shots = [picture for picture in shots if picture not in offer_images]
        shots = [resolve_catalog_image(picture, row, ctx["lang"], ROOT) or picture for picture in shots]
        shots = [picture for picture in shots if picture]
        if not shots and item["image"]:
            shots = [item["image"]]
        item.update(extra)
        item["images"] = shots

        def shown(url):
            return resolve_catalog_image(url, row, ctx["lang"], ROOT) or storefront_image(url, ctx["lang"], ROOT)

        item["image"] = shown(item["image"])
        item["detail_images"] = [shown(url) for url in item["detail_images"]]
        story = story_urls(row["sku"], ctx["lang"], ROOT)
        # Chinese keeps the original detail photos. English fills in only for other store languages.
        if not story and ctx["lang"] != "en" and not str(ctx["lang"]).startswith("zh"):
            story = story_urls(row["sku"], "en", ROOT)
        if story:
            item["detail_images"] = story
        item["images"] = [shown(url) for url in item["images"]]
        mains = main_urls(row["sku"], ctx["lang"], ROOT)
        if not mains and ctx["lang"] != "en" and not str(ctx["lang"]).startswith("zh"):
            mains = main_urls(row["sku"], "en", ROOT)
        if mains:
            item["images"] = mains
            item["image"] = mains[0]
        for offer in item.get("offers") or []:
            # Generated SKU packshots are shared across all languages (no en/ja sidecars).
            if offer.get("generated"):
                offer["image"] = offer.get("image") or ""
            else:
                offer["image"] = shown(offer.get("image") or "")
                # Quantity packs are not redrawn, so the file is still the Chinese upload.
                # On a non-Chinese page, show the generated main instead of that poster.
                if mains and not str(ctx["lang"]).startswith("zh"):
                    offer["image"] = mains[0]
        first = item["images"][0] if item["images"] else item["image"]
        item["image_phone"] = phone_image(first, ROOT)
        sale_cents, list_cents = sale_list_cents(row)
        item["off_pct"] = item.get("off_pct") or format_off_pct(sale_cents, list_cents)
        if list_cents > sale_cents > 0 and ctx.get("units") is not None:
            item["save_amount"] = format_money(
                goods_local(list_cents - sale_cents, ctx["units"], ctx["currency"]),
                ctx["currency"],
            )
            if not item.get("original"):
                item["original"] = format_money(
                    goods_local(list_cents, ctx["units"], ctx["currency"]),
                    ctx["currency"],
                )
                item["higher"] = True
        else:
            item.setdefault("save_amount", "")
        return item

    def listing_photo(sku, lang, fallback):
        """Thumbnail. Chinese keeps the upload. Any other language uses its generated main, then the English one."""
        if str(lang or "").startswith("zh"):
            return storefront_image(fallback, lang, ROOT)
        mains = main_urls(sku, lang, ROOT)
        if not mains and lang != "en":
            mains = main_urls(sku, "en", ROOT)
        if mains:
            return mains[0]
        return storefront_image(fallback, lang, ROOT)

    def present_card(row, ctx, with_offers=False):
        names = json.loads(row["names"])
        cents, original_cents = sale_list_cents(row)
        if ctx["units"] is None:
            price = "—"
            shipping = "—"
        elif not cents:
            price = "—"
            shipping = format_money(0, ctx["currency"]) if ctx["units"] is not None else "—"
        else:
            price = format_money(goods_local(cents, ctx["units"], ctx["currency"]), ctx["currency"])
            shipping = format_money(0, ctx["currency"])
        if ctx["units"] is None or not original_cents or original_cents == cents:
            original = ""
        else:
            original = format_money(goods_local(original_cents, ctx["units"], ctx["currency"]), ctx["currency"])
        image = (row["image_url"] if "image_url" in row.keys() and row["image_url"] else "") or f"/static/products/{row['sku']}.svg"
        image = resolve_catalog_image(image, row, ctx["lang"], ROOT) or image
        image = card_image(listing_photo(row["sku"], ctx["lang"], image), ROOT)
        card_name = localized_copy(
            names,
            ctx.get("lang") or "en",
            fallback=row["sku"],
            source_zh=row["source_zh"] if "source_zh" in row.keys() else "",
        )
        item = {
            "sku": row["sku"],
            "category": row["category"],
            "name": card_name,
            "price": price,
            "price_cents": cents,
            "stock": row["stock"],
            "shipping": shipping,
            "free_shipping": True,
            "image": image,
            "original": original,
            "higher": original_cents > cents,
            "offers": [],
        }
        if with_offers:
            extra = offer_view(row, ctx)
            fixed = []
            for offer in extra.get("offers") or []:
                offer = dict(offer)
                offer["image"] = resolve_catalog_image(offer.get("image") or "", row, ctx["lang"], ROOT) or image
                fixed.append(offer)
            item["offers"] = fixed
        try:
            _heat = int(heat(row, ctx["country"]) or 0)
        except Exception:
            _heat = 0
        item["heat"] = _heat
        item["hot"] = _heat > 0
        left, fake = scarcity_left(row["sku"], row["stock"])
        item["only_left"] = left
        item["only_left_fake"] = fake
        item["flash_ends"] = ""
        item["extra_off"] = ""
        item["off_pct"] = ""
        item["save_amount"] = ""
        if original_cents > cents > 0 and ctx.get("units") is not None:
            saved = original_cents - cents
            item["extra_off"] = format_money(
                goods_local(saved, ctx["units"], ctx["currency"]),
                ctx["currency"],
            )
            item["save_amount"] = item["extra_off"]
            item["off_pct"] = format_off_pct(cents, original_cents)
        return item

    def render(request, name, status_code=200, **extra):
        ctx = view(request)
        ctx.update(extra)
        staff = getattr(request.state, "staff", None)
        ctx.setdefault("is_admin_role", bool(staff and is_admin_role(staff)))
        ctx.setdefault("nav_badges", admin_nav_badges() if (staff or str(name).startswith("admin")) else {"ship": 0, "payout": 0})
        if "flash" not in ctx or not ctx.get("flash"):
            try:
                ctx["flash"] = str(request.query_params.get("flash") or "")
            except Exception:
                ctx["flash"] = str(extra.get("flash") or "")
        ctx.setdefault("ad_slots", [
            ("announcement", "顶部公告条"),
            ("sponsored", "首页赞助商品"),
            ("pdp-sponsored", "商品页推荐"),
            ("cart-recommend", "购物车推荐"),
        ])
        catalog_snapshot = job_read()
        ctx.setdefault("catalog_job", catalog_snapshot)
        ctx.setdefault("upload_job", catalog_snapshot.get("upload") or upload_job_read())
        ctx.setdefault("translate_job", catalog_snapshot.get("translate") or translate_job_read())
        ctx.setdefault("pending_parts", pending_part_uploads())
        ctx.setdefault("image_job", image_job_read())
        ctx.setdefault("image_account", image_account())
        ctx.setdefault("image_langs", [{"code": code, "name": label} for code, label in IMAGE_LANGS.items()])
        ctx.setdefault("image_left", 0)
        ctx.setdefault("story_products", 0)
        ctx.setdefault("gen_job", gen_job_read())
        ctx.setdefault("gen_paused", gen_is_paused())
        ctx.setdefault("gen_api", gen_api_account())
        ctx.setdefault("gen_workers", gen_worker_form())
        ctx.setdefault("gen_left", 0)
        ctx.setdefault("gen_error", "")
        ctx.setdefault("gen_plan", None)
        ctx.setdefault("sku_gen_left", 0)
        ctx.setdefault("sku_gen_queue", {"pending": 0, "calling": 0, "shots": 0, "idle": 0, "page": 1, "pages": 1, "items": []})
        ctx.setdefault("sku_gen_plan", None)
        ctx.setdefault("sku_gen_job", {"running": False, "label": "", "total": 0, "pending": 0, "active": 0, "error": "", "result": {"done": 0, "failed": 0}})
        ctx.setdefault("ad_pixels", {"meta_ok": False, "google_ok": False, "tiktok_ok": False})
        ctx.setdefault("ad_attrs", {})
        if status_code >= 400:
            ctx["seo_robots"] = "noindex, follow"
            ctx["seo_hreflang"] = []
        response = templates.TemplateResponse(request, name, ctx, status_code=status_code)
        try:
            qlang = (request.query_params.get("lang") or request.query_params.get("hl") or "").strip()
        except Exception:
            qlang = ""
        code = normalize_ui_lang(qlang)
        if code and code in UI and not request.url.path.startswith("/lp/ad"):
            response.set_cookie("harbor_hl", code, max_age=31536000, path="/", samesite="lax")
        if request.cookies.get("locale"):
            response.delete_cookie("locale", path="/")
        return response

    def buyer_email(request):
        token = request.cookies.get("buyer_session", "")
        if not token:
            return None
        row = conn.execute("select email from sessions where token = ?", (token,)).fetchone()
        return row["email"] if row else None

    def selected_lines(request):
        buy = request.query_params.get("buy") == "1"
        raw = request.cookies.get("checkout_line") if buy else request.cookies.get("cart")
        return load_lines(raw), buy

    def line_views(request, raw_lines):
        ctx = view(request)
        shown = []
        merchandise = 0
        email = buyer_email(request) or ""
        returning = request.cookies.get("harbor_bought") == "1"
        for line in raw_lines:
            sold = find_sellable(conn, line["sku"])
            if sold is None:
                continue
            item = present(sold["row"], ctx)
            label = sold["label"]
            text = label.get(ctx["lang"]) or label.get("en") or "" if isinstance(label, dict) else ""
            if text:
                item["name"] = f"{item['name']} · {text}"
            if sold["image"]:
                item["image"] = resolve_catalog_image(sold["image"], sold["row"], ctx["lang"], ROOT) or sold["image"]
            else:
                item["image"] = resolve_catalog_image(item.get("image") or "", sold["row"], ctx["lang"], ROOT) or item.get("image")
            item["product_sku"] = sold["parent"]
            item["sku"] = sold["code"]
            unit = int(sold["price_cents"])
            special, _item_id = price_for(
                conn, sold["code"], email, raw_lines, line["qty"], returning=returning, hold=ctx.get("hold")
            )
            if special is not None:
                unit = special
            item["price_cents"] = unit
            item["qty"] = line["qty"]
            item["line_cents"] = unit * line["qty"]
            gift_sku = request.cookies.get("gift_sku") or ""
            if gift_sku and item["sku"] == gift_sku and line["qty"] == 1 and 50 <= int(sold["price_cents"]) <= 200:
                item["price_cents"] = 0
                item["line_cents"] = 0
                item["gift"] = True
            merchandise += item["line_cents"]
            if ctx["units"] is None:
                item["line_price"] = "—"
            else:
                item["line_price"] = format_money(
                    goods_local(item["line_cents"], ctx["units"], ctx["currency"]),
                    ctx["currency"],
                )
            shown.append(item)
        return ctx, shown, merchandise

    def quote_for(ctx, merchandise, ship_country, coupon=None, balance_cents=0, use_balance=False):
        if ctx["units"] is None:
            return None
        return build_quote(
            ctx["promos"],
            merchandise_cents=merchandise,
            ship_country=ship_country,
            units=ctx["units"],
            currency=ctx["currency"],
            minor_units=MINOR[ctx["currency"]],
            coupon_cents=coupon["amount_cents"] if coupon else 0,
            coupon_threshold_cents=coupon["threshold_cents"] if coupon else 0,
            balance_cents=balance_cents,
            use_balance=use_balance,
        )

    def money(ctx, cents):
        if ctx["units"] is None:
            return "—"
        return format_money(goods_local(cents, ctx["units"], ctx["currency"]), ctx["currency"])

    def catalog_items(ctx):
        return [
            {
                "sku": row["sku"],
                "category": row["category"],
                "price_cents": row["price_cents"],
                "stock": row["stock"],
            }
            for row in catalog_list_rows()
        ]

    def cards_for(ctx, picks, with_offers=False):
        if with_offers:
            by_sku = catalog_index()
        else:
            by_sku = {row["sku"]: row for row in catalog_list_rows()}
        return [present_card(by_sku[item["sku"]], ctx, with_offers) for item in picks if item["sku"] in by_sku]

    def nudge_for(ctx, merchandise, has_lines):
        if not has_lines or ctx["units"] is None:
            return None
        tiers = sorted(
            (int(threshold), int(save))
            for threshold, save in (ctx["promos"].get("tiers") or [])
        )
        minimum = int(ctx.get("checkout_min_cents") or 0)
        if minimum and merchandise < minimum:
            need = minimum - merchandise
            pattern = ctx["t"].get("gap_min") or "Add {amount} to check out"
            return {
                "kind": "min",
                "role": "min",
                "text": pattern.format(amount=money(ctx, need)),
                "need": need,
                "progress": min(99, int(merchandise * 100 / minimum)) if minimum else 0,
                "save_text": "",
                "ship_done": False,
            }
        # Shipping is always free; after checkout min, push spend-save tiers.
        next_tier = next(((t, s) for t, s in tiers if merchandise < t), None)
        if next_tier is not None:
            threshold, save = next_tier
            need = threshold - merchandise
            return {
                "kind": "deal",
                "role": "spend",
                "text": ctx["t"]["gap_deal"].format(
                    amount=money(ctx, need),
                    save=money(ctx, save),
                ),
                "need": need,
                "progress": min(99, int(merchandise * 100 / threshold)) if threshold else 0,
                "save_text": money(ctx, save),
                "ship_done": True,
            }
        save = tiers[-1][1] if tiers else 0
        text = (
            ctx["t"]["gap_done"].format(save=money(ctx, save))
            if save
            else ctx["t"]["gap_free"]
        )
        return {
            "kind": "done",
            "role": "done",
            "text": text,
            "need": 0,
            "progress": 100,
            "save_text": money(ctx, save) if save else "",
            "ship_done": True,
        }

    def remember(response, request, category, weight, sku=None):
        email = buyer_email(request)
        if email and sku:
            note_click(conn, email, sku, weight)
        if sku:
            response.set_cookie(
                "interest",
                bump_interest(request.cookies.get("interest") or "", sku, int(weight) or 1),
                max_age=31536000,
                path="/",
            )
        if category:
            response.set_cookie(
                "taste",
                bump_taste(request.cookies.get("taste") or "", category, int(weight) or 1),
                max_age=31536000,
                path="/",
            )
        return response

    def touched_products(items, request):
        by_sku = {item["sku"]: item for item in items}
        weights = interest_profile(request, by_sku=by_sku)
        return [
            {
                "category": by_sku[sku]["category"],
                "price_cents": by_sku[sku]["price_cents"],
                "weight": weight,
            }
            for sku, weight in weights.items()
            if sku in by_sku
        ]

    def redirect(path, country, **cookies):
        response = RedirectResponse(href(path, country), status_code=303)
        for key, value in cookies.items():
            if value is None:
                response.delete_cookie(key)
            else:
                response.set_cookie(key, value, httponly=True, path="/")
        return response

    def listing(request, forced_category=None, forced_sub=""):
        ctx = view(request)
        params = request.query_params
        catalog_list_rows()
        key = "page:list:{lang}:{zh}:{country}:{category}:{sub}:{q}:{sort}:{low}:{high}:{page}:{partial}:{token}".format(
            lang=ctx["lang"],
            zh="1" if ctx.get("prefer_zh") else "0",
            country=ctx["country"],
            category=params.get("category") or forced_category or "",
            sub=forced_sub or "",
            q=params.get("q") or "",
            sort=params.get("sort") or "featured",
            low=params.get("min") or "",
            high=params.get("max") or "",
            page=params.get("page") or "1",
            partial=params.get("partial") or "",
            token=app.state.catalog_token,
        )
        hit = cached_public(request, key)
        if hit is not None:
            if forced_category in CATEGORIES:
                remember(hit, request, forced_category, 1)
            return hit
        sort = params.get("sort", "featured")
        if sort not in SORTS:
            sort = "featured"
        category = params.get("category") or forced_category
        sub = forced_sub if category and known(category, forced_sub) else ""
        rows = list(catalog_list_rows())
        if category:
            rows = [row for row in rows if row["category"] == category]
        chips = []
        if category:
            counts = {}
            for row in rows:
                slug = row.get("subcategory") or ""
                if known(category, slug):
                    counts[slug] = counts.get(slug, 0) + 1
            chips = [
                {"slug": slug, "name": labels_for(ctx["lang"]).get(slug, slug)}
                for slug in children(category)
                if counts.get(slug)
            ]
        if sub:
            rows = [row for row in rows if (row.get("subcategory") or "") == sub]
        if params.get("q"):
            needle = " ".join(str(params.get("q") or "").lower().split())
            tokens = [t for t in re.split(r"[\s,，+/|；;]+", needle) if t]

            def _search_haystack(row):
                parts = [
                    str(row.get("names") or ""),
                    str(row.get("description") or ""),
                    str(row.get("source_zh") or ""),
                    str(row.get("sku") or ""),
                    str(row.get("category") or ""),
                    str(row.get("subcategory") or ""),
                ]
                bullets = row.get("bullets")
                if bullets:
                    parts.append(str(bullets))
                return " ".join(parts).lower()

            def _search_score(row):
                hay = _search_haystack(row)
                names = str(row.get("names") or "").lower()
                if not tokens:
                    return 1 if (not needle or needle in hay) else -1
                if not all(t in hay for t in tokens):
                    return 50 if needle and needle in names else -1
                score = 0
                for t in tokens:
                    score += 12 if t in names else 3
                if needle and needle in names:
                    score += 25
                return score

            scored = []
            for row in rows:
                sc = _search_score(row)
                if sc >= 0:
                    row = dict(row)
                    row["_qscore"] = sc
                    scored.append((sc, row))
            scored.sort(key=lambda item: (-item[0], item[1].get("sku") or ""))
            rows = [row for sc, row in scored]
        if params.get("min"):
            floor = int(float(params.get("min")) * 100)
            rows = [row for row in rows if row["price_cents"] >= floor]
        if params.get("max"):
            ceiling = int(float(params.get("max")) * 100)
            rows = [row for row in rows if row["price_cents"] <= ceiling]
        if sort == "price_asc":
            rows.sort(key=lambda row: row["price_cents"])
        elif sort == "price_desc":
            rows.sort(key=lambda row: row["price_cents"], reverse=True)
        elif sort == "newest":
            rows.reverse()
        promoted = set(sponsored_skus(ctx["ads"]))
        if params.get("q") and sort == "featured":
            rows.sort(
                key=lambda row: (
                    0 if row["sku"] in promoted else 1,
                    -(row.get("_qscore") or 0),
                    row.get("sku") or "",
                )
            )
        elif not params.get("q") and sort == "featured":
            catalog = list(catalog_list_rows())
            by_sku = {row["sku"]: row for row in catalog}
            cart_skus = [line["sku"].split("~", 1)[0] for line in load_lines(request.cookies.get("cart"))]
            interest = interest_profile(request, by_sku=by_sku, cart_skus=cart_skus)
            rows = personal_order(
                rows,
                interest=interest,
                catalog=catalog,
                cart_skus=cart_skus,
                taste=read_taste(request.cookies.get("taste")),
                salt=rec_salt(request),
                heat={row["sku"]: heat(row, ctx["country"]) for row in rows},
                prior={row["sku"]: rank(row, ctx["country"]) for row in rows},
                boost={sku: 4.0 for sku in promoted},
            )
        else:
            rows.sort(key=lambda row: 0 if row["sku"] in promoted else 1)
        total = len(rows)
        page = max(1, int(params.get("page") or 1))
        page_size = 20
        rows = rows[(page - 1) * page_size:page * page_size]
        items = [present_card(row, ctx) for row in rows]
        for item in items:
            item["sponsored"] = item["sku"] in promoted
        ctx.update(
            {
                "items": items,
                "total": total,
                "sort": sort,
                "category": category or "",
                "sub": sub,
                "sub_name": labels_for(ctx["lang"]).get(sub, "") if sub else "",
                "chips": chips,
                "q": params.get("q") or "",
                "min": params.get("min") or "",
                "max": params.get("max") or "",
                "page": page,
                "page_size": page_size,
                "list_has_more": page * page_size < total,
            }
        )
        if (params.get("partial") or "") in {"1", "cards", "true"}:
            response = store_public(request, key, "home_cards.html", {**ctx, "products": items})
            response.headers["X-Harbor-Has-More"] = "1" if page * page_size < total else "0"
            response.headers["X-Harbor-Page"] = str(page)
            return response
        if category and category in ctx["t"]["categories"]:
            label = ctx["sub_name"] or ctx["t"]["categories"][category]
            ctx["seo_title"] = page_title(label)
            ctx["seo_description"] = first_sentence(ctx["t"]["shop_category"].format(name=label))
            home = public_url("/", ctx["lang"])
            dept = public_url(f"/c/{category}", ctx["lang"])
            crumbs = [(ctx["t"]["home"], home), (ctx["t"]["categories"][category], dept)]
            if sub and ctx["sub_name"]:
                crumbs.append((ctx["sub_name"], public_url(f"/c/{category}/{sub}", ctx["lang"])))
            ctx["seo_jsonld"] = [_breadcrumb(crumbs)]
        response = store_public(request, key, "listing.html", ctx)
        if forced_category in CATEGORIES:
            remember(response, request, forced_category, 1)
        return response

    @app.get("/robots.txt")
    def robots():
        # These tokens are training or image harvesters. Googlebot and Bingbot
        # do not match them, so they keep the User-agent: * rules below.
        blocked = (
            "ClaudeBot",
            "Claude-User",
            "Claude-SearchBot",
            "anthropic-ai",
            "GPTBot",
            "ChatGPT-User",
            "Google-Extended",
            "Applebot-Extended",
            "CCBot",
            "Bytespider",
            "Amazonbot",
            "meta-externalagent",
            "ImageMetaBot",
            "cohere-ai",
            "Diffbot",
        )
        lines = []
        for name in blocked:
            lines.extend([f"User-agent: {name}", "Disallow: /", ""])
        lines.extend([
            "User-agent: *",
            "Disallow: /admin",
            "Disallow: /cart",
            "Disallow: /checkout",
            "Disallow: /payment",
            "Disallow: /search",
            "Disallow: /account",
            "Disallow: /login",
            "Disallow: /register",
            "Disallow: /orders",
            "Disallow: /sale",
            "Disallow: /new",
            "",
        ])
        return Response("\n".join(lines), media_type="text/plain")

    @app.get("/sitemap.xml")
    def sitemap():
        paths = ["/", "/categories"]
        paths.extend(f"/c/{key}" for key in CATEGORIES)
        for row in catalog_rows():
            try:
                names = json.loads(row["names"] or "{}")
                description = json.loads(row["description"] or "{}")
            except json.JSONDecodeError:
                continue
            image = row["image_url"] if "image_url" in row.keys() else ""
            if not image and "listing" in row.keys():
                gallery = stored_gallery(row["listing"])
                image = gallery[0] if gallery else ""
            published = row["published"] if "published" in row.keys() else 1
            if indexable_product(names, description, image, row["stock"], row["price_cents"], published):
                paths.append(f"/p/{row['sku']}")
        locs = [public_url(path, lang) for path in paths for lang in OPEN_LANGS]
        body = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        ]
        for loc in locs:
            body.append(f"<url><loc>{_xml(loc)}</loc></url>")
        body.append("</urlset>")
        return Response("\n".join(body), media_type="application/xml")

    def home_feed_cards(request, ctx, tab="recommended", page=1, page_size=20, q="", exclude=()):
        """Liked items first, then the rest of this shelf. Order is stable across pages."""
        catalog = list(catalog_list_rows())
        rows = catalog
        needle = (q or "").strip().casefold()
        if needle:
            matched = []
            for row in rows:
                try:
                    names = json.loads(row["names"] or "{}")
                except (json.JSONDecodeError, TypeError):
                    names = {}
                blob = " ".join(str(value) for value in names.values()).casefold()
                if needle in blob or needle in str(row["sku"]).casefold():
                    matched.append(row)
            rows = matched
        by_sku = {row["sku"]: row for row in catalog}
        country = ctx["country"]
        promoted = set(sponsored_skus(ctx["ads"]))
        cart_skus = [line["sku"].split("~", 1)[0] for line in load_lines(request.cookies.get("cart"))]
        interest = interest_profile(request, by_sku=by_sku, cart_skus=cart_skus)
        taste = read_taste(request.cookies.get("taste"))
        salt = rec_salt(request)
        tab = (tab or "recommended").strip().lower()
        page = max(1, int(page or 1))
        page_size = max(4, min(48, int(page_size or 20)))
        feed_exclude = {str(sku) for sku in (exclude or ()) if sku}
        if tab in CATEGORIES:
            pool = [row for row in rows if row.get("category") == tab]
            salt = (salt ^ (sum(ord(ch) for ch in tab) * 131)) & 0xFFFFFFFF
            ordered = personal_order(
                pool,
                interest=interest,
                catalog=catalog,
                cart_skus=cart_skus,
                taste=taste,
                salt=salt,
                heat={row["sku"]: heat(row, country) for row in pool},
                prior={row["sku"]: rank(row, country) for row in pool},
                boost={sku: 4.0 for sku in promoted},
            )
            if feed_exclude:
                ordered = [row for row in ordered if str(row.get("sku") or "") not in feed_exclude]
        else:
            pool = list(rows)
            # Recommended: ~40% browse-weighted, ~60% cross-category random.
            ordered = blend_order(
                pool,
                interest=interest,
                catalog=catalog,
                cart_skus=cart_skus,
                taste=taste,
                salt=salt,
                heat={row["sku"]: heat(row, country) for row in pool},
                prior={row["sku"]: rank(row, country) for row in pool},
                boost={sku: 4.0 for sku in promoted},
                browse_share=BROWSE_SHARE,
                exclude=feed_exclude,
            )
        start = (page - 1) * page_size
        slice_rows = ordered[start : start + page_size]
        has_more = start + page_size < len(ordered)
        cards = []
        for row in slice_rows:
            item = present_card(row, ctx)
            item["sponsored"] = row["sku"] in promoted
            cards.append(item)
        return cards, has_more, tab

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        ctx = view(request)
        rows = list(catalog_list_rows())
        # Never serve a frozen public cache for the product shelf — each visitor / refresh must reshuffle.
        promoted = set(sponsored_skus(ctx["ads"]))
        by_sku = {row["sku"]: row for row in rows}
        country = ctx["country"]
        def on_shelf(row):
            return int(row["stock"] or 0) > 0

        def pictured(pool, limit):
            stocked = [row for row in pool if on_shelf(row)]
            with_photo = [row for row in stocked if (row.get("image_url") or "").strip()]
            return (with_photo or stocked)[:limit]

        rail_rows = {}
        for key in CATEGORIES:
            pool = sorted(
                [row for row in rows if row["category"] == key],
                key=lambda row: (rank(row, country), -heat(row, country)),
            )
            picked = pictured(pool, 4)
            if picked:
                rail_rows[key] = picked
        deal_rows = pictured(
            sorted([row for row in rows if row["price_cents"] <= 600], key=lambda row: (rank(row, country), -heat(row, country))),
            8,
        )
        cart_skus = [line["sku"].split("~", 1)[0] for line in load_lines(request.cookies.get("cart"))]
        interest = interest_profile(request, by_sku=by_sku, cart_skus=cart_skus)
        seen = read_skus(request.cookies.get("history"), 24) or [sku for sku in interest if sku in by_sku]
        recent_rows = [by_sku[sku] for sku in seen if sku in by_sku][:8]
        light = [
            {
                "sku": row["sku"],
                "category": row["category"],
                "price_cents": row["price_cents"],
                "stock": row["stock"],
            }
            for row in rows
        ]
        salt = rec_salt(request)
        heat_map = {row["sku"]: heat(row, country) for row in rows}
        prior_map = {row["sku"]: rank(row, country) for row in rows}
        boost_map = {sku: 4.0 for sku in promoted}
        stocked = [row for row in rows if int(row.get("stock") or 0) > 0]
        # In the shop: system random only — no browse interest, cross-category.
        # Skip recently viewed SKUs so this strip does not echo what they just opened.
        recent_skus = set(seen[:16])
        shop_pick_rows = diverse_order(
            stocked or rows,
            salt=(salt ^ 0x11111111) & 0xFFFFFFFF,
            exclude=recent_skus,
            heat=heat_map,
            prior=prior_map,
            boost=boost_map,
            limit=12,
        )
        shop_skus = {row["sku"] for row in shop_pick_rows}
        # Recommended feed first so Featured / For you can exclude its SKUs.
        feed_rows_cards, feed_has_more, _tab = home_feed_cards(
            request, ctx, tab="recommended", page=1, page_size=20, exclude=shop_skus
        )
        feed_skus = {item["sku"] for item in feed_rows_cards}
        # Prefer feed cards that do not repeat the In the shop strip on first paint.
        overlap = feed_skus & shop_skus
        if overlap and feed_has_more:
            alt_cards, alt_more, _alt_tab = home_feed_cards(
                request, ctx, tab="recommended", page=2, page_size=20, exclude=shop_skus
            )
            replaced = []
            used = set()
            alt_iter = iter(alt_cards)
            for item in feed_rows_cards:
                if item["sku"] in shop_skus:
                    swapped = None
                    for cand in alt_iter:
                        if cand["sku"] not in shop_skus and cand["sku"] not in used and cand["sku"] not in {x["sku"] for x in replaced}:
                            swapped = cand
                            break
                    replaced.append(swapped or item)
                else:
                    replaced.append(item)
                used.add(replaced[-1]["sku"])
            feed_rows_cards = replaced
            feed_skus = {item["sku"] for item in feed_rows_cards}
        # Featured sidebar: avoid In the shop + Recommended so rails do not collide.
        featured_rows = diverse_order(
            stocked or rows,
            salt=(salt ^ 0x22222222) & 0xFFFFFFFF,
            exclude=shop_skus | feed_skus | recent_skus,
            heat=heat_map,
            prior=prior_map,
            boost=boost_map,
            limit=8,
        )
        featured_skus = {row["sku"] for row in featured_rows}
        # For you: separate salt pool + exclude shop/feed (and featured when stock allows).
        you_exclude = shop_skus | feed_skus | featured_skus
        you_rows = [
            by_sku[item["sku"]]
            for item in ranked_for_you(
                light,
                interest,
                limit=12,
                salt=(salt ^ 0x33333333) & 0xFFFFFFFF,
                browse_share=BROWSE_SHARE,
                exclude=you_exclude,
            )
            if item["sku"] in by_sku
        ]
        # If catalog is too small after excludes, refill without featured so the rail is not empty.
        if len(you_rows) < 8:
            extra = [
                by_sku[item["sku"]]
                for item in ranked_for_you(
                    light,
                    interest,
                    limit=12,
                    salt=(salt ^ 0x44444444) & 0xFFFFFFFF,
                    browse_share=BROWSE_SHARE,
                    exclude=shop_skus | feed_skus | {row["sku"] for row in you_rows},
                )
                if item["sku"] in by_sku
            ]
            seen_you = {row["sku"] for row in you_rows}
            for row in extra:
                if row["sku"] in seen_you:
                    continue
                you_rows.append(row)
                seen_you.add(row["sku"])
                if len(you_rows) >= 12:
                    break

        shown = {item["sku"]: item for item in feed_rows_cards}

        def card(row):
            item = shown.get(row["sku"])
            if item is None:
                item = present_card(row, ctx)
                item["sponsored"] = row["sku"] in promoted
                shown[row["sku"]] = item
            return item

        cart_preview = []
        for line in load_lines(request.cookies.get("cart"))[:4]:
            parent = line["sku"].split("~", 1)[0]
            row = by_sku.get(parent)
            if row is not None:
                cart_preview.append(card(row))
        pull = category_weights(interest, rows, read_taste(request.cookies.get("taste")))
        liked = sorted(CATEGORIES, key=lambda key: (-pull.get(key, 0.0), CATEGORIES.index(key)))
        home_tabs = ["recommended", *liked]
        ctx.update({
            "cart_preview": cart_preview,
            "products": feed_rows_cards,
            "shop_picks": [card(row) for row in shop_pick_rows],
            "featured_rank": [card(row) for row in featured_rows],
            "rails": {key: [card(row) for row in picked] for key, picked in rail_rows.items()},
            "recent": [card(row) for row in recent_rows],
            "deals": [card(row) for row in deal_rows],
            "foryou": [card(row) for row in you_rows],
            "sale_block": campaign_block(ctx, "seckill", 16),
            "new_block": fresh_new(request, ctx, 8),
            "home_tabs": home_tabs,
            "home_tab": "recommended",
            "home_page": 1,
            "home_has_more": feed_has_more,
        })
        return render(request, "home.html", **{k: ctx[k] for k in ctx if k != "request"})

    @app.get("/home/feed", response_class=HTMLResponse)
    def home_feed(request: Request):
        ctx = view(request)
        tab = (request.query_params.get("tab") or "recommended").strip().lower()
        try:
            page = int(request.query_params.get("page") or 1)
        except ValueError:
            page = 1
        cards, has_more, tab = home_feed_cards(request, ctx, tab=tab, page=page, page_size=20)
        # partial: cards only
        if (request.query_params.get("partial") or "") in {"1", "cards", "true"}:
            html = templates.env.get_template("home_cards.html").render({**ctx, "products": cards})
            resp = HTMLResponse(html)
            resp.headers["X-Harbor-Has-More"] = "1" if has_more else "0"
            resp.headers["X-Harbor-Tab"] = tab
            resp.headers["X-Harbor-Page"] = str(page)
            return resp
        ctx.update({
            "products": cards,
            "shop_picks": [],
            "featured_rank": [],
            "home_tab": tab,
            "home_page": page,
            "home_has_more": has_more,
            "home_tabs": ["recommended", *CATEGORIES],
            "rails": {},
            "recent": [],
            "deals": [],
            "foryou": [],
            "sale_block": None,
            "new_block": None,
            "cart_preview": [],
        })
        return render(request, "home.html", **{k: ctx[k] for k in ctx if k != "request"})

    @app.get("/cart/picks", response_class=HTMLResponse)
    def cart_pick_cards(request: Request):
        ctx = view(request)
        tab = (request.query_params.get("tab") or "recommended").strip().lower()
        q = (request.query_params.get("q") or "").strip()
        cards, _has_more, tab = home_feed_cards(request, ctx, tab=tab, page=1, page_size=8, q=q)
        if q and cards and len(cards) < 8:
            extra, _extra_more, _extra_tab = home_feed_cards(
                request, ctx, tab=ctx.get("gap_tab") or "recommended", page=1, page_size=8, q=""
            )
            seen = {item["sku"] for item in cards}
            for item in extra:
                if item["sku"] in seen:
                    continue
                cards.append(item)
                seen.add(item["sku"])
                if len(cards) >= 8:
                    break
        stay = str(request.query_params.get("stay") or "")
        if not stay.startswith("/cart"):
            stay = ""
        html = templates.env.get_template("gap_picks.html").render({**ctx, "products": cards, "pick_tab": tab, "pick_next": stay})
        return HTMLResponse(html)

    def campaign_block(ctx, kind, limit=16):
        camp = active_campaign(conn, kind)
        if camp is None:
            return None
        index = catalog_index()
        cards = []
        for item in items_for(conn, camp["id"]):
            row = index.get(item["sku"])
            if row is None:
                continue
            card_item = present_card(row, ctx)
            special = int(item["price_cents"])
            if ctx["units"] is not None and special < card_item["price_cents"]:
                card_item["original"] = card_item["price"]
                card_item["higher"] = True
                card_item["price_cents"] = special
                card_item["price"] = format_money(
                    goods_local(special, ctx["units"], ctx["currency"]),
                    ctx["currency"],
                )
            card_item["limit_one"] = True
            card_item["campaign_kind"] = kind
            ends = camp["ends_at"] if "ends_at" in camp.keys() else None
            if ends:
                card_item["flash_ends"] = ends
            cards.append(card_item)
            if limit and len(cards) >= limit:
                break
        if not cards:
            return None
        return {
            "title": camp["title"],
            "rules": camp["rules"],
            "ends_at": camp["ends_at"] or "",
            "image": camp["image_url"] or "",
            "items": cards,
            "limit_one": True,
            "campaign_kind": kind,
        }

    def still_new(request):
        email = buyer_email(request) or ""
        if request.cookies.get("harbor_bought") == "1":
            return False
        return buyer_is_new(conn, email)

    def personal_new_block(ctx, hold):
        if not hold or not hold.get("alive"):
            return None
        row = catalog_index().get(hold["sku"])
        if row is None:
            return None
        card = present_card(row, ctx)
        if ctx["units"] is not None:
            card["original"] = card["price"]
            card["higher"] = True
            card["price_cents"] = int(hold["price_cents"])
            card["price"] = format_money(
                goods_local(int(hold["price_cents"]), ctx["units"], ctx["currency"]),
                ctx["currency"],
            )
        kept = int(hold["price_cents"]) != half_cents(row["price_cents"])
        card["limit_one"] = True
        card["campaign_kind"] = "newcomer"
        return {
            "title": ctx["t"]["new_title"],
            "rules": ctx["t"]["pop_hold_keep"] if kept else ctx["t"]["pop_hold_half"],
            "ends_at": hold["ends_at"],
            "image": "",
            "items": [card],
            "limit_one": True,
            "campaign_kind": "newcomer",
        }

    def fresh_new(request, ctx, limit=8):
        if not still_new(request):
            return None
        hold = ctx.get("hold")
        if hold:
            return personal_new_block(ctx, hold)
        return campaign_block(ctx, "newcomer", limit)

    def paint_deal(item, request, ctx):
        if ctx["units"] is None:
            return
        lines = load_lines(request.cookies.get("cart"))
        special, _item_id = price_for(
            conn,
            item["sku"],
            buyer_email(request) or "",
            lines,
            1,
            returning=not still_new(request),
            hold=ctx.get("hold"),
        )
        if special is None or special >= item["price_cents"]:
            return
        item["original"] = item["price"]
        item["higher"] = True
        item["price_cents"] = special
        item["price"] = format_money(
            goods_local(special, ctx["units"], ctx["currency"]),
            ctx["currency"],
        )
        item["limit_one"] = True

    @app.get("/sale", response_class=HTMLResponse)
    def sale_page(request: Request):
        ctx = view(request)
        block = campaign_block(ctx, "seckill", 0)
        return render(request, "sale.html", sale=block)


    @app.get("/flash", response_class=HTMLResponse)
    def flash_page(request: Request):
        ctx = view(request)
        block = campaign_block(ctx, "seckill", 0)
        return render(request, "flash.html", sale=block)


    _lp_flash_by_ip = {}

    def client_ip(request: Request) -> str:
        forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
        if forwarded:
            return forwarded[:64]
        host = request.client.host if request.client else ""
        return (host or "0.0.0.0")[:64]

    def lp_flash_window(request: Request, sale_end_raw: str = ""):
        """Return (ends_at_iso, should_set_cookie) for a per-IP 10-minute window."""
        now = datetime.now(timezone.utc)
        window = timedelta(minutes=10)
        ip = client_ip(request)
        candidates = []
        cookie_raw = (request.cookies.get("lp_flash_end") or "").strip()
        if cookie_raw:
            candidates.append(cookie_raw)
        stored = _lp_flash_by_ip.get(ip) or ""
        if stored and stored not in candidates:
            candidates.append(stored)
        ends = None
        for raw in candidates:
            try:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt > now:
                    ends = dt
                    break
            except ValueError:
                continue
        if ends is None:
            ends = now + window
        sale_raw = (sale_end_raw or "").strip()
        if sale_raw:
            try:
                sale_end = datetime.fromisoformat(sale_raw.replace("Z", "+00:00"))
                if sale_end.tzinfo is None:
                    sale_end = sale_end.replace(tzinfo=timezone.utc)
                if now < sale_end < ends:
                    ends = sale_end
            except ValueError:
                pass
        iso = ends.isoformat()
        _lp_flash_by_ip[ip] = iso
        if len(_lp_flash_by_ip) > 5000:
            keep = {}
            for k, v in list(_lp_flash_by_ip.items()):
                try:
                    dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    if dt > now:
                        keep[k] = v
                except ValueError:
                    continue
            _lp_flash_by_ip.clear()
            _lp_flash_by_ip.update(keep)
        return iso, True


    def lp_visitor_seed(request: Request) -> str:
        vid = (getattr(request.state, "visitor", None) or request.cookies.get("harbor_vid") or "").strip()
        if not vid:
            vid = client_ip(request)
        return vid or "anon"

    def lp_batch_index(request: Request) -> int:
        raw = (request.query_params.get("batch") or "").strip()
        try:
            return max(0, int(raw)) % 10_000
        except ValueError:
            return 0

    def lp_pick_assortment(request: Request, pool, flash_n=6, pack_n=4, seg=""):
        """Per-visitor assortment. With seg, strongly prefer matching catalog goods."""
        pool = [item for item in pool if item and item.get("sku") and int(item.get("price_cents") or 0) > 0]
        if not pool:
            return [], []
        seg = normalize_seg(seg or "")
        seed_key = f"{lp_visitor_seed(request)}|{lp_batch_index(request)}|{seg}|lp_ship_v2"
        rng = random.Random(hashlib.sha256(seed_key.encode("utf-8")).hexdigest())
        lang = getattr(request.state, "lang", None) or "en"

        def score(item):
            return seg_match_score(item, seg, lang) if seg else 0

        ranked = list(pool)
        if seg:
            matched = [item for item in ranked if score(item) > 0]
            rest = [item for item in ranked if score(item) <= 0]
            matched.sort(key=lambda item: (-score(item), item.get("sku") or ""))
            # shuffle within score bands so 换一批 still moves
            bands = {}
            for item in matched:
                bands.setdefault(score(item), []).append(item)
            matched_shuffled = []
            for sc in sorted(bands.keys(), reverse=True):
                bucket = bands[sc]
                rng.shuffle(bucket)
                matched_shuffled.extend(bucket)
            rng.shuffle(rest)
            ranked = matched_shuffled + rest
        else:
            rng.shuffle(ranked)

        # Flash slots: fill from matches first (hard preference).
        flash_items = []
        used = set()
        if seg:
            for item in ranked:
                if score(item) <= 0:
                    break
                flash_items.append(item)
                used.add(item["sku"])
                if len(flash_items) >= flash_n:
                    break
        if len(flash_items) < flash_n:
            # Prefer seckill-looking items next, then anything
            prefer = [
                item
                for item in ranked
                if item["sku"] not in used
                and (
                    item.get("campaign_kind") == "seckill"
                    or (item.get("limit_one") and item.get("campaign_kind") != "newcomer")
                )
            ]
            other = [item for item in ranked if item["sku"] not in used and item not in prefer]
            for item in prefer + other:
                flash_items.append(item)
                used.add(item["sku"])
                if len(flash_items) >= flash_n:
                    break
        pack_items = []
        for item in ranked:
            if item["sku"] in used:
                continue
            pack_items.append(item)
            used.add(item["sku"])
            if len(pack_items) >= pack_n:
                break
        return flash_items, pack_items


    def lp_build_seg_pool(request: Request, ctx, seg: str, limit: int = 48):
        """Pull live sellable catalog cards biased to seg category/keywords."""
        seg = normalize_seg(seg or "")
        lang = ctx.get("lang") or "en"
        rows = catalog_list_rows()
        scored = []
        for row in rows:
            if int(row.get("published") or 0) != 1:
                continue
            if int(row.get("stock") or 0) <= 0:
                continue
            sc = seg_match_score(row, seg, lang) if seg else 1
            if seg and sc <= 0:
                continue
            scored.append((sc, row))
        scored.sort(key=lambda pair: (-pair[0], pair[1].get("sku") or ""))
        # diversify a bit by batch seed
        seed = f"{lp_visitor_seed(request)}|{lp_batch_index(request)}|{seg}|pool"
        rng = random.Random(hashlib.sha256(seed.encode("utf-8")).hexdigest())
        # take top matches then light shuffle within top tier
        top = scored[: max(limit * 3, limit)]
        strong = [row for sc, row in top if sc >= 80]
        weak = [row for sc, row in top if sc < 80]
        rng.shuffle(strong)
        rng.shuffle(weak)
        ordered = strong + weak
        cards = []
        seen = set()
        for row in ordered:
            sku = row.get("sku")
            if not sku or sku in seen:
                continue
            card = present_card(row, ctx)
            if int(card.get("price_cents") or 0) <= 0:
                continue
            paint_deal(card, request, ctx)
            if seg:
                card["seg_score"] = seg_match_score(row, seg, lang)
            cards.append(card)
            seen.add(sku)
            if len(cards) >= limit:
                break
        return cards


    @app.get("/lp/ship", response_class=HTMLResponse)
    def lp_ship(request: Request):
        ctx = view(request)
        attrs = getattr(request.state, "ad_attrs", None) or parse_ad_cookie(
            request.cookies.get("harbor_ad")
        )
        seg = normalize_seg(
            (
                request.query_params.get("seg")
                or attrs.get("seg")
                or attrs.get("utm_content")
                or ""
            ).strip().lower()
        )
        batch = lp_batch_index(request)

        items = []
        seen = set()
        if seg:
            for card in lp_build_seg_pool(request, ctx, seg, limit=48):
                sku = card.get("sku")
                if sku and sku not in seen:
                    items.append(card)
                    seen.add(sku)

        sale = campaign_block(ctx, "seckill", 36) or {"items": [], "ends_at": ""}
        fresh = fresh_new(request, ctx, 18) or {"items": []}
        for block in (sale, fresh):
            for item in block.get("items") or []:
                sku = item.get("sku")
                if not sku or sku in seen:
                    continue
                if seg and seg_match_score(item, seg, ctx.get("lang") or "en") <= 0:
                    continue
                seen.add(sku)
                items.append(item)
                if len(items) >= 60:
                    break
            if len(items) >= 60:
                break

        if len(items) < 12:
            stocked = [
                row
                for row in catalog_list_rows()
                if int(row.get("stock") or 0) > 0
                and int(row.get("published") or 0) == 1
                and row["sku"] not in seen
            ]
            if seg:
                stocked.sort(
                    key=lambda row: (
                        -seg_match_score(row, seg, ctx.get("lang") or "en"),
                        int(row.get("price_cents") or 0),
                    )
                )
            else:
                stocked.sort(key=lambda row: int(row.get("price_cents") or 0))
            for row in stocked:
                card = present_card(row, ctx)
                if int(card.get("price_cents") or 0) <= 0:
                    continue
                paint_deal(card, request, ctx)
                items.append(card)
                seen.add(row["sku"])
                if len(items) >= 36:
                    break

        flash_items, pack_items = lp_pick_assortment(
            request, items, flash_n=6, pack_n=4, seg=seg
        )
        items = flash_items + pack_items
        free_cents = int(ctx["promos"]["free_shipping_cents"])
        free_ship_text = (
            "—"
            if ctx["units"] is None
            else format_money(goods_local(free_cents, ctx["units"], ctx["currency"]), ctx["currency"])
        )
        ends_at, set_flash_cookie = lp_flash_window(request, sale.get("ends_at") or "")
        next_batch = (batch + 1) % 10_000
        seo_title = page_title("Flash sale — limited deals")
        seo_description = first_sentence(
            f"Limited-time flash picks on Harbor. Tap a deal to open the product page. "
            f"{ctx['t']['sale_line']}"
        )
        try:
            record_funnel(
                conn,
                "land",
                seg=seg,
                utm_source=attrs.get("utm_source") or request.query_params.get("utm_source") or "",
                utm_campaign=attrs.get("utm_campaign") or request.query_params.get("utm_campaign") or "",
                visitor=lp_visitor_seed(request),
                extra=f"batch={batch}",
                acct=attrs.get("acct") or request.query_params.get("acct") or "",
            )
        except Exception:
            pass
        response = render(
            request,
            "lp_ship.html",
            lp_items=items,
            lp_flash=flash_items,
            lp_pack=pack_items,
            lp_ends=ends_at,
            lp_batch=batch,
            lp_next_batch=next_batch,
            lp_seg=seg,
            free_ship_text=free_ship_text,
            seo_title=seo_title,
            seo_description=seo_description,
        )
        if set_flash_cookie and ends_at:
            response.set_cookie(
                "lp_flash_end",
                ends_at,
                max_age=60 * 11,
                path="/",
                samesite="lax",
            )
        return response


    @app.get("/new", response_class=HTMLResponse)
    def new_page(request: Request):
        ctx = view(request)
        block = fresh_new(request, ctx, 0)
        return render(request, "new.html", fresh=block)

    @app.get("/categories", response_class=HTMLResponse)
    def categories_page(request: Request):
        ctx = view(request)
        labels = labels_for(ctx["lang"])
        counted = {}
        for row in catalog_list_rows():
            slug = row.get("subcategory") or ""
            if known(row["category"], slug):
                counted.setdefault(row["category"], {})
                bucket = counted[row["category"]]
                bucket[slug] = bucket.get(slug, 0) + 1
        boards = []
        for key in CATEGORIES:
            found = counted.get(key, {})
            chips = [
                labels.get(slug, slug)
                for slug in children(key)
                if found.get(slug)
            ][:3]
            # Prefer Figma illustrated JPGs (filename aliases), then SVG illustrations — never catalog product photos
            ill_dir = ROOT / "static" / "dept" / "illustrations"
            # Map category slug -> possible illustration basenames from Figma drops
            ill_aliases = {
                "daily": ["daily", "home-basics", "home_basics", "homebasics"],
                "kitchen": ["kitchen"],
                "tableware": ["tableware"],
                "storage": ["storage"],
                "cleaning": ["cleaning"],
                "paper": ["paper", "paper-and-care", "paper_and_care", "paperandcare"],
                "personal": ["personal", "personal-care", "personal_care", "personalcare"],
                "beauty": ["beauty"],
                "makeup": ["makeup"],
                "textile": ["textile", "textiles"],
                "decor": ["decor", "home-decor", "home_decor", "homedecor"],
                "appliance": ["appliance"],
                "hardware": ["hardware"],
                "pet": ["pet"],
                "office": ["office"],
                "party": ["party"],
            }
            image = None
            # Prefer raster Figma art across all aliases first, then SVG placeholders
            bases = ill_aliases.get(key, [key])
            for ext in (".jpg", ".jpeg", ".png", ".webp"):
                for base in bases:
                    cand = ill_dir / f"{base}{ext}"
                    if cand.is_file():
                        image = f"/static/dept/illustrations/{base}{ext}"
                        break
                if image:
                    break
            if not image:
                for base in bases:
                    cand = ill_dir / f"{base}.svg"
                    if cand.is_file():
                        image = f"/static/dept/illustrations/{base}.svg"
                        break
            if not image:
                legacy = ROOT / "static" / "dept" / f"{key}.svg"
                image = f"/static/dept/{key}.svg" if legacy.is_file() else "/static/placeholder.svg"
            boards.append({"key": key, "chips": chips, "image": image})
        return render(request, "departments.html", boards=boards)

    @app.get("/c/{category}", response_class=HTMLResponse)
    def category(request: Request, category: str):
        return listing(request, category)

    @app.get("/c/{category}/{sub}", response_class=HTMLResponse)
    def category_sub(request: Request, category: str, sub: str):
        if category not in CATEGORIES or not known(category, sub):
            return render(request, "not_found.html", status_code=404)
        return listing(request, category, sub)

    @app.get("/search", response_class=HTMLResponse)
    def search(request: Request):
        return listing(request)

    @app.get("/p/{sku}/peek", response_class=HTMLResponse)
    def product_peek(request: Request, sku: str):
        ctx = view(request)
        row = catalog_index().get(sku)
        if row is None:
            return HTMLResponse("", status_code=404)
        item = present(row, ctx)
        paint_deal(item, request, ctx)
        about = item.get("description") or ""
        if about == item.get("name"):
            about = ""
        ctx["item"] = item
        ctx["peek_about"] = about
        return templates.TemplateResponse(request, "peek.html", ctx)

    @app.get("/p/{sku}", response_class=HTMLResponse)
    def product(request: Request, sku: str):
        ctx = view(request)
        row = catalog_index().get(sku)
        if row is None:
            return render(request, "not_found.html", status_code=404)
        key = f"page:p:{sku}:{ctx['lang']}:{int(bool(ctx.get('prefer_zh')))}:{ctx['country']}:{app.state.catalog_token}"
        hit = cached_public(request, key)
        if hit is not None:
            seen = read_skus(request.cookies.get("history"))
            hit.set_cookie("history", write_skus([sku, *seen]), max_age=31536000, path="/")
            return remember(hit, request, row["category"], 1, sku=sku)
        item = present(row, ctx)
        paint_deal(item, request, ctx)
        stored = json.loads(row["bullets"]).get(ctx["lang"]) or []
        # Prefer real bullets only — hide section when empty instead of fake boilerplate.
        lines = [str(line).strip() for line in stored if str(line).strip()][:4]
        related = cards_for(
            ctx,
            [
                other
                for other in catalog_items(ctx)
                if other["sku"] in sponsored_skus(ctx["ads"], "pdp-sponsored") and other["sku"] != sku
            ],
        )
        for other in related:
            other["sponsored"] = True
        reviews = conn.execute(
            "select rating, body from reviews where sku = ? order by id desc",
            (sku,),
        ).fetchall()
        questions = conn.execute(
            "select email, body, answer from questions where sku = ? order by id desc",
            (sku,),
        ).fetchall()
        shelf = catalog_items(ctx)
        picks = cards_for(
            ctx,
            choose(
                shelf,
                exclude={sku},
                anchors=[item],
                touched=touched_products(shelf, request),
                limit=6,
            ),
        )
        start, end = delivery_span(ctx["country"])
        price_number = ""
        if ctx["units"] is not None:
            local = goods_local(item["price_cents"], ctx["units"], ctx["currency"])
            places = MINOR[ctx["currency"]]
            price_number = str(int(local)) if places <= 0 else f"{local / (10 ** places):.2f}"
        picture = absolute(item["images"][0] if item["images"] else item["image"])
        about = item["description"] if item["description"] != item["name"] else ""
        home = public_url("/", ctx["lang"])
        dept = public_url(f"/c/{item['category']}", ctx["lang"])
        here = public_url(f"/p/{sku}", ctx["lang"])
        ctx["seo_title"] = page_title(item["name"])
        ctx["seo_description"] = first_sentence(about)
        ctx["seo_image"] = picture
        product_ld = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": item["name"],
            "sku": sku,
            "image": [absolute(url) for url in item["images"] if url] or [picture],
            "brand": {"@type": "Brand", "name": "Harbor"},
        }
        if about:
            product_ld["description"] = first_sentence(about, 500)
        if price_number:
            product_ld["offers"] = {
                "@type": "Offer",
                "url": here,
                "priceCurrency": ctx["currency"],
                "price": price_number,
                "availability": "https://schema.org/InStock"
                if int(item["stock"] or 0) > 0
                else "https://schema.org/OutOfStock",
            }
        ctx["seo_jsonld"] = [
            product_ld,
            _breadcrumb([
                (ctx["t"]["home"], home),
                (ctx["t"]["categories"].get(item["category"], item["category"]), dept),
                (item["name"], here),
            ]),
        ]
        minimum = int(ctx.get("checkout_min_cents") or 0)
        ctx["can_buy_now"] = minimum <= 0 or int(item["price_cents"]) + int(ctx.get("cart_cents") or 0) >= minimum
        ctx.update({
            "item": item,
            "advantages": lines,
            "reviews": reviews,
            "related": related,
            "questions": questions,
            "picks": picks,
            "colors": COLORS,
            "delivery_start": start,
            "delivery_end": end,
        })
        response = store_public(request, key, "product.html", ctx)
        seen = read_skus(request.cookies.get("history"))
        response.set_cookie("history", write_skus([sku, *seen]), max_age=31536000, path="/")
        remember(response, request, item["category"], 1, sku=sku)
        return response

    def sell_code(sku, offer):
        return f"{sku}~{offer}" if offer else sku

    def chosen_offer(sku, offer):
        row = conn.execute("select offers from products where sku = ?", (sku,)).fetchone()
        if row is None:
            return offer or ""
        try:
            raw = json.loads(row["offers"] or "[]")
        except json.JSONDecodeError:
            raw = []
        live = [item for item in raw if item.get("id") and not item.get("hold")]
        ids = [str(item.get("id") or "") for item in live]
        all_ids = [str(item.get("id") or "") for item in raw if item.get("id")]
        if offer:
            if offer in ids:
                return offer
            # Held or unknown offer cannot be added
            return None if all_ids else (offer or "")
        if len(ids) == 1:
            return ids[0]
        if len(ids) > 1:
            # Prefer cheapest live SKU when the form omits offer
            best = min(live, key=lambda item: int(item.get("price_cents") or 0))
            return str(best.get("id") or "")
        if raw:
            return None
        return ""

    def stock_ok(code, qty):
        sold = find_sellable(conn, code)
        return sold is not None and qty > 0 and sold["stock"] >= qty

    def stamp_promo_notice(response, request, code, qty, lines):
        email = buyer_email(request) or ""
        returning = request.cookies.get("harbor_bought") == "1"
        hold = parse_hold(request.cookies.get("harbor_hold"))
        if campaign_special_possible(
            conn, code, email, lines, qty=qty, returning=returning, hold=hold
        ):
            response.set_cookie(
                "harbor_notice",
                "promo_limit",
                max_age=120,
                path="/",
                samesite="lax",
            )

    @app.post("/cart/add")
    async def add_cart(request: Request):
        form = await request.form()
        country = str(form.get("country") or "US")
        sku = str(form.get("sku") or "")
        offer = chosen_offer(sku, str(form.get("offer") or ""))
        wants_ajax = (
            str(form.get("ajax") or "") == "1"
            or request.headers.get("x-harbor-ajax") == "1"
            or "application/json" in (request.headers.get("accept") or "")
        )
        if offer is None:
            if wants_ajax:
                return JSONResponse({"ok": False, "error": "offer"}, status_code=400)
            return redirect(f"/p/{sku}", country)
        code = sell_code(sku, offer)
        qty = int(form.get("qty") or 1)
        if not stock_ok(code, qty):
            if wants_ajax:
                return JSONResponse({"ok": False, "error": "stock"}, status_code=400)
            return redirect(f"/p/{sku}", country)
        gift = str(form.get("gift") or "") == "1"
        buy = str(form.get("buy") or "") == "1"
        nxt = safe_next(form.get("next"))
        if buy and nxt == "/checkout":
            lines = merge_line(load_lines(request.cookies.get("checkout_line")), code, qty)
            response = redirect("/checkout?buy=1", country, checkout_line=dump_lines(lines))
        else:
            lines = merge_line(load_lines(request.cookies.get("cart")), code, qty)
            if wants_ajax and not buy:
                # Build JSON rail payload; cookies still set on JSONResponse.
                response = JSONResponse({"ok": True, "sku": sku, "qty": qty})
                response.set_cookie("cart", dump_lines(lines), max_age=31536000, path="/", samesite="lax")
            else:
                response = redirect(nxt, country, cart=dump_lines(lines))
        stamp_promo_notice(response, request, code, qty, lines)
        if gift:
            sold = find_sellable(conn, code)
            if sold and 50 <= int(sold["price_cents"]) <= 200:
                response.set_cookie("gift_sku", code, max_age=1800, httponly=True, path="/")
        row = conn.execute("select category from products where sku = ?", (sku,)).fetchone()
        if row is not None:
            remember(response, request, row["category"], 3, sku=sku)
        _track(request, "cart", sku, qty=qty, country=country)
        color = str(form.get("color") or "")
        if color in COLORS:
            notes = read_notes(request.cookies.get("notes"))
            notes[sku] = color
            response.set_cookie("notes", write_notes(notes), max_age=31536000, path="/")
        if str(form.get("remind") or "") == "1":
            reminded = read_skus(request.cookies.get("remind"), limit=36)
            response.set_cookie("remind", write_skus([sku, *reminded], 36), max_age=31536000, path="/")
        if wants_ajax and not buy and isinstance(response, JSONResponse):
            # Refresh view-like rail summary using the new cart cookie value.
            fake = request
            # Manually compute rail from `lines`
            ctx = view(request)
            # Override cart lines in ctx by recomputing with dumped cookie already set on response —
            # view() still reads old request cookies, so rebuild rail from `lines`.
            # Full catalog (not slim) so selected offer prices resolve correctly.
            by_sku = catalog_index()
            merchandise = 0
            list_merchandise = 0
            rail = []
            for index, line in enumerate(lines):
                parent = line["sku"].split("~", 1)[0]
                prow = by_sku.get(parent) or by_sku.get(line["sku"])
                if prow is None:
                    continue
                names = json.loads(prow["names"])
                unit_cents, list_cents = line_sale_list_cents(prow, line["sku"])
                qn = int(line["qty"])
                merchandise += unit_cents * qn
                list_merchandise += (list_cents if list_cents > unit_cents else unit_cents) * qn
                if index >= 8:
                    continue
                image = (prow["image_url"] if "image_url" in prow.keys() and prow["image_url"] else "") or f"/static/products/{prow['sku']}.svg"
                image = resolve_catalog_image(image, prow, ctx["lang"], ROOT)
                image = card_image(image, ROOT)
                if ctx["units"] is None or not unit_cents:
                    price_text = "—"
                else:
                    price_text = format_money(goods_local(unit_cents, ctx["units"], ctx["currency"]), ctx["currency"])
                rail.append({
                    "sku": line["sku"],
                    "product_sku": parent,
                    "name": names.get(ctx["lang"]) or names.get("en") or parent,
                    "qty": qn,
                    "price": price_text,
                    "image": image,
                })
            # Progress is toward checkout minimum only; shipping is always free in quote.
            free_cents = int(ctx.get("checkout_min_cents") or 0)
            save_cents = max(0, list_merchandise - merchandise)
            off_pct = format_off_pct(merchandise, list_merchandise) if save_cents else ""
            if ctx["units"] is None:
                subtotal = "—"
                save_text = ""
            else:
                subtotal = format_money(goods_local(merchandise, ctx["units"], ctx["currency"]), ctx["currency"])
                save_text = (
                    format_money(goods_local(save_cents, ctx["units"], ctx["currency"]), ctx["currency"])
                    if save_cents else ""
                )
            progress = min(100, int(merchandise * 100 / free_cents)) if free_cents and merchandise > 0 else (100 if merchandise > 0 else 0)
            ship_met = bool(merchandise > 0)  # always-free shipping
            added_name = ""
            added_image = ""
            added_label = ""
            added_row = by_sku.get(sku)
            if added_row is not None:
                try:
                    added_names = json.loads(added_row["names"] or "{}")
                except json.JSONDecodeError:
                    added_names = {}
                added_name = added_names.get(ctx["lang"]) or added_names.get("en") or sku
                added_image = (
                    added_row["image_url"] if "image_url" in added_row.keys() and added_row["image_url"] else ""
                ) or f"/static/products/{added_row['sku']}.svg"
                added_image = card_image(storefront_image(added_image, ctx["lang"], ROOT), ROOT)
                if offer:
                    try:
                        raw_offers = json.loads(added_row["offers"] or "[]") if "offers" in added_row.keys() else []
                    except json.JSONDecodeError:
                        raw_offers = []
                    for item in raw_offers:
                        if str(item.get("id") or "") != str(offer):
                            continue
                        lab = item.get("label") or ""
                        if isinstance(lab, dict):
                            added_label = lab.get(ctx["lang"]) or lab.get("en") or ""
                        shot = item.get("image") or ""
                        if isinstance(shot, str) and shot:
                            # Shared white packshot: do not swap to language sidecars.
                            if item.get("generated"):
                                added_image = card_image(shot, ROOT)
                            else:
                                added_image = card_image(storefront_image(shot, ctx["lang"], ROOT), ROOT)
                        break
            gap_title = ""
            gap_body = ""
            min_cents = int(ctx.get("checkout_min_cents") or 0)
            if ctx["units"] is None:
                ship_line = ctx.get("promise_line") or ""
            elif min_cents and merchandise < min_cents:
                need_text = format_money(
                    goods_local(min_cents - merchandise, ctx["units"], ctx["currency"]),
                    ctx["currency"],
                )
                target_text = format_money(
                    goods_local(min_cents, ctx["units"], ctx["currency"]),
                    ctx["currency"],
                )
                ship_line = (ctx["t"].get("gap_min") or "Add {amount} to check out").format(amount=need_text)
                gap_title = ctx["t"]["gap_modal_min_title"].format(
                    need=f'<em class="m">{need_text}</em>',
                    target=f'<em class="m">{target_text}</em>',
                )
                gap_body = ctx["t"]["gap_modal_min_body"].format(target=target_text)
            else:
                # Shipping is always free — celebrate free shipping / ready to check out.
                ship_line = ctx["t"].get("gap_free") or ctx.get("promise_line") or ""
            response = JSONResponse({
                "ok": True,
                "sku": sku,
                "qty": qty,
                "cart_count": sum(int(l["qty"]) for l in lines),
                "subtotal": subtotal,
                "progress": progress,
                "ship_met": ship_met,
                "ship_line": ship_line,
                "gap_title": gap_title,
                "gap_body": gap_body,
                "added": {
                    "name": added_name,
                    "label": added_label,
                    "image": added_image,
                    "qty": qty,
                },
                "rail": rail,
                "save_text": save_text,
                "off_pct": off_pct,
                "deal_ends": deal_ends_iso(conn) if save_cents else "",
                "message": ctx["t"].get("added_rail") or ctx["t"].get("add_cart") or "Added",
            })
            response.set_cookie("cart", dump_lines(lines), max_age=31536000, path="/", samesite="lax")
            stamp_promo_notice(response, request, code, qty, lines)
            if row is not None:
                remember(response, request, row["category"], 3, sku=sku)
        if not (buy and nxt == "/checkout"):
            push_open_room_cart(conn, request, lines)
        return response

    @app.post("/buy")
    async def buy_now(request: Request):
        form = await request.form()
        country = str(form.get("country") or "US")
        sku = str(form.get("sku") or "")
        offer = chosen_offer(sku, str(form.get("offer") or ""))
        if offer is None:
            return redirect(f"/p/{sku}", country)
        code = sell_code(sku, offer)
        qty = int(form.get("qty") or 1)
        if not stock_ok(code, qty):
            return redirect(f"/p/{sku}", country)
        response = redirect("/checkout", country, checkout_line=dump_lines([{"sku": code, "qty": qty}]))
        _track(request, "cart", sku, qty=qty, country=country)
        target = href("/checkout", country)
        join = "&" if "?" in target else "?"
        response.headers["location"] = f"{target}{join}buy=1"
        return response

    @app.post("/cart/update")
    async def update_cart(request: Request):
        form = await request.form()
        country = str(form.get("country") or "US")
        sku = str(form.get("sku") or "")
        qty = int(form.get("qty") or 0)
        lines = [line for line in load_lines(request.cookies.get("cart")) if line["sku"] != sku]
        if qty > 0:
            lines.append({"sku": sku, "qty": qty})
        response = redirect("/cart", country, cart=dump_lines(lines))
        if qty > 0:
            stamp_promo_notice(response, request, sku, qty, lines)
        push_open_room_cart(conn, request, lines)
        return response

    def cart_picks(request, ctx, shown, budget):
        exclude = {line.get("product_sku") or line["sku"] for line in shown}
        shelf = [item for item in catalog_items(ctx) if item["stock"] > 0 and item["sku"] not in exclude]
        salt = rec_salt(request)
        index = {item["sku"]: item for item in shelf}
        cart_skus = []
        for line in shown:
            parent = line.get("product_sku") or line["sku"]
            cart_skus.append(parent)
            if parent not in index and line.get("category"):
                index[parent] = {
                    "sku": parent,
                    "category": line.get("category"),
                    "price_cents": line.get("price_cents") or 0,
                    "stock": 1,
                }
        interest = interest_profile(request, by_sku=index, cart_skus=cart_skus)
        if shown:
            return ranked_choose(
                shelf,
                exclude=set(),
                anchors=shown,
                touched=touched_products(shelf, request),
                budget=budget,
                limit=8,
                salt=salt,
            )
        personal = ranked_for_you(shelf, interest, limit=8, salt=salt)
        if personal:
            return personal
        return ranked_for_you(shelf, {}, limit=8, salt=salt)

    @app.get("/cart", response_class=HTMLResponse)
    def cart(request: Request):
        ctx, shown, merchandise = line_views(request, load_lines(request.cookies.get("cart")))
        bill = quote_for(ctx, merchandise, ctx["country"]) if shown else None
        ship_text = money(ctx, bill.shipping_cents) if bill else ""
        due_text = format_money(bill.due_local, ctx["currency"]) if bill else ""
        have = {line["sku"] for line in shown}
        nudge = nudge_for(ctx, merchandise, bool(shown))
        budget = nudge["need"] if nudge and nudge["kind"] != "done" else None
        shelf = [item for item in catalog_items(ctx) if item["stock"] > 0 and item["sku"] not in have]
        touched = touched_products(shelf, request)
        bundle_groups = []
        for key in CATEGORIES:
            rows = [item for item in shelf if item["category"] == key]
            if not rows:
                continue
            bundle_groups.append({
                "key": key,
                "items": cards_for(
                    ctx,
                    choose(
                        rows,
                        exclude=set(),
                        anchors=shown,
                        touched=touched,
                        budget=budget,
                        limit=min(8, len(rows)),
                    ),
                    with_offers=True,
                ),
            })
        _saved_ctx, saved, _saved_total = line_views(request, [{"sku": sku, "qty": 1} for sku in read_skus(request.cookies.get("saved"))])
        notes = read_notes(request.cookies.get("notes"))
        for line in shown:
            line["color"] = notes.get(line["sku"], "")
        discount_text = money(ctx, bill.discount_cents) if bill else ""
        gap_pick = None
        if nudge and nudge.get("need"):
            cats = {line.get("category") for line in shown if line.get("category")}
            picked = fit_add(shelf, cats, nudge["need"])
            if picked:
                gap_pick = cards_for(ctx, [picked], with_offers=True)[0]
        saved_cents = (bill.discount_cents + bill.coupon_cents) if bill else 0
        goods_cents = max(0, merchandise - saved_cents)
        # List-vs-sale savings across cart lines (real original_cents only)
        list_cents_total = 0
        for line in shown:
            unit = int(line.get("price_cents") or 0)
            # present() may have higher/original; recover list from the selected offer
            parent = (line.get("product_sku") or line.get("sku") or "").split("~", 1)[0]
            prow = catalog_index().get(parent)
            sale_u, list_u = (
                line_sale_list_cents(prow, line.get("sku"))
                if prow is not None
                else (unit, 0)
            )
            qty = int(line.get("qty") or 1)
            list_cents_total += (list_u if list_u > sale_u else sale_u) * qty
        # Prefer strike-list total for "Original"; never show Original == Total.
        list_basis = list_cents_total if list_cents_total > merchandise else merchandise
        list_save_cents = max(0, list_basis - merchandise)
        list_off_pct = format_off_pct(merchandise, list_basis) if list_save_cents else ""
        original_local = goods_local(list_basis, ctx["units"], ctx["currency"]) if ctx["units"] is not None else None
        pay_local = goods_local(goods_cents, ctx["units"], ctx["currency"]) if original_local is not None else None
        save_local = max(0, (original_local or 0) - (pay_local or 0)) if pay_local is not None else 0
        # Hide struck Original when it would equal what the shopper pays (no real save).
        show_original = bool(original_local is not None and pay_local is not None and original_local > pay_local)
        ctx.update({
            "lines": shown,
            "saved": saved,
            "bill": bill,
            "ship_text": ship_text,
            "due_text": due_text,
            "discount_text": discount_text,
            "bundle_groups": bundle_groups,
            "nudge": nudge,
            "original_text": format_money(original_local, ctx["currency"]) if show_original else "",
            "pay_text": format_money(pay_local, ctx["currency"]) if pay_local is not None else "",
            "save_text": format_money(save_local, ctx["currency"]) if show_original and save_local else "",
            "save_local": save_local if show_original else 0,
            "list_save_text": money(ctx, list_save_cents) if list_save_cents else "",
            "list_off_pct": list_off_pct,
            "list_save_cents": list_save_cents,
            "deal_met": bool(bill and bill.discount_cents > 0),
            "ship_met": True,  # always-free shipping
            "ship_gap": "",
            "picks": cards_for(ctx, cart_picks(request, ctx, shown, budget)),
            "gap_pick": gap_pick,
            "notice": request.cookies.get("harbor_notice") or "",
        })
        checkout_min = int(ctx.get("checkout_min_cents") or 0)
        below_min = bool(shown and checkout_min > 0 and merchandise < checkout_min)
        ctx["show_gap_modal"] = below_min
        ctx["gap_modal_kind"] = "min"
        ctx["gap_modal_need_cents"] = max(0, checkout_min - merchandise)
        ctx["gap_modal_target_cents"] = checkout_min
        ctx["gap_modal_progress"] = 100
        target = ctx["gap_modal_target_cents"]
        if target > 0:
            ctx["gap_modal_progress"] = max(0, min(100, int(100 * merchandise / target)))
        # Primary game stays free-shipping; checkout_min only blocks when admin turns it on (>0).
        ctx["checkout_ok"] = (not below_min)
        ctx["gap_modal_picks"] = ctx["picks"]
        ctx["gap_modal_need_text"] = money(ctx, ctx["gap_modal_need_cents"]) if ctx["gap_modal_need_cents"] else ""
        ctx["gap_modal_target_text"] = money(ctx, ctx["gap_modal_target_cents"]) if ctx["gap_modal_target_cents"] else ""
        return templates.TemplateResponse(request, "cart.html", ctx)

    def address_book(email, country):
        email = (email or "").strip().lower()
        country = (country or "").strip().upper()
        if not email:
            return []
        rows = []
        seen = set()

        def add(name, address, city, region, postal, ship_country, phone):
            ship_country = str(ship_country or "").strip().upper()
            address = str(address or "").strip()
            if not address or (country and ship_country and ship_country != country):
                return
            key = tuple(
                str(part or "").strip().lower()
                for part in (address, city, region, postal, ship_country)
            )
            if key in seen:
                return
            seen.add(key)
            rows.append({
                "name": str(name or "").strip(),
                "address": address,
                "city": str(city or "").strip(),
                "region": str(region or "").strip(),
                "postal": str(postal or "").strip(),
                "ship_country": ship_country or country,
                "phone": str(phone or "").strip(),
            })

        for row in conn.execute(
            "select * from addresses where email = ? order by id desc",
            (email,),
        ).fetchall():
            add(
                row["name"], row["address"], row["city"], row["region"],
                row["postal"], row["ship_country"], row["phone"],
            )
        for row in conn.execute(
            """
            select ship_name, address, city, region, postal, ship_country, phone
            from orders where email = ? and address != ''
            order by id desc
            """,
            (email,),
        ).fetchall():
            add(
                row["ship_name"], row["address"], row["city"], row["region"],
                row["postal"], row["ship_country"], row["phone"],
            )
        return rows

    def ship_from_cookie(request, country):
        raw = request.cookies.get("harbor_ship") or ""
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        address = str(data.get("address") or "").strip()
        ship_country = str(data.get("ship_country") or "").strip().upper()
        if not address or ship_country != str(country or "").strip().upper():
            return None
        return {
            "name": str(data.get("name") or "").strip(),
            "address": address,
            "city": str(data.get("city") or "").strip(),
            "region": str(data.get("region") or "").strip(),
            "postal": str(data.get("postal") or "").strip(),
            "ship_country": ship_country,
            "phone": str(data.get("phone") or "").strip(),
        }

    def remember_address(email, name, address, city, region, postal, ship_country, phone):
        email = (email or "").strip().lower()
        address = (address or "").strip()
        if not email or not address:
            return
        existing = conn.execute(
            """
            select id from addresses
            where email = ? and lower(address) = lower(?)
              and lower(city) = lower(?) and lower(postal) = lower(?)
            """,
            (email, address, (city or "").strip(), (postal or "").strip()),
        ).fetchone()
        if existing:
            return
        conn.execute(
            """
            insert into addresses (email, name, address, city, region, postal, ship_country, phone)
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                email, (name or "").strip(), address, (city or "").strip(),
                (region or "").strip(), (postal or "").strip(),
                (ship_country or "").strip().upper(), (phone or "").strip(),
            ),
        )

    def checkout_page(request, *, raw_lines, buy, errors=None, stock_sku="", code="", values=None, submit_id=None):
        ctx, shown, merchandise = line_views(request, raw_lines)
        posted = {
            "email": "",
            "name": "",
            "address": "",
            "city": "",
            "region": "",
            "postal": "",
            "phone": "",
            "ship_country": ctx["country"],
            "street_number": "",
            "district": "",
        }
        if values:
            posted.update(values)
        if not posted["email"]:
            posted["email"] = buyer_email(request) or ""
        posted["ship_country"] = ctx["country"]
        ship_country = posted["ship_country"]
        email = posted["email"]
        coupons = list_coupons(conn, email, merchandise)
        # Do not auto-apply a coupon until the shopper selects one.
        picked = None
        bill = quote_for(ctx, merchandise, ship_country, coupon=picked)
        due_text = format_money(bill.due_local, ctx["currency"]) if bill else "—"
        ship_text = money(ctx, bill.shipping_cents) if bill else "—"
        email = buyer_email(request) or posted["email"]
        addresses = address_book(email, ctx["country"])
        saved = ship_from_cookie(request, ctx["country"])
        if saved:
            key = (
                saved["address"].lower(), saved["city"].lower(),
                saved["region"].lower(), saved["postal"].lower(),
            )
            if not any(
                (row["address"].lower(), row["city"].lower(), row["region"].lower(), row["postal"].lower()) == key
                for row in addresses
            ):
                addresses.insert(0, saved)
        address_picked = -1
        if addresses:
            if not values:
                posted.update(addresses[0])
                posted["ship_country"] = ctx["country"]
                address_picked = 0
            else:
                current = (
                    posted["address"].strip().lower(),
                    posted["city"].strip().lower(),
                    posted["postal"].strip().lower(),
                )
                for index, row in enumerate(addresses):
                    if (row["address"].lower(), row["city"].lower(), row["postal"].lower()) == current:
                        address_picked = index
                        break
        start, end = delivery_span(ship_country)
        nudge = nudge_for(ctx, merchandise, bool(shown))
        addons = []
        if nudge and nudge["kind"] != "done":
            shelf = catalog_items(ctx)
            exclude = {line["sku"] for line in shown}
            if buy:
                exclude.update(line["sku"] for line in load_lines(request.cookies.get("cart")))
            addons = cards_for(
                ctx,
                choose(
                    shelf,
                    exclude=exclude,
                    anchors=shown,
                    touched=touched_products(shelf, request),
                    budget=nudge["need"],
                    limit=6,
                ),
            )
        ctx.update(
            {
                "lines": shown,
                "bill": bill,
                "due_text": due_text,
                "ship_text": ship_text,
                "errors": errors or [],
                "stock_sku": stock_sku,
                "code": code,
                "values": posted,
                "submit_id": submit_id or uuid.uuid4().hex,
                "coupons": [
                    {
                        "id": coupon["id"],
                        "name": ctx["t"].get(f"coupon_{coupon['kind']}") or coupon["name"],
                        "amount": money(ctx, coupon["amount_cents"]),
                        "threshold": money(ctx, coupon["threshold_cents"]),
                    }
                    for coupon in coupons
                ],
                "best_id": picked["id"] if picked else None,
                "merchandise_text": money(ctx, merchandise) if bill else "",
                "discount_text": money(ctx, bill.discount_cents) if bill else "",
                "coupon_text": money(ctx, bill.coupon_cents) if bill and bill.coupon_cents else "",
                "balance_text": money(ctx, bill.balance_cents) if bill and bill.balance_cents else "",
                "buy": buy,
                "addresses": addresses,
                "address_picked": address_picked,
                "delivery_start": start,
                "delivery_end": end,
                "nudge": nudge,
                "addons": addons,
                "balance_note": ctx["t"].get("balance_goods_note", ""),
                "can_use_coupons": bool(coupons),
                "pay_methods": list(app.state.pay_status.get("shown") or []),
                "checkout_ok": not (int(ctx.get("checkout_min_cents") or 0) and merchandise < int(ctx.get("checkout_min_cents") or 0)),
                "min_gap_text": (ctx["t"].get("gap_min") or "Add {amount} to check out").format(
                    amount=money(ctx, max(0, int(ctx.get("checkout_min_cents") or 0) - merchandise))
                ),
            }
        )
        return templates.TemplateResponse(request, "checkout.html", ctx)

    @app.get("/lookup/regions")
    def regions_lookup(country: str = ""):
        return {"regions": region_choices(country)}

    @app.get("/lookup/cities")
    def cities_lookup(country: str = "", region: str = ""):
        return {"cities": city_choices(country, region[:80])}

    @app.get("/lookup/postal")
    def postal_lookup(country: str = "", code: str = ""):
        return lookup_postal(country, code)

    @app.get("/lookup/here")
    def here_lookup(lat: float | None = None, lon: float | None = None):
        if lat is None or lon is None:
            return {}
        return lookup_here(lat, lon)

    @app.get("/api/geo")
    def api_geo(request: Request):
        """Lightweight IP country + currency for native apps. No HTML."""
        country = country_for(request)
        _lang, currency = resolve(country)
        return {"ok": True, "country": country, "currency": currency}

    @app.get("/checkout", response_class=HTMLResponse)
    def checkout(request: Request):
        raw_lines, buy = selected_lines(request)
        return checkout_page(request, raw_lines=raw_lines, buy=buy)

    def start_paypal(order_id, due_local, currency, due_cents):
        gateway = app.state.gateways.get("paypal")
        if not isinstance(gateway, PayPalCheckout):
            return None
        try:
            return gateway.create_checkout(
                order_id=order_id,
                amount=int(due_local or 0),
                currency=currency,
            )
        except StripeError as exc:
            if "CURRENCY_NOT_SUPPORTED" not in str(exc).upper() or str(currency or "").upper() == "USD":
                return None
            try:
                return gateway.create_checkout(
                    order_id=order_id,
                    amount=int(due_cents or 0),
                    currency="USD",
                )
            except StripeError:
                return None

    @app.post("/checkout")
    async def submit_checkout(request: Request):
        form = await request.form()
        buy = str(form.get("buy") or "") == "1"
        raw_lines = load_lines(request.cookies.get("checkout_line") if buy else request.cookies.get("cart"))
        values = {key: str(form.get(key) or "") for key in (
            "email", "name", "address", "city", "region", "postal", "ship_country", "phone",
            "street_number", "district",
        )}
        values["ship_country"] = view(request)["country"]
        written = compose_street(
            values["ship_country"], values["address"], values["street_number"], values["district"]
        )
        submit_id = str(form.get("submit_id") or "")
        ctx = view(request)
        _lines_ctx, _shown, merchandise = line_views(request, raw_lines)
        minimum = int(ctx.get("checkout_min_cents") or 0)
        if raw_lines and minimum and merchandise < minimum:
            return checkout_page(
                request, raw_lines=raw_lines, buy=buy, code="min", values=values, submit_id=submit_id
            )
        if ctx["no_rate"]:
            return checkout_page(
                request, raw_lines=raw_lines, buy=buy, code="rate", values=values, submit_id=submit_id
            )
        coupon_raw = str(form.get("coupon_id") or "")
        try:
            coupon_id = int(coupon_raw) if coupon_raw else None
        except ValueError:
            coupon_id = -1
        try:
            order_id = place_order(
                conn,
                ctx["promos"],
                app.state.outbox,
                lines=raw_lines,
                submit_id=submit_id,
                email=values["email"],
                name=values["name"],
                address=written,
                city=values["city"],
                region=values["region"],
                postal=values["postal"],
                ship_country=values["ship_country"],
                phone=values["phone"],
                currency=ctx["currency"],
                units=ctx["units"],
                minor_units=MINOR[ctx["currency"]],
                use_balance=str(form.get("use_balance") or "") == "1",
                coupon_id=coupon_id,
                referrer=referrer_email(request),
                gift_sku=request.cookies.get("gift_sku") or "",
                returning=request.cookies.get("harbor_bought") == "1",
                hold=parse_hold(request.cookies.get("harbor_hold")),
            )
        except CheckoutError as exc:
            return checkout_page(
                request,
                raw_lines=raw_lines,
                buy=buy,
                errors=exc.fields,
                stock_sku=exc.sku or "",
                code=exc.code,
                values=values,
                submit_id=submit_id,
            )
        gift = str(form.get("gift") or "")[:200]
        speed = "standard"
        offered = list(app.state.pay_status.get("shown") or [])
        picked_pay = str(form.get("pay_method") or "")
        if picked_pay == "card":
            picked_pay = "stripe"
        pay_method = picked_pay if picked_pay in offered else (offered[0] if offered else "card")
        conn.execute(
            "update orders set gift_message = ?, speed = ?, pay_method = ? where id = ?",
            (gift, speed, pay_method, order_id),
        )
        remember_address(
            values["email"], values["name"], written, values["city"],
            values["region"], values["postal"], values["ship_country"], values["phone"],
        )
        try:
            attrs = getattr(request.state, "ad_attrs", None) or parse_ad_cookie(
                request.cookies.get("harbor_ad")
            )
            # Prefer fresh fbp/ttp from form if checkout posted them.
            for key in ("fbp", "ttp", "fbc"):
                raw = str(form.get(key) or "").strip()
                if raw:
                    attrs[key] = raw[:512]
            attrs["event_source_url"] = str(request.base_url).rstrip("/") + "/checkout"
            save_attribution(conn, order_id, attrs)
        except Exception:
            pass
        placed = conn.execute(
            "select due_cents, ship_country from orders where id = ?",
            (order_id,),
        ).fetchone()
        if placed is not None:
            _track(
                request,
                "order",
                cents=placed["due_cents"],
                country=placed["ship_country"] or values["ship_country"],
            )
        response = redirect(f"/orders/{order_id}", ctx["country"], pending_password=str(order_id))
        pay = conn.execute(
            "select due_local, due_cents, currency, status from orders where id = ?",
            (order_id,),
        ).fetchone()
        if (
            pay is not None
            and pay["status"] == "pending"
            and int(pay["due_local"] or 0) > 0
            and pay_method in {"paypal", "stripe", "lianlian"}
        ):
            session = None
            if pay_method == "paypal":
                session = start_paypal(order_id, pay["due_local"], pay["currency"], pay["due_cents"])
            else:
                gateway = app.state.gateways.get(pay_method)
                if gateway is not None:
                    try:
                        session = gateway.create_checkout(
                            order_id=order_id,
                            amount=int(pay["due_local"] or 0),
                            currency=pay["currency"],
                        )
                    except StripeError:
                        session = None
            if session and session.get("url"):
                response = RedirectResponse(session["url"], status_code=303)
                response.set_cookie("pending_password", str(order_id), path="/", max_age=60 * 60 * 24 * 14)
        if buy:
            response.delete_cookie("checkout_line", path="/")
        else:
            response.delete_cookie("cart", path="/")
        if request.cookies.get("desktop_pending") == "1":
            grant_templates(conn, values["email"].strip().lower(), "desktop", "once")
            response.delete_cookie("desktop_pending", path="/")
        response.set_cookie(
            "harbor_ship",
            json.dumps(
                {
                    "name": values["name"],
                    "address": written,
                    "city": values["city"],
                    "region": values["region"],
                    "postal": values["postal"],
                    "phone": values["phone"],
                    "ship_country": values["ship_country"],
                },
                ensure_ascii=False,
            ),
            max_age=60 * 60 * 24 * 365,
            path="/",
            samesite="lax",
        )
        response.delete_cookie("gift_sku", path="/")
        forget_catalog()
        return response

    def referrer_email(request):
        code = request.cookies.get("referrer_code") or ""
        if not code:
            return None
        row = conn.execute("select email from referrals where code = ?", (code,)).fetchone()
        return row["email"] if row else None

    @app.get("/payment", response_class=HTMLResponse)
    def payment(request: Request):
        picks = [present(row, view(request)) for row in catalog_rows()[:4]]
        return render(request, "payment.html", order_number="—", status_key="awaiting", suggestions=picks)

    @app.post("/orders/{order_id}/pay")
    async def pay_order(request: Request, order_id: str):
        row = conn.execute("select * from orders where id = ?", (order_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404)
        owns = request.cookies.get("pending_password") == str(row["id"]) or buyer_email(request) == row["email"]
        if not owns or row["status"] != "pending":
            raise HTTPException(status_code=403)
        if int(row["due_local"] or 0) <= 0:
            mark_paid(conn, row["id"])
            return redirect(f"/orders/{row['id']}", row["ship_country"] or "US")
        form = await request.form()
        offered = list(app.state.pay_status.get("shown") or [])
        picked = str(form.get("pay_method") or "")
        if picked == "card":
            picked = "stripe"
        if picked in offered:
            conn.execute("update orders set pay_method = ? where id = ?", (picked, row["id"]))
            method = picked
        else:
            method = row["pay_method"] if row["pay_method"] in app.state.gateways else ""
        if method == "paypal":
            session = start_paypal(row["id"], row["due_local"], row["currency"], row["due_cents"])
        elif method:
            try:
                session = app.state.gateways[method].create_checkout(
                    order_id=row["id"],
                    amount=int(row["due_local"] or 0),
                    currency=row["currency"],
                )
            except StripeError:
                session = None
        else:
            session = None
        session = session or {
            "currency": row["currency"].lower(),
            "amount": row["due_local"],
        }
        if session.get("url"):
            return RedirectResponse(session["url"], status_code=303)
        return render(
            request,
            "payment.html",
            order_number=row["id"],
            status_key="awaiting",
            pay_currency=session["currency"],
            pay_amount=session["amount"],
        )

    @app.post("/stripe/webhook")
    async def stripe_webhook(request: Request):
        raw = await request.body()
        stripe = app.state.gateways.get("stripe") or app.state.stripe
        secret = getattr(stripe, "webhook_secret", "")
        if secret and not stripe.valid_signature(raw, request.headers.get("stripe-signature", "")):
            raise HTTPException(status_code=400)
        event = json.loads(raw)
        paid = handle_event(conn, stripe, event)
        return {"ok": paid}

    @app.get("/orders/{order_id}/paypal")
    async def paypal_return(request: Request, order_id: str):
        finish = getattr(app.state.gateways.get("paypal"), "finish", None)
        token = str(request.query_params.get("token") or "")
        if finish:
            try:
                finish(order_id, token=token)
            except TypeError:
                finish(order_id)
        row = conn.execute("select ship_country from orders where id = ?", (order_id,)).fetchone()
        return redirect(f"/orders/{order_id}", (row["ship_country"] if row else None) or "US")

    @app.post("/paypal/webhook")
    async def paypal_webhook(request: Request):
        accept = getattr(app.state.gateways.get("paypal"), "accept_notify", None)
        raw = await request.body()
        if accept is None or not accept(raw, dict(request.headers)):
            raise HTTPException(status_code=400, detail="paypal")
        return {"ok": True}

    @app.api_route("/orders/{order_id}/lianlian", methods=["GET", "POST"])
    async def lianlian_return(request: Request, order_id: str):
        finish = getattr(app.state.gateways.get("lianlian"), "finish", None)
        if finish:
            try:
                finish(order_id)
            except TypeError:
                finish(order_id)
        row = conn.execute("select ship_country from orders where id = ?", (order_id,)).fetchone()
        return redirect(f"/orders/{order_id}", (row["ship_country"] if row else None) or "US")

    @app.post("/lianlian/notify")
    async def lianlian_notify(request: Request):
        accept = getattr(app.state.gateways.get("lianlian"), "accept_notify", None)
        raw = await request.body()
        if accept is None or not accept(raw, request.headers.get("signature", "")):
            return JSONResponse({"code": 400, "message": "fail"}, status_code=400)
        return {"code": 200, "message": "success"}

    @app.get("/r/{code}", response_class=HTMLResponse)
    def open_referral(request: Request, code: str):
        known = conn.execute("select email from referrals where code = ?", (code,)).fetchone()
        if known is None:
            return RedirectResponse("/", status_code=303)
        response = night(request, mode="claim", invite_code=code, own=buyer_email(request) == known["email"])
        return keep_referrer(response, request, code)

    @app.post("/r/{code}/claim", response_class=HTMLResponse)
    async def claim_referral(request: Request, code: str):
        known = conn.execute("select email from referrals where code = ?", (code,)).fetchone()
        if known is None:
            return RedirectResponse("/", status_code=303)
        form = await request.form()
        email = str(form.get("email") or "").strip().lower()
        if "@" not in email or email == known["email"]:
            return night(request, mode="claim", status_code=400, invite_code=code, own=email == known["email"], bad=True)
        conn.execute(
            "insert into accounts (email, password_hash, referrer_email) values (?, null, null) on conflict(email) do nothing",
            (email,),
        )
        cookie_code = request.cookies.get("referrer_code") or ""
        cookie_owner = conn.execute(
            "select email from referrals where code = ?",
            (cookie_code,),
        ).fetchone() if cookie_code else None
        _bind_referrer(conn, email, cookie_owner["email"] if cookie_owner else known["email"])
        grant_templates(conn, email, "share", utc_day())
        row = conn.execute("select password_hash from accounts where email = ?", (email,)).fetchone()
        response = night(
            request,
            mode="claim",
            invite_code=code,
            claimed=True,
            share_email=email,
            need_login=bool(row and row["password_hash"]),
        )
        response = keep_referrer(response, request, code)
        if row and not row["password_hash"]:
            token = secrets.token_urlsafe(24)
            conn.execute("insert into sessions (token, email) values (?, ?)", (token, email))
            response.set_cookie("buyer_session", token, httponly=True, path="/")
        return response

    def order_view(request, order_id):
        row = conn.execute("select * from orders where id = ?", (order_id,)).fetchone()
        session_id = request.query_params.get("session_id") or ""
        confirm = getattr(app.state.gateways.get("stripe"), "confirm", None)
        if row is not None and session_id and row["status"] == "pending" and confirm:
            confirm(session_id)
            row = conn.execute("select * from orders where id = ?", (order_id,)).fetchone()
        if row is None:
            return render(
                request,
                "order.html",
                order_id=order_id,
                order=None,
                can_set_password=False,
                can_cancel=False,
                can_pay=False,
                can_review=False,
            )
        account = conn.execute("select password_hash from accounts where email = ?", (row["email"],)).fetchone()
        owns_cookie = request.cookies.get("pending_password") == str(row["id"])
        session_email = buyer_email(request)
        owns = owns_cookie or session_email == row["email"]
        paid = row["status"] in {"paid", "shipped"}
        can_set = paid and (owns_cookie or session_email == row["email"]) and account is not None and not account["password_hash"]
        can_cancel = row["status"] == "pending" and owns
        lines = conn.execute(
            "select sku, qty, price_cents from order_lines where order_id = ?",
            (row["id"],),
        ).fetchall()
        due_text = format_money(row["due_local"], row["currency"])

        def order_money(cents):
            return format_money(goods_local(cents, row["units_per_usd"], row["currency"]), row["currency"])
        start, end = delivery_span(row["ship_country"] or "US", row["speed"] if "speed" in row.keys() else "standard")
        return_rows = conn.execute(
            "select reason, status from returns where order_id = ? order by id desc",
            (row["id"],),
        ).fetchall()
        try:
            from shop.adtrack import load_attribution as _load_attr, resolve_account as _resolve_acct, account_to_cfg as _acct_cfg
            _attrs = _load_attr(conn, row["id"])
            _acct = _resolve_acct(conn, acct_code=(_attrs or {}).get("acct") or "")
            if _acct:
                _ad_cfg = _acct_cfg(_acct)
                _key = f"{_acct.get('code')}:{row['id']}"
            else:
                _ad_cfg = load_ad_config(conn)
                _key = row["id"]
            ad_send_ok = 1 if should_send_conversion(_key, float(_ad_cfg.get("send_ratio_pct") or 100)) else 0
        except Exception:
            ad_send_ok = 1
        response = render(
            request,
            "order.html",
            order_id=row["id"],
            order=row,
            ad_send_ok=ad_send_ok,
            due_text=due_text,
            merchandise_text=order_money(row["merchandise_cents"]),
            discount_text=order_money(row["discount_cents"]),
            coupon_text=order_money(row["coupon_cents"]) if row["coupon_cents"] else "",
            shipping_text=order_money(row["shipping_cents"]),
            balance_text=order_money(row["balance_cents"]) if row["balance_cents"] else "",
            can_set_password=can_set,
            can_cancel=can_cancel,
            can_pay=row["status"] == "pending" and owns,
            pay_methods=list(app.state.pay_status.get("shown") or []),
            can_review=row["status"] == "shipped" and session_email == row["email"],
            review_skus=[line["sku"] for line in lines],
            order_lines=lines,
            delivery_start=start,
            delivery_end=end,
            return_rows=return_rows,
            show_retain=owns and row["status"] in {"paid", "shipped"},
        )
        if paid and owns:
            response.set_cookie("harbor_bought", "1", max_age=31536000, path="/", samesite="lax")
        return response

    @app.get("/orders/{order_id}", response_class=HTMLResponse)
    def order_detail(request: Request, order_id: str):
        return order_view(request, order_id)

    @app.post("/orders/{order_id}/password")
    async def set_order_password(request: Request, order_id: str):
        form = await request.form()
        row = conn.execute("select * from orders where id = ?", (order_id,)).fetchone()
        if row is None or row["status"] not in {"paid", "shipped"}:
            raise HTTPException(status_code=403)
        owns = request.cookies.get("pending_password") == str(row["id"]) or buyer_email(request) == row["email"]
        if not owns:
            raise HTTPException(status_code=403)
        account = conn.execute("select password_hash from accounts where email = ?", (row["email"],)).fetchone()
        password = str(form.get("password") or "")
        if len(password) < 8 or (account and account["password_hash"]):
            raise HTTPException(status_code=400)
        if account is None:
            conn.execute(
                "insert into accounts (email, password_hash, referrer_email) values (?, null, null)",
                (row["email"],),
            )
        conn.execute(
            "update accounts set password_hash = ? where email = ?",
            (hash_password(password), row["email"]),
        )
        token = secrets.token_urlsafe(24)
        conn.execute("insert into sessions (token, email) values (?, ?)", (token, row["email"]))
        response = order_view(request, order_id)
        response.set_cookie("buyer_session", token, httponly=True, path="/")
        return response

    @app.post("/orders/{order_id}/cancel")
    def cancel(request: Request, order_id: str):
        row = conn.execute("select * from orders where id = ?", (order_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404)
        owns = request.cookies.get("pending_password") == str(row["id"]) or buyer_email(request) == row["email"]
        if not owns:
            raise HTTPException(status_code=403)
        cancel_order(conn, order_id)
        forget_catalog()
        return order_view(request, order_id)

    @app.get("/login", response_class=HTMLResponse)
    def login(request: Request):
        return render(request, "auth.html", mode="login")

    @app.post("/login")
    async def login_post(request: Request):
        form = await request.form()
        email = str(form.get("email") or "").strip().lower()
        password = str(form.get("password") or "")
        account = conn.execute("select * from accounts where email = ?", (email,)).fetchone()
        if account is None or not verify_password(password, account["password_hash"]):
            return render(request, "auth.html", mode="login", status_code=401)
        token = secrets.token_urlsafe(24)
        conn.execute("insert into sessions (token, email) values (?, ?)", (token, email))
        nxt = str(form.get("next") or "")
        if not nxt.startswith("/") or nxt.startswith("//"):
            nxt = href("/account/orders", country_for(request))
        response = RedirectResponse(nxt, status_code=303)
        response.set_cookie("buyer_session", token, httponly=True, path="/")
        return response

    def register_next(request, raw):
        nxt = str(raw or "")
        if not nxt.startswith("/") or nxt.startswith("//"):
            return href("/account", country_for(request))
        return nxt

    @app.get("/register", response_class=HTMLResponse)
    def register(request: Request):
        return render(request, "auth.html", mode="register")

    @app.post("/register")
    async def register_post(request: Request):
        form = await request.form()
        email = str(form.get("email") or "").strip().lower()
        password = str(form.get("password") or "")
        nxt = register_next(request, form.get("next"))
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            return render(request, "auth.html", mode="register", status_code=400, code="email", form_email=email)
        if len(password) < 8:
            return render(request, "auth.html", mode="register", status_code=400, code="short", form_email=email)
        row = conn.execute("select password_hash from accounts where email = ?", (email,)).fetchone()
        if row and row["password_hash"]:
            return render(request, "auth.html", mode="register", status_code=400, code="taken", form_email=email)
        if row is None:
            conn.execute(
                "insert into accounts (email, password_hash, referrer_email) values (?, null, null)",
                (email,),
            )
        code = request.cookies.get("referrer_code") or ""
        if code:
            known = conn.execute("select email from referrals where code = ?", (code,)).fetchone()
            if known:
                _bind_referrer(conn, email, known["email"])
        conn.execute(
            "update accounts set password_hash = ? where email = ?",
            (hash_password(password), email),
        )
        token = secrets.token_urlsafe(24)
        conn.execute("insert into sessions (token, email) values (?, ?)", (token, email))
        response = RedirectResponse(nxt, status_code=303)
        response.set_cookie("buyer_session", token, httponly=True, path="/")
        return response


    @app.post("/api/auth/login")
    async def api_auth_login(request: Request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}
        email = str(body.get("email") or "").strip().lower()
        password = str(body.get("password") or "")
        account = conn.execute("select * from accounts where email = ?", (email,)).fetchone()
        if account is None or not verify_password(password, account["password_hash"]):
            return JSONResponse({"ok": False, "code": "bad", "message": "Incorrect email or password"}, status_code=401)
        token = secrets.token_urlsafe(24)
        conn.execute("insert into sessions (token, email) values (?, ?)", (token, email))
        response = JSONResponse({"ok": True, "email": email})
        response.set_cookie("buyer_session", token, httponly=True, path="/")
        return response

    @app.post("/api/auth/register")
    async def api_auth_register(request: Request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}
        email = str(body.get("email") or "").strip().lower()
        password = str(body.get("password") or "")
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            return JSONResponse({"ok": False, "code": "email", "message": "Enter a valid email"}, status_code=400)
        if len(password) < 8:
            return JSONResponse({"ok": False, "code": "short", "message": "Password must be at least 8 characters"}, status_code=400)
        row = conn.execute("select password_hash from accounts where email = ?", (email,)).fetchone()
        if row and row["password_hash"]:
            return JSONResponse({"ok": False, "code": "taken", "message": "Email already registered"}, status_code=400)
        if row is None:
            conn.execute(
                "insert into accounts (email, password_hash, referrer_email) values (?, null, null)",
                (email,),
            )
        code = request.cookies.get("referrer_code") or ""
        if code:
            known = conn.execute("select email from referrals where code = ?", (code,)).fetchone()
            if known:
                _bind_referrer(conn, email, known["email"])
        conn.execute(
            "update accounts set password_hash = ? where email = ?",
            (hash_password(password), email),
        )
        token = secrets.token_urlsafe(24)
        conn.execute("insert into sessions (token, email) values (?, ?)", (token, email))
        response = JSONResponse({"ok": True, "email": email})
        response.set_cookie("buyer_session", token, httponly=True, path="/")
        return response

    def keep_referrer(response, request, code):
        current = request.cookies.get("referrer_code") or ""
        if current:
            known = conn.execute("select email from referrals where code = ?", (current,)).fetchone()
            if known:
                return response
        response.set_cookie("referrer_code", code, max_age=31536000, httponly=True, path="/")
        return response

    @app.get("/account/password", response_class=HTMLResponse)
    def set_password(request: Request):
        email = buyer_email(request)
        account = conn.execute("select password_hash from accounts where email = ?", (email,)).fetchone() if email else None
        has_password = bool(account and account["password_hash"])
        return render(request, "auth.html", mode="set", has_password=has_password)

    @app.post("/account/password")
    async def set_password_post(request: Request):
        ctx = view(request)
        email = buyer_email(request)
        if not email:
            return RedirectResponse(href("/login?next=/account/password", ctx["country"]), status_code=303)
        account = conn.execute("select password_hash from accounts where email = ?", (email,)).fetchone()
        if account and account["password_hash"]:
            issue_reset(conn, app.state.outbox, email)
            return RedirectResponse(href("/account/password?sent=1", ctx["country"]), status_code=303)
        form = await request.form()
        password = str(form.get("password") or "")
        if len(password) < 8:
            return render(request, "auth.html", mode="set", status_code=400, code="short", has_password=False)
        if account is None:
            conn.execute(
                "insert into accounts (email, password_hash, referrer_email) values (?, null, null)",
                (email,),
            )
        conn.execute(
            "update accounts set password_hash = ? where email = ?",
            (hash_password(password), email),
        )
        return RedirectResponse(href("/account/password?saved=1", ctx["country"]), status_code=303)

    @app.get("/reset-password", response_class=HTMLResponse)
    def reset_password(request: Request):
        return render(request, "auth.html", mode="reset")

    @app.post("/reset-password")
    async def reset_password_post(request: Request):
        form = await request.form()
        token = str(form.get("token") or "")
        if token:
            password = str(form.get("password") or "")
            if len(password) < 8 or not apply_reset(conn, token, password):
                return render(request, "auth.html", mode="reset", status_code=400, code="bad")
            return RedirectResponse("/login", status_code=303)
        issue_reset(conn, app.state.outbox, str(form.get("email") or ""))
        return render(request, "auth.html", mode="reset", code="sent")

    def account_extras(request):
        ctx = view(request)
        email = buyer_email(request) or ""
        offers = []
        open_orders = 0
        granted_ids = set()
        if email:
            open_orders = conn.execute(
                "select count(*) as n from orders where email = ? and status != 'cancelled'",
                (email,),
            ).fetchone()["n"]
            granted_ids = {
                int(row["coupon_id"])
                for row in conn.execute(
                    "select coupon_id from coupon_grants where email = ?",
                    (email,),
                ).fetchall()
            }
        cart_cents = int(ctx.get("cart_cents") or 0)
        labels = ctx["t"]
        for row in conn.execute(
            "select id, name, kind, threshold_cents, amount_cents from coupons where enabled = 1 order by amount_cents"
        ).fetchall():
            kind = row["kind"]
            threshold = int(row["threshold_cents"] or 0)
            if kind == "first" and open_orders > 0:
                state = "used"
            elif kind == "public" or (kind == "first" and open_orders == 0) or int(row["id"]) in granted_ids:
                state = "ready" if cart_cents >= threshold else "short"
            else:
                state = "locked"
            gap = max(0, threshold - cart_cents)
            if state == "ready":
                status = labels.get("coupon_ready") or "Ready for this order"
            elif state == "short":
                status = (labels.get("coupon_short") or "Add {amount}").format(amount=money(ctx, gap))
            elif state == "used":
                status = labels.get("coupon_used") or "Used"
            else:
                status = labels.get("coupon_locked") or ""
            offers.append({
                "id": int(row["id"]),
                "name": labels.get(f"coupon_{kind}") or row["name"],
                "kind": kind,
                "threshold": money(ctx, threshold),
                "amount": money(ctx, row["amount_cents"]),
                "owned": state == "ready",
                "status": status,
            })
        counts = {"pending": 0, "paid": 0, "shipped": 0, "returns": 0}
        balance = 0
        if email:
            for row in conn.execute("select status from orders where email = ?", (email,)).fetchall():
                if row["status"] in counts:
                    counts[row["status"]] += 1
            found = conn.execute(
                "select available_cents from balances where email = ?",
                (email,),
            ).fetchone()
            balance = found["available_cents"] if found else 0
            try:
                counts["returns"] = conn.execute(
                    "select count(*) as n from returns where email = ?",
                    (email,),
                ).fetchone()["n"]
            except Exception:
                counts["returns"] = 0
        by_sku = {row["sku"]: row for row in catalog_rows()}
        seen = [sku for sku in account_weights(conn, email) if sku in by_sku]
        recent = [present(by_sku[sku], ctx) for sku in seen[:4]]
        if len(recent) < 4:
            have = {item["sku"] for item in recent}
            for row in catalog_rows():
                if row["sku"] in have or row["stock"] <= 0:
                    continue
                recent.append(present(row, ctx))
                if len(recent) >= 4:
                    break
        checked_today = False
        if email:
            checked_today = conn.execute(
                """
                select 1 from coupon_grants g
                join coupons c on c.id = g.coupon_id
                where g.email = ? and c.kind = 'checkin' and g.day = ?
                """,
                (email, utc_day()),
            ).fetchone() is not None
        return {
            "email": email,
            "offers": offers,
            "counts": counts,
            "checked_today": checked_today,
            "balance_text": money(ctx, balance),
        "recent": recent,
        "from_history": bool(seen),
        "wish_count": len(read_skus(request.cookies.get("wishlist"), 36)),
    }

    @app.get("/account/orders", response_class=HTMLResponse)
    def my_orders(request: Request):
        email = buyer_email(request)
        orders = []
        status_filter = str(request.query_params.get("status") or "").strip().lower()
        if email:
            if status_filter == "returns":
                # Orders that have a return row for this email
                try:
                    orders = conn.execute(
                        """
                        select distinct o.* from orders o
                        join returns r on r.order_id = o.id
                        where o.email = ?
                        order by o.id desc
                        """,
                        (email,),
                    ).fetchall()
                except Exception:
                    orders = []
            elif status_filter in ("pending", "paid", "shipped"):
                orders = conn.execute(
                    "select * from orders where email = ? and status = ? order by id desc",
                    (email, status_filter),
                ).fetchall()
            else:
                orders = conn.execute(
                    "select * from orders where email = ? order by id desc",
                    (email,),
                ).fetchall()
        lang = ui_lang_for(request, resolve(country_for(request))[0])
        show_zh = prefer_zh_copy(request) or str(lang).startswith("zh")

        def line_preview(code, qty):
            parent, sep, offer_id = str(code or "").partition("~")
            row = conn.execute(
                "select names, source_zh, image_url, offers from products where sku = ?",
                (parent,),
            ).fetchone()
            name = parent
            image = ""
            option = ""
            if row is not None:
                try:
                    names = json.loads(row["names"] or "{}")
                except Exception:
                    names = {}
                if show_zh:
                    name = _product_label(row["source_zh"], names, parent)
                else:
                    name = names.get(lang) or names.get("en") or parent
                image = row["image_url"] or ""
                if sep:
                    try:
                        offers = json.loads(row["offers"] or "[]")
                    except Exception:
                        offers = []
                    for offer in offers:
                        if str(offer.get("id") or "") != offer_id:
                            continue
                        if offer.get("image"):
                            image = offer["image"]
                        label = offer.get("source_label") if show_zh else offer.get("label")
                        if not label:
                            label = offer.get("label") or offer.get("source_label") or ""
                        if isinstance(label, dict):
                            option = label.get(lang) or label.get("zh") or label.get("en") or ""
                        else:
                            option = str(label or "")
                        # Shared SKU packshot: keep base catalog URL across languages.
                        if offer.get("generated") and image:
                            image = card_image(image, ROOT)
                            return {"name": name, "image": image, "qty": int(qty or 1), "option": option}
                        break
            if image:
                image = card_image(storefront_image(image, lang, ROOT), ROOT)
            return {"name": name, "image": image, "qty": int(qty or 1), "option": option}

        cards = []
        for order in orders:
            rows = conn.execute(
                "select sku, qty from order_lines where order_id = ?",
                (order["id"],),
            ).fetchall()
            track = ""
            try:
                track = str(order["tracking"] or order["tracking_no"] or "")
            except Exception:
                track = str(order["tracking"] or "") if "tracking" in order.keys() else ""
            carrier = ""
            try:
                carrier = str(order["carrier"] or "")
            except Exception:
                carrier = ""
            cards.append({
                "id": order["id"],
                "status": order["status"],
                "due": format_money(order["due_local"], order["currency"]),
                "tracking": (carrier + " " + track).strip() if track else "",
                "items": [line_preview(row["sku"], row["qty"]) for row in rows],
            })
        return render(request, "account.html", panel="orders", orders=cards, **account_extras(request))

    @app.get("/account/coupons", response_class=HTMLResponse)
    def my_coupons(request: Request):
        return render(request, "account.html", panel="coupons", **account_extras(request))

    @app.get("/account/balance", response_class=HTMLResponse)
    def my_balance(request: Request):
        return render(request, "account.html", panel="balance", **account_extras(request))

    @app.get("/account/withdraw", response_class=HTMLResponse)
    def withdraw(request: Request):
        return render(request, "account.html", panel="withdraw", **account_extras(request))

    @app.post("/account/withdraw")
    async def withdraw_post(request: Request):
        email = buyer_email(request)
        if not email:
            raise HTTPException(status_code=401)
        form = await request.form()
        try:
            amount = int(form.get("amount_cents") or 0)
        except ValueError:
            amount = 0
        ok = request_withdrawal(conn, email, amount, str(form.get("payout") or ""))
        if not ok:
            return render(request, "account.html", panel="withdraw", status_code=400, **account_extras(request))
        return render(request, "account.html", panel="withdraw", **account_extras(request))

    def night(request, **extra):
        extra.setdefault("weekday", datetime.now(timezone.utc).weekday())
        return render(request, "campaign.html", **account_extras(request), **extra)

    @app.post("/hold")
    async def lock_hold(request: Request):
        existing = parse_hold(request.cookies.get("harbor_hold"))
        if not still_new(request):
            return JSONResponse({"ok": False})
        if existing:
            return JSONResponse({
                "ok": True,
                "sku": existing["sku"],
                "ends": existing["ends_at"],
                "alive": existing["alive"],
                "price_cents": existing["price_cents"],
            })
        form = await request.form()
        shown = str(form.get("sku") or "").strip()
        request.state.hold_extra = shown
        by_sku = {row["sku"]: row for row in catalog_rows()}
        lines = load_lines(request.cookies.get("cart"))
        # Lock the SKU the popup already showed (avoids image/title mismatch).
        chosen, sale, kept = hold_choice(request, by_sku, lines, prefer_sku=shown)
        if chosen is None:
            return JSONResponse({"ok": False})
        # Stick to the SKU already rendered in the popup unless a live newcomer hold applies.
        if (not kept) and shown and shown in by_sku and int(by_sku[shown].get("stock") or 0) > 0:
            chosen = by_sku[shown]
            sale = half_cents(chosen["price_cents"])
        ends = (datetime.now(timezone.utc).replace(microsecond=0) + timedelta(minutes=15)).isoformat()
        names = {}
        try:
            names = json.loads(chosen.get("names") or "{}")
        except Exception:
            names = {}
        lang = resolve(country_for(request))[0]
        image = chosen.get("image_url") or f"/static/products/{chosen['sku']}.svg"
        body = JSONResponse({
            "ok": True,
            "sku": chosen["sku"],
            "ends": ends,
            "alive": True,
            "price_cents": sale,
            "kept": kept,
            "name": names.get(lang) or names.get("en") or chosen["sku"],
            "image": storefront_image(image, lang, ROOT),
        })
        body.set_cookie(
            "harbor_hold",
            pack_hold(chosen["sku"], sale, ends),
            max_age=60 * 20,
            path="/",
            samesite="lax",
            httponly=True,
        )
        return body

    @app.get("/rewards", response_class=HTMLResponse)
    def rewards(request: Request):
        return night(request, mode="plaza")

    @app.get("/locale", response_class=HTMLResponse)
    def locale_page(request: Request):
        return render(request, "locale.html")

    @app.get("/share", response_class=HTMLResponse)
    def share(request: Request):
        email = buyer_email(request) or ""
        link = f"/r/{ensure_code(conn, email)}" if email else ""
        return night(request, mode="share", share_email=email, share_link=link)

    @app.post("/share")
    async def share_post(request: Request):
        return RedirectResponse("/share", status_code=303)

    @app.get("/install", response_class=HTMLResponse)
    def install(request: Request):
        return night(request, mode="install", share_email=buyer_email(request) or "")

    @app.post("/pwa/open")
    async def pwa_open(request: Request):
        form = await request.form()
        if str(form.get("standalone") or "") != "1":
            return JSONResponse({"ok": False})
        email = buyer_email(request)
        if not email:
            return JSONResponse({"ok": False, "need_login": True})
        grant_templates(conn, email, "desktop", "once")
        response = JSONResponse({"ok": True})
        response.set_cookie("pwa_opened", "1", max_age=31536000, path="/", samesite="lax")
        return response

    @app.post("/desktop")
    async def desktop(request: Request):
        form = await request.form()
        email = str(form.get("email") or buyer_email(request) or "").strip().lower()
        if "@" not in email:
            response = RedirectResponse("/install", status_code=303)
            response.set_cookie("desktop_pending", "1", max_age=31536000, httponly=True, path="/")
            return response
        grant_templates(conn, email, "desktop", "once")
        return night(request, mode="install", share_email=email, claimed=True)

    @app.get("/check-in", response_class=HTMLResponse)
    def check_in(request: Request):
        return night(request, mode="checkin")

    @app.post("/check-in")
    def check_in_post(request: Request):
        email = buyer_email(request)
        if not email:
            return night(request, mode="checkin", status_code=401)
        grant_templates(conn, email, "checkin", utc_day())
        return night(request, mode="checkin", stamped=True)

    @app.post("/p/{sku}/review")
    async def review(request: Request, sku: str):
        email = buyer_email(request)
        if not email:
            raise HTTPException(status_code=401)
        form = await request.form()
        add_review(conn, email, sku, form.get("rating"), str(form.get("body") or ""))
        return RedirectResponse(href(f"/p/{sku}", country_for(request)), status_code=303)

    @app.get("/policies/shipping", response_class=HTMLResponse)
    def shipping_policy(request: Request):
        return render(request, "text.html", panel="shipping")

    @app.get("/policies/privacy", response_class=HTMLResponse)
    def privacy(request: Request):
        return render(request, "text.html", panel="privacy")

    @app.get("/policies/terms", response_class=HTMLResponse)
    def terms(request: Request):
        return render(request, "text.html", panel="terms")

    @app.get("/contact", response_class=HTMLResponse)
    def contact(request: Request):
        return render(request, "text.html", panel="contact")

    def require_staff(request: Request):
        """Any enabled staff session (ops login)."""
        row = staff_from_token(conn, request.cookies.get("admin_session", ""))
        if row is None or not row["enabled"]:
            accept = request.headers.get("accept", "")
            if request.method == "GET" and "text/html" in accept:
                raise LoginRequired()
            raise HTTPException(status_code=401, detail="Unauthorized")
        request.state.staff = row
        return row

    def require_admin(request: Request):
        """Backward-compatible alias: any logged-in staff."""
        return require_staff(request)

    def require_admin_role(request: Request):
        """Administrator role only (refunds, keys, staff, credentials)."""
        row = require_staff(request)
        if not is_admin_role(row):
            raise HTTPException(status_code=403, detail="Forbidden")
        return row

    def admin_nav_badges():
        try:
            ship = conn.execute(
                "select count(*) as n from orders where status = 'paid'"
            ).fetchone()["n"]
            payout = conn.execute(
                "select count(*) as n from withdrawals where status != 'paid'"
            ).fetchone()["n"]
            try:
                ensure_cs_tables(conn)
                cs = conn.execute(
                    "select coalesce(sum(unread_staff),0) as n from cs_rooms where status='open'"
                ).fetchone()["n"]
            except Exception:
                cs = 0
            return {"ship": int(ship or 0), "payout": int(payout or 0), "cs": int(cs or 0)}
        except Exception:
            return {"ship": 0, "payout": 0, "cs": 0}

    def flash_redirect(url: str, flash: str):
        join = "&" if "?" in url else "?"
        return RedirectResponse(f"{url}{join}flash={flash}", status_code=303)

    @app.get("/admin/login", response_class=HTMLResponse)
    def admin_login_page(request: Request):
        return render(request, "admin_login.html")

    @app.post("/admin/login")
    async def admin_login(request: Request):
        form = await request.form()
        row = authenticate(conn, form.get("username"), str(form.get("password") or ""))
        if row is None:
            return render(request, "admin_login.html", status_code=401, error="账号或密码不正确，或账号已停用。请联系管理员重置密码。")
        response = RedirectResponse("/admin/orders", status_code=303)
        response.set_cookie("admin_session", start_session(conn, row["username"]), httponly=True, path="/")
        return response

    @app.post("/admin/logout")
    def admin_logout(request: Request):
        token = request.cookies.get("admin_session", "")
        if token:
            conn.execute("delete from staff_sessions where token = ?", (token,))
        response = RedirectResponse("/admin/login", status_code=303)
        response.delete_cookie("admin_session", path="/")
        return response

    def _staff_members():
        return conn.execute(
            "select username, role, enabled from staff order by username"
        ).fetchall()

    def _secret_tail(value):
        text = str(value or "").strip()
        return text[-4:] if len(text) >= 4 else ""

    def payment_page(request):
        status = apply_checkout()
        return render(
            request,
            "admin.html",
            panel="payments",
            pay={
                "enabled": status.get("enabled") or [],
                "shown": status.get("shown") or [],
                "paypal_client_id": saved_or_env("paypal_client_id", "PAYPAL_CLIENT_ID"),
                "paypal_secret_saved": bool(saved_or_env("paypal_client_secret", "PAYPAL_CLIENT_SECRET")),
                "paypal_secret_tail": _secret_tail(saved_or_env("paypal_client_secret", "PAYPAL_CLIENT_SECRET")),
                "paypal_env": saved_or_env("paypal_env", "PAYPAL_ENV", "sandbox"),
                "paypal_webhook_id": saved_or_env("paypal_webhook_id", "PAYPAL_WEBHOOK_ID"),
                "lianlian_merchant_id": saved_or_env("lianlian_merchant_id", "LIANLIAN_MERCHANT_ID"),
                "lianlian_sub_merchant_id": saved_or_env("lianlian_sub_merchant_id", "LIANLIAN_SUB_MERCHANT_ID"),
                "lianlian_key_saved": bool(saved_or_env("lianlian_private_key") or _secret_text("LIANLIAN_PRIVATE_KEY", "LIANLIAN_PRIVATE_KEY_FILE")),
                "lianlian_env": saved_or_env("lianlian_env", "LIANLIAN_ENV", "sandbox"),
                "lianlian_country": saved_or_env("lianlian_country", "LIANLIAN_COUNTRY", "CN"),
                "stripe_saved": bool(saved_or_env("stripe_secret_key", "STRIPE_SECRET_KEY")),
                "stripe_tail": _secret_tail(saved_or_env("stripe_secret_key", "STRIPE_SECRET_KEY")),
                "stripe_webhook_saved": bool(saved_or_env("stripe_webhook_secret", "STRIPE_WEBHOOK_SECRET")),
                "active": status["active"],
            },
        )

    @app.get("/admin/payments", response_class=HTMLResponse)
    def admin_payments(request: Request):
        require_admin_role(request)
        return payment_page(request)

    @app.post("/admin/payments")
    async def admin_payments_save(request: Request):
        require_admin_role(request)
        form = await request.form()
        allowed = ("paypal", "lianlian", "stripe")
        enabled = [name for name in allowed if name in form.getlist("pay_on")]
        paypal_env = "live" if str(form.get("paypal_env") or "") == "live" else "sandbox"
        lianlian_env = "live" if str(form.get("lianlian_env") or "") == "live" else "sandbox"
        plain = {
            "pay_providers": ",".join(enabled),
            "paypal_client_id": str(form.get("paypal_client_id") or "").strip(),
            "paypal_env": paypal_env,
            "paypal_webhook_id": str(form.get("paypal_webhook_id") or "").strip(),
            "lianlian_merchant_id": str(form.get("lianlian_merchant_id") or "").strip(),
            "lianlian_sub_merchant_id": str(form.get("lianlian_sub_merchant_id") or "").strip(),
            "lianlian_env": lianlian_env,
            "lianlian_country": str(form.get("lianlian_country") or "CN").strip().upper()[:2] or "CN",
        }
        for key, value in plain.items():
            save_setting(key, value)
        for key, field in (
            ("paypal_client_secret", "paypal_client_secret"),
            ("lianlian_private_key", "lianlian_private_key"),
            ("lianlian_public_key", "lianlian_public_key"),
            ("stripe_secret_key", "stripe_secret_key"),
            ("stripe_webhook_secret", "stripe_webhook_secret"),
        ):
            incoming = str(form.get(field) or "").strip()
            if incoming:
                save_setting(key, incoming)
        apply_checkout()
        return RedirectResponse("/admin/payments?saved=1", status_code=303)


    @app.get("/admin/coefficients", response_class=HTMLResponse)
    def admin_coefficients(request: Request):
        require_admin_role(request)
        from shop.extras import LOCALES
        rows = []
        for code in LOCALES:
            lang, currency = resolve(code)
            coef = coefficient_for(conn, code)
            delta = round((coef - 1.0) * 100, 1)
            rows.append({
                "code": code,
                "currency": currency,
                "coefficient": coef,
                "is_base": code == "US",
                "delta_pct": delta,
            })
        return render(
            request,
            "admin_coefficients.html",
            rows=rows,
            flash=request.query_params.get("flash") or "",
        )

    @app.post("/admin/coefficients")
    async def admin_coefficients_save(request: Request):
        require_admin_role(request)
        form = await request.form()
        if str(form.get("reset") or "") == "1":
            save_coefficients(conn, dict(COEF_DEFAULTS))
            return flash_redirect("/admin/coefficients", "coef_reset")
        mapping = {"US": 1.0}
        for key, value in form.multi_items():
            if not str(key).startswith("coef_"):
                continue
            code = str(key)[5:].upper()
            try:
                mapping[code] = float(value)
            except (TypeError, ValueError):
                return flash_redirect("/admin/coefficients", "coef_bad")
        if not mapping:
            return flash_redirect("/admin/coefficients", "coef_bad")
        save_coefficients(conn, mapping)
        return flash_redirect("/admin/coefficients", "coef_saved")

    @app.get("/admin/staff", response_class=HTMLResponse)
    def admin_staff(request: Request):
        require_admin_role(request)
        return render(request, "admin.html", panel="staff", members=_staff_members())

    @app.post("/admin/staff")
    async def admin_staff_add(request: Request):
        require_admin_role(request)
        form = await request.form()
        username = clean_username(form.get("username"))
        password = str(form.get("password") or "")
        role = str(form.get("role") or "staff")
        if role not in {"admin", "staff"}:
            role = "staff"
        members = _staff_members()
        if not username or len(password) < 8:
            return render(
                request,
                "admin.html",
                status_code=400,
                panel="staff",
                members=members,
                staff_error="账号用字母或数字，密码至少 8 位",
            )
        taken = conn.execute("select username from staff where username = ?", (username,)).fetchone()
        if taken:
            return render(
                request,
                "admin.html",
                status_code=400,
                panel="staff",
                members=members,
                staff_error="这个账号已经有了",
            )
        save_staff(conn, username, password, role)
        return flash_redirect("/admin/staff", "staff_added")

    @app.post("/admin/staff/{username}/disable")
    def admin_staff_disable(request: Request, username: str):
        actor = require_admin_role(request)
        name = clean_username(username)
        if not name or name == actor["username"]:
            return flash_redirect("/admin/staff", "staff_self")
        set_staff_enabled(conn, name, False)
        return flash_redirect("/admin/staff", "staff_disabled")

    @app.post("/admin/staff/{username}/enable")
    def admin_staff_enable(request: Request, username: str):
        require_admin_role(request)
        name = clean_username(username)
        if not name:
            return flash_redirect("/admin/staff", "staff_fail")
        set_staff_enabled(conn, name, True)
        return flash_redirect("/admin/staff", "staff_enabled")

    @app.post("/admin/staff/{username}/reset")
    async def admin_staff_reset(request: Request, username: str):
        require_admin_role(request)
        form = await request.form()
        name = clean_username(username)
        password = str(form.get("password") or "")
        if not name or len(password) < 8:
            return flash_redirect("/admin/staff", "staff_pwd")
        if not reset_staff_password(conn, name, password):
            return flash_redirect("/admin/staff", "staff_fail")
        return flash_redirect("/admin/staff", "staff_reset")

    @app.get("/admin/stats", response_class=HTMLResponse)
    def admin_stats(request: Request, days: int = 7):
        require_staff(request)
        data = board(conn, days)
        skus = [row["sku"] for row in data["items"]] + [row["sku"] for row in data["sold"]]
        labels = {}
        if skus:
            marks = ",".join("?" for _ in dict.fromkeys(skus))
            wanted = tuple(dict.fromkeys(skus))
            for row in conn.execute(
                f"select sku, source_zh, names from products where sku in ({marks})",
                wanted,
            ).fetchall():
                labels[row["sku"]] = _product_label(row["source_zh"], row["names"], row["sku"])
        for row in data["items"]:
            row["name"] = labels.get(row["sku"]) or row["sku"]
        for row in data["sold"]:
            row["name"] = labels.get(row["sku"]) or row["sku"]
        try:
            funnel = funnel_stats(conn, min(14, max(1, int(days or 7))))
        except Exception:
            funnel = {"totals": {"land": 0, "deal_click": 0, "purchase": 0}}
        return render(
            request,
            "admin_board.html",
            board=data,
            push_line=push_line(conn),
            hot_line=hot_line(app.state.hot, app.state.hot_ready),
            ad_funnel=funnel,
        )

    @app.get("/admin/orders", response_class=HTMLResponse)
    def admin_orders(request: Request):
        require_staff(request)
        status = str(request.query_params.get("status") or "all").strip().lower()
        q = str(request.query_params.get("q") or "").strip()
        all_rows = conn.execute(
            "select id, email, status, currency, due_local, tracking, carrier from orders order by id desc"
        ).fetchall()
        counts = {
            "all": len(all_rows),
            "pending": sum(row["status"] == "pending" for row in all_rows),
            "paid": sum(row["status"] == "paid" for row in all_rows),
            "shipped": sum(row["status"] == "shipped" for row in all_rows),
            "cancelled": sum(row["status"] == "cancelled" for row in all_rows),
            "refunded": sum(row["status"] == "refunded" for row in all_rows),
        }
        rows = all_rows
        if status and status != "all":
            rows = [row for row in rows if row["status"] == status]
        if q:
            needle = q.lower()
            filtered = []
            for row in rows:
                blob = " ".join(
                    [
                        str(row["id"]),
                        str(row["email"] or ""),
                        str(row["tracking"] or ""),
                        str(row["carrier"] or ""),
                    ]
                ).lower()
                if needle in blob:
                    filtered.append(row)
            rows = filtered
        return render(
            request,
            "admin.html",
            panel="orders",
            orders=rows,
            counts=counts,
            order_status=status or "all",
            order_q=q,
        )

    @app.get("/admin/orders/{order_id}", response_class=HTMLResponse)
    def admin_order(request: Request, order_id: str):
        actor = require_staff(request)
        row = conn.execute("select * from orders where id = ?", (order_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404)
        lines = conn.execute(
            "select sku, price_cents, qty from order_lines where order_id = ?",
            (order_id,),
        ).fetchall()
        shown = [
            {
                **sale_source(line["sku"]),
                "price_cents": line["price_cents"],
                "qty": line["qty"],
                "price_usd": cents_to_dollars_str(line["price_cents"]),
            }
            for line in lines
        ]
        sheet = label_lines(
            row["ship_country"], row["ship_name"], row["phone"], row["address"],
            row["city"], row["region"], row["postal"],
        )
        can_ship = row["status"] == "paid"
        can_refund = is_admin_role(actor) and row["status"] in {"paid", "shipped"}
        return render(
            request,
            "admin.html",
            panel="order",
            order_id=order_id,
            order=row,
            lines=shown,
            label_lines=sheet,
            can_ship=can_ship,
            can_refund=can_refund,
        )

    @app.post("/admin/orders/{order_id}/ship")
    async def admin_ship(request: Request, order_id: str):
        require_staff(request)
        form = await request.form()
        if not ship_order(conn, order_id, str(form.get("carrier") or ""), str(form.get("tracking") or "")):
            return flash_redirect(f"/admin/orders/{order_id}", "ship_fail")
        return flash_redirect(f"/admin/orders/{order_id}", "shipped")

    @app.post("/admin/orders/{order_id}/refund")
    async def admin_refund(request: Request, order_id: str):
        require_admin_role(request)
        form = await request.form()
        reason = str(form.get("reason") or "").strip()[:300]
        if len(reason) < 3:
            return flash_redirect(f"/admin/orders/{order_id}", "refund_need_reason")
        row = conn.execute("select status from orders where id = ?", (order_id,)).fetchone()
        if row is None or row["status"] not in {"paid", "shipped"}:
            return flash_redirect(f"/admin/orders/{order_id}", "refund_not_allowed")
        try:
            conn.execute(
                "update orders set refund_reason = ? where id = ?",
                (reason, order_id),
            )
        except Exception:
            pass
        paid = conn.execute("select pay_method from orders where id = ?", (order_id,)).fetchone()
        method = paid["pay_method"] if paid else ""
        gateway = app.state.gateways.get(method) or app.state.stripe
        if not refund_order(conn, gateway, order_id):
            return flash_redirect(f"/admin/orders/{order_id}", "refund_fail")
        forget_catalog()
        return flash_redirect(f"/admin/orders/{order_id}", "refunded")

    @app.get("/admin/withdrawals", response_class=HTMLResponse)
    def admin_withdrawals(request: Request):
        require_staff(request)
        rows = conn.execute("select * from withdrawals order by id desc").fetchall()
        return render(request, "admin.html", panel="withdrawals", withdrawals=rows)

    @app.get("/admin/promos", response_class=HTMLResponse)
    def admin_promos(request: Request):
        require_admin(request)
        first = conn.execute(
            "select threshold_cents, amount_cents from coupons where kind = 'first' order by id limit 1"
        ).fetchone()
        return render(
            request,
            "admin.html",
            panel="promos",
            first_coupon={
                "threshold_cents": first["threshold_cents"] if first else 2500,
                "amount_cents": first["amount_cents"] if first else 200,
            },
            guarantees=load_guarantees(conn),
        )

    @app.get("/admin/campaigns", response_class=HTMLResponse)
    def admin_campaigns(request: Request):
        require_admin(request)
        rows = []
        for camp in conn.execute("select * from campaigns order by kind, id").fetchall():
            raw_items = conn.execute(
                """
                select ci.id, ci.sku, ci.price_cents, ci.stock, p.names, p.source_zh
                from campaign_items ci
                left join products p on p.sku = ci.sku
                where ci.campaign_id = ?
                order by ci.id
                """,
                (camp["id"],),
            ).fetchall()
            items = []
            for item in raw_items:
                items.append({
                    "id": item["id"],
                    "sku": item["sku"],
                    "price_cents": item["price_cents"],
                    "stock": item["stock"],
                    "name": _product_label(item["source_zh"], item["names"], item["sku"]),
                })
            rows.append({"camp": camp, "items": items})
        catalog = conn.execute(
            "select sku, names, source_zh, price_cents from products where published = 1 order by sku"
        ).fetchall()
        choices = [
            {
                "sku": row["sku"],
                "name": _product_label(row["source_zh"], row["names"], row["sku"]),
                "price": f"${row['price_cents'] / 100:.2f}",
            }
            for row in catalog
        ]
        return render(request, "admin.html", panel="campaigns", campaign_rows=rows, product_choices=choices)

    @app.get("/admin/coupons", response_class=HTMLResponse)
    def admin_coupons(request: Request):
        require_admin(request)
        rows = conn.execute("select * from coupons order by id").fetchall()
        return render(request, "admin.html", panel="coupons", coupons=rows)

    _CATEGORY_ZH = ZH
    _PARAMS = (
        ("brand", "品牌"),
        ("model", "型号"),
        ("variant", "规格"),
        ("material", "材质"),
        ("color", "颜色"),
        ("size", "尺寸"),
        ("weight", "重量"),
        ("origin", "产地"),
        ("unit", "单位"),
        ("supply", "供货能力"),
        ("port", "发货港口"),
        ("payment", "付款方式"),
        ("lead_time", "交货期"),
        ("packaging", "包装"),
        ("keywords", "关键词"),
        ("group", "分组"),
        ("offer_id", "商品ID"),
    )

    def load_object(raw):
        try:
            value = json.loads(raw or "")
        except json.JSONDecodeError:
            return {}
        return value if isinstance(value, dict) else {}

    def setting(key):
        row = conn.execute("select value from settings where key = ?", (key,)).fetchone()
        return row["value"] if row else ""

    def preview_zip_path(token):
        if not re.fullmatch(r"[0-9a-f]{16}", str(token or "")):
            return None
        return preview_root / f"{token}.zip"

    def preview_meta_path(token):
        path = preview_zip_path(token)
        return None if path is None else path.with_suffix(".preview.json")

    def load_catalog_queue():
        raw = setting("catalog_queue")
        queue = []
        if raw:
            try:
                saved = json.loads(raw)
            except json.JSONDecodeError:
                saved = None
            if isinstance(saved, list):
                for item in saved:
                    if isinstance(item, dict) and preview_zip_path(item.get("token")) is not None:
                        queue.append(item)
        if queue:
            return queue
        legacy = setting("catalog_preview")
        if not legacy:
            return []
        try:
            data = json.loads(legacy)
        except json.JSONDecodeError:
            return []
        if not isinstance(data, dict) or not data.get("token"):
            return []
        token = data["token"]
        meta_path = preview_meta_path(token)
        if meta_path is not None and not meta_path.is_file():
            meta_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        summary = {
            "token": token,
            "filename": str(data.get("filename") or "package.zip"),
            "list_rate": data.get("list_rate"),
            "sale_rate": data.get("sale_rate"),
            "grams_per_dollar": data.get("grams_per_dollar"),
            "hold_percent": data.get("hold_percent"),
            "passed": data.get("passed") or 0,
            "held": data.get("held") or 0,
            "spec_held": data.get("spec_held") or 0,
            "product_count": len(data.get("products") or []),
        }
        conn.execute(
            "insert into settings (key, value) values ('catalog_queue', ?) on conflict(key) do update set value = excluded.value",
            (json.dumps([summary], ensure_ascii=False),),
        )
        return [summary]

    def save_catalog_queue(queue):
        conn.execute(
            "insert into settings (key, value) values ('catalog_queue', ?) on conflict(key) do update set value = excluded.value",
            (json.dumps(queue, ensure_ascii=False),),
        )
        conn.execute("delete from settings where key = 'catalog_preview'")

    def save_last_upload(payload):
        conn.execute(
            "insert into settings (key, value) values ('catalog_last_upload', ?) on conflict(key) do update set value = excluded.value",
            (json.dumps(payload, ensure_ascii=False),),
        )
        history = []
        raw_hist = setting("catalog_upload_history")
        if raw_hist:
            try:
                loaded = json.loads(raw_hist)
                if isinstance(loaded, list):
                    history = [item for item in loaded if isinstance(item, dict)]
            except json.JSONDecodeError:
                history = []
        history = [payload, *history][:8]
        conn.execute(
            "insert into settings (key, value) values ('catalog_upload_history', ?) on conflict(key) do update set value = excluded.value",
            (json.dumps(history, ensure_ascii=False),),
        )

    def load_last_upload():
        raw = setting("catalog_last_upload")
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    def load_upload_history():
        raw = setting("catalog_upload_history")
        history = []
        if raw:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = []
            if isinstance(data, list):
                history = [item for item in data if isinstance(item, dict) and item.get("imported")]
        if not history:
            last = load_last_upload()
            if last:
                history = [last]
        return history

    def load_preview_detail(token):
        meta_path = preview_meta_path(token)
        if meta_path is None or not meta_path.is_file():
            return None
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(data, dict) or data.get("token") != token:
            return None
        return data

    def load_catalog_preview():
        queue = load_catalog_queue()
        if not queue:
            return None
        packages = []
        rows = []
        products = []
        for item in queue:
            detail = load_preview_detail(item.get("token"))
            package = dict(item)
            if detail:
                package["passed"] = detail.get("passed") or package.get("passed") or 0
                package["held"] = detail.get("held") or package.get("held") or 0
                package["spec_held"] = detail.get("spec_held") or package.get("spec_held") or 0
                if len(queue) == 1:
                    rows = detail.get("rows") or []
                    products = detail.get("products") or []
            packages.append(package)
        first = packages[0]
        return {
            "token": first["token"] if len(packages) == 1 else "queue",
            "filename": first.get("filename") or "",
            "list_rate": first.get("list_rate"),
            "sale_rate": first.get("sale_rate"),
            "grams_per_dollar": first.get("grams_per_dollar"),
            "hold_percent": first.get("hold_percent"),
            "passed": sum(int(p.get("passed") or 0) for p in packages),
            "held": sum(int(p.get("held") or 0) for p in packages),
            "spec_held": sum(int(p.get("spec_held") or 0) for p in packages),
            "packages": packages,
            "rows": rows,
            "products": products,
        }

    def drop_preview_package(token):
        path = preview_zip_path(token)
        if path is not None:
            path.unlink(missing_ok=True)
        meta = preview_meta_path(token)
        if meta is not None:
            meta.unlink(missing_ok=True)

    def drop_preview_zip():
        for item in load_catalog_queue():
            drop_preview_package(item.get("token"))
        save_catalog_queue([])

    def plain_decimal(number):
        text = format(Decimal(number), "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text or "0"

    def pricing_rules():
        defaults = {
            "list_rate": Decimal("2"),
            "sale_rate": Decimal("1.3"),
            "hold_percent": Decimal("20"),
            "grams_per_dollar": Decimal("25"),
        }
        rules = {}
        for key, default in defaults.items():
            raw = setting(f"price_{key}")
            if not raw:
                number = default
            elif key == "hold_percent":
                number = parse_percent(raw)
            else:
                number = parse_rate(raw)
            rules[key] = default if number is None else number
        return rules

    def pricing_form():
        rules = pricing_rules()
        return {key: plain_decimal(value) for key, value in rules.items()}

    def store_pricing(list_rate, sale_rate, hold_percent, grams_per_dollar):
        for key, value in (
            ("price_list_rate", list_rate),
            ("price_sale_rate", sale_rate),
            ("price_hold_percent", hold_percent),
            ("price_grams_per_dollar", grams_per_dollar),
        ):
            conn.execute(
                "insert into settings (key, value) values (?, ?) on conflict(key) do update set value = excluded.value",
                (key, plain_decimal(value)),
            )

    def quoted_rates(form, fallback):
        parsed = {}
        for key, parser in (
            ("list_rate", parse_rate),
            ("sale_rate", parse_rate),
            ("hold_percent", parse_percent),
            ("grams_per_dollar", parse_rate),
        ):
            raw = form.get(key)
            if raw in (None, ""):
                parsed[key] = Decimal(str(fallback[key]))
                continue
            number = parser(raw)
            if number is None:
                return None
            parsed[key] = number
        if parsed["hold_percent"] > 1000 or parsed["grams_per_dollar"] > 100000:
            return None
        return parsed["list_rate"], parsed["sale_rate"], parsed["hold_percent"], parsed["grams_per_dollar"]

    def save_preview(token, raw, list_rate, sale_rate, grams_per_dollar, hold_percent, write_zip, filename="", replace_all=False):
        name = str(filename or "package.zip").strip() or "package.zip"
        products = preview_sheets(
            [(raw, name)], list_rate, sale_rate, grams_per_dollar, hold_percent,
        )
        described = describe_preview(products, sale_rate, grams_per_dollar)
        path = preview_zip_path(token)
        meta_path = preview_meta_path(token)
        if path is None or meta_path is None:
            raise PackageError("分析编号不对。")
        if write_zip:
            if replace_all:
                for item in load_catalog_queue():
                    if item.get("token") != token:
                        drop_preview_package(item.get("token"))
            path.write_bytes(raw)
        payload = {
            "token": token,
            "filename": name,
            "list_rate": plain_decimal(list_rate),
            "sale_rate": plain_decimal(sale_rate),
            "grams_per_dollar": plain_decimal(grams_per_dollar),
            "hold_percent": plain_decimal(hold_percent),
            "products": products,
            "rows": described["rows"],
            "passed": described["passed"],
            "held": described["held"],
            "spec_held": described["spec_held"],
        }
        meta_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        summary = {
            "token": token,
            "filename": name,
            "list_rate": payload["list_rate"],
            "sale_rate": payload["sale_rate"],
            "grams_per_dollar": payload["grams_per_dollar"],
            "hold_percent": payload["hold_percent"],
            "passed": described["passed"],
            "held": described["held"],
            "spec_held": described["spec_held"],
            "product_count": len(products),
        }
        # Same zip name re-analyzed → replace old queue row (avoids 26/34 double-commit / 500+ skips)
        norm = name.casefold()
        queue = []
        if not replace_all:
            for item in load_catalog_queue():
                if item.get("token") == token:
                    continue
                if str(item.get("filename") or "").casefold() == norm:
                    drop_preview_package(item.get("token"))
                    continue
                queue.append(item)
        queue.append(summary)
        save_catalog_queue(queue)
        store_pricing(list_rate, sale_rate, hold_percent, grams_per_dollar)

    def ensure_ai():
        if app.state.writer is not None or app.state.translator is not None or app.state.complete is not None:
            return
        writer, translator, complete = _ai_parts(
            ai_pair(setting("ai_key"), setting("ai_base"), setting("ai_model")) or ai_from_env()
        )
        app.state.writer = writer
        app.state.translator = translator
        app.state.complete = complete

    def active_translator():
        ensure_ai()
        return app.state.translator or translator_from_env()

    def active_complete():
        ensure_ai()
        return app.state.complete

    def cny_per_usd():
        row = conn.execute(
            "select units_per_usd from rates where currency = 'CNY' order by hour desc limit 1"
        ).fetchone()
        if row:
            return float(row["units_per_usd"])
        try:
            import httpx

            body = httpx.get("https://open.er-api.com/v6/latest/USD", timeout=8).json()
            rate = float(body["rates"]["CNY"])
        except Exception:
            return None
        remember_rates(conn, {"CNY": rate}, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H"))
        return rate

    def blank_copy():
        empty = {lang: "" for lang in LANGS}
        return empty, {lang: [] for lang in LANGS}, dict(empty)

    def store_item(item, names, bullets, description, specs, published):
        listing = json.dumps(item["listing"], ensure_ascii=False)
        source = json.dumps(
            {"name": item["title"], "description": item["listing"].get("description") or "", "bullets": []},
            ensure_ascii=False,
        )
        payload = (
            item["category"],
            item["price_cents"],
            item["stock"],
            json.dumps(names, ensure_ascii=False),
            json.dumps(bullets, ensure_ascii=False),
            json.dumps(description, ensure_ascii=False),
            json.dumps(specs, ensure_ascii=False),
            item["image_url"],
            source,
            listing,
            published,
            int(item.get("original_cents") or 0),
            json.dumps(item.get("offers") or [], ensure_ascii=False),
        )
        existing = conn.execute("select sku from products where sku = ?", (item["sku"],)).fetchone()
        if existing:
            conn.execute(
                """
                update products
                set category = ?, price_cents = ?, stock = ?, names = ?, bullets = ?, description = ?,
                    specs = ?, image_url = ?, source_zh = ?, listing = ?, published = ?,
                    original_cents = ?, offers = ?
                where sku = ?
                """,
                (*payload, item["sku"]),
            )
        else:
            conn.execute(
                """
                insert into products
                    (sku, category, price_cents, stock, names, bullets, description, specs, image_url, source_zh, listing, published, original_cents, offers, uploaded_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (item["sku"], *payload, date.today().isoformat()),
            )

    def translated_copy(listing, translate):
        texts = {}
        if listing.get("title"):
            texts["title"] = listing["title"]
        if listing.get("description"):
            texts["description"] = listing["description"]
        if listing.get("material"):
            texts["material"] = listing["material"]
        filled = translate_fields(texts, translate)
        names = filled["title"]
        description = filled.get("description") or {lang: names[lang] for lang in names}
        specs = {
            "material": filled.get("material") or "",
            "size": listing.get("size") or "",
            "weight": listing.get("weight") or "",
        }
        return names, {lang: [] for lang in names}, description, specs

    def translate_offers(offers, translate):
        indexed = [
            (index, offer.get("source_label") or "")
            for index, offer in enumerate(offers)
            if offer.get("source_label")
        ]
        if not indexed:
            return offers
        packed = "\n".join(label for _, label in indexed)
        filled = translate_fields({"options": packed}, translate).get("options") or {}
        parts = {}
        matched = isinstance(filled, dict)
        if matched:
            for lang, text in filled.items():
                lines = str(text).split("\n")
                if len(lines) != len(indexed):
                    matched = False
                    break
                parts[lang] = lines
        if not matched:
            texts = {f"o{index}": label for index, label in indexed}
            filled = translate_fields(texts, translate)
            for index, _label in indexed:
                key = f"o{index}"
                if key in filled:
                    offers[index]["label"] = filled[key]
            return offers
        for pos, (index, _label) in enumerate(indexed):
            offers[index]["label"] = {lang: lines[pos] for lang, lines in parts.items()}
        return offers

    def compose_copy(listing, offers, translate):
        ensure_ai()
        writer = app.state.writer
        if writer is not None:
            source_options = [offer.get("source_label") or "" for offer in offers if offer.get("source_label")]
            written = writer({
                "title": listing.get("title") or "",
                "description": listing.get("description") or "",
                "material": listing.get("material") or "",
                "size": listing.get("size") or "",
                "weight": listing.get("weight") or "",
                "options": source_options,
            })
            localized = bool(written.get("localized")) and isinstance(written.get("title"), dict)
            if isinstance(written.get("title"), dict):
                names = {
                    lang: str(written["title"].get(lang) or written["title"].get("en") or "").strip()
                    for lang in LANGS
                }
            else:
                names = {lang: written["title"] for lang in LANGS}
            raw_description = written.get("description") or names.get("en") or ""
            if isinstance(raw_description, dict):
                english = str(raw_description.get("en") or names.get("en") or "").strip()
                description = {
                    lang: str(raw_description.get(lang) or english).strip()
                    for lang in LANGS
                }
            else:
                description = {lang: raw_description or names.get("en") or "" for lang in LANGS}
            option_lines = written.get("options") or []
            if len(option_lines) == len(source_options) and option_lines:
                cursor = 0
                for offer in offers:
                    if not offer.get("source_label"):
                        continue
                    line = option_lines[cursor]
                    cursor += 1
                    if isinstance(line, dict):
                        offer["label"] = line
                    else:
                        offer["label"] = {"en": line}
            elif source_options and not localized:
                offers = translate_offers(offers, translate)
            material = written.get("material")
            if not isinstance(material, dict):
                material = listing.get("material") or ""
                if material and has_cjk(material) and not localized:
                    try:
                        material = translate_fields({"material": material}, translate)["material"]
                    except Exception:
                        material = ""
            specs = {"material": material, "size": listing.get("size") or "", "weight": listing.get("weight") or ""}
            return names, {lang: [] for lang in names}, description, specs, offers, localized
        names, bullets, description, specs = translated_copy(listing, translate)
        return names, bullets, description, specs, translate_offers(offers, translate), False

    def publish_row(row, translate, judge=True):
        listing = load_object(row["listing"])
        if listing.get("hold"):
            return False
        try:
            held_offers = json.loads(row["offers"] or "[]")
        except json.JSONDecodeError:
            held_offers = []
        if held_offers and not any(
            isinstance(offer, dict) and offer.get("id") and not offer.get("hold")
            for offer in held_offers
        ):
            return False
        if not listing.get("title"):
            source = load_object(row["source_zh"])
            listing["title"] = source.get("name") or source.get("title") or ""
            listing["description"] = listing.get("description") or source.get("description") or ""
        if not listing.get("title"):
            return False
        try:
            offers = json.loads(row["offers"] or "[]")
        except json.JSONDecodeError:
            offers = []
        names, bullets, description, specs, offers, localized = compose_copy(listing, offers, translate)
        saved = _save_copy(row["sku"], listing, names, bullets, description, specs, offers)
        if app.state.writer is not None and names.get("en") and not localized:
            try:
                filled = fill_from_english(
                    {"title": names["en"], "description": description.get("en") or names["en"]},
                    translate,
                )
                _save_copy(row["sku"], listing, filled["title"], bullets, filled["description"], specs, offers)
            except Exception:
                pass
        if judge:
            _remember_markets(row["sku"], listing)
        return saved

    def _remember_batch(skus):
        ensure_ai()
        if app.state.complete is None or not skus:
            return
        pending = []
        for start in range(0, len(skus), 400):
            chunk = skus[start:start + 400]
            marks = ",".join("?" for _ in chunk)
            for row in conn.execute(
                f"select sku, listing, markets, markets_lock, published from products where sku in ({marks})",
                chunk,
            ).fetchall():
                if int(row["markets_lock"] or 0) or str(row["markets"] or "").strip():
                    continue
                if not int(row["published"] or 0):
                    continue
                title = str(load_object(row["listing"]).get("title") or "").strip()
                if title:
                    pending.append({"sku": row["sku"], "title": title})
        for start in range(0, len(pending), 200):
            piece = pending[start:start + 200]
            try:
                found = judge_batch(piece, app.state.complete)
            except Exception:
                continue
            for sku, flags in found.items():
                conn.execute(
                    """
                    update products set markets = ?
                    where sku = ? and trim(markets) = '' and markets_lock = 0
                    """,
                    (json.dumps(flags, ensure_ascii=False), sku),
                )

    def _remember_markets(sku, listing):
        current = conn.execute(
            "select markets, markets_lock from products where sku = ?",
            (sku,),
        ).fetchone()
        if current is None:
            return
        if int(current["markets_lock"] or 0) or str(current["markets"] or "").strip():
            return
        ensure_ai()
        if app.state.complete is None:
            return
        title = str(listing.get("title") or "").strip()
        if not title:
            return
        try:
            judged = judge_one(sku, title, listing.get("description") or "", app.state.complete)
        except Exception:
            return
        if not judged:
            return
        conn.execute(
            "update products set markets = ? where sku = ?",
            (json.dumps(judged, ensure_ascii=False), sku),
        )

    def _save_copy(sku, listing, names, bullets, description, specs, offers):
        conn.execute(
            """
            update products
            set names = ?, bullets = ?, description = ?, specs = ?, published = 1, listing = ?, offers = ?
            where sku = ?
            """,
            (
                json.dumps(names, ensure_ascii=False),
                json.dumps(bullets, ensure_ascii=False),
                json.dumps(description, ensure_ascii=False),
                json.dumps(specs, ensure_ascii=False),
                json.dumps(listing, ensure_ascii=False),
                json.dumps(offers, ensure_ascii=False),
                sku,
            ),
        )
        return True

    def admin_product_counts():
        """Counts for the import tab. SQL only — opening the page must not parse every listing."""
        total = int(conn.execute("select count(*) from products").fetchone()[0] or 0)
        row = conn.execute(
            """
            select
              sum(case
                when json_valid(listing)
                 and trim(ifnull(json_extract(listing, '$.hold'), '')) != ''
                then 1 else 0 end),
              sum(case
                when not json_valid(listing)
                  or trim(ifnull(json_extract(listing, '$.hold'), '')) = ''
                then 1 else 0 end)
            from products
            where ifnull(published, 0) = 0
            """
        ).fetchone()
        held_intercept = int(row[0] or 0)
        wait_translate = int(row[1] or 0)
        return {
            "total": total,
            "wait_translate": wait_translate,
            "held_intercept": held_intercept,
            "held": wait_translate + held_intercept,
        }

    def admin_product_list(q="", page=1, page_size=50):
        products = []
        needle = str(q or "").strip()
        try:
            page = max(1, int(page or 1))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(page_size or 50)
        except (TypeError, ValueError):
            page_size = 50
        if page_size not in (20, 50, 100, 200):
            page_size = 50
        where = ""
        params: list = []
        if needle:
            like = f"%{needle}%"
            where = (
                " where sku like ?"
                " or ifnull(listing, '') like ?"
                " or ifnull(source_zh, '') like ?"
                " or ifnull(names, '') like ?"
            )
            params = [like, like, like, like]
        total_matching = conn.execute(
            f"select count(*) from products{where}", params
        ).fetchone()[0]
        offset = (page - 1) * page_size
        if offset >= total_matching and total_matching:
            page = max(1, (total_matching + page_size - 1) // page_size)
            offset = (page - 1) * page_size
        rows = conn.execute(
            f"select * from products{where} order by rowid desc limit ? offset ?",
            [*params, page_size, offset],
        ).fetchall()
        for row in rows:
            listing = load_object(row["listing"])
            source = load_object(row["source_zh"])
            names = load_object(row["names"])
            source_title = listing.get("title") or source.get("name") or ""
            english = str(names.get("en") or "").strip()
            title = english if english and not has_cjk(english) else (source_title or english or row["sku"])
            params = []
            amount = listing.get("amount")
            if amount:
                if isinstance(amount, float) and amount.is_integer():
                    amount = int(amount)
                unit = "人民币" if listing.get("money") == "CNY" else "美元"
                params.append(("供货价", f"{amount} {unit}"))
            seen = set()
            for key, label in _PARAMS:
                value = listing.get(key) or ""
                if value == "":
                    continue
                params.append((label, value))
                seen.add(label)
            for attr in listing.get("attributes") or []:
                if attr.get("name") not in seen and attr.get("value"):
                    params.append((attr["name"], attr["value"]))
            try:
                offers = json.loads(row["offers"] or "[]")
            except json.JSONDecodeError:
                offers = []
            products.append({
                "sku": row["sku"],
                "title": title,
                "source_title": source_title if source_title and source_title != title else "",
                "category": listing.get("category_name") or _CATEGORY_ZH.get(row["category"], row["category"]),
                "cargo": listing.get("cargo") or "—",
                "price_cents": row["price_cents"],
                "original_cents": int(row["original_cents"] or 0),
                "offers": [
                    {
                        "code": offer.get("code") or "",
                        "source_label": offer.get("source_label") or "",
                        "label": (
                            offer.get("label", {}).get("en")
                            if isinstance(offer.get("label"), dict) and offer.get("label", {}).get("en") and not has_cjk(offer.get("label", {}).get("en"))
                            else offer.get("source_label") or "默认"
                        ),
                        "source_cents": int(offer.get("source_cents") or 0),
                        "price_cents": int(offer.get("price_cents") or 0),
                        "original_cents": int(offer.get("original_cents") or 0),
                        "hold": bool(offer.get("hold")),
                    }
                    for offer in offers
                ],
                "stock": row["stock"],
                "image": row["image_url"] or "",
                "published": int(row["published"] or 0),
                "hold": listing.get("hold") or "",
                "uploaded": row["uploaded_at"] or "",
                "gen_at": str(row["gen_at"] or "") if "gen_at" in row.keys() else "",
                "params": params,
            })
        pages = max(1, (total_matching + page_size - 1) // page_size) if total_matching else 1
        return {
            "items": products,
            "q": needle,
            "page": page,
            "page_size": page_size,
            "total_matching": int(total_matching),
            "pages": pages,
            "has_prev": page > 1,
            "has_next": page < pages,
        }

    def ai_form():
        key = setting("ai_key")
        return {
            "model": setting("ai_model") or "auto",
            "base": setting("ai_base") or "https://api.cursor.com",
            "saved": bool(key),
            "tail": key[-4:] if len(key) >= 4 else "",
        }

    def product_page(request, status_code=200, import_error="", image_error="", gen_error="", section=None):
        section = str(section or request.query_params.get("section") or "catalog").strip().lower()
        if section not in {"catalog", "import", "pricing"}:
            section = "catalog"
        q = str(request.query_params.get("q") or "").strip()
        page = request.query_params.get("page") or 1
        page_size = request.query_params.get("page_size") or 50
        # Catalog list is paginated/filtered; import badges use a light full-table count.
        counts = admin_product_counts()
        wait_translate = counts["wait_translate"]
        held_intercept = counts["held_intercept"]
        held = counts["held"]
        catalog = admin_product_list(q=q, page=page, page_size=page_size) if section == "catalog" else {
            "items": [],
            "q": q,
            "page": 1,
            "page_size": 50,
            "total_matching": 0,
            "pages": 1,
            "has_prev": False,
            "has_next": False,
        }
        # batch held from current weight preview queue (analysis packages), if any
        preview = load_catalog_preview()
        batch_held = int((preview or {}).get("held") or 0) if isinstance(preview, dict) else 0
        batch_passed = int((preview or {}).get("passed") or 0) if isinstance(preview, dict) else 0
        return render(
            request,
            "admin.html",
            status_code=status_code,
            panel="products",
            products=catalog["items"],
            product_section=section,
            product_q=catalog["q"],
            product_page_num=catalog["page"],
            product_page_size=catalog["page_size"],
            product_total_matching=catalog["total_matching"],
            product_total_all=counts["total"],
            product_pages=catalog["pages"],
            product_has_prev=catalog["has_prev"],
            product_has_next=catalog["has_next"],
            held=held,
            held_intercept=held_intercept,
            wait_translate=wait_translate,
            batch_held=batch_held,
            batch_passed=batch_passed,
            import_error=import_error,
            image_error=image_error,
            image_left=remaining_images(),
            story_products=getattr(app.state, "story_products_left", 0),
            gen_error=gen_error,
            gen_left=gen_remaining_count(),
            ai=ai_form(),
            pricing=pricing_form(),
            weight_preview=preview,
            last_upload=load_last_upload(),
            upload_history=load_upload_history(),
        )

    def load_gen_links():
        raw = setting("gen_links")
        try:
            saved = json.loads(raw) if raw else []
        except json.JSONDecodeError:
            saved = []
        links = []
        if not isinstance(saved, list):
            return links
        for item in saved[:8]:
            if not isinstance(item, dict):
                continue
            links.append(
                {
                    "url": str(item.get("url") or "").strip(),
                    "host": str(item.get("host") or "").strip(),
                    "port": str(item.get("port") or "41125").strip() or "41125",
                    "user": str(item.get("user") or "root").strip() or "root",
                    "password": str(item.get("password") or ""),
                    "ok": bool(item.get("ok")),
                    "detail": str(item.get("detail") or ""),
                }
            )
        return links

    def save_gen_links(links):
        conn.execute(
            "insert into settings (key, value) values ('gen_links', ?) on conflict(key) do update set value = excluded.value",
            (json.dumps(links, ensure_ascii=False),),
        )
        urls = [item["url"] for item in links if item.get("ok") and item.get("url")]
        conn.execute(
            "insert into settings (key, value) values ('gen_workers', ?) on conflict(key) do update set value = excluded.value",
            (json.dumps(urls),),
        )

    def gen_worker_form():
        shown = []
        for item in load_gen_links():
            host, port, user = parse_ssh(item["host"], item["port"], item["user"])
            shown.append(
                {
                    "url": item["url"],
                    "host": host,
                    "port": port,
                    "user": user,
                    "has_password": bool(item["password"]),
                    "ok": item["ok"],
                    "detail": item["detail"],
                }
            )
        if not shown:
            raw = setting("gen_workers")
            try:
                saved_urls = json.loads(raw) if raw else []
            except json.JSONDecodeError:
                saved_urls = []
            if isinstance(saved_urls, list):
                for saved_url in saved_urls:
                    text = str(saved_url or "").strip()
                    if not text:
                        continue
                    host = "connect.westb.seetacloud.com" if "westb.seetacloud.com" in text else ""
                    shown.append(
                        {
                            "url": text,
                            "host": host,
                            "port": "41125",
                            "user": "root",
                            "has_password": False,
                            "ok": False,
                            "detail": "还没连上。补上 SSH 密码后再点连接。",
                        }
                    )
        if not shown:
            shown.append(
                {
                    "url": "",
                    "host": "",
                    "port": "41125",
                    "user": "root",
                    "has_password": False,
                    "ok": False,
                    "detail": "",
                }
            )
        token = setting("gen_token")
        return {
            "urls": [item["url"] for item in shown if item["ok"] and item["url"]],
            "links": shown,
            "saved": bool(token),
            "tail": token[-4:] if len(token) >= 4 else "",
        }

    def gen_ready_or_error():
        if app.state.gen_editors is not None:
            return ""
        if gen_api_account()["saved"]:
            return ""
        if gen_worker_form()["urls"]:
            return ""
        return "先保存生图 API 密钥，或连上至少一张显卡。"

    def gen_editors():
        if app.state.gen_editors is not None:
            return list(app.state.gen_editors)
        api = gen_api_account()
        if api["saved"]:
            return [
                ApiEditor(api["url"], setting("gen_api_key"), api["model"], name="api-%s" % (index + 1))
                for index in range(api["workers"])
            ]
        form = gen_worker_form()
        token = setting("gen_token")
        return [HttpEditor(url, token) for url in form["urls"] if url]

    def gen_remaining_count():
        # Page label only. The real queue is built when a gen job starts.
        row = conn.execute(
            """
            select count(*) from products
            where trim(ifnull(gen_at, '')) = ''
              and ifnull(image_url, '') like '/static/catalog/%'
            """
        ).fetchone()
        return int(row[0] or 0)

    def gen_backup_root():
        if db_path and db_path != ":memory:":
            return Path(db_path).resolve().parent / "gen-backup"
        return Path(tempfile.mkdtemp(prefix="harbor-gen-"))

    def editor_key(editor):
        return str(getattr(editor, "url", "") or getattr(editor, "name", "") or "")

    def stop_gen_pool():
        for slot in list(app.state.gen_pool.values()):
            slot["stop"].set()
        app.state.gen_pool.clear()

    def consume(editor, stop, key):
        if stop.is_set() or gen_is_paused() or not app.state.gen_armed:
            return False
        sku = claim_task(conn, key)
        if not sku:
            return False
        try:
            generate_product(conn, ROOT, sku, editor, gen_backup_root(), workers=1)
            finish_task(conn, sku, True)
            forget_catalog()
        except GenError as exc:
            finish_task(conn, sku, "不会再跑" in str(exc), str(exc))
        except Exception:
            finish_task(conn, sku, False, "这件商品没有出成。")
        return True

    def worker_loop(editor, stop, key):
        while consume(editor, stop, key):
            pass

    def supervise():
        while True:
            if gen_is_paused() or not app.state.gen_armed:
                stop_gen_pool()
                time.sleep(0.4)
                continue
            wanted = max(1, min(MAX_GEN_API_WORKERS, gen_api_account()["workers"]))
            alive = {}
            for name, slot in list(app.state.gen_pool.items()):
                if slot["thread"].is_alive():
                    alive[name] = slot
                else:
                    slot["stop"].set()
            app.state.gen_pool = alive
            pending = conn.execute(
                "select 1 from gen_tasks where status = 'pending' limit 1"
            ).fetchone()
            editors = gen_editors() if pending else []
            if pending and editors:
                index = 0
                while len(app.state.gen_pool) < wanted:
                    name = "w%s" % index
                    index += 1
                    if name in app.state.gen_pool:
                        continue
                    stop = threading.Event()
                    editor = editors[len(app.state.gen_pool) % len(editors)]
                    thread = threading.Thread(
                        target=worker_loop, args=(editor, stop, name), daemon=True
                    )
                    app.state.gen_pool[name] = {"stop": stop, "thread": thread}
                    thread.start()
            time.sleep(0.4)

    def ensure_supervisor():
        if app.state.gen_supervisor_started:
            return
        app.state.gen_supervisor_started = True
        app.state.gen_pool = {}
        threading.Thread(target=supervise, daemon=True).start()

    app.state.gen_supervisor_started = False
    app.state.gen_pool = {}
    app.state.gen_armed = not gen_is_paused()
    app.state.gen_queue_snapshot = None
    release_abandoned(conn)
    ensure_supervisor()

    def stop_sku_gen_pool():
        for slot in list(app.state.sku_gen_pool.values()):
            slot["stop"].set()
        app.state.sku_gen_pool.clear()

    def consume_sku(editor, stop, key):
        if stop.is_set() or gen_is_paused() or not app.state.sku_gen_armed:
            return False
        task = claim_sku_task(conn, key)
        if not task:
            return False
        task_id = task["id"]
        try:
            generate_one_sku_shot(
                conn,
                ROOT,
                task["product_sku"],
                task["image"],
                editor,
                gen_backup_root(),
            )
            finish_sku_task(conn, task_id, True)
            forget_catalog()
        except GenError as exc:
            finish_sku_task(
                conn,
                task_id,
                "不会再跑" in str(exc) or "没有要出的规格图" in str(exc),
                str(exc),
            )
        except Exception:
            finish_sku_task(conn, task_id, False, "这张规格图没有出成。")
        return True

    def sku_worker_loop(editor, stop, key):
        while consume_sku(editor, stop, key):
            pass

    def supervise_sku():
        while True:
            if gen_is_paused() or not app.state.sku_gen_armed:
                stop_sku_gen_pool()
                time.sleep(0.4)
                continue
            wanted = max(1, min(MAX_GEN_API_WORKERS, gen_api_account()["workers"]))
            alive = {}
            for name, slot in list(app.state.sku_gen_pool.items()):
                if slot["thread"].is_alive():
                    alive[name] = slot
                else:
                    slot["stop"].set()
            app.state.sku_gen_pool = alive
            pending = conn.execute(
                "select 1 from sku_gen_tasks where status = 'pending' limit 1"
            ).fetchone()
            editors = gen_editors() if pending else []
            if pending and editors:
                index = 0
                while len(app.state.sku_gen_pool) < wanted:
                    name = "s%s" % index
                    index += 1
                    if name in app.state.sku_gen_pool:
                        continue
                    stop = threading.Event()
                    editor = editors[len(app.state.sku_gen_pool) % len(editors)]
                    thread = threading.Thread(
                        target=sku_worker_loop, args=(editor, stop, name), daemon=True
                    )
                    app.state.sku_gen_pool[name] = {"stop": stop, "thread": thread}
                    thread.start()
            time.sleep(0.4)

    def ensure_sku_supervisor():
        if app.state.sku_gen_supervisor_started:
            return
        app.state.sku_gen_supervisor_started = True
        app.state.sku_gen_pool = {}
        threading.Thread(target=supervise_sku, daemon=True).start()

    app.state.sku_gen_supervisor_started = False
    app.state.sku_gen_pool = {}
    app.state.sku_gen_armed = not gen_is_paused()
    app.state.sku_gen_queue_snapshot = None
    release_abandoned_sku(conn)
    ensure_sku_supervisor()

    def images_page(request, status_code=200, image_error="", gen_error="", gen_plan=None):
        try:
            gpage = int(request.query_params.get("gpage") or 1)
        except (TypeError, ValueError):
            gpage = 1
        try:
            qpage = int(request.query_params.get("qpage") or 1)
        except (TypeError, ValueError):
            qpage = 1
        try:
            spage = int(request.query_params.get("spage") or 1)
        except (TypeError, ValueError):
            spage = 1
        return render(
            request,
            "admin.html",
            status_code=status_code,
            panel="images",
            image_error=image_error,
            gen_error=gen_error,
            image_left=remaining_images(),
            story_products=getattr(app.state, "story_products_left", 0),
            gen_left=gen_remaining_count(),
            gen_compare=gen_compare(gpage),
            gen_queue=gen_queue_view(qpage),
            gen_plan=gen_plan,
            sku_gen_left=sku_gen_remaining_count(),
            sku_gen_queue=sku_gen_queue_view(spage),
            sku_gen_plan=getattr(request.state, "sku_gen_plan", None),
            sku_gen_job=sku_gen_job_read(),
        )

    def gen_queue_view(page):
        snapshot = app.state.gen_queue_snapshot
        if snapshot is None:
            path = None
            if db_path and db_path != ":memory:":
                path = Path(db_path).resolve().parent / "gen-queue-plan.json"
            if path is not None and path.is_file():
                snapshot = json.loads(path.read_text(encoding="utf-8"))
            else:
                snapshot = plan_queue(conn)
            app.state.gen_queue_snapshot = snapshot
        pending = {
            row["sku"]
            for row in conn.execute("select sku from gen_tasks where status = 'pending'").fetchall()
        }
        items = [item for item in snapshot.get("items") or [] if item.get("sku") in pending]
        size = 10
        page = max(1, int(page or 1))
        pages = max(1, (len(items) + size - 1) // size) if items else 1
        if page > pages:
            page = pages
        calling = sum(1 for item in items if item.get("generate"))
        shots = sum(int(item.get("generate") or 0) for item in items)
        start = (page - 1) * size
        return {
            "pending": len(items),
            "calling": calling,
            "shots": shots,
            "idle": len(items) - calling,
            "page": page,
            "pages": pages,
            "items": items[start:start + size],
        }


    def sku_gen_remaining_count():
        """待出规格图张数（已上架、c*/s*、文件在、未 generated）。"""
        cached = getattr(app.state, "sku_gen_left_cache", None)
        now = time.time()
        if cached and now - cached.get("at", 0) < 30:
            return int(cached["n"])
        n = count_pending_sku_shots(conn, root=ROOT, force=False)
        app.state.sku_gen_left_cache = {"at": now, "n": n}
        return n

    def sku_gen_queue_view(page):
        snapshot = app.state.sku_gen_queue_snapshot
        if snapshot is None:
            snapshot = plan_sku_queue(conn)
            app.state.sku_gen_queue_snapshot = snapshot
        pending = {
            row["id"]
            for row in conn.execute("select id from sku_gen_tasks where status = 'pending'").fetchall()
        }
        items = [item for item in snapshot.get("items") or [] if item.get("id") in pending]
        size = 10
        page = max(1, int(page or 1))
        pages = max(1, (len(items) + size - 1) // size) if items else 1
        if page > pages:
            page = pages
        calling = sum(1 for item in items if item.get("generate"))
        shots = sum(int(item.get("generate") or 0) for item in items)
        start = (page - 1) * size
        return {
            "pending": len(items),
            "calling": calling,
            "shots": shots,
            "idle": len(items) - calling,
            "page": page,
            "pages": pages,
            "items": items[start:start + size],
        }

    def sku_gen_job_read():
        progress = sku_task_progress(conn)
        return {
            "running": progress["running"] and app.state.sku_gen_armed and not gen_is_paused(),
            "label": progress.get("label") or "",
            "total": progress.get("total") or 0,
            "pending": progress.get("pending") or 0,
            "active": progress.get("active") or 0,
            "error": progress.get("error") or "",
            "result": progress.get("result") or {"done": 0, "failed": 0},
        }

    def gen_compare(page):
        size = 10
        page = max(1, int(page or 1))
        total = conn.execute(
            "select count(*) from gen_tasks where status in ('running', 'done', 'failed')"
        ).fetchone()[0]
        pages = max(1, (int(total) + size - 1) // size) if total else 1
        if page > pages:
            page = pages
        rows = conn.execute(
            """
            select t.sku, t.status, t.error, t.touched, p.image_url
            from gen_tasks t
            left join products p on p.sku = t.sku
            where t.status in ('running', 'done', 'failed')
            order by case t.status when 'running' then 0 when 'failed' then 1 else 2 end,
                     t.touched desc, t.rowid desc
            limit ? offset ?
            """,
            (size, (page - 1) * size),
        ).fetchall()
        backup = gen_backup_root()
        items = []
        for row in rows:
            sku = str(row["sku"] or "")
            current = str(row["image_url"] or "")
            fourth = ROOT / "static" / "catalog" / sku / "en" / "main" / "4.jpg"
            stamp = int(fourth.stat().st_mtime) if fourth.is_file() else int(row["touched"] or 0)
            after = ""
            before = current
            fresh = False
            if fourth.is_file():
                after = "/static/catalog/%s/en/main/4.jpg" % sku
                fresh = True
            else:
                main_name = Path(current.split("?", 1)[0]).name
                if current and _gen_before_file(backup, sku, main_name) is not None:
                    before = "/admin/images/gen/before/" + sku
                    after = current
                    fresh = True
            if after and stamp:
                after = after + ("&" if "?" in after else "?") + "g=" + str(stamp)
            items.append({
                "sku": sku,
                "status": row["status"],
                "error": row["error"] or "",
                "before": before,
                "after": after,
                "fresh": fresh,
            })
        return {"items": items, "page": page, "pages": pages, "total": int(total)}

    def _gen_before_file(backup, sku, name=""):
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", sku or ""):
            return None
        folder = Path(backup) / sku
        if not folder.is_dir():
            return None
        wanted = Path(str(name or "")).name
        if wanted and re.fullmatch(r"[A-Za-z0-9._-]{1,80}", wanted):
            picked = folder / wanted
            if picked.is_file() and picked.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                return picked
        return None

    @app.get("/admin/products", response_class=HTMLResponse)
    def admin_products(request: Request):
        require_admin(request)
        return product_page(request)

    @app.get("/admin/images", response_class=HTMLResponse)
    def admin_images(request: Request):
        require_admin(request)
        return images_page(request)

    def dollars_to_cents(value, allow_zero=False):
        try:
            return int((Decimal(str(value or "0")) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        except Exception:
            return 0 if allow_zero else 0

    def product_editor(row):
        listing = load_object(row["listing"])
        source = load_object(row["source_zh"])
        names = load_object(row["names"])
        specs = load_object(row["specs"])
        stored_description = load_object(row["description"])
        try:
            offers = json.loads(row["offers"] or "[]")
        except json.JSONDecodeError:
            offers = []

        def spec_text(key):
            value = specs.get(key) or listing.get(key) or ""
            if isinstance(value, dict):
                return value.get("en") or ""
            return value

        return {
            "sku": row["sku"],
            "title": listing.get("title") or source.get("name") or names.get("en") or "",
            "store_title": names.get("en") or "",
            "description": listing.get("description") or source.get("description") or stored_description.get("en") or "",
            "category": row["category"],
            "subcategory": row["subcategory"] if "subcategory" in row.keys() else "",
            "departments": [(key, ZH[key]) for key in CATEGORIES],
            "sub_tree": {
                key: [(slug, labels_for("zh").get(slug, slug)) for slug in slugs]
                for key, slugs in CHILDREN.items()
            },
            "stock": row["stock"],
            "price_cents": row["price_cents"],
            "original_cents": int(row["original_cents"] or 0),
            "cargo": listing.get("cargo") or "",
            "offer_id": listing.get("offer_id") or "",
            "url": supplier_link(listing),
            "material": spec_text("material"),
            "size": spec_text("size"),
            "weight": spec_text("weight"),
            "published": int(row["published"] or 0),
            "offers": offers,
            "image": (row["image_url"] or "") or f"/static/products/{row['sku']}.svg",
            "detail_images": stored_detail_images(row["listing"]),
        }

    @app.get("/admin/products/{sku}", response_class=HTMLResponse)
    def admin_product_edit(request: Request, sku: str):
        require_admin(request)
        row = conn.execute("select * from products where sku = ?", (sku,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404)
        return render(request, "admin.html", panel="product", product=product_editor(row))

    @app.post("/admin/products/{sku}/save")
    async def admin_product_save(request: Request, sku: str):
        require_admin(request)
        row = conn.execute("select * from products where sku = ?", (sku,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404)
        form = await request.form()
        listing = load_object(row["listing"])
        specs = load_object(row["specs"])
        category = str(form.get("category") or row["category"])
        if category not in CATEGORIES:
            category = row["category"]
        subcategory = str(form.get("subcategory") or "")
        if not known(category, subcategory):
            subcategory = ""
        listing["title"] = str(form.get("title") or "").strip()
        if "description" in form:
            listing["description"] = str(form.get("description") or "").strip()
        kept = []
        for value in form.getlist("detail_keep"):
            path = str(value or "")
            if path.startswith("/static/catalog/") and path not in kept:
                kept.append(path)
        for index, url in enumerate(detail_image_urls(str(form.get("detail_urls") or ""))):
            saved = pull(url, sku, f"d{len(kept) + index}")
            if saved and saved not in kept:
                kept.append(saved)
        listing["detail_images"] = kept
        listing["cargo"] = str(form.get("cargo") or "").strip()
        listing["offer_id"] = str(form.get("offer_id") or "").strip()
        listing["url"] = str(form.get("url") or "").strip()
        listing["material"] = str(form.get("material") or "").strip()
        listing["size"] = str(form.get("size") or "").strip()
        listing["weight"] = str(form.get("weight") or "").strip()
        for key in ("material", "size", "weight"):
            current = specs.get(key)
            incoming = listing[key]
            if isinstance(current, dict):
                current["en"] = incoming
                specs[key] = current
            else:
                specs[key] = incoming
        try:
            offers = json.loads(row["offers"] or "[]")
        except json.JSONDecodeError:
            offers = []
        for offer in offers:
            offer_id = offer.get("id") or ""
            if form.get(f"sale_{offer_id}") not in (None, ""):
                offer["price_cents"] = dollars_to_cents(form.get(f"sale_{offer_id}"))
            if form.get(f"original_{offer_id}") not in (None, ""):
                offer["original_cents"] = dollars_to_cents(form.get(f"original_{offer_id}"))
            label = str(form.get(f"label_{offer_id}") or "").strip()
            if label:
                offer["source_label"] = label
        if offers:
            chosen = min(offers, key=lambda offer: int(offer.get("price_cents") or 0))
            price_cents = int(chosen.get("price_cents") or 0)
            original_cents = int(chosen.get("original_cents") or 0)
        else:
            price_cents = dollars_to_cents(form.get("price"))
            original_cents = dollars_to_cents(form.get("original"))
        try:
            stock = int(form.get("stock") or row["stock"] or 0)
        except ValueError:
            stock = row["stock"]
        source = json.dumps(
            {"name": listing["title"], "description": listing["description"], "bullets": []},
            ensure_ascii=False,
        )
        conn.execute(
            """
            update products
            set category = ?, subcategory = ?, price_cents = ?, original_cents = ?, stock = ?, specs = ?,
                source_zh = ?, listing = ?, offers = ?
            where sku = ?
            """,
            (
                category,
                subcategory,
                price_cents,
                original_cents,
                stock,
                json.dumps(specs, ensure_ascii=False),
                source,
                json.dumps(listing, ensure_ascii=False),
                json.dumps(offers, ensure_ascii=False),
                sku,
            ),
        )
        forget_catalog()
        return RedirectResponse(f"/admin/products/{sku}", status_code=303)

    def sale_source(code):
        parent, _, offer_id = str(code or "").partition("~")
        product = conn.execute("select * from products where sku = ?", (parent,)).fetchone()
        found = {
            "sku": code,
            "item_code": offer_id or parent or code,
            "title_zh": "",
            "spec_zh": "",
            "title_en": "",
            "cargo": "—",
            "offer_id": "—",
            "url": "",
            "cost": 0,
        }
        if product is None:
            return found
        listing = load_object(product["listing"])
        source = load_object(product["source_zh"])
        names = load_object(product["names"])
        try:
            offers = json.loads(product["offers"] or "[]")
        except json.JSONDecodeError:
            offers = []
        offer = next((item for item in offers if str(item.get("id") or "") == offer_id), None) if offer_id else None
        if offer is None and len(offers) == 1:
            offer = offers[0]
        found["title_zh"] = listing.get("title") or source.get("name") or ""
        found["spec_zh"] = (offer or {}).get("source_label") or ""
        found["title_en"] = str(names.get("en") or "")
        found["item_code"] = (offer or {}).get("code") or offer_id or listing.get("cargo") or parent
        found["cargo"] = listing.get("cargo") or "—"
        found["offer_id"] = listing.get("offer_id") or "—"
        found["url"] = supplier_link(listing)
        found["cost"] = int((offer or {}).get("source_cents") or 0)
        return found

    def purchase_rows():
        lines = conn.execute(
            """
            select ol.sku, ol.qty, ol.order_id, o.status
            from order_lines ol
            join orders o on o.id = ol.order_id
            where ol.bought = 0 and o.status in ('pending', 'paid')
            order by ol.order_id
            """
        ).fetchall()
        grouped = {}
        for line in lines:
            bucket = grouped.setdefault(line["sku"], {"qty": 0, "orders": [], "status": set()})
            bucket["qty"] += line["qty"]
            bucket["orders"].append(str(line["order_id"]))
            bucket["status"].add(line["status"])
        rows = []
        for code, bucket in grouped.items():
            identity = sale_source(code)
            rows.append({
                **identity,
                "title": identity["title_zh"] or identity["title_en"] or code.partition("~")[0],
                "spec": identity["spec_zh"] or "—",
                "qty": bucket["qty"],
                "orders": "、".join(bucket["orders"]),
            })
        return rows

    @app.get("/admin/purchasing", response_class=HTMLResponse)
    def admin_purchasing(request: Request):
        require_admin(request)
        return render(request, "admin.html", panel="purchasing", purchases=purchase_rows())

    @app.post("/admin/purchasing/bought")
    async def admin_purchasing_bought(request: Request):
        require_staff(request)
        form = await request.form()
        codes = [str(x) for x in form.getlist("sku") if str(x).strip()]
        single = str(form.get("sku") or "").strip()
        if single and single not in codes:
            codes.append(single)
        for code in codes:
            conn.execute(
                """
                update order_lines
                set bought = 1
                where sku = ? and order_id in (select id from orders where status in ('pending', 'paid'))
                """,
                (code,),
            )
        return flash_redirect("/admin/purchasing", "purchased")



    @app.get("/api/catalog/interest/{sku:path}")
    def catalog_interest(request: Request, sku: str):
        parent = str(sku or "").split("~", 1)[0][:80]
        if not parent or "/" in parent:
            return JSONResponse({"sku": "", "count": 0}, status_code=404)
        vid = (getattr(request.state, "visitor", None) or request.cookies.get("harbor_vid") or "").strip()
        try:
            picked = country_for(request)
            lang, _currency = resolve(picked)
            if vid:
                record(conn, "product", sku=parent, country=picked, lang=lang, visitor=vid)
        except Exception:
            pass
        return {"sku": parent, "count": product_interest_count(conn, parent)}


    @app.get("/api/ad/deal")
    def ad_deal_click(request: Request, sku: str = "", to: str = ""):
        attrs = getattr(request.state, "ad_attrs", None) or parse_ad_cookie(
            request.cookies.get("harbor_ad")
        )
        sku = (sku or "").strip()
        try:
            record_funnel(
                conn,
                "deal_click",
                seg=attrs.get("seg") or request.query_params.get("seg") or "",
                utm_source=attrs.get("utm_source") or "",
                utm_campaign=attrs.get("utm_campaign") or "",
                sku=sku,
                visitor=(getattr(request.state, "visitor", None) or request.cookies.get("harbor_vid") or ""),
                acct=attrs.get("acct") or request.query_params.get("acct") or "",
            )
        except Exception:
            pass
        country = country_for(request)
        dest = (to or "").strip()
        if not dest.startswith("/"):
            dest = f"/p/{sku}" if sku else "/"
        # preserve country
        join = "&" if "?" in dest else "?"
        if "country=" not in dest:
            dest = f"{dest}{join}country={country}"
        return RedirectResponse(dest, status_code=302)

    def _traffic_redirect(platform: str, acct_code: str = "", notice: str = "") -> RedirectResponse:
        q = f"/admin/traffic?platform={platform}"
        if acct_code:
            q += f"&acct={acct_code}"
        if notice:
            q += f"&notice={notice}"
        return RedirectResponse(q, status_code=303)

    def _traffic_context(request: Request, platform: str = "", acct_code: str = "", notice: str = "", link_preview: str = "", link_fields=None):
        ensure_ad_tables(conn)
        platform = (platform or request.query_params.get("platform") or "meta").strip().lower()
        if platform not in dict(PLATFORMS):
            platform = "meta"
        grouped = accounts_by_platform(conn)
        accounts = grouped.get(platform) or []
        acct_code = (acct_code or request.query_params.get("acct") or "").strip()
        active = None
        if acct_code:
            active = get_account(conn, code=acct_code)
            if active and active.get("platform") != platform:
                active = None
        if active is None and accounts:
            active = next((a for a in accounts if a.get("is_default") and a.get("enabled")), None) or accounts[0]
        masked = {}
        fields = PLATFORM_FIELDS.get(platform) or []
        if active:
            for key, _title, is_secret in fields:
                if is_secret:
                    masked[key] = mask_secret((active.get("credentials") or {}).get(key) or "")
        return {
            "platforms": PLATFORMS,
            "platform": platform,
            "platform_fields": fields,
            "accounts_by_plat": grouped,
            "active_acct": active,
            "ad_masked": masked,
            "ad_logs": recent_ad_logs(conn, 40),
            "ad_funnel": funnel_stats(conn, 14),
            "seg_presets": SEG_PRESETS,
            "notice": notice or str(request.query_params.get("notice") or ""),
            "link_preview": link_preview or "",
            "link_fields": link_fields or {},
        }

    @app.get("/admin/traffic", response_class=HTMLResponse)
    def admin_traffic(request: Request):
        require_admin(request)
        ctx = _traffic_context(request)
        return render(request, "admin_traffic.html", **ctx)

    @app.post("/admin/traffic/account/create")
    async def admin_traffic_account_create(request: Request):
        require_admin_role(request)
        actor = request.state.staff
        form = await request.form()
        platform = str(form.get("platform") or "meta").strip().lower()
        name = str(form.get("name") or "").strip()
        code = str(form.get("code") or "").strip()
        try:
            acct = create_account(conn, platform, name, code)
            return _traffic_redirect(platform, acct.get("code") or "", "created")
        except ValueError as exc:
            notice = "code_taken" if str(exc) == "code_taken" else "error"
            return _traffic_redirect(platform, "", notice)

    @app.post("/admin/traffic/account/save")
    async def admin_traffic_account_save(request: Request):
        require_admin_role(request)
        actor = request.state.staff
        form = await request.form()
        try:
            account_id = int(form.get("account_id") or 0)
        except ValueError:
            account_id = 0
        platform = str(form.get("platform") or "meta").strip().lower()
        acct = get_account(conn, account_id=account_id)
        if not acct:
            return _traffic_redirect(platform, "", "error")
        patch = {}
        for key, _title, _secret in PLATFORM_FIELDS.get(acct["platform"], []):
            if key in form:
                patch[key] = str(form.get(key) or "")
        try:
            ratio = float(str(form.get("send_ratio_pct") or acct["send_ratio_pct"]))
        except ValueError:
            ratio = acct["send_ratio_pct"]
        try:
            mult = float(str(form.get("value_multiplier") or acct["value_multiplier"]))
        except ValueError:
            mult = acct["value_multiplier"]
        enabled = str(form.get("enabled") or "") in {"1", "on", "true", "yes"}
        make_default = str(form.get("make_default") or "") in {"1", "on", "true", "yes"}
        updated = update_account(
            conn,
            account_id,
            name=str(form.get("name") or acct["name"]),
            credentials_patch=patch,
            send_ratio_pct=ratio,
            value_multiplier=mult,
            enabled=enabled,
            make_default=make_default,
        )
        return _traffic_redirect(platform, (updated or acct).get("code") or "", "saved")

    @app.post("/admin/traffic/account/delete")
    async def admin_traffic_account_delete(request: Request):
        require_admin_role(request)
        actor = request.state.staff
        form = await request.form()
        platform = str(form.get("platform") or "meta").strip().lower()
        try:
            account_id = int(form.get("account_id") or 0)
        except ValueError:
            account_id = 0
        delete_account(conn, account_id)
        return _traffic_redirect(platform, "", "deleted")

    @app.post("/admin/traffic/test")
    async def admin_traffic_test(request: Request):
        require_admin(request)
        form = await request.form()
        platform = str(form.get("platform") or "").strip().lower()
        try:
            account_id = int(form.get("account_id") or 0) or None
        except ValueError:
            account_id = None
        acct = get_account(conn, account_id=account_id) if account_id else None
        ok, detail = send_test_event(conn, platform=platform, account_id=account_id)
        notice = "test_ok" if ok else "test_fail"
        return _traffic_redirect(platform or (acct or {}).get("platform") or "meta", (acct or {}).get("code") or "", notice)

    @app.post("/admin/traffic/link")
    async def admin_traffic_link(request: Request):
        require_admin(request)
        form = await request.form()
        platform = str(form.get("platform") or "meta").strip().lower()
        acct_code = str(form.get("acct") or "").strip()
        url = build_creative_url(
            str(form.get("base") or "/lp/ship"),
            country=str(form.get("country") or "US"),
            seg=str(form.get("seg") or ""),
            acct=acct_code,
            utm={
                "utm_source": str(form.get("utm_source") or ""),
                "utm_medium": str(form.get("utm_medium") or ""),
                "utm_campaign": str(form.get("utm_campaign") or ""),
                "utm_content": str(form.get("utm_content") or ""),
                "utm_term": str(form.get("utm_term") or ""),
            },
        )
        preview = "https://linkiip.com" + url if url.startswith("/") else url
        link_fields = {
            "base": str(form.get("base") or "/lp/ship"),
            "country": str(form.get("country") or "US"),
            "seg": str(form.get("seg") or ""),
            "utm_source": str(form.get("utm_source") or ""),
            "utm_medium": str(form.get("utm_medium") or ""),
            "utm_campaign": str(form.get("utm_campaign") or ""),
            "utm_content": str(form.get("utm_content") or ""),
        }
        ctx = _traffic_context(
            request,
            platform=platform,
            acct_code=acct_code,
            notice="link_built",
            link_preview=preview,
            link_fields=link_fields,
        )
        return render(request, "admin_traffic.html", **ctx)

    # legacy save endpoint kept as no-op redirect for old bookmarks
    @app.post("/admin/traffic/save")
    async def admin_traffic_save_legacy(request: Request):
        require_admin(request)
        return RedirectResponse("/admin/traffic?notice=saved", status_code=303)

    def _lp_text(source, key, default=""):
        if source is None:
            return default
        raw = source.get(key)
        if raw is None:
            return default
        text = str(raw).strip()
        return text or default

    def _lp_form_state(source=None):
        platform = _lp_text(source, "platform", "meta") or "meta"
        category = _lp_text(source, "category", "kitchen") or "kitchen"
        return {
            "template": _lp_text(source, "template", "dense_flash") or "dense_flash",
            "category": category,
            "skin": _lp_text(source, "skin", category) or category,
            "platform": platform,
            "utm_source": _lp_text(source, "utm_source", platform) or platform,
            "utm_medium": _lp_text(source, "utm_medium", "paid") or "paid",
            "utm_campaign": _lp_text(source, "utm_campaign"),
            "utm_content": _lp_text(source, "utm_content"),
            "utm_term": _lp_text(source, "utm_term"),
            "acct": _lp_text(source, "acct"),
            "country": (_lp_text(source, "country", "US") or "US").upper()[:2],
            "label": _lp_text(source, "label"),
        }

    def _lp_market(request, ctx, preview):
        """Ad LP language follows the IP country. Preview may pass ?country=.

        Uses the country view() already resolved from the local MMDB. No second
        lookup and no remote geo call. A manual storefront cookie is ignored.
        """
        country = ctx["country"]
        if preview:
            query = str(request.query_params.get("country") or "").strip().upper()[:2]
            if len(query) == 2 and query.isalpha():
                country = query
        lang, currency = resolve(country)
        if lang not in UI:
            lang = "en"
        text = UI.get(lang) or UI["en"]
        market = dict(ctx)
        market["country"] = country
        market["lang"] = lang
        market["currency"] = currency
        market["t"] = text
        market["prefer_zh"] = str(lang).startswith("zh")
        if currency != ctx.get("currency") or country != ctx.get("country"):
            try:
                rate = app.state.book.rate_for(currency, datetime.now(timezone.utc))
                units = rate.units_per_usd
                coef = coefficient_for(conn, country)
                if coef != 1.0:
                    units = float(units) * float(coef)
                market["units"] = units
                market["coefficient"] = coef
            except NoRate:
                market["units"] = None
        return market

    def _lp_cards(request, category, preview):
        ctx = view(request)
        market = _lp_market(request, ctx, preview)
        picked = []
        fallback = []
        for row in catalog_rows():
            if str(row.get("category") or "") != category:
                continue
            if int(row.get("published") or 0) != 1:
                continue
            if int(row.get("stock") or 0) <= 0:
                continue
            cents = int(row.get("price_cents") or 0)
            if IMPULSE_MIN_CENTS <= cents <= IMPULSE_MAX_CENTS:
                picked.append(row)
            else:
                fallback.append(row)
        rows = picked or fallback
        rows.sort(key=lambda row: (int(row.get("price_cents") or 0), str(row.get("sku") or "")))
        cards = []
        country = market["country"]
        for row in rows[:24]:
            card = present_card(row, market)
            sku = card["sku"]
            card["grab_href"] = f"/api/ad/deal?sku={sku}&country={country}&to=/p/{sku}"
            cards.append(card)
        return cards, market

    def _lp_response(request, spec, *, preview=False, code=""):
        cards, ctx = _lp_cards(request, spec["category"], preview)
        bands, overflow = band_groups(cards)
        ends_at, _set_cookie = lp_flash_window(request)
        lp = {
            **spec,
            "ends_at": ends_at,
            "enter_href": href(f"/c/{spec['category']}", ctx["country"]),
            "preview": preview,
            "code": code,
            "product_count": len(cards),
        }
        if not preview:
            try:
                attrs = getattr(request.state, "ad_attrs", None) or {}
                record_funnel(
                    conn,
                    "land",
                    seg=spec["category"],
                    utm_source=attrs.get("utm_source") or request.query_params.get("utm_source") or "",
                    utm_campaign=attrs.get("utm_campaign") or request.query_params.get("utm_campaign") or "",
                    visitor=lp_visitor_seed(request),
                    extra=f"template={spec['template_id']}",
                    acct=attrs.get("acct") or request.query_params.get("acct") or "",
                )
            except Exception:
                pass
        response = render(
            request,
            "lp_ad.html",
            lp=lp,
            cards=cards,
            hero=cards[0] if cards else None,
            rest=cards[1:] if len(cards) > 1 else [],
            bands=bands,
            overflow=overflow,
            lang=ctx["lang"],
            t=ctx["t"],
            prefer_zh=ctx["prefer_zh"],
            seo_title=page_title(ctx["t"]["categories"].get(spec["category"]) or spec["category_en"]),
            seo_description=ctx["t"].get("lp_dense_sub") or "",
            seo_robots="noindex, nofollow",
        )
        if ends_at:
            response.set_cookie(
                "lp_flash_end",
                ends_at,
                max_age=60 * 11,
                path="/",
                samesite="lax",
            )
        return response

    @app.get("/lp/ad/preview", response_class=HTMLResponse)
    def lp_ad_preview(request: Request):
        try:
            spec = resolve_module(
                request.query_params.get("template"),
                request.query_params.get("category"),
                request.query_params.get("skin"),
            )
        except LpChoiceError:
            return render(request, "not_found.html", status_code=404)
        return _lp_response(request, spec, preview=True)

    @app.get("/lp/ad/{code}", response_class=HTMLResponse)
    def lp_ad_saved(request: Request, code: str):
        row = get_lp_link(conn, code)
        if row is None:
            return render(request, "not_found.html", status_code=404)
        try:
            spec = resolve_module(row["template"], row["category"], row["skin"])
        except LpChoiceError:
            return render(request, "not_found.html", status_code=404)
        return _lp_response(request, spec, preview=False, code=row["code"])

    _LP_ERRORS = {
        "template": "请选择有效的落地页模块。",
        "category": "请选择有效的类目。",
        "skin": "请选择有效的皮肤。",
    }

    def _launch_page(request, form_state, notice="", error="", built=None):
        try:
            resolve_module(form_state["template"], form_state["category"], form_state["skin"])
            preview_src = lp_preview_path(
                form_state["template"],
                form_state["category"],
                form_state["skin"],
                form_state["country"],
            )
        except LpChoiceError:
            preview_src = lp_preview_path("dense_flash", "kitchen", "kitchen", "US")
        return render(
            request,
            "admin_launch.html",
            lp_templates=LP_TEMPLATES,
            lp_skins=LP_SKINS,
            form_state=form_state,
            preview_src=preview_src,
            launch_notice=notice,
            launch_error=error,
            built_link=built,
            launch_links=list_lp_links(conn),
        )

    @app.get("/admin/launch", response_class=HTMLResponse)
    def admin_launch(request: Request):
        require_admin(request)
        return _launch_page(request, _lp_form_state())

    @app.post("/admin/launch", response_class=HTMLResponse)
    async def admin_launch_create(request: Request):
        require_admin(request)
        form = await request.form()
        state = _lp_form_state(form)
        try:
            built = create_lp_link(
                conn,
                template=state["template"],
                category=state["category"],
                skin=state["skin"],
                platform=state["platform"],
                utm_source=state["utm_source"],
                utm_medium=state["utm_medium"],
                utm_campaign=state["utm_campaign"],
                utm_content=state["utm_content"],
                utm_term=state["utm_term"],
                acct=state["acct"],
                country=state["country"],
                label=state["label"],
            )
        except LpChoiceError as exc:
            return _launch_page(request, state, error=_LP_ERRORS.get(exc.field, "无法生成链接。"))
        return _launch_page(request, state, notice="built", built=built)

    @app.get("/admin/ads", response_class=HTMLResponse)
    def admin_ads(request: Request):
        require_admin(request)
        ad_rows = conn.execute("select slot, lang, image_url, href, body from ads order by slot, lang").fetchall()
        return render(request, "admin.html", panel="ads", ad_rows=ad_rows)

    def strip_held_offers_from_product(sku, offers, listing, price_cents, original_cents):
        """Apply intercept delete rules to one saved product.

        Returns (action, offers_json, listing_json, price, original, removed_offers)
        action: 'delete_product' | 'strip_offers' | 'noop'
        """
        try:
            offer_list = json.loads(offers or "[]")
        except json.JSONDecodeError:
            offer_list = []
        if not isinstance(offer_list, list):
            offer_list = []
        try:
            listing_obj = json.loads(listing or "{}") if listing else {}
        except json.JSONDecodeError:
            listing_obj = {}
        if not isinstance(listing_obj, dict):
            listing_obj = {}
        before = len(offer_list)
        held_n = sum(1 for o in offer_list if isinstance(o, dict) and o.get("hold"))
        whole_held = bool(str(listing_obj.get("hold") or "").strip())
        draft = {
            "sku": sku,
            "offers": offer_list,
            "listing": listing_obj,
            "price_cents": price_cents,
            "original_cents": original_cents,
        }
        cleaned = apply_intercept_rules(draft)
        if cleaned is None:
            return "delete_product", None, None, None, None, max(held_n, before)
        removed = before - len(cleaned["offers"])
        changed = whole_held or removed > 0 or held_n > 0
        if not changed:
            return "noop", None, None, None, None, 0
        return (
            "strip_offers",
            json.dumps(cleaned["offers"], ensure_ascii=False),
            json.dumps(cleaned["listing"], ensure_ascii=False),
            int(cleaned.get("price_cents") or price_cents or 0),
            int(cleaned.get("original_cents") or original_cents or 0),
            removed,
        )

    def purge_intercepted_products():
        """拦截清理规则（存量与后续一致）：

        - 整件拦截且未上架（listing.hold，或全部规格 hold）：删除整件 + catalog 目录。
        - 仅部分规格拦截：只删这些 SKU/规格，保留商品并重算售价。
        不再把拦截商品挂在「已拦截/未上架」里。
        """
        deleted_products = 0
        stripped_products = 0
        deleted_offers = 0
        to_delete = []
        for row in conn.execute(
            "select sku, published, listing, offers, price_cents, original_cents from products"
        ).fetchall():
            sku = str(row["sku"] or "")
            published = int(row["published"] or 0)
            try:
                listing_obj = json.loads(row["listing"] or "{}") if row["listing"] else {}
            except json.JSONDecodeError:
                listing_obj = {}
            whole_held = bool(str((listing_obj or {}).get("hold") or "").strip())
            action, offers_json, listing_json, price, original, removed = strip_held_offers_from_product(
                sku,
                row["offers"],
                row["listing"],
                row["price_cents"],
                row["original_cents"],
            )
            # 未上架 + 整件拦截标记：无论 offers 残缺与否，整件删除。
            if published == 0 and whole_held:
                to_delete.append(sku)
                deleted_offers += int(removed or 0)
                continue
            if action == "delete_product":
                # 规格全灭：未上架删；已上架异常态也删。
                to_delete.append(sku)
                deleted_offers += int(removed or 0)
                continue
            if action == "strip_offers":
                conn.execute(
                    "update products set offers = ?, listing = ?, price_cents = ?, original_cents = ? where sku = ?",
                    (offers_json, listing_json, price, original, sku),
                )
                stripped_products += 1
                deleted_offers += int(removed or 0)
        if to_delete:
            deleted_products = remove_products(to_delete)
        else:
            forget_catalog()
        return {
            "deleted_products": deleted_products,
            "stripped_products": stripped_products,
            "deleted_offers": deleted_offers,
        }

    def remove_products(skus):
        removed = 0
        for raw in skus:
            sku = str(raw or "").strip()
            if not sku or any(part in sku for part in ("/", "\\", "..")):
                continue
            found = conn.execute("select sku from products where sku = ?", (sku,)).fetchone()
            if found is None:
                continue
            conn.execute("delete from products where sku = ?", (sku,))
            folder = ROOT / "static" / "catalog" / sku
            if folder.is_dir():
                shutil.rmtree(folder)
            removed += 1
        if removed:
            forget_catalog()
        return removed

    @app.post("/admin/catalog/delete")
    async def admin_products_delete(request: Request):
        require_admin_role(request)
        form = await request.form()
        remove_products(form.getlist("sku"))
        return RedirectResponse("/admin/products", status_code=303)

    @app.post("/admin/products/{sku}/delete")
    def admin_product_delete(request: Request, sku: str):
        require_admin(request)
        remove_products([sku])
        return RedirectResponse("/admin/products", status_code=303)

    @app.post("/admin/products/{sku}")
    async def admin_price(request: Request, sku: str):
        require_admin(request)
        form = await request.form()
        if form.get("price_cents") not in (None, ""):
            cents = int(form.get("price_cents") or 0)
        else:
            cents = int((Decimal(str(form.get("price") or "0")) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        conn.execute(
            "update products set price_cents = ? where sku = ?",
            (cents, sku),
        )
        forget_catalog()
        return RedirectResponse("/admin/products", status_code=303)

    @app.post("/admin/products/{sku}/advantages")
    def admin_advantages(request: Request, sku: str):
        require_admin(request)
        if app.state.advantage_model is None:
            raise HTTPException(status_code=400)
        row = conn.execute("select * from products where sku = ?", (sku,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404)
        specs = json.loads(row["specs"])
        names = json.loads(row["names"])

        def english_spec(key):
            value = specs.get(key) or ""
            if isinstance(value, dict):
                return value.get("en") or ""
            return value

        lines = generate_advantages(
            app.state.advantage_model,
            name=names.get("en") or "",
            category=row["category"],
            material=english_spec("material"),
            size=english_spec("size"),
            weight=english_spec("weight"),
        )
        bullets = {lang: lines for lang in UI}
        conn.execute("update products set bullets = ? where sku = ?", (json.dumps(bullets), sku))
        forget_catalog()
        return RedirectResponse(f"/p/{sku}", status_code=303)

    @app.post("/admin/promos")
    async def admin_promo_save(request: Request):
        require_admin_role(request)
        form = await request.form()
        section = str(form.get("section") or "all")
        if section in {"all", "guarantees"}:
            late = dollars_to_cents(form.get("late_credit_dollars"), allow_zero=True)
            try:
                days = int(str(form.get("return_days") or "").strip() or "30")
            except ValueError:
                days = 30
            cmin = dollars_to_cents(form.get("checkout_min_dollars"), allow_zero=True)
            current = load_guarantees(conn)
            if late is not None:
                current["late_delivery_credit_cents"] = int(late)
            current["return_days"] = days
            if cmin is not None:
                current["checkout_min_cents"] = int(cmin)
            save_guarantees(conn, current)
            app.state.memo.pop("guarantees", None)
            if section == "guarantees":
                return RedirectResponse("/admin/promos", status_code=303)
        free = dollars_to_cents(form.get("free_shipping_dollars"), allow_zero=True)
        if free is not None and section in {"all", "free"}:
            conn.execute(
                "update promos set value = ? where key = 'free_shipping_cents'",
                (json.dumps(int(free)),),
            )
        if section in {"all", "tiers"} and (form.getlist("tier_over") or form.getlist("tier_off")):
            tiers = []
            for over, off in zip(form.getlist("tier_over"), form.getlist("tier_off")):
                thr = dollars_to_cents(over)
                amt = dollars_to_cents(off)
                if thr and amt:
                    tiers.append([thr, amt])
            tiers.sort()
            conn.execute(
                "update promos set value = ? where key = 'tiers'",
                (json.dumps(tiers),),
            )
        if section in {"all", "first"}:
            first_over = dollars_to_cents(form.get("first_over_dollars"), allow_zero=True)
            first_off = dollars_to_cents(form.get("first_off_dollars"))
            if first_over is not None and first_off and first_off > 0:
                current = conn.execute(
                    "select id from coupons where kind = 'first' order by id limit 1"
                ).fetchone()
                if current:
                    conn.execute(
                        "update coupons set threshold_cents = ?, amount_cents = ?, enabled = 1 where id = ?",
                        (first_over, first_off, current["id"]),
                    )
                else:
                    conn.execute(
                        """
                        insert into coupons (name, kind, threshold_cents, amount_cents, enabled)
                        values ('First order', 'first', ?, ?, 1)
                        """,
                        (first_over, first_off),
                    )
        if section in {"all", "shipping"}:
            shipping = {}
            for key in ("USCA", "EU", "JP", "MXBR"):
                cents = dollars_to_cents(form.get(f"ship_{key}_dollars"), allow_zero=True)
                if cents is not None and cents >= 0:
                    shipping[key] = cents
            if len(shipping) == 4:
                conn.execute(
                    "update promos set value = ? where key = 'shipping'",
                    (json.dumps(shipping),),
                )
        forget_catalog()
        return flash_redirect("/admin/promos", "promos_saved")

    @app.post("/admin/campaigns/{campaign_id}")
    async def admin_campaign_save(request: Request, campaign_id: int):
        require_admin(request)
        form = await request.form()
        conn.execute(
            """
            update campaigns
            set enabled = ?, title = ?, rules = ?, image_url = ?, starts_at = ?, ends_at = ?
            where id = ?
            """,
            (
                1 if form.get("enabled") == "1" else 0,
                str(form.get("title") or "")[:80],
                str(form.get("rules") or "")[:500],
                str(form.get("image_url") or "")[:300],
                str(form.get("starts_at") or "")[:40],
                str(form.get("ends_at") or "")[:40],
                campaign_id,
            ),
        )
        forget_catalog()
        return RedirectResponse("/admin/campaigns", status_code=303)

    @app.post("/admin/campaigns/{campaign_id}/items")
    async def admin_campaign_item(request: Request, campaign_id: int):
        require_admin(request)
        form = await request.form()
        sku = str(form.get("sku") or "").strip().split("~", 1)[0]
        known = conn.execute(
            "select sku from products where sku = ? and published = 1",
            (sku,),
        ).fetchone()
        cents = int((Decimal(str(form.get("price") or "0")) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        try:
            stock = max(0, int(form.get("stock") or 0))
        except ValueError:
            stock = 0
        if known is None or cents <= 0:
            return RedirectResponse("/admin/campaigns", status_code=303)
        existing = conn.execute(
            "select id from campaign_items where campaign_id = ? and sku = ?",
            (campaign_id, sku),
        ).fetchone()
        if existing:
            conn.execute(
                "update campaign_items set price_cents = ?, stock = ? where id = ?",
                (cents, stock, existing["id"]),
            )
        else:
            conn.execute(
                "insert into campaign_items (campaign_id, sku, price_cents, stock) values (?, ?, ?, ?)",
                (campaign_id, sku, cents, stock),
            )
        forget_catalog()
        return RedirectResponse("/admin/campaigns", status_code=303)

    @app.post("/admin/campaigns/items/{item_id}/delete")
    def admin_campaign_item_delete(request: Request, item_id: int):
        require_staff(request)
        conn.execute("delete from campaign_items where id = ?", (item_id,))
        forget_catalog()
        return RedirectResponse("/admin/campaigns", status_code=303)

    @app.post("/admin/coupons/{coupon_id}/disable")
    def admin_coupon_disable(request: Request, coupon_id: int):
        require_admin_role(request)
        conn.execute("update coupons set enabled = 0 where id = ?", (coupon_id,))
        forget_catalog()
        return flash_redirect("/admin/coupons", "coupon_disabled")

    @app.post("/admin/coupons/{coupon_id}/enable")
    def admin_coupon_enable(request: Request, coupon_id: int):
        require_admin_role(request)
        conn.execute("update coupons set enabled = 1 where id = ?", (coupon_id,))
        forget_catalog()
        return flash_redirect("/admin/coupons", "coupon_enabled")

    @app.post("/admin/coupons/{coupon_id}/save")
    async def admin_coupon_save(request: Request, coupon_id: int):
        require_admin_role(request)
        form = await request.form()
        kind = str(form.get("kind") or "public")
        if kind not in {"public", "first", "share", "desktop", "checkin"}:
            kind = "public"
        thr = dollars_to_cents(form.get("threshold_dollars"), allow_zero=True)
        amt = dollars_to_cents(form.get("amount_dollars"))
        if thr is None or amt is None or amt <= 0:
            return flash_redirect("/admin/coupons", "coupon_bad")
        conn.execute(
            """
            update coupons
            set name = ?, kind = ?, threshold_cents = ?, amount_cents = ?
            where id = ?
            """,
            (str(form.get("name") or "Coupon")[:40], kind, int(thr), int(amt), coupon_id),
        )
        forget_catalog()
        return flash_redirect("/admin/coupons", "coupon_saved")

    @app.post("/admin/ads")
    async def admin_ad_save(request: Request):
        require_staff(request)
        form = await request.form()
        allowed = {"announcement", "sponsored", "pdp-sponsored", "cart-recommend"}
        slot = str(form.get("slot") or "").strip()
        if slot not in allowed:
            return flash_redirect("/admin/ads", "ads_bad_slot")
        conn.execute(
            """
            insert into ads (slot, lang, image_url, href, body)
            values (?, ?, ?, ?, ?)
            on conflict(slot, lang) do update set
                image_url = excluded.image_url,
                href = excluded.href,
                body = excluded.body
            """,
            (
                slot,
                str(form.get("lang") or "en"),
                str(form.get("image_url") or ""),
                str(form.get("href") or ""),
                str(form.get("body") or ""),
            ),
        )
        forget_public()
        return flash_redirect("/admin/ads", "ads_saved")

    def owned_order(request, order_id):
        row = conn.execute("select * from orders where id = ?", (order_id,)).fetchone()
        if row is None:
            return None, False
        owns = request.cookies.get("pending_password") == str(row["id"]) or buyer_email(request) == row["email"]
        return row, owns

    @app.post("/locale")
    async def set_locale(request: Request):
        form = await request.form()
        lang = normalize_ui_lang(form.get("lang") or "")
        if lang not in UI:
            lang = "en"
        country = country_for(request)
        nxt = str(form.get("next") or "/")
        if not nxt.startswith("/") or nxt.startswith("//"):
            nxt = "/"
        response = RedirectResponse(href(nxt, country), status_code=303)
        response.set_cookie("harbor_hl", lang, max_age=31536000, path="/", samesite="lax")
        return response

    @app.post("/cart/save")
    async def save_for_later(request: Request):
        form = await request.form()
        country = str(form.get("country") or "US")
        sku = str(form.get("sku") or "")
        lines = [line for line in load_lines(request.cookies.get("cart")) if line["sku"] != sku]
        saved = read_skus(request.cookies.get("saved"), limit=36)
        response = redirect("/cart", country, cart=dump_lines(lines))
        response.set_cookie("saved", write_skus([sku, *saved], 36), max_age=31536000, path="/")
        push_open_room_cart(conn, request, lines)
        return response

    @app.post("/cart/restore")
    async def restore_saved(request: Request):
        form = await request.form()
        country = str(form.get("country") or "US")
        sku = str(form.get("sku") or "")
        lines = merge_line(load_lines(request.cookies.get("cart")), sku, 1)
        saved = [item for item in read_skus(request.cookies.get("saved"), 36) if item != sku]
        response = redirect("/cart", country, cart=dump_lines(lines))
        response.set_cookie("saved", write_skus(saved, 36), max_age=31536000, path="/")
        push_open_room_cart(conn, request, lines)
        return response

    @app.post("/wishlist")
    async def toggle_wishlist(request: Request):
        form = await request.form()
        country = str(form.get("country") or "US")
        sku = str(form.get("sku") or "")
        items = read_skus(request.cookies.get("wishlist"), 36)
        if sku in items:
            items = [item for item in items if item != sku]
        else:
            items = [sku, *items]
        nxt = str(form.get("next") or "/account/wishlist")
        if not nxt.startswith("/") or nxt.startswith("//"):
            nxt = "/account/wishlist"
        response = RedirectResponse(href(nxt, country), status_code=303)
        response.set_cookie("wishlist", write_skus(items, 36), max_age=31536000, path="/")
        return response

    
    @app.post("/api/notify-me")
    async def api_notify_me(request: Request):
        """Back-in-stock / Notify me — Figma 建议新增, now persisted."""
        ctype = (request.headers.get("content-type") or "").lower()
        email = sku = offer = country = ""
        try:
            if "application/json" in ctype:
                body = await request.json()
                email = str((body or {}).get("email") or "").strip()
                sku = str((body or {}).get("sku") or "").strip()
                offer = str((body or {}).get("offer") or "").strip()
                country = str((body or {}).get("country") or "US").strip().upper() or "US"
            else:
                form = await request.form()
                email = str(form.get("email") or "").strip()
                sku = str(form.get("sku") or "").strip()
                offer = str(form.get("offer") or "").strip()
                country = str(form.get("country") or "US").strip().upper() or "US"
        except Exception:
            return JSONResponse({"ok": False, "error": "bad_request"}, status_code=400)
        if not email or "@" not in email or not sku:
            return JSONResponse({"ok": False, "error": "email_and_sku_required"}, status_code=400)
        # session email wins when signed in
        sess_email = ""
        try:
            sess_email = str(getattr(request.state, "email", "") or request.cookies.get("email") or "")
        except Exception:
            sess_email = ""
        if sess_email and "@" in sess_email:
            email = sess_email.strip()
        try:
            app.state.db.execute(
                "insert or ignore into stock_alerts(sku, email, country, offer) values(?,?,?,?)",
                (sku, email.lower(), country[:8], offer[:80]),
            )
            app.state.db.commit()
        except Exception as exc:
            return JSONResponse({"ok": False, "error": "db", "detail": str(exc)[:120]}, status_code=500)
        return JSONResponse({"ok": True, "sku": sku, "email": email.lower()})

    @app.post("/notify-me")
    async def notify_me_form(request: Request):
        """HTML form fallback for desktop PDP Notify me."""
        form = await request.form()
        email = str(form.get("email") or "").strip()
        sku = str(form.get("sku") or "").strip()
        offer = str(form.get("offer") or "").strip()
        country = str(form.get("country") or "US").strip().upper() or "US"
        nxt = str(form.get("next") or f"/product/{sku}")
        if not nxt.startswith("/") or nxt.startswith("//"):
            nxt = f"/product/{sku}" if sku else "/"
        ok = False
        if email and "@" in email and sku:
            try:
                app.state.db.execute(
                    "insert or ignore into stock_alerts(sku, email, country, offer) values(?,?,?,?)",
                    (sku, email.lower(), country[:8], offer[:80]),
                )
                app.state.db.commit()
                ok = True
            except Exception:
                ok = False
        sep = "&" if "?" in nxt else "?"
        return RedirectResponse(nxt + (f"{sep}notify=1" if ok else f"{sep}notify=0"), status_code=303)

    @app.post("/compare")
    async def add_compare(request: Request):
        form = await request.form()
        country = str(form.get("country") or "US")
        sku = str(form.get("sku") or "")
        items = read_skus(request.cookies.get("compare"), 4)
        if sku and sku not in items:
            items = [sku, *items]
        response = RedirectResponse(href("/compare", country), status_code=303)
        response.set_cookie("compare", write_skus(items, 4), max_age=31536000, path="/")
        return response

    @app.get("/compare", response_class=HTMLResponse)
    def compare(request: Request):
        ctx = view(request)
        wanted = set(read_skus(request.cookies.get("compare"), 4))
        items = [present(row, ctx) for row in catalog_rows() if row["sku"] in wanted]
        return templates.TemplateResponse(request, "compare.html", {**ctx, "items": items})

    @app.post("/p/{sku}/question")
    async def ask_question(request: Request, sku: str):
        email = buyer_email(request)
        if not email:
            raise HTTPException(status_code=401)
        form = await request.form()
        body = str(form.get("body") or "").strip()
        if body:
            conn.execute(
                "insert into questions (sku, email, body, answer) values (?, ?, ?, '')",
                (sku, email, body[:500]),
            )
        return RedirectResponse(href(f"/p/{sku}", country_for(request)), status_code=303)

    @app.get("/orders")
    def orders_list_alias(request: Request):
        return RedirectResponse(href("/account/orders", country_for(request)), status_code=302)

    @app.get("/me")
    def me_alias(request: Request):
        return RedirectResponse(href("/account", country_for(request)), status_code=302)

    @app.get("/wishlist")
    def wishlist_alias(request: Request):
        return RedirectResponse(href("/account/wishlist", country_for(request)), status_code=302)

    @app.get("/account", response_class=HTMLResponse)
    def account_home(request: Request):
        extras = account_extras(request)
        email = extras.get("email") or ""
        recent_orders = []
        if email:
            # Build a short recent-orders list for D05 Me overview
            rows = conn.execute(
                "select * from orders where email = ? order by id desc limit 5",
                (email,),
            ).fetchall()
            lang = ui_lang_for(request, resolve(country_for(request))[0])
            show_zh = prefer_zh_copy(request) or str(lang).startswith("zh")

            def _preview(code, qty):
                parent, sep, offer_id = str(code or "").partition("~")
                row = conn.execute(
                    "select names, source_zh, image_url, offers from products where sku = ?",
                    (parent,),
                ).fetchone()
                name = parent
                image = ""
                if row is not None:
                    try:
                        names = json.loads(row["names"] or "{}")
                    except Exception:
                        names = {}
                    if show_zh:
                        name = _product_label(row["source_zh"], names, parent)
                    else:
                        name = names.get(lang) or names.get("en") or parent
                    image = row["image_url"] or ""
                    if image:
                        image = card_image(storefront_image(image, lang, ROOT), ROOT)
                return {"name": name, "image": image, "qty": int(qty or 1)}

            for order in rows:
                lines = conn.execute(
                    "select sku, qty from order_lines where order_id = ?",
                    (order["id"],),
                ).fetchall()
                recent_orders.append({
                    "id": order["id"],
                    "status": order["status"],
                    "due": format_money(order["due_local"], order["currency"]),
                    "items": [_preview(r["sku"], r["qty"]) for r in lines],
                })
        return render(
            request,
            "account.html",
            panel="home",
            recent_orders=recent_orders,
            **extras,
        )

    @app.get("/account/wishlist", response_class=HTMLResponse)
    def wishlist(request: Request):
        # Indexed/batched lookups only — never scan+present the full catalog.
        ctx = view(request)
        wanted = read_skus(request.cookies.get("wishlist"), 36)
        index = catalog_index()
        items = []
        for sku in wanted:
            row = index.get(sku)
            if row is not None:
                items.append(present(row, ctx))
        suggestions = []
        if not items:
            hint_rows = conn.execute(
                "select * from products where published = 1 and stock > 0 order by rowid limit 4"
            ).fetchall()
            suggestions = [present(dict(row), ctx) for row in hint_rows]
        return templates.TemplateResponse(
            request, "account.html", {**ctx, "panel": "wishlist", "items": items, "suggestions": suggestions}
        )

    @app.get("/account/history", response_class=HTMLResponse)
    def history(request: Request):
        ctx = view(request)
        # t173u: avoid full catalog_rows() scan (same hang class as wishlist)
        index = catalog_index()
        wanted = [sku for sku in account_weights(conn, buyer_email(request) or "") if sku in index]
        items = [present(index[sku], ctx) for sku in wanted]
        suggestions = []
        if not items:
            rows = conn.execute(
                "select * from products where published=1 and stock>0 order by rowid limit 4"
            ).fetchall()
            suggestions = [present(row, ctx) for row in rows]
        return templates.TemplateResponse(
            request, "account.html", {**ctx, "panel": "history", "items": items, "suggestions": suggestions}
        )

    @app.get("/account/addresses", response_class=HTMLResponse)
    def addresses(request: Request):
        email = buyer_email(request) or ""
        rows = []
        if email:
            rows = conn.execute("select * from addresses where email = ? order by id desc", (email,)).fetchall()
        return render(request, "account.html", panel="addresses", email=email, addresses=rows)

    @app.post("/account/addresses")
    async def add_address(request: Request):
        email = buyer_email(request)
        if not email:
            raise HTTPException(status_code=401)
        form = await request.form()
        country = str(form.get("ship_country") or "US")[:2].upper()
        conn.execute(
            """
            insert into addresses (email, name, address, city, region, postal, ship_country, phone)
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                email,
                str(form.get("name") or ""),
                compose_street(country, str(form.get("address") or ""), str(form.get("street_number") or ""), str(form.get("district") or "")),
                str(form.get("city") or ""),
                str(form.get("region") or ""),
                str(form.get("postal") or ""),
                country,
                str(form.get("phone") or ""),
            ),
        )
        return RedirectResponse(href("/account/addresses", country_for(request)), status_code=303)

    @app.get("/account/payments", response_class=HTMLResponse)
    def payments(request: Request):
        email = buyer_email(request) or ""
        rows = []
        if email:
            rows = conn.execute("select * from pay_methods where email = ? order by id desc", (email,)).fetchall()
        return render(request, "account.html", panel="payments", email=email, methods=rows)

    @app.post("/account/payments")
    async def add_payment(request: Request):
        email = buyer_email(request)
        if not email:
            raise HTTPException(status_code=401)
        form = await request.form()
        last4 = "".join(ch for ch in str(form.get("last4") or "") if ch.isdigit())[-4:]
        brand = str(form.get("brand") or "Card")[:20]
        if len(last4) == 4:
            conn.execute(
                "insert into pay_methods (email, brand, last4) values (?, ?, ?)",
                (email, brand, last4),
            )
        return RedirectResponse(href("/account/payments", country_for(request)), status_code=303)

    @app.post("/orders/{order_id}/again")
    def buy_again(request: Request, order_id: str):
        row, owns = owned_order(request, order_id)
        if row is None or not owns:
            raise HTTPException(status_code=403)
        lines = load_lines(request.cookies.get("cart"))
        again = conn.execute(
            "select sku, qty from order_lines where order_id = ?",
            (row["id"],),
        ).fetchall()
        for item in again:
            lines = merge_line(lines, item["sku"], item["qty"])
        return redirect("/cart", country_for(request), cart=dump_lines(lines))

    @app.post("/orders/{order_id}/return")
    async def request_return(request: Request, order_id: str):
        row, owns = owned_order(request, order_id)
        if row is None or not owns or row["status"] not in {"paid", "shipped"}:
            raise HTTPException(status_code=403)
        form = await request.form()
        reason = str(form.get("reason") or "").strip()
        if reason:
            conn.execute(
                "insert into returns (order_id, email, reason, status) values (?, ?, ?, 'requested')",
                (row["id"], row["email"], reason[:300]),
            )
        return RedirectResponse(href(f"/orders/{order_id}", country_for(request)), status_code=303)

    @app.get("/orders/{order_id}/invoice", response_class=HTMLResponse)
    def invoice(request: Request, order_id: str):
        row, owns = owned_order(request, order_id)
        if row is None or not owns:
            raise HTTPException(status_code=403)
        lines = conn.execute(
            "select sku, qty, price_cents from order_lines where order_id = ?",
            (row["id"],),
        ).fetchall()
        return render(
            request,
            "invoice.html",
            order=row,
            lines=lines,
            due_text=format_money(row["due_local"], row["currency"]),
        )

    @app.get("/help", response_class=HTMLResponse)
    def help_page(request: Request):
        return render(request, "text.html", panel="help")

    @app.post("/contact")
    async def contact_post(request: Request):
        form = await request.form()
        email = str(form.get("email") or buyer_email(request) or "").strip().lower()
        body = str(form.get("body") or "").strip()
        if "@" in email and body:
            conn.execute("insert into messages (email, body) values (?, ?)", (email, body[:1000]))
        return RedirectResponse(href("/contact", country_for(request)), status_code=303)

    @app.post("/admin/coupons")
    async def admin_coupon_create(request: Request):
        require_admin_role(request)
        form = await request.form()
        kind = str(form.get("kind") or "public")
        if kind not in {"public", "first", "share", "desktop", "checkin"}:
            kind = "public"
        thr = dollars_to_cents(form.get("threshold_dollars"), allow_zero=True) or 0
        amt = dollars_to_cents(form.get("amount_dollars"))
        if amt is None or amt <= 0:
            return flash_redirect("/admin/coupons", "coupon_bad")
        conn.execute(
            "insert into coupons (name, kind, threshold_cents, amount_cents, enabled) values (?, ?, ?, ?, 1)",
            (str(form.get("name") or "Coupon")[:40], kind, int(thr), int(amt)),
        )
        forget_catalog()
        return flash_redirect("/admin/coupons", "coupon_saved")

    @app.post("/admin/withdrawals/{withdrawal_id}/paid")
    async def admin_withdrawal_paid(request: Request, withdrawal_id: int):
        require_admin_role(request)
        form = await request.form()
        note = str(form.get("payout_note") or "").strip()[:200]
        if len(note) < 2:
            return flash_redirect("/admin/withdrawals", "payout_need_note")
        row = conn.execute("select status from withdrawals where id = ?", (withdrawal_id,)).fetchone()
        if row is None or row["status"] == "paid":
            return flash_redirect("/admin/withdrawals", "payout_fail")
        try:
            conn.execute(
                "update withdrawals set status = 'paid', payout_note = ? where id = ?",
                (note, withdrawal_id),
            )
        except Exception:
            conn.execute("update withdrawals set status = 'paid' where id = ?", (withdrawal_id,))
        return flash_redirect("/admin/withdrawals", "payout_ok")

    @app.post("/admin/catalog")
    async def admin_product_import(request: Request):
        require_admin(request)
        form = await request.form()
        sku = str(form.get("sku") or "").strip().lower()
        category = str(form.get("category") or "").strip()
        name_zh = str(form.get("name_zh") or "").strip()
        description_zh = str(form.get("description_zh") or "").strip()
        bullets_zh = [line.strip() for line in str(form.get("bullets_zh") or "").splitlines() if line.strip()][:4]
        image_url = str(form.get("image_url") or "").strip()
        try:
            price_cents = int(form.get("price_cents") or 0)
        except ValueError:
            price_cents = 0
        sku_ok = 2 <= len(sku) <= 40 and all(ch.isascii() and (ch.isalnum() or ch == "-") for ch in sku)
        if not sku_ok or category not in CATEGORIES or price_cents <= 0 or not name_zh:
            return HTMLResponse("商品编号、类目、美元价格（美分）和中文名称都要填。", status_code=400)
        translate = active_translator()
        if translate is None:
            return HTMLResponse(
                "还没有 AI 密钥。在商品页填上密钥后再翻译。模型用 auto。没有密钥时不会把中文直接上架。",
                status_code=400,
            )
        fields = {"name": name_zh, "description": description_zh}
        for index, line in enumerate(bullets_zh):
            fields[f"b{index}"] = line
        filled = fill_languages(fields, translate)
        names = filled["name"]
        description = filled["description"]
        bullets = {lang: [filled[f"b{index}"][lang] for index in range(len(bullets_zh))] for lang in names}
        source = json.dumps(
            {"name": name_zh, "description": description_zh, "bullets": bullets_zh},
            ensure_ascii=False,
        )
        listing = json.dumps(
            {"title": name_zh, "description": description_zh, "money": "USD", "amount": price_cents / 100},
            ensure_ascii=False,
        )
        payload = (
            json.dumps(names, ensure_ascii=False),
            json.dumps(bullets, ensure_ascii=False),
            json.dumps(description, ensure_ascii=False),
            image_url,
            source,
            listing,
        )
        existing = conn.execute("select sku from products where sku = ?", (sku,)).fetchone()
        if existing:
            conn.execute(
                """
                update products
                set category = ?, price_cents = ?, names = ?, bullets = ?, description = ?, image_url = ?,
                    source_zh = ?, listing = ?, published = 1
                where sku = ?
                """,
                (category, price_cents, *payload, sku),
            )
        else:
            conn.execute(
                """
                insert into products
                    (sku, category, price_cents, stock, names, bullets, description, specs, image_url, source_zh, listing, published, uploaded_at)
                values (?, ?, ?, 100, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    sku,
                    category,
                    price_cents,
                    *payload[:3],
                    json.dumps({"material": "", "size": "", "weight": ""}),
                    *payload[3:],
                    date.today().isoformat(),
                ),
            )
        forget_catalog()
        return RedirectResponse("/admin/products", status_code=303)

    @app.post("/admin/ai")
    async def admin_ai_save(request: Request):
        require_admin_role(request)
        form = await request.form()
        model = str(form.get("ai_model") or "").strip() or "auto"
        base = str(form.get("ai_base") or "").strip() or "https://api.cursor.com"
        key = str(form.get("ai_key") or "").strip() or setting("ai_key")
        for name, value in (("ai_model", model), ("ai_base", base)):
            conn.execute(
                "insert into settings (key, value) values (?, ?) on conflict(key) do update set value = excluded.value",
                (name, value),
            )
        if key:
            conn.execute(
                "insert into settings (key, value) values ('ai_key', ?) on conflict(key) do update set value = excluded.value",
                (key,),
            )
        app.state.writer = None
        app.state.translator = None
        app.state.complete = None
        ensure_ai()
        return RedirectResponse("/admin/products?section=pricing&ai=saved", status_code=303)

    def run_image_translation(lang, tasks):
        client = app.state.image_client
        worker_cap = 60
        if client is None:
            editors = gen_editors()
            if not editors:
                image_job_update(running=False, error="先在右边保存生图 API 密钥。")
                return
            client = CommerceImageClient(editors[0])
            worker_cap = gen_api_account()["workers"]
        stats = {"translated": 0, "failed": 0, "skipped": 0, "done": 0}
        counter = threading.Lock()
        stop = threading.Event()
        pending = queue.Queue()
        sync_workers = min(max(1, int(worker_cap or 1)), len(tasks)) or 1
        try:
            def remember(sku, *, translated=0, failed=0, skipped=0, only_done=False):
                with counter:
                    stats["translated"] += translated
                    stats["failed"] += failed
                    stats["skipped"] += skipped
                    stats["done"] += 1 if only_done else translated + failed + skipped
                    snapshot = {
                        "translated": stats["translated"],
                        "failed": stats["failed"],
                        "skipped": stats["skipped"],
                        "products": 0,
                    }
                    done = stats["done"]
                image_job_update(done=done, label=sku, result=snapshot)

            def recognize(item):
                sku, path = item
                if stop.is_set():
                    return
                if language_file(path, lang).is_file():
                    remember(sku, only_done=True)
                    return
                # No Chinese on the image: reuse original, do not call DashScope.
                if image_has_cjk(path) is False:
                    dest = language_file(path, lang)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(Path(path).read_bytes())
                    remember(sku, skipped=1)
                    return
                pending.put(item)

            def translate_ready():
                while True:
                    item = pending.get()
                    if item is None:
                        return
                    if stop.is_set():
                        continue
                    sku, path = item
                    try:
                        data = client.translate(path, lang)
                        dest = language_file(path, lang)
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(data)
                        remember(sku, translated=1)
                    except (ImageAuthError, GenError) as exc:
                        message = str(exc)
                        if isinstance(exc, ImageAuthError) or any(
                            token in message.lower() for token in ("403", "balance", "密钥")
                        ):
                            stop.set()
                            image_job_update(error=message)
                        remember(sku, failed=1)
                    except Exception:
                        remember(sku, failed=1)

            with ThreadPoolExecutor(max_workers=2) as ocr_pool, ThreadPoolExecutor(max_workers=sync_workers) as sync_pool:
                senders = [sync_pool.submit(translate_ready) for _ in range(sync_workers)]
                list(ocr_pool.map(recognize, tasks))
                for _ in range(sync_workers):
                    pending.put(None)
                for job in senders:
                    job.result()
            image_job_update(
                done=stats["done"],
                result={
                    "translated": stats["translated"],
                    "failed": stats["failed"],
                    "skipped": stats["skipped"],
                    "products": len({sku for sku, _path in tasks}),
                },
            )
        finally:
            image_job_update(running=False)

    @app.get("/admin/images/progress")
    def admin_image_progress(request: Request):
        require_admin(request)
        return JSONResponse(image_job_read())

    @app.post("/admin/images/key")
    async def admin_image_key(request: Request):
        require_admin_role(request)
        form = await request.form()
        key = str(form.get("image_key") or "").strip()
        workspace = str(form.get("image_workspace") or "").strip()
        if key:
            conn.execute(
                "insert into settings (key, value) values ('image_key', ?) on conflict(key) do update set value = excluded.value",
                (key,),
            )
        conn.execute(
            "insert into settings (key, value) values ('image_workspace', ?) on conflict(key) do update set value = excluded.value",
            (workspace,),
        )
        return RedirectResponse("/admin/images?image=saved", status_code=303)

    def run_story_batch(lang, skus):
        """One hundred products at once. Each product draws its frames one by one.

        A short set stays on disk. After the first pass, one fill-in draws only the missing frames.
        """
        editors = gen_editors()
        if not editors:
            image_job_update(running=False, error="先在右边保存生图 API 密钥。")
            return
        editor = editors[0]
        complete = active_complete()
        total = len(skus)
        state = {"done": 0, "failed": 0, "short": 0, "live": 0}
        lock = threading.Lock()
        stop = threading.Event()

        def lanes_now():
            return max(1, int(gen_api_account()["workers"] or 1))

        def tally(label):
            image_job_update(
                done=state["done"],
                total=total,
                label=label,
                result={
                    "translated": state["done"],
                    "failed": state["failed"],
                    "skipped": state["short"],
                    "products": state["done"],
                    "kind": "story",
                },
            )

        def attempt(sku, count):
            if stop.is_set():
                return
            image_job_update(label=sku)
            try:
                generate_story(
                    conn,
                    ROOT,
                    sku,
                    lang,
                    editor,
                    complete=complete,
                    workers=1,
                    only_missing=True,
                )
            except GenError as exc:
                message = str(exc)
                if any(token in message.lower() for token in ("403", "balance", "密钥")):
                    stop.set()
                    image_job_update(error=message[:180])
                with lock:
                    if not missing_story_slots(ROOT, sku, lang):
                        pass
                    elif not any((ROOT / "static" / "catalog" / sku / lang).rglob("*.jpg")):
                        state["failed"] += 1
            except Exception:
                with lock:
                    state["failed"] += 1
            with lock:
                if count:
                    state["done"] += 1
                    if missing_story_slots(ROOT, sku, lang):
                        state["short"] += 1
            app.state.story_missing_cache = None
            app.state.story_left_cache = None
            tally(sku)

        def sweep(targets, count):
            if not targets or stop.is_set():
                return
            pending = queue.Queue()
            for sku in targets:
                pending.put(sku)

            def worker():
                try:
                    while not stop.is_set():
                        with lock:
                            if state["live"] > lanes_now():
                                return
                        try:
                            sku = pending.get_nowait()
                        except queue.Empty:
                            return
                        attempt(sku, count)
                finally:
                    with lock:
                        state["live"] -= 1

            def ensure():
                if stop.is_set():
                    return
                want = lanes_now()
                with lock:
                    while state["live"] < want and not pending.empty() and not stop.is_set():
                        state["live"] += 1
                        threading.Thread(target=worker, daemon=True).start()

            while True:
                ensure()
                with lock:
                    idle = state["live"] == 0 and (pending.empty() or stop.is_set())
                if idle:
                    return
                time.sleep(0.4)

        try:
            sweep(skus, True)
            if not stop.is_set():
                again = [sku for sku in skus if missing_story_slots(ROOT, sku, lang)]
                sweep(again, False)
            state["short"] = sum(1 for sku in skus if missing_story_slots(ROOT, sku, lang))
            tally("补完" if skus else "")
        finally:
            image_job_update(running=False)

    @app.post("/admin/images/translate")
    async def admin_image_translate(request: Request):
        require_admin(request)
        if image_job_busy():
            return images_page(request, 400, image_error="上一批图片还在译，等这一批走完再开下一种。")
        form = await request.form()
        lang = str(form.get("lang") or "").strip()
        if app.state.image_client is None:
            missing = gen_ready_or_error()
            if missing:
                return images_page(request, 400, image_error=missing)
            if lang not in ("en", "ja", "es", "fr", "pt"):
                return images_page(request, 400, image_error="一次只能选一种语言。德语这档没有。")
            skus = products_missing_story(lang)
            if not skus:
                return images_page(request, 400, image_error="这些商品都已经有 3 张主图和 5 张详情。")
            image_job_update(
                running=True,
                lang=lang,
                date_from="",
                date_to="",
                done=0,
                total=len(skus),
                label=skus[0],
                error="",
                result={"translated": 0, "failed": 0, "skipped": 0, "products": len(skus), "kind": "story"},
            )
            thread = threading.Thread(target=run_story_batch, args=(lang, skus), daemon=True)
            app.state.image_thread = thread
            thread.start()
            return RedirectResponse("/admin/images", status_code=303)
        rows = conn.execute(
            "select sku, image_url, listing, offers, uploaded_at from products"
        ).fetchall()
        try:
            tasks = pending_images(rows, ROOT, lang)
        except ImageTranslateError as exc:
            return images_page(request, 400, image_error=str(exc))
        if not tasks:
            return images_page(request, 400, image_error="没有还没译成这种语言的图。")
        image_job_update(
            running=True,
            lang=lang,
            date_from="",
            date_to="",
            done=0,
            total=len(tasks),
            label=tasks[0][0],
            error="",
            result={"translated": 0, "failed": 0, "skipped": 0, "products": len({sku for sku, _path in tasks}), "kind": "translate"},
        )
        thread = threading.Thread(target=run_image_translation, args=(lang, tasks), daemon=True)
        app.state.image_thread = thread
        thread.start()
        return RedirectResponse("/admin/images", status_code=303)

    @app.post("/admin/images/translate/one")
    async def admin_image_translate_one(request: Request):
        require_admin(request)
        if image_job_busy():
            return images_page(request, 400, image_error="上一批图片还在译，等这一批走完再开这一件。")
        form = await request.form()
        lang = str(form.get("lang") or "").strip()
        sku = str(form.get("sku") or "").strip()
        if not sku:
            return images_page(request, 400, image_error="先填写要翻译的货号。")
        if app.state.image_client is None:
            missing = gen_ready_or_error()
            if missing:
                return images_page(request, 400, image_error=missing)
        rows = conn.execute(
            "select sku, image_url, listing, offers, uploaded_at from products where sku = ?",
            (sku,),
        ).fetchall()
        if not rows:
            return images_page(request, 400, image_error="没有这个商品。")
        try:
            tasks = pending_images(rows, ROOT, lang, sku=sku)
        except ImageTranslateError as exc:
            return images_page(request, 400, image_error=str(exc))
        if not tasks:
            return images_page(request, 400, image_error="这一件没有还要处理的图。")
        image_job_update(
            running=True,
            lang=lang,
            date_from="",
            date_to="",
            done=0,
            total=len(tasks),
            label=sku,
            error="",
            result={"translated": 0, "failed": 0, "skipped": 0, "products": 1, "kind": "translate"},
        )
        thread = threading.Thread(target=run_image_translation, args=(lang, tasks), daemon=True)
        app.state.image_thread = thread
        thread.start()
        return RedirectResponse("/admin/images", status_code=303)

    @app.post("/admin/images/story/one")
    async def admin_image_story_one(request: Request):
        require_admin(request)
        if image_job_busy():
            return images_page(request, 400, image_error="上一批图片还在跑，等这一批走完再生成详情。")
        form = await request.form()
        lang = str(form.get("lang") or "").strip()
        sku = str(form.get("sku") or "").strip()
        if not sku:
            return images_page(request, 400, image_error="先填写要生成详情的货号。")
        if lang not in ("en", "ja", "es", "fr", "pt"):
            return images_page(request, 400, image_error="一次只能选一种语言。")
        row = conn.execute("select sku from products where sku = ?", (sku,)).fetchone()
        if row is None:
            return images_page(request, 400, image_error="没有这个商品。")
        if app.state.gen_editors is None:
            missing = gen_ready_or_error()
            if missing:
                return images_page(request, 400, image_error=missing)
        editors = gen_editors()
        if not editors:
            return images_page(request, 400, image_error="先保存生图 API 密钥。")
        image_job_update(
            running=True,
            lang=lang,
            date_from="",
            date_to="",
            done=0,
            total=0,
            label=sku,
            error="",
            result={"translated": 0, "failed": 0, "skipped": 0, "products": 1, "kind": "story"},
        )

        def run_story():
            try:
                count = generate_story(
                    conn,
                    ROOT,
                    sku,
                    lang,
                    editors[0],
                    complete=active_complete(),
                    on_progress=lambda done, total: image_job_update(done=done, total=total, label=sku),
                    workers=gen_api_account()["workers"],
                )
                image_job_update(
                    running=False,
                    done=count,
                    total=count,
                    label=sku,
                    error="",
                    result={"translated": count, "failed": 0, "skipped": 0, "products": 1, "kind": "story"},
                )
            except GenError as exc:
                image_job_update(running=False, error=str(exc)[:180])
            except Exception as exc:
                image_job_update(running=False, error=str(exc)[:180])

        thread = threading.Thread(target=run_story, daemon=True)
        app.state.image_thread = thread
        thread.start()
        return RedirectResponse("/admin/images", status_code=303)

    @app.post("/admin/images/continue")
    async def admin_image_continue(request: Request):
        require_admin(request)
        if image_job_busy():
            return images_page(request, 400, image_error="上一批图片还在译，等这一批走完再继续。")
        job = image_job_read()
        lang = str(job.get("lang") or "")
        if app.state.image_client is None:
            missing = gen_ready_or_error()
            if missing:
                return images_page(request, 400, image_error=missing)
            if lang not in ("en", "ja", "es", "fr", "pt"):
                lang = "en"
            skus = products_missing_story(lang)
            if not skus:
                return images_page(request, 400, image_error="这些商品都已经有 3 张主图和 5 张详情。")
            image_job_update(
                running=True,
                lang=lang,
                date_from="",
                date_to="",
                done=0,
                total=len(skus),
                label=skus[0],
                error="",
                result={"translated": 0, "failed": 0, "skipped": 0, "products": len(skus), "kind": "story"},
            )
            thread = threading.Thread(target=run_story_batch, args=(lang, skus), daemon=True)
            app.state.image_thread = thread
            thread.start()
            return RedirectResponse("/admin/images", status_code=303)
        rows = conn.execute(
            "select sku, image_url, listing, offers, uploaded_at from products"
        ).fetchall()
        try:
            tasks = pending_images(rows, ROOT, lang)
        except ImageTranslateError as exc:
            return images_page(request, 400, image_error=str(exc))
        if not tasks:
            return images_page(request, 400, image_error="已经译好的都还在，没有要继续的图。")
        image_job_update(
            running=True,
            lang=lang,
            date_from="",
            date_to="",
            done=0,
            total=len(tasks),
            label=tasks[0][0],
            error="",
            result={"translated": 0, "failed": 0, "skipped": 0, "products": len({sku for sku, _path in tasks}), "kind": "translate"},
        )
        thread = threading.Thread(target=run_image_translation, args=(lang, tasks), daemon=True)
        app.state.image_thread = thread
        thread.start()
        return RedirectResponse("/admin/images", status_code=303)

    def clean_gen_urls(values):
        urls = []
        for value in values:
            text = str(value or "").strip().rstrip("/")
            if not text:
                continue
            if not text.startswith(("http://", "https://")) or len(text) > 200:
                raise GenError("显卡地址要写成 http:// 开头。")
            urls.append(text)
        return urls[:8]

    @app.post("/admin/images/gen/api")
    async def admin_gen_api(request: Request):
        require_admin_role(request)
        form = await request.form()
        url = str(form.get("gen_api_url") or "").strip().rstrip("/")
        if not url:
            url = DEFAULT_GEN_API_URL
        if not url.startswith(("http://", "https://")) or len(url) > 200:
            return images_page(request, 400, gen_error="生图 API 地址要写成 https:// 开头。")
        if url.endswith("/v1"):
            url = url[:-3].rstrip("/")
        model = str(form.get("gen_api_model") or "").strip() or DEFAULT_GEN_API_MODEL
        if len(model) > 120:
            return images_page(request, 400, gen_error="模型名太长。")
        try:
            workers = int(str(form.get("gen_api_workers") or DEFAULT_GEN_API_WORKERS).strip() or DEFAULT_GEN_API_WORKERS)
        except ValueError:
            return images_page(request, 400, gen_error="并发路数要填数字。")
        workers = max(1, min(MAX_GEN_API_WORKERS, workers))
        key = str(form.get("gen_api_key") or "").strip()
        conn.execute(
            "insert into settings (key, value) values ('gen_api_url', ?) on conflict(key) do update set value = excluded.value",
            (url,),
        )
        conn.execute(
            "insert into settings (key, value) values ('gen_api_model', ?) on conflict(key) do update set value = excluded.value",
            (model,),
        )
        conn.execute(
            "insert into settings (key, value) values ('gen_api_workers', ?) on conflict(key) do update set value = excluded.value",
            (str(workers),),
        )
        if key:
            conn.execute(
                "insert into settings (key, value) values ('gen_api_key', ?) on conflict(key) do update set value = excluded.value",
                (key,),
            )
        return RedirectResponse("/admin/images?gen=api", status_code=303)

    @app.post("/admin/images/gen/workers")
    async def admin_gen_workers(request: Request):
        require_admin_role(request)
        form = await request.form()
        try:
            urls = clean_gen_urls(form.getlist("gpu"))
        except GenError as exc:
            return images_page(request, 400, gen_error=str(exc))
        token = str(form.get("gen_token") or "").strip()
        conn.execute(
            "insert into settings (key, value) values ('gen_workers', ?) on conflict(key) do update set value = excluded.value",
            (json.dumps(urls),),
        )
        if token:
            conn.execute(
                "insert into settings (key, value) values ('gen_token', ?) on conflict(key) do update set value = excluded.value",
                (token,),
            )
        return RedirectResponse("/admin/images?gen=saved", status_code=303)

    @app.post("/admin/images/gen/connect")
    async def admin_gen_connect(request: Request):
        require_admin_role(request)
        form = await request.form()
        url = str(form.get("public_url") or "").strip().rstrip("/")
        host, port, user = parse_ssh(
            str(form.get("ssh_host") or "").strip(),
            str(form.get("ssh_port") or "").strip() or "41125",
            str(form.get("ssh_user") or "").strip() or "root",
        )
        password = str(form.get("ssh_password") or "")
        links = load_gen_links()
        previous = next(
            (
                item
                for item in links
                if (url and item["url"] == url) or (host and item["host"] == host and item["port"] == port)
            ),
            None,
        )
        if not password and previous:
            password = previous["password"]
        error = ""
        if not url.startswith(("http://", "https://")) or len(url) > 200:
            error = "公网地址填自定义服务那条 https。"
        elif not host or len(host) > 200 or any(char.isspace() for char in host):
            error = "先填 SSH 主机。主机只填 connect.westb.seetacloud.com，不要把 ssh 那一行整段贴进来。"
        elif not port.isdigit() or not 1 <= int(port) <= 65535:
            error = "SSH 端口不对。"
        elif not password:
            error = "先填 SSH 密码。在 AutoDL 实例那一行点「密码」复制，粘贴后格子里要出现圆点。"
        if not url and not host:
            return images_page(request, 400, gen_error=error or "先填公网地址和 SSH 主机。")
        record = {
            "url": url,
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "ok": False,
            "detail": error or "正在连接，请稍等。",
        }
        updated = [item for item in links if item is not previous]
        updated.append(record)
        save_gen_links(updated[:8])
        if error:
            return RedirectResponse("/admin/images", status_code=303)
        token = setting("gen_token") or secrets.token_urlsafe(18)
        try:
            connector = app.state.gen_connector or open_gpu
            detail = await asyncio.to_thread(
                connector,
                host=host,
                port=port,
                user=user,
                password=password,
                public_url=url,
                token=token,
            )
            record["ok"] = True
            record["detail"] = str(detail or "已连上。")
        except LinkError as exc:
            record["detail"] = str(exc)
        except Exception as exc:
            record["detail"] = "连接失败。（%s）" % type(exc).__name__
        save_gen_links(updated[:8])
        if record["ok"]:
            conn.execute(
                "insert into settings (key, value) values ('gen_token', ?) on conflict(key) do update set value = excluded.value",
                (token,),
            )
        return RedirectResponse("/admin/images", status_code=303)

    @app.post("/admin/images/gen/remove")
    async def admin_gen_remove(request: Request):
        require_admin_role(request)
        form = await request.form()
        url = str(form.get("public_url") or "").strip().rstrip("/")
        host, port, _user = parse_ssh(
            str(form.get("ssh_host") or "").strip(),
            str(form.get("ssh_port") or "").strip() or "41125",
            str(form.get("ssh_user") or "").strip() or "root",
        )
        links = load_gen_links()
        kept = []
        removed = False
        for item in links:
            same = (host and item["host"] == host and str(item["port"]) == str(port)) or (
                url and not host and item["url"] == url
            )
            if same and not removed:
                removed = True
                continue
            kept.append(item)
        if removed:
            save_gen_links(kept)
        return RedirectResponse("/admin/images", status_code=303)

    @app.post("/admin/images/gen/pause")
    async def admin_gen_pause(request: Request):
        require_admin_role(request)
        form = await request.form()
        paused = str(form.get("paused") or "1").strip() != "0"
        conn.execute(
            "insert into settings (key, value) values ('gen_paused', ?) on conflict(key) do update set value = excluded.value",
            ("1" if paused else "0",),
        )
        if paused:
            app.state.gen_armed = False
            app.state.sku_gen_armed = False
            stop_gen_pool()
            stop_sku_gen_pool()
        else:
            app.state.gen_armed = True
            app.state.sku_gen_armed = True
            ensure_supervisor()
            ensure_sku_supervisor()
        return RedirectResponse("/admin/images", status_code=303)

    @app.get("/admin/images/gen/before/{sku}")
    def admin_gen_before(request: Request, sku: str):
        require_admin(request)
        row = conn.execute("select image_url from products where sku = ?", (sku,)).fetchone()
        name = Path(str(row["image_url"] if row else "").split("?", 1)[0]).name
        path = _gen_before_file(gen_backup_root(), sku, name)
        if path is None:
            raise HTTPException(status_code=404)
        return FileResponse(path)

    @app.get("/admin/images/gen/progress")
    def admin_gen_progress(request: Request):
        require_admin(request)
        return JSONResponse(gen_job_read())

    @app.post("/admin/images/gen/one")
    async def admin_gen_one(request: Request):
        require_admin(request)
        missing = gen_ready_or_error()
        if missing:
            return images_page(request, 400, gen_error=missing)
        form = await request.form()
        sku = str(form.get("sku") or "").strip()
        if not sku:
            return images_page(request, 400, gen_error="先填写要跑的货号。")
        row = conn.execute(
            "select sku, image_url, listing, gen_at from products where sku = ?",
            (sku,),
        ).fetchone()
        if row is None:
            return images_page(request, 400, gen_error="没有这个商品。")
        if not source_url(row):
            return images_page(request, 400, gen_error="这个商品没有原图，不能出图。")
        editors = gen_editors()
        if not editors:
            return images_page(request, 400, gen_error="先保存生图 API 密钥，或连上至少一张显卡。")
        held = conn.execute("select status from gen_tasks where sku = ?", (sku,)).fetchone()
        if held and held["status"] == "running":
            return images_page(request, 400, gen_error="这一件正在出图。")
        full = conn.execute(
            "select sku, image_url, listing, offers, gen_at from products where sku = ?",
            (sku,),
        ).fetchone()
        if str(full["gen_at"] or "").strip() and not has_pending_shot(full):
            return images_page(request, 400, gen_error="这个商品已经出过主图第4张。规格白底图请用下面的「只出规格图」。")
        if held is None:
            conn.execute(
                "insert into gen_tasks (sku, status, worker, error, touched) values (?, 'running', 'one', '', ?)",
                (sku, time.time()),
            )
        else:
            conn.execute(
                "update gen_tasks set status = 'running', worker = 'one', error = '', touched = ? where sku = ?",
                (time.time(), sku),
            )

        def run_one():
            try:
                generate_product(
                    conn,
                    ROOT,
                    sku,
                    editors[0],
                    gen_backup_root(),
                    force=True,
                    workers=gen_api_account()["workers"],
                )
                finish_task(conn, sku, True)
                forget_catalog()
            except GenError as exc:
                finish_task(conn, sku, "不会再跑" in str(exc), str(exc))
            except Exception:
                finish_task(conn, sku, False, "这件商品没有出成。")

        threading.Thread(target=run_one, daemon=True).start()
        return RedirectResponse("/admin/images", status_code=303)

    @app.post("/admin/images/gen/plan")
    async def admin_gen_plan(request: Request):
        require_admin(request)
        form = await request.form()
        sku = str(form.get("sku") or "").strip()
        if not sku:
            return images_page(request, 400, gen_error="先填写要算的货号。")
        row = conn.execute(
            "select sku, image_url, listing, offers, gen_at from products where sku = ?",
            (sku,),
        ).fetchone()
        if row is None:
            return images_page(request, 400, gen_error="没有这个商品。")
        rows = plan_product(row)
        return images_page(
            request,
            gen_plan={
                "sku": sku,
                "rows": rows,
                "generate": sum(1 for item in rows if item["action"] == "generate"),
                "skip": sum(1 for item in rows if item["action"] != "generate"),
            },
        )

    @app.post("/admin/images/gen/rest")
    async def admin_gen_rest(request: Request):
        require_admin(request)
        missing = gen_ready_or_error()
        if missing:
            return images_page(request, 400, gen_error=missing)
        if gen_is_paused():
            return images_page(request, 400, gen_error="生图已暂停。先点「继续生图」。")
        skus = [
            row["sku"]
            for row in conn.execute(
                """
                select p.sku as sku
                from products p
                left join gen_tasks t on t.sku = p.sku
                where trim(ifnull(p.gen_at, '')) = ''
                  and ifnull(p.image_url, '') like '/static/catalog/%'
                  and (t.sku is null or t.status not in ('pending', 'running'))
                """
            ).fetchall()
        ]
        skus.extend(
            row["sku"]
            for row in conn.execute("select sku from gen_tasks where status = 'failed'").fetchall()
        )
        added = enqueue(conn, skus)
        app.state.gen_queue_snapshot = None
        if not added:
            return images_page(request, 400, gen_error="没有还要出的商品。失败的规格已经补完，或者都在队列里。")
        app.state.gen_armed = True
        ensure_supervisor()
        return RedirectResponse("/admin/images", status_code=303)

    @app.get("/admin/images/sku/progress")
    def admin_sku_gen_progress(request: Request):
        require_admin(request)
        return JSONResponse(sku_gen_job_read())

    @app.post("/admin/images/sku/plan")
    async def admin_sku_gen_plan(request: Request):
        require_admin(request)
        form = await request.form()
        sku = str(form.get("sku") or "").strip()
        if not sku:
            return images_page(request, 400, gen_error="先填写要算规格图的货号。")
        row = conn.execute(
            "select sku, image_url, listing, offers, gen_at, published from products where sku = ?",
            (sku,),
        ).fetchone()
        if row is None:
            return images_page(request, 400, gen_error="没有这个商品。")
        rows = plan_sku_product(row, root=ROOT)
        request.state.sku_gen_plan = {
            "sku": sku,
            "rows": rows,
            "generate": sum(1 for item in rows if item["action"] == "generate"),
            "skip": sum(1 for item in rows if item["action"] != "generate"),
        }
        return images_page(request)

    @app.post("/admin/images/sku/one")
    async def admin_sku_gen_one(request: Request):
        """把这一件商品待出的规格图（按张）放进 SKU 队列。"""
        require_admin(request)
        missing = gen_ready_or_error()
        if missing:
            return images_page(request, 400, gen_error=missing)
        form = await request.form()
        sku = str(form.get("sku") or "").strip()
        force = str(form.get("force") or "").strip() in {"1", "true", "on", "yes"}
        if not sku:
            return images_page(request, 400, gen_error="先填写要出规格图的货号。")
        row = conn.execute(
            "select sku, image_url, listing, offers, gen_at, published from products where sku = ?",
            (sku,),
        ).fetchone()
        if row is None:
            return images_page(request, 400, gen_error="没有这个商品。")
        if not has_pending_sku_shot(row, force=force, root=ROOT):
            return images_page(request, 400, gen_error="这个商品没有要出的规格图（已生成的会跳过，除非勾选强制）。")
        if not gen_editors():
            return images_page(request, 400, gen_error="先保存生图 API 密钥，或连上至少一张显卡。")
        units = list(list_pending_sku_shot_units(conn, root=ROOT, force=force, product_sku=sku))
        added = enqueue_sku_shots(conn, units, force=force)
        app.state.sku_gen_queue_snapshot = None
        app.state.sku_gen_left_cache = None
        if not added:
            return images_page(request, 400, gen_error="没有新的规格图可入队（可能已在队列里）。")
        app.state.sku_gen_armed = True
        ensure_sku_supervisor()
        return RedirectResponse("/admin/images", status_code=303)

    @app.post("/admin/images/sku/rest")
    async def admin_sku_gen_rest(request: Request):
        """把已上架、仍缺的规格图按「张」全部放进 SKU 队列。不碰主图。"""
        require_admin(request)
        missing = gen_ready_or_error()
        if missing:
            return images_page(request, 400, gen_error=missing)
        if gen_is_paused():
            return images_page(request, 400, gen_error="生图已暂停。先点「继续生图」。")
        form = await request.form()
        force = str(form.get("force") or "").strip() in {"1", "true", "on", "yes"}
        units = list(list_pending_sku_shot_units(conn, root=ROOT, force=force))
        for row in conn.execute(
            "select id, product_sku, image from sku_gen_tasks where status = 'failed'"
        ).fetchall():
            units.append({
                "id": row["id"],
                "product_sku": row["product_sku"],
                "image": row["image"],
                "label": "",
            })
        seen = set()
        unique_units = []
        for unit in units:
            tid = unit.get("id") or ""
            if not tid or tid in seen:
                continue
            held = conn.execute(
                "select status from sku_gen_tasks where id = ?", (tid,)
            ).fetchone()
            if held and held["status"] in ("pending", "running") and not force:
                continue
            seen.add(tid)
            unique_units.append(unit)
        added = enqueue_sku_shots(conn, unique_units, force=force)
        app.state.sku_gen_queue_snapshot = None
        app.state.sku_gen_left_cache = None
        if not added:
            return images_page(request, 400, gen_error="没有还要出的规格图。失败的已补完，或都在队列里。")
        app.state.sku_gen_armed = True
        ensure_sku_supervisor()
        return RedirectResponse("/admin/images", status_code=303)

    @app.post("/admin/catalog/purge-intercept")
    def admin_purge_intercept(request: Request):
        """按拦截删除规则清理存量：整件未上架删商品，部分只删规格。"""
        require_admin_role(request)
        result = purge_intercepted_products()
        return RedirectResponse(
            "/admin/products?section=import&purged=%s&stripped=%s&offers=%s"
            % (result["deleted_products"], result["stripped_products"], result["deleted_offers"]),
            status_code=303,
        )


    def products_missing_story(lang):
        """Published products with no pictures in this language yet."""
        lang = str(lang or "").strip()
        cached = getattr(app.state, "story_missing_cache", None)
        now = time.time()
        if cached and cached.get("lang") == lang and now - cached.get("at", 0) < 60:
            return list(cached["skus"])
        missing = []
        root = ROOT / "static" / "catalog"
        image_ext = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
        for row in conn.execute("select sku from products where published = 1").fetchall():
            sku = str(row["sku"] or "")
            if not sku or ".." in sku or "/" in sku or "\\" in sku:
                continue
            base = root / sku / lang
            if base.is_dir() and any(
                item.is_file() and item.suffix.lower() in image_ext for item in base.iterdir()
            ):
                continue
            if missing_story_slots(ROOT, sku, lang):
                missing.append(sku)
        app.state.story_missing_cache = {"lang": lang, "skus": missing, "at": now}
        if lang == "en":
            app.state.story_left_cache = {"n": len(missing), "at": now}
            app.state.story_products_left = len(missing)
        return missing

    def products_without_story():
        """Products that do not yet have the English 3 + 5 set."""
        return len(products_missing_story("en"))

    def remaining_images():
        if image_job_read().get("running"):
            return 0
        missing = products_without_story()
        app.state.story_products_left = missing
        return missing * 8

    def persist_item(item):
        for index, offer in enumerate(item["offers"]):
            offer["image"] = pull(offer.get("image") or "", item["sku"], index)
        item["image_url"] = next((offer["image"] for offer in item["offers"] if offer["image"]), "") or item.get("image_url") or ""
        saved_details = []
        for index, url in enumerate(item["listing"].get("detail_images") or []):
            local = pull(url, item["sku"], f"d{index}")
            if local and local not in saved_details:
                saved_details.append(local)
        item["listing"]["detail_images"] = saved_details
        names, bullets, description = blank_copy()
        specs = {
            "material": "",
            "size": item["listing"].get("size") or "",
            "weight": item["listing"].get("weight") or "",
        }
        store_item(item, names, bullets, description, specs, 0)

    def run_upload(raw, filename, is_zip, list_rate, sale_rate, grams_per_dollar, hold_percent):
        try:
            if is_zip:
                upload_job_update(phase="读取压缩包", done=0, total=0, label="正在拆开压缩包")
                groups = read_package(raw, list_rate, sale_rate, grams_per_dollar, hold_percent)
            else:
                upload_job_update(phase="读取表格", done=0, total=0, label="")
                items = parse_sheet(raw, filename)
                ready, errors = apply_prices(items, None)
                if not ready:
                    raise AlibabaFormatError(errors[0] if errors else "没有导入任何商品。")
                for item in ready:
                    item["source_cents"] = item["price_cents"]
                    label = item["listing"].get("variant") or item["listing"].get("color") or ""
                    priced = sku_price(
                        item["source_cents"], item["listing"].get("weight"), label, list_rate, sale_rate,
                        grams_per_dollar, hold_percent,
                    )
                    item["original_cents"] = priced["original_cents"]
                    item["price_cents"] = priced["price_cents"]
                    item["grams"] = priced["grams"]
                    item["hold"] = hold_reason(hold_percent) if priced["hold"] else ""
                groups = group_rows(ready)
            kept = []
            price_held = 0
            for item in groups:
                cleaned = apply_intercept_rules(item)
                if cleaned is None:
                    price_held += 1
                    continue
                kept.append(cleaned)
            groups = kept
            total = len(groups)
            imported = 0
            for index, item in enumerate(groups, 1):
                upload_job_update(phase="保存商品", done=index - 1, total=total, label=item.get("title") or item["sku"])
                if is_zip:
                    _plant_package_images(item)
                persist_item(item)
                imported = index
                upload_job_update(
                    done=index,
                    result={"imported": imported, "held": imported, "skipped": 0, "published": 0, "failed": 0},
                )
            forget_catalog()
            upload_job_update(url=f"/admin/products?section=import&imported={imported}&held={imported}&skipped=0")
        except (PackageError, AlibabaFormatError) as exc:
            upload_job_update(error=str(exc), url="/admin/products?section=import")
        except Exception:
            upload_job_update(error="上传没有完成。", url="/admin/products?section=import")
        finally:
            upload_job_update(running=False, workers=0)

    def run_commit_queue(packages, list_rate, sale_rate, grams_per_dollar, hold_percent):
        imported = 0
        skipped = 0
        images_filled = 0
        price_held = 0
        try:
            package_total = len(packages)
            for pack_index, package in enumerate(packages, 1):
                token = package.get("token")
                filename = str(package.get("filename") or "package.zip")
                path = preview_zip_path(token)
                if path is None or not path.is_file():
                    raise PackageError(f"数据包丢失：{filename}")
                raw = path.read_bytes()
                upload_job_update(
                    phase=f"读取压缩包 {pack_index}/{package_total}",
                    done=imported + skipped + images_filled,
                    total=0,
                    label=filename,
                )
                preview_products = preview_sheets(
                    [(raw, filename)], list_rate, sale_rate, grams_per_dollar, hold_percent,
                )
                upload_job_update(
                    phase=f"配图 {pack_index}/{package_total}",
                    done=imported + skipped + images_filled,
                    total=0,
                    label=filename,
                )
                loaded = read_package(
                    raw, list_rate, sale_rate, grams_per_dollar, hold_percent, skip_held_images=True,
                )
                by_cargo = {
                    (item["listing"].get("cargo") or item["sku"]): item
                    for item in loaded
                }
                groups = []
                for item in preview_products:
                    cargo = item["listing"].get("cargo") or item["sku"]
                    loaded_item = by_cargo.get(cargo)
                    if loaded_item is None:
                        # 整件拦截：不再入库，计入本批定价拦截。
                        price_held += 1
                        continue
                    # 再保险：若预览回退带 hold，按删除规则剥掉。
                    cleaned = apply_intercept_rules(loaded_item)
                    if cleaned is None:
                        price_held += 1
                        continue
                    groups.append(cleaned)
                total = len(groups)
                for index, item in enumerate(groups, 1):
                    label = f"[{pack_index}/{package_total}] {item.get('title') or item['sku']}"
                    upload_job_update(
                        phase=f"保存商品 {pack_index}/{package_total}",
                        done=imported + skipped + images_filled,
                        total=max(imported + skipped + images_filled + (total - index + 1), 1),
                        label=label,
                    )
                    existing = conn.execute(
                        "select sku, published from products where sku = ?",
                        (item["sku"],),
                    ).fetchone()
                    if existing is not None:
                        filled = False
                        try:
                            filled = fill_saved_product_images(conn, item)
                        except Exception:
                            filled = False
                        if filled:
                            images_filled += 1
                        else:
                            skipped += 1
                        upload_job_update(
                            done=imported + skipped + images_filled,
                            result={
                                "imported": imported,
                                "held": max(imported - price_held, 0),
                                "price_held": price_held,
                                "skipped": skipped,
                                "images_filled": images_filled,
                                "published": 0,
                                "failed": 0,
                            },
                        )
                        continue
                    has_bytes = any(
                        isinstance(offer.get("image"), (bytes, bytearray)) and offer.get("image")
                        for offer in item.get("offers") or []
                    )
                    if item.get("mains") or item.get("details") or has_bytes:
                        _plant_package_images(item)
                    else:
                        item.pop("mains", None)
                        item.pop("details", None)
                        for offer in item.get("offers") or []:
                            if isinstance(offer.get("image"), (bytes, bytearray)):
                                offer["image"] = ""
                    persist_item(item)
                    imported += 1
                    if (item.get("listing") or {}).get("hold"):
                        price_held += 1
                    upload_job_update(
                        done=imported + skipped + images_filled,
                        result={
                            "imported": imported,
                            "held": max(imported - price_held, 0),
                            "price_held": price_held,
                            "skipped": skipped,
                            "images_filled": images_filled,
                            "published": 0,
                            "failed": 0,
                        },
                    )
                drop_preview_package(token)
                save_catalog_queue([
                    item for item in load_catalog_queue() if item.get('token') != token
                ])
            # Only the packages in this commit were dropped above; keep any packages
            # analyzed concurrently during upload so「分析重量」can run in parallel.
            committed = {str(p.get("token") or "") for p in packages}
            leftovers = [item for item in load_catalog_queue() if str(item.get("token") or "") in committed]
            for item in leftovers:
                drop_preview_package(item.get("token"))
            save_catalog_queue([
                item for item in load_catalog_queue() if str(item.get("token") or "") not in committed
            ])
            forget_catalog()
            wait_n = max(imported - price_held, 0)
            save_last_upload({
                "finished_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "packages": [
                    {
                        "filename": str(p.get("filename") or "package.zip"),
                        "token": p.get("token") or "",
                    }
                    for p in packages
                ],
                "package_count": len(packages),
                "imported": imported,
                "wait_translate": wait_n,
                "price_held": price_held,
                "skipped": skipped,
                "images_filled": images_filled,
            })
            upload_job_update(
                url="/admin/products?section=import",
                result={
                    "imported": imported,
                    "held": wait_n,
                    "price_held": price_held,
                    "skipped": skipped,
                    "images_filled": images_filled,
                    "published": 0,
                    "failed": 0,
                },
            )
        except PackageError as exc:
            upload_job_update(error=str(exc), url="/admin/products?section=import")
        except Exception:
            upload_job_update(error="上传没有完成。", url="/admin/products?section=import")
        finally:
            upload_job_update(running=False, workers=0)

    def run_commit(raw, list_rate, sale_rate, grams_per_dollar, hold_percent, token):
        run_commit_queue(
            [{"token": token, "filename": "package.zip"}],
            list_rate,
            sale_rate,
            grams_per_dollar,
            hold_percent,
        )

    def translate_failure(exc):
        name = type(exc).__name__
        text = str(exc).lower()
        unreachable = (
            any(token in name for token in ("Connect", "Proxy"))
            or "10060" in text
            or "10061" in text
        )
        if unreachable:
            active = outbound_proxy()
            remembered = remembered_proxy()
            if active:
                where = f"当前代理 {active} 连不上。"
            elif remembered:
                where = f"系统里记过代理 {remembered}，但没有启用。"
            else:
                where = "请先打开代理。"
            return f"连不上翻译接口，一件都没有译成，也没有上架。{where}打开后再点「翻译并上架」。"
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status == 401 or "unauthorized" in text:
            return "翻译接口拒绝了密钥。商品没有上架。请重新保存密钥后再译。"
        return ""

    def run_translate():
        stats = {"published": 0, "failed": 0, "error": ""}
        counter = threading.Lock()
        stop = threading.Event()
        try:
            translate = active_translator()
            rows = []
            for row in conn.execute("select * from products where published = 0").fetchall():
                if load_object(row["listing"]).get("hold"):
                    continue
                rows.append(dict(row))
            total = len(rows)
            workers = min(CURSOR_LANES, total) or 1
            translate_job_update(phase="翻译", done=0, total=total, workers=workers, label="同时翻译")
            prepare_cursor_lanes(setting("ai_key"))
            auth_misses = {"n": 0}

            def one(row):
                if stop.is_set():
                    return
                title = load_object(row["listing"]).get("title") or row["sku"]
                ok = False
                try:
                    with cursor_product():
                        ok = publish_row(row, translate, judge=False)
                except Exception as exc:
                    message = translate_failure(exc)
                    with counter:
                        if message and not stats["error"]:
                            stats["error"] = message
                        if message.startswith("翻译接口拒绝了密钥"):
                            auth_misses["n"] += 1
                            if auth_misses["n"] >= 8:
                                stop.set()
                with counter:
                    if ok:
                        stats["published"] += 1
                        auth_misses["n"] = 0
                    else:
                        stats["failed"] += 1
                    published = stats["published"]
                    failed = stats["failed"]
                    done = published + failed
                translate_job_update(
                    done=done,
                    label=title,
                    result={"imported": 0, "held": 0, "skipped": 0, "published": published, "failed": failed},
                )

            with ThreadPoolExecutor(max_workers=workers) as pool:
                list(pool.map(one, rows))
            if stats["published"]:
                translate_job_update(phase="判断国家", label="这一批标题")
                _remember_batch([row["sku"] for row in rows])
            forget_catalog()
            if stop.is_set() and stats["error"]:
                translate_job_update(
                    phase="翻译未完成",
                    error=stats["error"],
                    url="/admin/products?section=import",
                )
            elif stats["published"]:
                translate_job_update(error="", url="/admin/products?section=import")
            elif stats["error"]:
                translate_job_update(phase="翻译未完成", error=stats["error"], url="/admin/products?section=import")
            else:
                translate_job_update(url="/admin/products?section=import")
        except Exception:
            translate_job_update(error="翻译没有完成，商品仍是待翻译，没有上架。", url="/admin/products?section=import")
        finally:
            translate_job_update(running=False, workers=0)

    @app.get("/admin/catalog/progress")
    def admin_catalog_progress(request: Request):
        require_admin(request)
        return JSONResponse(job_read())

    def part_folder(upload_id):
        if not re.fullmatch(r"[0-9a-f]{16}", str(upload_id or "")):
            return None
        return preview_root / "parts" / upload_id

    def part_status_payload(upload_id):
        folder = part_folder(upload_id)
        if folder is None:
            return {"ok": False, "error": "上传编号不对。"}, 400
        if not folder.is_dir():
            return {
                "ok": True,
                "upload_id": upload_id,
                "total": 0,
                "received": [],
                "missing": [],
                "complete": False,
                "bytes": 0,
            }, 200
        total = 0
        total_path = folder / "total"
        if total_path.is_file():
            try:
                total = int(total_path.read_text(encoding="utf-8").strip())
            except ValueError:
                total = 0
        received = []
        bytes_done = 0
        for path in sorted(folder.glob("*.part")):
            try:
                index = int(path.stem)
            except ValueError:
                continue
            received.append(index)
            try:
                bytes_done += path.stat().st_size
            except OSError:
                pass
        received = sorted(set(received))
        missing = [i for i in range(total) if i not in set(received)] if total else []
        meta = {}
        meta_path = folder / "meta.json"
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                meta = {}
        return {
            "ok": True,
            "upload_id": upload_id,
            "total": total,
            "received": received,
            "missing": missing,
            "complete": bool(total) and not missing,
            "bytes": bytes_done,
            "filename": meta.get("filename") or "",
            "size": meta.get("size") or 0,
        }, 200

    @app.get("/admin/catalog/parts")
    def admin_catalog_parts(request: Request):
        require_admin(request)
        upload_id = str(request.query_params.get("upload_id") or "")
        payload, status = part_status_payload(upload_id)
        return JSONResponse(payload, status_code=status)

    @app.post("/admin/catalog/part")
    async def admin_catalog_part(request: Request):
        require_admin(request)
        try:
            form = await request.form(max_part_size=9 * 1024 * 1024)
        except Exception as exc:
            return JSONResponse({"error": f"分块解析失败：{exc}"}, status_code=400)
        try:
            folder = part_folder(form.get("upload_id"))
            if folder is None:
                return JSONResponse({"error": "上传编号不对。"}, status_code=400)
            try:
                index = int(form.get("index"))
                total = int(form.get("total"))
            except (TypeError, ValueError):
                return JSONResponse({"error": "分块编号不对。"}, status_code=400)
            if total < 1 or total > 512 or index < 0 or index >= total:
                return JSONResponse({"error": "数据包超过 2GB，或分块编号不对。"}, status_code=400)
            upload = form.get("chunk")
            data = await upload.read() if upload is not None else b""
            if not data or len(data) > 8 * 1024 * 1024:
                return JSONResponse({"error": "这一块是空的，或超过 8MB。"}, status_code=400)
            folder.mkdir(parents=True, exist_ok=True)
            part_path = folder / f"{index:06d}.part"
            if part_path.is_file() and part_path.stat().st_size == len(data):
                # identical chunk already on disk — skip rewrite
                pass
            else:
                part_path.write_bytes(data)
            (folder / "total").write_text(str(total), encoding="utf-8")
            filename = str(form.get("filename") or "").strip()
            try:
                size = int(form.get("size") or 0)
            except (TypeError, ValueError):
                size = 0
            if filename or size:
                meta_path = folder / "meta.json"
                meta = {}
                if meta_path.is_file():
                    try:
                        meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    except Exception:
                        meta = {}
                if filename:
                    meta["filename"] = filename
                if size:
                    meta["size"] = size
                meta["total"] = total
                meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
            return JSONResponse({"ok": True, "index": index, "total": total, "skipped": False})
        except Exception as exc:
            return JSONResponse({"error": f"分块保存失败：{exc}"}, status_code=500)

    @app.post("/admin/catalog/assemble")
    async def admin_catalog_assemble(request: Request):
        require_admin(request)
        try:
            form = await request.form()
            upload_id = str(form.get("upload_id") or "")
            folder = part_folder(upload_id)
            if folder is None or not (folder / "total").is_file():
                return JSONResponse({"error": "这次上传已经过期，请重新选择数据包。"}, status_code=400)
            try:
                total = int((folder / "total").read_text(encoding="utf-8"))
            except ValueError:
                return JSONResponse({"error": "分块记录坏了，请重新选择数据包。"}, status_code=400)
            if total < 1 or total > 512:
                return JSONResponse({"error": "数据包超过 2GB。"}, status_code=400)
            missing = []
            pieces = []
            size = 0
            for index in range(total):
                path = folder / f"{index:06d}.part"
                if not path.is_file():
                    missing.append(index)
                    continue
                data = path.read_bytes()
                size += len(data)
                if size > 2 * 1024 * 1024 * 1024:
                    return JSONResponse({"error": "数据包超过 2GB。"}, status_code=400)
                pieces.append(data)
            if missing:
                return JSONResponse(
                    {
                        "error": f"还有 {len(missing)} 个分块没到，请再点「分析重量」续传。",
                        "missing": missing,
                        "total": total,
                        "received": [i for i in range(total) if i not in set(missing)],
                    },
                    status_code=400,
                )
            raw = b"".join(pieces)
            shutil.rmtree(folder, ignore_errors=True)
            if raw[:2] != b"PK":
                return JSONResponse({"error": "这不是 zip 数据包。"}, status_code=400)
            rules = pricing_rules()
            filename = str(form.get("filename") or "package.zip").strip() or "package.zip"
            try:
                save_preview(
                    secrets.token_hex(8),
                    raw,
                    rules["list_rate"],
                    rules["sale_rate"],
                    rules["grams_per_dollar"],
                    rules["hold_percent"],
                    True,
                    filename=filename,
                    replace_all=False,
                )
            except PackageError as exc:
                return JSONResponse({"error": str(exc)}, status_code=400)
            queue = load_catalog_queue()
            return JSONResponse({"ok": True, "queued": len(queue), "filename": filename})
        except Exception as exc:
            return JSONResponse({"error": f"合并分析失败：{exc}"}, status_code=500)

    @app.post("/admin/catalog/preview")
    async def admin_catalog_preview(request: Request):
        require_admin(request)
        form = await request.form(max_part_size=10**18)
        upload = form.get("file")
        name = str(getattr(upload, "filename", "") or "")
        raw = await upload.read() if upload is not None and name else b""
        if not raw or not name.lower().endswith(".zip"):
            return product_page(request, 400, "请上传整个商品数据包 zip。每个商品的表格都在里面，这一步只读表格。", section="import")
        rules = pricing_rules()
        quoted = quoted_rates(form, rules)
        if quoted is None:
            return product_page(request, 400, "原价倍率、售价倍率要大于 0，拦截百分比从 0 到 1000，多少克 1 美元要大于 0。", section="import")
        list_rate, sale_rate, hold_percent, grams_per_dollar = quoted
        try:
            save_preview(
                secrets.token_hex(8),
                raw,
                list_rate,
                sale_rate,
                grams_per_dollar,
                hold_percent,
                True,
                filename=name,
                replace_all=False,
            )
        except PackageError as exc:
            return product_page(request, 400, str(exc), section="import")
        return RedirectResponse("/admin/products?section=import", status_code=303)

    @app.post("/admin/catalog/reprice")
    async def admin_catalog_reprice(request: Request):
        require_admin(request)
        form = await request.form()
        preview = load_catalog_preview()
        queue = load_catalog_queue()
        token = str(form.get("token") or "")
        if preview is None or not queue:
            return product_page(request, 400, "这次分析已经过期，请重新上传商品数据包。", section="import")
        if token not in {"queue", *(item.get("token") for item in queue)}:
            return product_page(request, 400, "这次分析已经过期，请重新上传商品数据包。", section="import")
        quoted = quoted_rates(form, preview)
        if quoted is None:
            return product_page(request, 400, "原价倍率、售价倍率要大于 0，拦截百分比从 0 到 1000，多少克 1 美元要大于 0。", section="import")
        list_rate, sale_rate, hold_percent, grams_per_dollar = quoted
        queue = load_catalog_queue()
        if not queue:
            return product_page(request, 400, "这次分析已经过期，请重新上传商品数据包。", section="import")
        try:
            for item in queue:
                item_token = item.get("token")
                item_path = preview_zip_path(item_token)
                if item_path is None or not item_path.is_file():
                    return product_page(request, 400, "这次分析已经过期，请重新上传商品数据包。", section="import")
                save_preview(
                    item_token,
                    item_path.read_bytes(),
                    list_rate,
                    sale_rate,
                    grams_per_dollar,
                    hold_percent,
                    False,
                    filename=item.get("filename") or "package.zip",
                    replace_all=False,
                )
        except PackageError as exc:
            return product_page(request, 400, str(exc), section="import")
        return RedirectResponse("/admin/products?section=import", status_code=303)

    @app.post("/admin/catalog/commit")
    async def admin_catalog_commit(request: Request):
        require_admin(request)
        if upload_job_busy():
            return product_page(request, 400, "上一批上传还在处理，等上传进度走完再点「开始上传」。", section="import")
        form = await request.form()
        preview = load_catalog_preview()
        queue = load_catalog_queue()
        token = str(form.get("token") or "")
        if preview is None or not queue:
            return product_page(request, 400, "这次分析已经过期，请重新上传商品数据包。", section="import")
        if token not in {"queue", *(item.get("token") for item in queue)}:
            return product_page(request, 400, "这次分析已经过期，请重新上传商品数据包。", section="import")
        for item in queue:
            path = preview_zip_path(item.get("token"))
            if path is None or not path.is_file():
                return product_page(request, 400, "这次分析已经过期，请重新上传商品数据包。", section="import")
        quoted = quoted_rates(form, preview)
        if quoted is None:
            return product_page(request, 400, "原价倍率、售价倍率要大于 0，拦截百分比从 0 到 1000，多少克 1 美元要大于 0。", section="import")
        list_rate, sale_rate, hold_percent, grams_per_dollar = quoted
        store_pricing(list_rate, sale_rate, hold_percent, grams_per_dollar)
        packages = []
        seen_names = set()
        # walk newest→oldest so last analyze of a filename wins, then restore order
        for item in reversed(queue):
            fname = str(item.get("filename") or "package.zip")
            key = fname.casefold()
            if key in seen_names:
                # stale duplicate left in queue — drop zip so it cannot be re-committed
                drop_preview_package(item.get("token"))
                continue
            seen_names.add(key)
            packages.append({"token": item.get("token"), "filename": fname})
        packages.reverse()
        if len(packages) != len(queue):
            save_catalog_queue([
                item for item in queue
                if str(item.get("filename") or "package.zip").casefold() in {
                    str(p["filename"]).casefold() for p in packages
                } and item.get("token") in {p["token"] for p in packages}
            ])
        upload_job_update(
            running=True,
            kind="upload",
            phase="读取压缩包",
            done=0,
            total=0,
            label=f"共 {len(packages)} 个数据包",
            error="",
            url="",
            workers=0,
            result={"imported": 0, "held": 0, "skipped": 0, "published": 0, "failed": 0},
        )
        threading.Thread(
            target=run_commit_queue,
            args=(packages, list_rate, sale_rate, grams_per_dollar, hold_percent),
            daemon=True,
        ).start()
        return RedirectResponse("/admin/products?section=import", status_code=303)

    @app.post("/admin/pricing")
    async def admin_pricing(request: Request):
        require_admin_role(request)
        form = await request.form()
        list_rate = parse_rate(form.get("list_rate"))
        sale_rate = parse_rate(form.get("sale_rate"))
        hold_percent = parse_percent(form.get("hold_percent"))
        grams_per_dollar = parse_rate(form.get("grams_per_dollar"))
        if (
            list_rate is None
            or sale_rate is None
            or hold_percent is None
            or grams_per_dollar is None
            or hold_percent > 1000
            or grams_per_dollar > 100000
        ):
            return product_page(
                request,
                400,
                "定价规则填原价倍率、售价倍率、拦截百分比，还有多少克卖 1 美元。倍率要大于 0，百分比从 0 到 1000，克数要大于 0。",
            )
        store_pricing(list_rate, sale_rate, hold_percent, grams_per_dollar)
        return RedirectResponse("/admin/products?section=pricing&pricing=saved", status_code=303)

    @app.post("/admin/catalog/file")
    async def admin_catalog_file(request: Request):
        require_admin(request)
        if upload_job_busy():
            return product_page(request, 400, "上一批上传还在处理，等上传进度走完再传。", section="import")
        form = await request.form(max_part_size=10**18)
        upload = form.get("file")
        if upload is None or not getattr(upload, "filename", ""):
            return product_page(request, 400, "请选择阿里巴巴导出的 CSV 或 Excel。", section="import")
        raw = await upload.read()
        if not raw:
            return product_page(request, 400, "文件是空的。", section="import")
        name = upload.filename.lower()
        is_zip = name.endswith(".zip") or (raw[:2] == b"PK" and not name.endswith((".xlsx", ".xlsm")))
        rules = pricing_rules()
        list_rate = parse_rate(form.get("list_rate"))
        sale_rate = parse_rate(form.get("sale_rate"))
        if list_rate is None or sale_rate is None:
            return product_page(
                request,
                400,
                "上架前要填写原价倍率和售价倍率。例如成本是 0.35 美元，售价倍率填 1.3，售价就是 0.46 美元；原价倍率填 2，原价就是 0.70 美元。两个都要填。",
                section="import",
            )
        if not is_zip and is_jushuitan_sheet(raw, upload.filename):
            return product_page(request, 400, "这是数据包里的表格。请到上面的「上传商品数据包」选整个 zip，只传一次。", section="import")
        filename = upload.filename
        upload_job_update(
            running=True,
            kind="upload",
            phase="读取文件",
            done=0,
            total=0,
            label="",
            error="",
            url="",
            workers=0,
            result={"imported": 0, "held": 0, "skipped": 0, "published": 0, "failed": 0},
        )
        threading.Thread(
            target=run_upload,
            args=(
                raw, filename, is_zip, list_rate, sale_rate,
                rules["grams_per_dollar"], rules["hold_percent"],
            ),
            daemon=True,
        ).start()
        return RedirectResponse("/admin/products?section=import", status_code=303)

    @app.post("/admin/catalog/publish")
    def admin_catalog_publish(request: Request):
        require_admin(request)
        if translate_job_busy():
            return product_page(request, 400, "上一批翻译还在处理，等翻译进度走完再点。", section="import")
        translate = active_translator()
        if translate is None:
            return product_page(
                request,
                400,
                "还没有 AI 密钥。在商品页填上密钥后再翻译。模型用 auto。没有密钥时不会把中文直接上架。",
                section="import",
            )
        waiting = 0
        for row in conn.execute("select listing from products where published = 0").fetchall():
            if load_object(row["listing"]).get("hold"):
                continue
            waiting += 1
        if not waiting:
            return RedirectResponse("/admin/products?section=import", status_code=303)
        translate_job_update(
            running=True,
            kind="translate",
            phase="翻译",
            done=0,
            total=waiting,
            label="",
            error="",
            url="",
            workers=min(CURSOR_LANES, waiting),
            result={"imported": 0, "held": 0, "skipped": 0, "published": 0, "failed": 0},
        )
        threading.Thread(target=run_translate, daemon=True).start()
        return RedirectResponse("/admin/products?section=import", status_code=303)

    @app.post("/admin/products/{sku}/translate")
    def admin_product_translate(request: Request, sku: str):
        require_admin(request)
        translate = active_translator()
        if translate is None:
            return product_page(
                request,
                400,
                "还没有 AI 密钥。在商品页填上密钥后再翻译。模型用 auto。没有密钥时不会把中文直接上架。",
                section="import",
            )
        row = conn.execute("select * from products where sku = ?", (sku,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404)
        prepare_cursor_lanes(setting("ai_key"))
        try:
            with cursor_product():
                ok = publish_row(row, translate)
        except Exception as exc:
            return product_page(request, 400, translate_failure(exc))
        if not ok:
            return product_page(request, 400, "这件商品没有标题，不能翻译。", section="import")
        forget_catalog()
        return RedirectResponse("/admin/products?section=import", status_code=303)

    @app.post("/admin/products/{sku}/copy")
    async def admin_product_copy(request: Request, sku: str):
        require_admin(request)
        row = conn.execute("select * from products where sku = ?", (sku,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404)
        form = await request.form()
        names = json.loads(row["names"])
        description = json.loads(row["description"])
        for lang in UI:
            value = str(form.get(f"name_{lang}") or "").strip()
            if value:
                names[lang] = value
        english = str(form.get("description_en") or "").strip()
        if english:
            description["en"] = english
        conn.execute(
            "update products set names = ?, description = ?, image_url = ? where sku = ?",
            (
                json.dumps(names),
                json.dumps(description),
                str(form.get("image_url") or row["image_url"] or ""),
                sku,
            ),
        )
        forget_catalog()
        return RedirectResponse("/admin/products", status_code=303)

    @app.exception_handler(404)
    async def missing(request: Request, exc):
        return render(request, "not_found.html", status_code=404)

    def hot_loop():
        while True:
            try:
                if stale(conn):
                    refresh_titles(conn)
                    reload_hot()
            except Exception:
                pass
            time.sleep(6 * 3600)

    if db_path != ":memory:":
        threading.Thread(target=hot_loop, daemon=True).start()


    try:
        ensure_cs_tables(conn)
        mount_support(app, conn=conn, render=render, require_staff=require_staff, buyer_email=buyer_email, get_translator=active_translator, get_complete=active_complete)
    except Exception as exc:
        print("support mount failed", exc)

    try:
        mount_mobile_api(
            app,
            view=view,
            catalog_rows=catalog_list_rows,
            catalog_index=catalog_index,
            present_card=present_card,
            present=present,
            home_feed_cards=home_feed_cards,
            ui=UI,
        )
    except Exception as exc:
        print("mobile api mount failed", exc)

    return app


app = create_app()
