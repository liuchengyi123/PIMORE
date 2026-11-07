import hashlib
import io
import re
import zipfile
from decimal import Decimal, ROUND_HALF_UP

from shop.alibaba import category_for, hold_reason, markup_cents, sku_price, weight_floor_cents


class PackageError(Exception):
    pass


def is_jushuitan_sheet(raw, filename):
    if not str(filename or "").lower().endswith(".xlsx") or raw[:2] != b"PK":
        return False
    try:
        from openpyxl import load_workbook

        book = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        row = next(book.worksheets[0].iter_rows(max_row=1, values_only=True), ())
        book.close()
    except Exception:
        return False
    header = {str(cell or "").strip() for cell in row}
    return "资料编码" in header and "供货价" in header


def _text(value):
    if value is None:
        return ""
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return format(value, "f").rstrip("0").rstrip(".")
    return str(value).strip()


def _number(value):
    text = _text(value).replace(",", "")
    if not text:
        return Decimal("0")
    try:
        return Decimal(text)
    except Exception:
        return Decimal("0")


def _slug(value):
    text = re.sub(r"[^a-z0-9]+", "-", _text(value).lower()).strip("-")
    if 2 <= len(text) <= 40:
        return text
    return ""


def _kind(name):
    parts = name.replace("\\", "/").split("/")
    if any(part == "商品详情页图" for part in parts):
        return "detail"
    if any(part == "商品主图" for part in parts):
        return "main"
    if any(part == "颜色图" for part in parts):
        return "color"
    return ""


def _order(name):
    match = re.search(r"_(\d+)\.", name.replace("\\", "/").split("/")[-1])
    return int(match.group(1)) if match else 0


def _safe_name(name):
    text = name.replace("\\", "/")
    if text.startswith("/") or ".." in text.split("/"):
        return ""
    return text


def dollar_cents(amount):
    if amount <= 0:
        return 0
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _product_root(name, kind):
    parts = name.split("/")
    if kind:
        return "/".join(parts[:-2])
    return "/".join(parts[:-1])


def _sku_for(code, item_code, seen):
    sku = _slug(code) or _slug(item_code) or f"p-{hashlib.sha1(code.encode('utf-8')).hexdigest()[:8]}"
    base = sku
    number = 2
    while sku in seen:
        suffix = f"-{number}"
        sku = base[:40 - len(suffix)] + suffix
        number += 1
    seen.add(sku)
    return sku


def _offer_id(code, index, label, source, used):
    safe = re.sub(r"[^A-Za-z0-9._-]+", "", code).strip("._-")
    if not 1 <= len(safe) <= 48:
        safe = hashlib.sha1(f"{index}:{label}:{source}".encode()).hexdigest()[:8]
    base = safe
    number = 2
    while safe in used:
        suffix = f"-{number}"
        safe = (base[:48 - len(suffix)] + suffix)
        number += 1
    used.add(safe)
    return safe


def _empty_pictures():
    return {"main": [], "detail": [], "color": []}


def _blank_images(products):
    for item in products:
        item["mains"] = []
        item["details"] = []
        for offer in item.get("offers") or []:
            offer["image"] = ""
    return products


def _dollars(cents):
    return f"${int(cents) / 100:.2f}"


def describe_preview(products, sale_rate, grams_per_dollar):
    rows = []
    passed = 0
    held = 0
    for item in products:
        blocked = bool(item["listing"].get("hold"))
        if blocked:
            held += 1
        else:
            passed += 1
        for offer in item["offers"]:
            cost = markup_cents(offer["source_cents"], sale_rate)
            weight = weight_floor_cents(offer.get("grams") or 0, grams_per_dollar)
            rows.append({
                "title": item["title"],
                "label": offer.get("source_label") or "默认",
                "grams": int(offer.get("grams") or 0),
                "source": _dollars(offer["source_cents"]),
                "cost": _dollars(cost),
                "weight": _dollars(weight),
                "sale": _dollars(offer["price_cents"]),
                "held": bool(offer.get("hold")),
                "product_held": blocked,
            })
    return {
        "rows": rows,
        "passed": passed,
        "held": held,
        "spec_held": sum(1 for row in rows if row["held"]),
    }


def preview_sheets(blobs, list_rate, sale_rate, grams_per_dollar=25, hold_percent=20):
    products = []
    seen = set()
    found = False
    for raw, filename in blobs:
        name = str(filename or "")
        lower = name.lower()
        if lower.endswith(".zip") or (raw[:2] == b"PK" and not lower.endswith(".xlsx")):
            found = True
            products.extend(_preview_zip(
                raw, list_rate, sale_rate, seen, grams_per_dollar, hold_percent,
            ))
            continue
        sheet_name = name if lower.endswith(".xlsx") else f"{name or '表格'}.xlsx"
        if not is_jushuitan_sheet(raw, sheet_name):
            raise PackageError(f"{name or '这个文件'} 不是商品数据表。表头要有资料编码和供货价。")
        found = True
        products.extend(_products(
            raw, _empty_pictures(), list_rate, sale_rate, seen, grams_per_dollar, hold_percent,
        ))
    if not found:
        raise PackageError("请先选择数据包里的商品表格。")
    if not products:
        raise PackageError("表格里没有读到商品。需要商品名称、供货价和商品编码。")
    return _blank_images(products)


def _preview_zip(raw, list_rate, sale_rate, seen, grams_per_dollar, hold_percent):
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:
        raise PackageError("这个压缩包打不开。")
    products = []
    for info in archive.infolist():
        if info.is_dir():
            continue
        name = _safe_name(info.filename)
        lower = name.lower()
        if not lower.endswith(".xlsx") or "商品数据" not in name or name.split("/")[-1].startswith("~$"):
            continue
        products.extend(_products(
            archive.read(info), _empty_pictures(), list_rate, sale_rate, seen,
            grams_per_dollar, hold_percent,
        ))
    if not products:
        raise PackageError("压缩包里没有「商品数据」表格。")
    return products


def read_package(raw, list_rate, sale_rate, grams_per_dollar=25, hold_percent=20, skip_held_images=False):
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:
        raise PackageError("这个压缩包打不开。请上传聚水潭导出的商品数据包 zip。")
    infos = [info for info in archive.infolist() if not info.is_dir()]
    buckets = {}
    order = []
    for info in infos:
        name = _safe_name(info.filename)
        if not name:
            continue
        lower = name.lower()
        kind = ""
        if lower.endswith(".xlsx") and "商品数据" in name and not name.split("/")[-1].startswith("~$"):
            root = _product_root(name, "")
        else:
            kind = _kind(name)
            if not kind:
                continue
            root = _product_root(name, kind)
        bucket = buckets.setdefault(root, {"sheet": "", "main": [], "detail": [], "color": []})
        if root not in order:
            order.append(root)
        if kind:
            bucket[kind].append((name, info))
        else:
            bucket["sheet"] = name
    sheets = [root for root in order if buckets[root]["sheet"]]
    if not sheets:
        raise PackageError("压缩包里没有「商品数据」表格。")
    products = []
    seen = set()
    for root in sheets:
        bucket = buckets[root]
        sheet_bytes = archive.read(bucket["sheet"])
        if skip_held_images:
            probe = set(seen)
            bare = _products(
                sheet_bytes, _empty_pictures(), list_rate, sale_rate, probe,
                grams_per_dollar, hold_percent,
            )
            if bare and all(item["listing"].get("hold") for item in bare):
                seen.clear()
                seen.update(probe)
                products.extend(_blank_images(bare))
                continue
        pictures = {}
        for kind in ("main", "detail", "color"):
            files = sorted(bucket[kind], key=lambda item: (_order(item[0]), item[0]))
            pictures[kind] = [archive.read(info) for _, info in files]
        part = _products(
            sheet_bytes, pictures, list_rate, sale_rate, seen,
            grams_per_dollar, hold_percent,
        )
        if skip_held_images:
            for item in part:
                if item["listing"].get("hold"):
                    _blank_images([item])
        products.extend(part)
    if not products:
        raise PackageError("表格里没有读到商品。需要商品名称、供货价和商品编码。")
    return products


def _products(raw, pictures, list_rate, sale_rate, seen, grams_per_dollar=25, hold_percent=20):
    from openpyxl import load_workbook

    workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    sheet = workbook.worksheets[0]
    rows = [list(row) for row in sheet.iter_rows(values_only=True)]
    workbook.close()
    if not rows:
        return []
    header = [_text(cell) for cell in rows[0]]
    if "资料编码" not in header or "供货价" not in header:
        raise PackageError("这不是聚水潭商品数据包。表头要有资料编码、商品名称和供货价。")
    index = {name: pos for pos, name in enumerate(header) if name}

    def cell(row, name):
        pos = index.get(name)
        if pos is None or pos >= len(row):
            return ""
        return row[pos]

    grouped = {}
    order = []
    for row in rows[1:]:
        title = _text(cell(row, "商品名称"))
        cost = _number(cell(row, "供货价"))
        if not title or cost <= 0:
            continue
        code = _text(cell(row, "资料编码")) or title
        if code not in grouped:
            grouped[code] = []
            order.append(code)
        grouped[code].append(row)
    products = []
    for code in order:
        body = grouped[code]
        first = body[0]
        title = _text(cell(first, "商品名称"))
        first_code = _text(cell(first, "商品编码"))
        sku = _sku_for(code, first_code, seen)
        offers = []
        used_ids = set()
        stock = 0
        costs = []
        for row_index, row in enumerate(body):
            cost = _number(cell(row, "供货价"))
            costs.append(cost)
            source = dollar_cents(cost)
            color = _text(cell(row, "颜色"))
            spec = _text(cell(row, "规格"))
            label = color if spec in {"", "无规格"} else " ".join(part for part in (color, spec) if part)
            item_code = _text(cell(row, "商品编码"))
            priced = sku_price(
                source, _text(cell(row, "重量")), label, list_rate, sale_rate,
                grams_per_dollar, hold_percent,
            )
            offers.append({
                "id": _offer_id(item_code, row_index, label, source, used_ids),
                "source_label": label,
                "label": "",
                "source_cents": source,
                "original_cents": priced["original_cents"],
                "price_cents": priced["price_cents"],
                "grams": priced["grams"],
                "image": pictures["color"][row_index] if row_index < len(pictures["color"]) else b"",
                "code": item_code,
                "hold": priced["hold"],
            })
            stock_text = _text(cell(row, "库存"))
            stock += int(stock_text) if stock_text.isdigit() else 0
        for offer in offers:
            if offer.get("hold") and isinstance(offer.get("image"), (bytes, bytearray)):
                offer["image"] = ""
        sellable = [offer for offer in offers if not offer.get("hold")]
        chosen = min(sellable or offers, key=lambda offer: (offer["price_cents"], offer["original_cents"]))
        weight = _text(cell(first, "重量"))
        if weight and weight.replace(".", "", 1).isdigit():
            weight = f"{weight}kg"
        products.append({
            "sku": sku,
            "title": title,
            "category": category_for(
                _text(cell(first, "商品分类")),
                _text(cell(first, "类目")),
                _text(cell(first, "分类")),
                title,
            ),
            "stock": stock,
            "price_cents": chosen["price_cents"],
            "original_cents": chosen["original_cents"],
            "source_cents": chosen["source_cents"],
            "image_url": "",
            "mains": list(pictures["main"]),
            "details": list(pictures["detail"]),
            "listing": {
                "offer_id": "",
                "title": title,
                "cargo": code,
                "supplier": _text(cell(first, "供应商名称")),
                "amount": float(min(costs)),
                "money": "USD",
                "weight": weight,
                "hold": hold_reason(hold_percent) if offers and not sellable else "",
                "description": "",
                "detail_images": [],
                "gallery": [],
                "url": "",
            },
            "offers": offers,
        })
    return products
