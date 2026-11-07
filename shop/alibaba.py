import csv
import hashlib
import io
import re
from decimal import Decimal, ROUND_HALF_UP


class AlibabaFormatError(Exception):
    pass


_KNOWN = {
    "商品id", "产品id", "productid", "offerid",
    "商品标题", "产品名称", "商品名称", "标题", "productname", "subject",
    "关键词", "产品关键词", "keywords", "keyword",
    "类目", "类目名称", "产品类目", "category",
    "分组", "产品分组", "group", "groupname",
    "货号", "商品货号", "产品货号", "artno", "itemno",
    "型号", "model", "modelnumber",
    "fobprice", "fob价格", "美元价格", "价格usd", "priceusd",
    "价格", "单价", "批发价", "拿货价", "商品价格", "price", "unitprice",
    "币种", "货币", "currency", "moneytype",
    "起订量", "最小起订量", "起批量", "moq", "minorderquantity", "minorder",
    "单位", "计量单位", "unit",
    "库存", "可售数量", "stock", "inventory",
    "供货能力", "supplyability",
    "港口", "发货港", "发货港口", "port",
    "付款方式", "payment", "paymentterms",
    "交货期", "发货期", "deliverytime", "leadtime",
    "包装", "包装说明", "packaging", "packagingdetails",
    "重量", "毛重", "产品毛重", "weight", "grossweight",
    "尺寸", "规格尺寸", "size",
    "长", "宽", "高", "length", "width", "height",
    "材质", "材料", "material",
    "品牌", "brand", "brandname",
    "颜色", "color",
    "产地", "原产地", "placeoforigin", "origin",
    "详情", "商品详情", "产品描述", "描述", "description",
    "详情图", "详情图片", "宝贝详情", "宝贝描述",
    "详情地址", "详情链接", "详情图地址", "详情图片地址", "详情图片链接",
    "电脑详情", "手机详情", "商品详情图",
    "主图", "主图链接", "产品图片", "图片", "图片链接", "image", "imageurl", "mainimage",
    "商品链接", "产品链接", "链接", "producturl",
    "规格", "规格名称", "sku规格", "sku属性",
    "产品属性", "商品属性", "属性",
}

_TITLE = {"商品标题", "产品名称", "商品名称", "标题", "productname", "subject"}
_USD_PRICE = {"fobprice", "fob价格", "美元价格", "价格usd", "priceusd"}
_CNY_PRICE = {"价格", "单价", "批发价", "拿货价", "商品价格", "人民币价格"}
_USD_WORD = {"usd", "us$", "美元", "$"}
_CNY_WORD = {"cny", "rmb", "人民币", "元", "cnyuan"}
_ATTR_NAME = {
    "品牌": "brand",
    "材质": "material",
    "材料": "material",
    "颜色": "color",
    "尺寸": "size",
    "重量": "weight",
    "产地": "origin",
    "型号": "model",
    "货号": "cargo",
}



def norm(value):
    text = str(value or "").strip().lower()
    text = text.replace("*", "").replace("＊", "")
    text = re.sub(r"(必填|required)", "", text)
    return re.sub(r"[\s_\-./\\（）()【】\[\]：:,，]+", "", text)


def cell_text(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    return str(value).strip()


def plain_text(value):
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", value or "")
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()[:2000]


def _header_score(row):
    names = [norm(cell) for cell in row if norm(cell) in _KNOWN or norm(cell) in _TITLE]
    if not any(norm(cell) in _TITLE for cell in row):
        return 0
    return len(names)


def find_header(matrix):
    best_at = -1
    best = 0
    for index, row in enumerate(matrix[:30]):
        score = _header_score(row)
        if score > best:
            best = score
            best_at = index
    if best_at < 0 or best < 2:
        raise AlibabaFormatError("没有找到阿里巴巴表头。表里要有标题，以及价格、类目、货号这些列。")
    return best_at


def category_for(*parts):
    from shop.taxonomy import guess_parent

    text = " ".join(part for part in parts if part)
    return guess_parent(text) or "daily"


def _amount(value):
    match = re.search(r"\d[\d,]*(?:\.\d+)?", str(value or "").replace(" ", ""))
    if not match:
        return 0.0
    token = match.group(0)
    if "," in token and "." not in token:
        token = token.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{3})+", token) else token.replace(",", ".")
    else:
        token = token.replace(",", "")
    return float(token)


def to_cents(amount, money, cny_per_usd):
    del money, cny_per_usd
    if amount <= 0:
        return 0
    number = Decimal(str(amount))
    return int((number * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _images(value):
    return [part for part in re.split(r"[\s,，;；|]+", value or "") if part.startswith("http")]


def detail_image_urls(value):
    text = value or ""
    text = re.sub(r"(?i)(?<=[\"'\s(])//", "https://", text)
    text = re.sub(r"(?i)^//", "https://", text)
    found = []
    for tag in re.findall(r"(?is)<img\b[^>]*>", text):
        match = re.search(r"(?is)\b(?:data-src|src)\s*=\s*(?:([\"'])(.*?)\1|(\S+))", tag)
        url = (match.group(2) or match.group(3) or "").strip() if match else ""
        if url.startswith("http"):
            found.append(url)
    found.extend(_images(text))
    pictures = []
    for url in found:
        if url not in pictures:
            pictures.append(url)
    return pictures[:40]


def _attrs(value):
    found = []
    for part in re.split(r"[;；\n|]", value or ""):
        if ":" not in part and "：" not in part:
            continue
        name, raw = re.split(r"[:：]", part, maxsplit=1)
        name, raw = name.strip(), raw.strip()
        if name and raw:
            found.append({"name": name, "value": raw})
    return found


def _slug(value):
    text = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    if 2 <= len(text) <= 40:
        return text
    return ""


def suggest_sku(listing):
    cargo = _slug(listing.get("cargo"))
    if cargo:
        return cargo
    offer = re.sub(r"\D", "", listing.get("offer_id") or "")
    extra = " ".join(part for part in (listing.get("variant"), listing.get("color")) if part)
    if offer and extra:
        digest = hashlib.sha1(extra.encode()).hexdigest()[:6]
        return f"a-{offer[:16]}-{digest}"[:40]
    if offer:
        return f"a-{offer[:20]}"
    return "a-" + hashlib.sha1((listing.get("title") or "").encode()).hexdigest()[:10]


def _size(length, width, height, size):
    if size:
        return size
    dims = [part for part in (length, width, height) if part]
    if len(dims) < 2:
        return ""
    if all(re.fullmatch(r"\d+(?:\.\d+)?", part) for part in dims):
        return " × ".join(dims) + " cm"
    return " × ".join(dims)


def _money_of(header, raw_money, english_sheet):
    token = norm(raw_money)
    if token in _USD_WORD or "usd" in token or "美元" in token:
        return "USD"
    if token in _CNY_WORD or "人民币" in token or token == "元":
        return "CNY"
    if header in _USD_PRICE:
        return "USD"
    if header in {"price", "unitprice"} and english_sheet:
        return "USD"
    return "CNY"


def rows_to_items(matrix):
    header_at = find_header(matrix)
    header = [cell_text(cell) for cell in matrix[header_at]]
    while header and not header[-1]:
        header.pop()
    keys = [norm(cell) for cell in header]
    english_sheet = any(key in {"productname", "fobprice", "keywords"} for key in keys)
    items = []
    for raw in matrix[header_at + 1:]:
        cells = [cell_text(cell) for cell in raw]
        if not any(cells):
            continue
        bag = {}
        images = []
        attributes = []
        length = width = height = ""
        variant = ""
        for index, key in enumerate(keys):
            if index >= len(cells) or not key:
                continue
            value = cells[index]
            if not value:
                continue
            if key in _TITLE and "title" not in bag:
                bag["title"] = value
            elif key in {"商品id", "产品id", "productid", "offerid"}:
                bag["offer_id"] = value
            elif key in {"关键词", "产品关键词", "keywords", "keyword"}:
                bag["keywords"] = value
            elif key in {"类目", "类目名称", "产品类目", "category"}:
                bag["category_name"] = value
            elif key in {"分组", "产品分组", "group", "groupname"}:
                bag["group"] = value
            elif key in {"货号", "商品货号", "产品货号", "artno", "itemno"}:
                bag["cargo"] = value
            elif key in {"型号", "model", "modelnumber"}:
                bag["model"] = value
            elif key in _USD_PRICE or key in _CNY_PRICE or key in {"price", "unitprice", "人民币价格"}:
                previous = bag.get("price_header")
                if previous in _USD_PRICE and key not in _USD_PRICE:
                    continue
                bag["price_header"] = key
                bag["price_text"] = value
            elif key in {"币种", "货币", "currency", "moneytype"}:
                bag["money_text"] = value
            elif key in {"起订量", "最小起订量", "起批量", "moq", "minorderquantity", "minorder"}:
                bag["moq"] = value
            elif key in {"单位", "计量单位", "unit"}:
                bag["unit"] = value
            elif key in {"库存", "可售数量", "stock", "inventory"}:
                bag["stock_text"] = value
            elif key in {"供货能力", "supplyability"}:
                bag["supply"] = value
            elif key in {"港口", "发货港", "发货港口", "port"}:
                bag["port"] = value
            elif key in {"付款方式", "payment", "paymentterms"}:
                bag["payment"] = value
            elif key in {"交货期", "发货期", "deliverytime", "leadtime"}:
                bag["lead_time"] = value
            elif key in {"包装", "包装说明", "packaging", "packagingdetails"}:
                bag["packaging"] = value
            elif key in {"重量", "毛重", "产品毛重", "weight", "grossweight"}:
                bag["weight"] = value
            elif key in {"尺寸", "规格尺寸", "size"}:
                bag["size"] = value
            elif key == "长" or key == "length":
                length = value
            elif key == "宽" or key == "width":
                width = value
            elif key == "高" or key == "height":
                height = value
            elif key in {"材质", "材料", "material"}:
                bag["material"] = value
            elif key in {"品牌", "brand", "brandname"}:
                bag["brand"] = value
            elif key in {"颜色", "color"}:
                bag["color"] = value
            elif key in {"产地", "原产地", "placeoforigin", "origin"}:
                bag["origin"] = value
            elif "详情" in key or key in {"产品描述", "描述", "description", "宝贝描述"}:
                bag.setdefault("detail_images", []).extend(detail_image_urls(value))
                text = re.sub(r"https?://\S+", " ", plain_text(value))
                text = re.sub(r"\s+", " ", text).strip()
                pictures_only = key in {
                    "详情图", "详情图片", "宝贝详情", "详情地址", "详情链接",
                    "详情图地址", "详情图片地址", "详情图片链接",
                    "电脑详情", "手机详情", "商品详情图",
                } or "图" in key or "地址" in key
                if text and not pictures_only:
                    bag["description"] = text[:2000]
            elif key in {"商品链接", "产品链接", "链接", "producturl"} and value.startswith("http"):
                bag["url"] = value
            elif key in {"规格", "规格名称", "sku规格", "sku属性"}:
                variant = value
            elif key in {"产品属性", "商品属性", "属性"}:
                attributes.extend(_attrs(value))
            elif key in {"主图", "主图链接", "产品图片", "图片", "图片链接", "image", "imageurl", "mainimage"}:
                images.extend(_images(value))
        if not bag.get("title"):
            continue
        for attr in attributes:
            field = _ATTR_NAME.get(attr["name"])
            if field and not bag.get(field):
                bag[field] = attr["value"]
        money = _money_of(bag.get("price_header") or "", bag.get("money_text") or "", english_sheet)
        amount = _amount(bag.get("price_text"))
        stock_text = bag.get("stock_text") or ""
        stock = 100 if not stock_text else int(re.search(r"\d+", stock_text.replace(",", "")).group(0)) if re.search(r"\d+", stock_text) else 0
        listing = {
            "offer_id": bag.get("offer_id") or "",
            "title": bag["title"],
            "keywords": bag.get("keywords") or "",
            "category_name": bag.get("category_name") or "",
            "group": bag.get("group") or "",
            "cargo": bag.get("cargo") or "",
            "model": bag.get("model") or "",
            "variant": variant,
            "amount": amount,
            "money": money,
            "price_text": bag.get("price_text") or "",
            "moq": bag.get("moq") or "",
            "unit": bag.get("unit") or "",
            "supply": bag.get("supply") or "",
            "port": bag.get("port") or "",
            "payment": bag.get("payment") or "",
            "lead_time": bag.get("lead_time") or "",
            "packaging": bag.get("packaging") or "",
            "weight": bag.get("weight") or "",
            "size": _size(length, width, height, bag.get("size") or ""),
            "material": bag.get("material") or "",
            "brand": bag.get("brand") or "",
            "color": bag.get("color") or "",
            "origin": bag.get("origin") or "",
            "description": bag.get("description") or "",
            "detail_images": list(dict.fromkeys(bag.get("detail_images") or [])),
            "url": bag.get("url") or "",
            "images": images,
            "attributes": attributes,
        }
        items.append({
            "sku": suggest_sku(listing),
            "title": listing["title"],
            "category": category_for(listing["category_name"], listing["title"]),
            "amount": amount,
            "money": money,
            "stock": stock,
            "image_url": images[0] if images else "",
            "listing": listing,
        })
    if not items:
        raise AlibabaFormatError("表里没有商品。每一行需要标题和价格。")
    seen = set()
    for item in items:
        sku = item["sku"]
        number = 2
        while sku in seen:
            suffix = f"-{number}"
            sku = item["sku"][:40 - len(suffix)] + suffix
            number += 1
        seen.add(sku)
        item["sku"] = sku
    return items


def apply_prices(items, cny_per_usd):
    ready = []
    errors = []
    for item in items:
        cents = to_cents(item["amount"], item["money"], cny_per_usd)
        if cents <= 0:
            errors.append(f"{item['title']}：没有读到价格")
            continue
        item["price_cents"] = cents
        ready.append(item)
    return ready, errors


def read_csv(raw):
    text = ""
    chosen = None
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            candidate = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        if any(word in candidate for word in ("标题", "名称", "Product", "product", "价格", "FOB")):
            text = candidate
            chosen = encoding
            break
        if chosen is None:
            text = candidate
            chosen = encoding
    if not text:
        text = raw.decode("utf-8", errors="replace")
    sample = text[:4096]
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=",\t;|").delimiter
    except csv.Error:
        delimiter = ","
    return [row for row in csv.reader(io.StringIO(text), delimiter=delimiter)]


def read_xlsx(raw):
    from openpyxl import load_workbook

    workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    try:
        best = []
        best_score = -1
        for sheet in workbook.worksheets:
            matrix = []
            for index, row in enumerate(sheet.iter_rows(values_only=True)):
                if index >= 20000:
                    break
                matrix.append([cell_text(cell) for cell in row])
            score = 0
            for header in matrix[:30]:
                score = max(score, _header_score(header))
            if score > best_score:
                best_score = score
                best = matrix
        return best
    finally:
        workbook.close()


def markup_cents(cents, rate):
    return int((Decimal(cents) * Decimal(str(rate))).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def grams_from_weight(value):
    text = str(value or "").strip().lower().replace(" ", "")
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return Decimal(0)
    number = Decimal(match.group(0))
    if "kg" in text or "千克" in text or "公斤" in text:
        return number * 1000
    if text.endswith("g") or "克" in text:
        return number
    if number >= 30:
        return number
    return number * 1000


def weight_floor_cents(grams, grams_per_dollar=25):
    unit = Decimal(str(grams_per_dollar))
    if grams <= 0 or unit <= 0:
        return 0
    return int((Decimal(grams) / unit * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))



def offer_is_held(offer):
    """True when a SKU/offer was intercepted by the weight-price rule."""
    value = offer.get("hold") if isinstance(offer, dict) else None
    if isinstance(value, bool):
        return value
    return bool(str(value or "").strip())


def apply_intercept_rules(item):
    """Intercept rules (delete, do not hold unpublished):

    - Some SKUs intercepted: drop only those offers; keep the product.
    - Every SKU intercepted (整件拦截): drop the product (return None).
    - Never leave listing.hold set — intercepted rows are removed, not parked.
    """
    if not isinstance(item, dict):
        return None
    offers = [dict(offer) for offer in (item.get("offers") or []) if isinstance(offer, dict)]
    kept = []
    for offer in offers:
        if offer_is_held(offer):
            continue
        clean = dict(offer)
        clean.pop("hold", None)
        kept.append(clean)
    if not kept:
        return None
    item = dict(item)
    item["offers"] = kept
    listing = dict(item.get("listing") or {})
    listing["hold"] = ""
    item["listing"] = listing
    chosen = min(kept, key=lambda offer: (int(offer.get("price_cents") or 0), int(offer.get("original_cents") or 0)))
    item["price_cents"] = chosen["price_cents"]
    item["original_cents"] = chosen["original_cents"]
    if "source_cents" in chosen:
        item["source_cents"] = chosen["source_cents"]
    if not item.get("image_url"):
        item["image_url"] = next((offer.get("image") for offer in kept if offer.get("image")), "") or item.get("image_url") or ""
    return item

def hold_reason(percent=20):
    number = Decimal(str(percent))
    if number == number.to_integral_value():
        label = str(int(number))
    else:
        label = format(number, "f").rstrip("0").rstrip(".")
    return f"重量价比成本售价高出 {label}%，已拦截，不能上架。"


HOLD_REASON = hold_reason(20)


def sku_price(source_cents, weight, label, list_rate, sale_rate, grams_per_dollar=25, hold_percent=20):
    del label
    source = int(source_cents)
    grams = grams_from_weight(weight)
    by_cost = markup_cents(source, sale_rate)
    by_weight = weight_floor_cents(grams, grams_per_dollar)
    sale = max(by_cost, by_weight)
    original = max(markup_cents(source, list_rate), sale)
    gap = Decimal(str(hold_percent))
    hold = by_cost > 0 and Decimal(by_weight) * 100 >= Decimal(by_cost) * (Decimal(100) + gap)
    return {
        "grams": int(grams.quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
        "price_cents": sale,
        "original_cents": original,
        "hold": hold,
    }


def parse_rate(value):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        number = Decimal(text)
    except Exception:
        return None
    if number <= 0:
        return None
    return number


def parse_percent(value):
    text = str(value or "").strip().rstrip("%").strip()
    if not text:
        return None
    try:
        number = Decimal(text)
    except Exception:
        return None
    if number < 0:
        return None
    return number


def group_rows(items):
    grouped = []
    index = {}
    for item in items:
        listing = item["listing"]
        cargo = _slug(listing.get("cargo"))
        offer = re.sub(r"\D", "", listing.get("offer_id") or "")
        if cargo:
            key, parent = f"cargo:{cargo}", cargo
        elif offer:
            key, parent = f"offer:{offer}", f"a-{offer[:20]}"
        else:
            key, parent = f"sku:{item['sku']}", item["sku"]
        if key not in index:
            copy = dict(item)
            copy["sku"] = parent
            copy["offers"] = []
            copy["stock"] = 0
            index[key] = copy
            grouped.append(copy)
        parent_item = index[key]
        parent_item["stock"] += int(item.get("stock") or 0)
        details = parent_item["listing"].setdefault("detail_images", [])
        for url in item["listing"].get("detail_images") or []:
            if url not in details:
                details.append(url)
        label = listing.get("variant") or listing.get("color") or ""
        offer_index = len(parent_item["offers"])
        parent_item["offers"].append({
            "id": hashlib.sha1(f"{offer_index}:{label}:{item['price_cents']}".encode()).hexdigest()[:8],
            "source_label": label,
            "label": "",
            "source_cents": item["source_cents"],
            "original_cents": item["original_cents"],
            "price_cents": item["price_cents"],
            "grams": int(item.get("grams") or 0),
            "image": item.get("image_url") or "",
            "hold": bool(item.get("hold")),
        })
    seen = set()
    kept_products = []
    for item in grouped:
        sku = item["sku"]
        base = sku
        number = 2
        while sku in seen:
            suffix = f"-{number}"
            sku = base[:40 - len(suffix)] + suffix
            number += 1
        seen.add(sku)
        item["sku"] = sku
        # 拦截规则：超线规格直接删掉；整件超线则整件不入库。
        cleaned = apply_intercept_rules(item)
        if cleaned is None:
            continue
        kept_products.append(cleaned)
    return kept_products


def parse_sheet(raw, filename):
    name = (filename or "").lower()
    if raw[:2] == b"PK" or name.endswith(".xlsx"):
        if raw[:2] != b"PK":
            raise AlibabaFormatError("这个 Excel 文件打不开。请另存为 xlsx 或 csv。")
        matrix = read_xlsx(raw)
    elif name.endswith(".xls"):
        raise AlibabaFormatError("请把 xls 另存为 xlsx 或 csv 再上传。")
    else:
        matrix = read_csv(raw)
    return rows_to_items(matrix)
