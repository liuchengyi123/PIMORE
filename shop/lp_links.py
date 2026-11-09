"""Persisted Meta / TikTok landing links.

The public URL is /lp/ad/{code}. Template, category, and skin live on the
row so the link stays stable if the query string is stripped. UTM fields are
also written onto the share URL so the existing ad cookie still attributes.
"""

import secrets
from datetime import datetime, timezone
from urllib.parse import urlencode

from shop.images import safe_image_url
from shop.lp_modules import LpChoiceError, keeps_hero, needs_hero, resolve_module, uses_scene
from shop.seo import ORIGIN

UTM_KEYS = ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term")


def ensure_table(conn):
    conn.execute(
        """
        create table if not exists ad_launch_links (
            id integer primary key,
            code text not null unique,
            template text not null,
            category text not null,
            skin text not null default '',
            platform text not null default '',
            utm_source text not null default '',
            utm_medium text not null default '',
            utm_campaign text not null default '',
            utm_content text not null default '',
            utm_term text not null default '',
            acct text not null default '',
            country text not null default 'US',
            label text not null default '',
            hero_sku text not null default '',
            scene_image text not null default '',
            created_at text not null default ''
        )
        """
    )
    cols = {row[1] for row in conn.execute("pragma table_info(ad_launch_links)").fetchall()}
    if "hero_sku" not in cols:
        conn.execute(
            "alter table ad_launch_links add column hero_sku text not null default ''"
        )
    if "scene_image" not in cols:
        conn.execute(
            "alter table ad_launch_links add column scene_image text not null default ''"
        )


def clean_scene(value):
    """A scene image is a file we stored, or an http(s) picture. Nothing else."""
    text = str(value or "").strip()
    prefix = "/static/lp-scenes/"
    if text.startswith(prefix):
        name = text[len(prefix):]
        if name and "/" not in name and "\\" not in name and ".." not in name:
            return prefix + name
        return ""
    if safe_image_url(text):
        return text[:500]
    return ""


def _clip(value, limit):
    return " ".join(str(value or "").split())[:limit]


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _mint_code(conn):
    for _ in range(8):
        code = secrets.token_hex(4)
        found = conn.execute(
            "select 1 as ok from ad_launch_links where code = ?",
            (code,),
        ).fetchone()
        if found is None:
            return code
    raise RuntimeError("code")


def share_path(row):
    query = {"country": (row.get("country") or "US")}
    for key in UTM_KEYS:
        val = row.get(key) or ""
        if val:
            query[key] = val
    acct = row.get("acct") or ""
    if acct:
        query["acct"] = acct
    path = f"/lp/ad/{row['code']}?{urlencode(query)}"
    platform = (row.get("platform") or "").lower()
    if platform == "meta":
        path += "&adset_id={{adset.id}}&campaign_id={{campaign.id}}&ad_id={{ad.id}}"
    elif platform == "tiktok":
        path += "&adgroup_id=__AID__&campaign_id=__CAMPAIGN_ID__&ad_id=__CID__"
    return path


def absolute_url(path):
    text = str(path or "")
    if text.startswith("http://") or text.startswith("https://"):
        return text
    if not text.startswith("/"):
        text = "/" + text
    return ORIGIN + text


def preview_path(template, category, skin="", country="US", hero="", scene=""):
    query = {
        "template": template,
        "category": category,
        "skin": skin or category,
        "preview": "1",
        "country": (country or "US").upper()[:2],
    }
    hero = _clip(hero, 80)
    if hero:
        query["hero"] = hero
    scene = clean_scene(scene)
    if scene:
        query["scene"] = scene
    return "/lp/ad/preview?" + urlencode(query)


def _pack(row):
    if row is None:
        return None
    data = dict(row)
    data["path"] = share_path(data)
    data["url"] = absolute_url(data["path"])
    try:
        spec = resolve_module(data.get("template"), data.get("category"), data.get("skin"))
    except LpChoiceError:
        spec = None
    data["template_label"] = spec["template_label"] if spec else data.get("template") or ""
    data["category_zh"] = spec["category_zh"] if spec else data.get("category") or ""
    data["skin_zh"] = spec["skin_zh"] if spec else data.get("skin") or ""
    return data


def create_link(
    conn,
    *,
    template,
    category,
    skin="",
    platform="",
    utm_source="",
    utm_medium="",
    utm_campaign="",
    utm_content="",
    utm_term="",
    acct="",
    country="US",
    label="",
    hero_sku="",
    scene_image="",
):
    ensure_table(conn)
    spec = resolve_module(template, category, skin)
    hero_sku = _clip(hero_sku, 80)
    if needs_hero(spec["template_id"]):
        if not hero_sku:
            raise LpChoiceError("hero")
    elif not keeps_hero(spec["template_id"]):
        hero_sku = ""
    scene_image = clean_scene(scene_image) if uses_scene(spec["template_id"]) else ""
    country = _clip(country, 2).upper() or "US"
    if len(country) != 2 or not country.isalpha():
        country = "US"
    source = _clip(utm_source, 128) or _clip(platform, 32)
    code = _mint_code(conn)
    conn.execute(
        """
        insert into ad_launch_links (
            code, template, category, skin, platform,
            utm_source, utm_medium, utm_campaign, utm_content, utm_term,
            acct, country, label, hero_sku, scene_image, created_at
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            code,
            spec["template_id"],
            spec["category"],
            spec["skin_id"],
            _clip(platform, 32),
            source,
            _clip(utm_medium, 128),
            _clip(utm_campaign, 128),
            _clip(utm_content, 128),
            _clip(utm_term, 128),
            _clip(acct, 64),
            country,
            _clip(label, 80),
            hero_sku,
            scene_image,
            _now(),
        ),
    )
    return get_by_code(conn, code)


def get_by_code(conn, code):
    ensure_table(conn)
    text = str(code or "").strip().lower()
    if not text or any(ch not in "0123456789abcdef" for ch in text):
        return None
    row = conn.execute(
        "select * from ad_launch_links where code = ?",
        (text,),
    ).fetchone()
    return _pack(row)


def set_scene_image(conn, code, scene_image):
    ensure_table(conn)
    image = clean_scene(scene_image)
    row = get_by_code(conn, code)
    if row is None or not image or not uses_scene(row.get("template")):
        return None
    conn.execute(
        "update ad_launch_links set scene_image = ? where code = ?",
        (image, row["code"]),
    )
    return get_by_code(conn, row["code"])


def list_recent(conn, limit=30):
    ensure_table(conn)
    rows = conn.execute(
        "select * from ad_launch_links order by id desc limit ?",
        (max(1, min(int(limit or 30), 100)),),
    ).fetchall()
    return [_pack(row) for row in rows]
