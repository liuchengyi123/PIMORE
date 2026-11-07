import os
import re

LANGS = ("en", "es", "de", "fr", "pt", "ja")

# Chinese catalog terms that must stay stable. Longest phrases are applied first.
GLOSSARY = (
    ("不锈钢沥水架", "stainless steel dish rack"),
    ("沥水架", "dish rack"),
    ("喷油壶", "oil sprayer"),
    ("喷油瓶", "oil sprayer"),
    ("硅胶铲", "silicone spatula"),
    ("调味盒", "seasoning box"),
    ("量勺", "measuring spoons"),
    ("水槽过滤网", "sink strainer"),
    ("粘毛器", "lint roller"),
    ("缝隙刷", "gap brush"),
    ("百洁布", "cleaning cloth"),
    ("锅刷", "pot brush"),
    ("扫把簸箕", "dustpan set"),
    ("无痕挂钩", "adhesive hooks"),
    ("抽真空收纳袋", "vacuum storage bag"),
    ("抽屉分隔", "drawer divider"),
    ("缝隙置物架", "gap shelf"),
    ("衣柜挂袋", "closet hanging organizer"),
    ("折叠收纳箱", "folding storage bin"),
    ("发夹", "hair clips"),
    ("沐浴球", "bath sponge"),
    ("指甲刀", "nail clipper"),
    ("化妆棉盒", "cotton pad box"),
    ("牙刷架", "toothbrush holder"),
    ("拾便袋盒", "waste bag holder"),
    ("折叠宠物碗", "folding pet bowl"),
    ("舔食垫", "lick mat"),
    ("撸猫手套", "grooming glove"),
    ("笔筒", "pen cup"),
    ("长尾夹", "binder clips"),
    ("手机支架", "phone stand"),
    ("桌面收纳", "desk organizer"),
    ("理线夹", "cable clips"),
    ("便签座", "note holder"),
)

_MEASURE = re.compile(
    r"\d+(?:\.\d+)?\s?(?:cm|mm|ml|kg|pcs|pc|inch|in|oz|厘米|毫米|毫升|公斤|克|升|个装)",
    re.IGNORECASE,
)
_UNIT = (
    ("厘米", "cm"),
    ("毫米", "mm"),
    ("毫升", "ml"),
    ("公斤", "kg"),
    ("个装", " pcs"),
    ("克", "g"),
    ("升", "l"),
)


def _normalize_measure(raw):
    text = raw.strip()
    for src, dst in _UNIT:
        if text.endswith(src):
            return text[: -len(src)].strip() + dst
    return text


def shield(text, glossary=()):
    tokens = {}
    index = 0
    for src, dst in sorted(glossary, key=lambda pair: len(pair[0]), reverse=True):
        token = f"<k{index}/>"
        if src and src in text:
            text = text.replace(src, token)
            tokens[token] = dst
            index += 1
    def swap(match):
        nonlocal index
        token = f"<k{index}/>"
        index += 1
        tokens[token] = _normalize_measure(match.group(0))
        return token
    return _MEASURE.sub(swap, text), tokens


def restore(text, tokens):
    for token, value in tokens.items():
        text = text.replace(token, value)
    return re.sub(r"\s+", " ", text).strip()


def has_cjk(text):
    return any("\u4e00" <= ch <= "\u9fff" for ch in text or "")


def fill_from_english(texts, translate):
    out = {}
    for field, raw in texts.items():
        value = str(raw or "").strip()
        out[field] = {"en": value}
        for lang in LANGS:
            if lang == "en":
                continue
            if not value:
                out[field][lang] = ""
                continue
            hidden, tokens = shield(value)
            out[field][lang] = restore(translate(hidden, "en", lang), tokens)
    return out


def translate_fields(texts, translate):
    if any(has_cjk(value) for value in texts.values()):
        return fill_languages(texts, translate)
    return fill_from_english(texts, translate)


def fill_languages(texts, translate, glossary=GLOSSARY):
    english = {}
    for field, raw in texts.items():
        source = str(raw or "").strip()
        if not source:
            english[field] = ""
            continue
        hidden, tokens = shield(source, glossary)
        english[field] = restore(translate(hidden, "zh", "en"), tokens)
    out = {field: {"en": value} for field, value in english.items()}
    for lang in LANGS:
        if lang == "en":
            continue
        for field, value in english.items():
            if not value:
                out[field][lang] = ""
                continue
            hidden, tokens = shield(value)
            out[field][lang] = restore(translate(hidden, "en", lang), tokens)
    return out


def deepl_translate(text, source, target, key):
    import httpx

    host = "https://api-free.deepl.com" if key.endswith(":fx") else "https://api.deepl.com"
    targets = {"en": "EN-US", "es": "ES", "de": "DE", "fr": "FR", "pt": "PT-BR", "ja": "JA"}
    from shop.net import outbound_proxy

    response = httpx.post(
        f"{host}/v2/translate",
        proxy=outbound_proxy() or None,
        data={
            "text": text,
            "source_lang": "ZH" if source == "zh" else "EN",
            "target_lang": targets[target],
            "tag_handling": "xml",
            "ignore_tags": ",".join(f"k{i}" for i in range(24)),
        },
        headers={"Authorization": f"DeepL-Auth-Key {key}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["translations"][0]["text"]


def translator_from_env():
    key = os.environ.get("DEEPL_AUTH_KEY", "").strip()
    if not key:
        return None

    def translate(text, source, target):
        return deepl_translate(text, source, target, key)

    return translate
