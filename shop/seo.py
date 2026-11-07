ORIGIN = "https://linkiip.com"
OPEN_LANGS = ("en", "de", "es")
PREFIX = {"en": "", "de": "/de", "es": "/es"}

PRIVATE_EXACT = {
    "/cart",
    "/checkout",
    "/payment",
    "/search",
    "/login",
    "/register",
    "/sale",
    "/new",
    "/share",
    "/install",
    "/check-in",
    "/rewards",
    "/desktop",
    "/reset-password",
}
PRIVATE_PREFIX = ("/admin", "/account", "/orders", "/r/", "/lp")


def strip_prefix(path):
    text = (path or "/").split("?")[0]
    if not text.startswith("/"):
        text = "/" + text
    for code in ("de", "es"):
        head = f"/{code}"
        if text == head or text.startswith(head + "/"):
            text = text[len(head):] or "/"
            break
    if len(text) > 1 and text.endswith("/"):
        text = text[:-1]
    return text or "/"


def is_private(path):
    bare = strip_prefix(path)
    if bare in PRIVATE_EXACT:
        return True
    return any(bare == prefix or bare.startswith(prefix) for prefix in PRIVATE_PREFIX)


def page_title(name):
    text = " ".join(str(name or "").split())
    if not text or text == "Harbor":
        return "Harbor"
    if text.endswith("| Harbor"):
        return text
    return f"{text} | Harbor"


def first_sentence(text, limit=160):
    raw = " ".join(str(text or "").split())
    if not raw:
        return ""
    cut = len(raw)
    for mark in (". ", "! ", "? ", "。", "！", "？"):
        found = raw.find(mark)
        if found != -1:
            cut = min(cut, found + (1 if mark.strip() in ".!?。！？" else 0))
    sentence = raw[:cut].strip()
    if len(sentence) <= limit:
        return sentence
    return sentence[: limit - 1].rstrip() + "…"


def public_url(path, lang):
    bare = strip_prefix(path)
    code = lang if lang in OPEN_LANGS else "en"
    return ORIGIN + PREFIX[code] + bare


def hreflang_links(path):
    bare = strip_prefix(path)
    links = [(code, ORIGIN + PREFIX[code] + bare) for code in OPEN_LANGS]
    links.append(("x-default", ORIGIN + bare))
    return links


def absolute(url):
    text = str(url or "")
    if not text:
        return ""
    if text.startswith("http://") or text.startswith("https://"):
        return text
    if not text.startswith("/"):
        text = "/" + text
    return ORIGIN + text


def indexable_product(names, description, image, stock, price_cents, published=1):
    if not int(published or 0) or int(stock or 0) <= 0 or int(price_cents or 0) < 100:
        return False
    picture = str(image or "")
    if not picture or picture.endswith(".svg"):
        return False
    title = str((names or {}).get("en") or "").strip()
    about = str((description or {}).get("en") or "").strip()
    if not about or about == title:
        return False
    return True
