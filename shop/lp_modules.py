"""Ad landing-page modules.

Five structural templates share one renderer. Category skins only recolor
the chrome. Kitchen is the master skin (navy header, flash accent).
"""

IMPULSE_MIN_CENTS = 100
IMPULSE_MAX_CENTS = 1000

BANDS = (
    {"id": "under_3", "label": "Under $3", "min": 100, "max": 299},
    {"id": "3_5", "label": "$3 – $5", "min": 300, "max": 499},
    {"id": "5_10", "label": "$5 – $10", "min": 500, "max": 1000},
)

TEMPLATES = (
    {
        "id": "dense_flash",
        "label_zh": "密铺闪购",
        "label_en": "Dense flash",
        "blurb_zh": "头图 + 倒计时 + 密铺商品 + 进站",
        "partial": "lp/dense_flash.html",
    },
    {
        "id": "hero_headline",
        "label_zh": "爆款头条",
        "label_en": "Headline SKU",
        "blurb_zh": "大号主推 SKU + 横滑列表",
        "partial": "lp/hero_headline.html",
    },
    {
        "id": "countdown_grid",
        "label_zh": "倒计时密铺",
        "label_en": "Countdown grid",
        "blurb_zh": "顶部倒计时 + 商品网格",
        "partial": "lp/countdown_grid.html",
    },
    {
        "id": "price_waterfall",
        "label_zh": "价格瀑布",
        "label_en": "Price waterfall",
        "blurb_zh": "$1–$10 价格带瀑布",
        "partial": "lp/price_waterfall.html",
    },
    {
        "id": "rush_flash",
        "label_zh": "抢购闪购",
        "label_en": "Rush flash",
        "blurb_zh": "抢购闪购壳 + 密铺",
        "partial": "lp/rush_flash.html",
    },
)

# Owner order: kitchen is the master; the rest are category color skins.
SKINS = (
    {"id": "kitchen", "label_zh": "厨房", "label_en": "Kitchen", "master": True, "accent": "#E85D04", "ink": "#9A3412", "wash": "#FFF7ED", "deep": "#C2410C"},
    {"id": "storage", "label_zh": "收纳", "label_en": "Storage", "master": False, "accent": "#0F766E", "ink": "#134E4A", "wash": "#F0FDFA", "deep": "#0F766E"},
    {"id": "cleaning", "label_zh": "清洁", "label_en": "Cleaning", "master": False, "accent": "#0369A1", "ink": "#0C4A6E", "wash": "#F0F9FF", "deep": "#0369A1"},
    {"id": "textile", "label_zh": "家纺", "label_en": "Textiles", "master": False, "accent": "#BE185D", "ink": "#831843", "wash": "#FDF2F8", "deep": "#BE185D"},
    {"id": "daily", "label_zh": "家居日用", "label_en": "Home basics", "master": False, "accent": "#A16207", "ink": "#713F12", "wash": "#FEFCE8", "deep": "#A16207"},
    {"id": "tableware", "label_zh": "餐具", "label_en": "Tableware", "master": False, "accent": "#B45309", "ink": "#7C2D12", "wash": "#FFFBEB", "deep": "#B45309"},
    {"id": "paper", "label_zh": "纸品护理", "label_en": "Paper and care", "master": False, "accent": "#4D7C0F", "ink": "#365314", "wash": "#F7FEE7", "deep": "#4D7C0F"},
    {"id": "personal", "label_zh": "个人护理", "label_en": "Personal care", "master": False, "accent": "#6D28D9", "ink": "#4C1D95", "wash": "#F5F3FF", "deep": "#6D28D9"},
    {"id": "beauty", "label_zh": "护肤", "label_en": "Skin care", "master": False, "accent": "#BE123C", "ink": "#881337", "wash": "#FFF1F2", "deep": "#BE123C"},
    {"id": "makeup", "label_zh": "彩妆", "label_en": "Makeup", "master": False, "accent": "#A21CAF", "ink": "#701A75", "wash": "#FDF4FF", "deep": "#A21CAF"},
    {"id": "decor", "label_zh": "家居装饰", "label_en": "Home decor", "master": False, "accent": "#047857", "ink": "#064E3B", "wash": "#ECFDF5", "deep": "#047857"},
    {"id": "appliance", "label_zh": "小家电", "label_en": "Appliances", "master": False, "accent": "#1D4ED8", "ink": "#1E3A8A", "wash": "#EFF6FF", "deep": "#1D4ED8"},
    {"id": "hardware", "label_zh": "五金工具", "label_en": "Tools", "master": False, "accent": "#44403C", "ink": "#292524", "wash": "#FAFAF9", "deep": "#44403C"},
    {"id": "pet", "label_zh": "宠物", "label_en": "Pet", "master": False, "accent": "#C026D3", "ink": "#86198F", "wash": "#FDF4FF", "deep": "#C026D3"},
    {"id": "office", "label_zh": "办公学习", "label_en": "Office and study", "master": False, "accent": "#1E40AF", "ink": "#1E3A8A", "wash": "#EEF2FF", "deep": "#1E40AF"},
    {"id": "party", "label_zh": "派对礼品", "label_en": "Party and gifts", "master": False, "accent": "#0E7490", "ink": "#155E75", "wash": "#ECFEFF", "deep": "#0E7490"},
)

TEMPLATE_BY_ID = {row["id"]: row for row in TEMPLATES}
SKIN_BY_ID = {row["id"]: row for row in SKINS}


class LpChoiceError(ValueError):
    def __init__(self, field):
        super().__init__(field)
        self.field = field


def resolve_module(template_id, category, skin_id=""):
    template_id = str(template_id or "").strip()
    category = str(category or "").strip()
    skin_id = str(skin_id or "").strip() or category
    tpl = TEMPLATE_BY_ID.get(template_id)
    if tpl is None:
        raise LpChoiceError("template")
    cat = SKIN_BY_ID.get(category)
    if cat is None:
        raise LpChoiceError("category")
    skin = SKIN_BY_ID.get(skin_id)
    if skin is None:
        raise LpChoiceError("skin")
    return {
        "template_id": tpl["id"],
        "template_label": tpl["label_zh"],
        "template_en": tpl["label_en"],
        "partial": tpl["partial"],
        "category": cat["id"],
        "category_en": cat["label_en"],
        "category_zh": cat["label_zh"],
        "skin_id": skin["id"],
        "skin_zh": skin["label_zh"],
        "master": bool(skin.get("master")),
        "accent": skin["accent"],
        "ink": skin["ink"],
        "wash": skin["wash"],
        "deep": skin["deep"],
    }


def band_groups(cards):
    """Split already-priced cards into the $1–$10 waterfall. Overflow is separate."""
    groups = []
    used = set()
    for band in BANDS:
        items = []
        for card in cards:
            cents = int(card.get("price_cents") or 0)
            if band["min"] <= cents <= band["max"]:
                items.append(card)
                used.add(card.get("sku"))
        if items:
            groups.append({**band, "items": items})
    overflow = [card for card in cards if card.get("sku") not in used]
    return groups, overflow
