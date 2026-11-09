"""Shopper storefront theme.

Persisted in the ``settings`` table so templates and HTTP middleware can read
the same value. ``legacy`` keeps the current Harbor HTML. ``pimo`` renders the
Figma Pimo shopper chrome and home.
"""

THEME_KEY = "storefront_theme"
LEGACY = "legacy"
PIMO = "pimo"
THEMES = (LEGACY, PIMO)
DEFAULT = LEGACY


def normalize_theme(value) -> str:
    text = str(value or "").strip().lower()
    if text in THEMES:
        return text
    return ""


def get_storefront_theme(conn) -> str:
    try:
        row = conn.execute(
            "select value from settings where key = ?",
            (THEME_KEY,),
        ).fetchone()
    except Exception:
        return DEFAULT
    if row is None:
        return DEFAULT
    return normalize_theme(row["value"]) or DEFAULT


def set_storefront_theme(conn, value) -> str:
    theme = normalize_theme(value)
    if not theme:
        return get_storefront_theme(conn)
    conn.execute(
        "insert into settings (key, value) values (?, ?) "
        "on conflict(key) do update set value = excluded.value",
        (THEME_KEY, theme),
    )
    return theme
