import json

MARKETS = ("US", "CA", "GB", "DE", "FR", "ES", "PT", "BR", "MX", "JP")

LABELS = {
    "US": "美国",
    "CA": "加拿大",
    "GB": "英国",
    "DE": "德国",
    "FR": "法国",
    "ES": "西班牙",
    "PT": "葡萄牙",
    "BR": "巴西",
    "MX": "墨西哥",
    "JP": "日本",
}


def parsed(raw):
    if isinstance(raw, dict):
        data = raw
    else:
        text = str(raw or "").strip()
        if not text:
            return {}
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return {}
    if not isinstance(data, dict):
        return {}
    found = {}
    for code in MARKETS:
        if code in data:
            found[code] = _flag(data[code])
    return found


def _flag(value):
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "是"}
    return bool(value)


def rank(row, country):
    data = parsed(row.get("markets") if hasattr(row, "get") else "")
    code = str(country or "US").upper()
    if code not in MARKETS:
        code = "US"
    if code not in data:
        return 0
    return 0 if data[code] else 1


def push_line(conn):
    counts = {code: 0 for code in MARKETS}
    judged = False
    for row in conn.execute(
        "select markets from products where published = 1 and stock > 0"
    ).fetchall():
        data = parsed(row["markets"])
        if not data:
            continue
        judged = True
        for code in MARKETS:
            if data.get(code):
                counts[code] += 1
    if not judged:
        return "主推款　还没有判断"
    body = "　".join(f"{LABELS[code]} {counts[code]}" for code in MARKETS)
    return f"主推款　{body}"


def _prompt(items):
    lines = []
    for item in items:
        title = " ".join(str(item.get("title") or "").split())
        lines.append(f"{item.get('sku')}\t{title}")
    return (
        "判断这些日用品标题在哪些国家适合普通家庭使用。只看标题。\n"
        "国家顺序：US CA GB DE FR ES PT BR MX JP。会用写 1，不会写 0。\n"
        "电瓶车罩、雅迪、爱玛、九号配件、筷子、蒸碗、饺子勺、国风书签、家用马桶垫、冬季全脸面罩，"
        "在 US CA GB DE FR ES PT BR MX 写 0。日本对筷子、蒸碗、面罩可以写 1。每个国家单独判断。\n"
        "只回复表格，每行 11 列，用英文逗号分隔：sku,US,CA,GB,DE,FR,ES,PT,BR,MX,JP。\n"
        "不要表头，不要解释，不要重复标题。\n\n"
        + "\n".join(lines)
    )


def _entries(raw):
    text = str(raw or "").strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]")
        if start < 0 or end <= start:
            start = text.find("{")
            end = text.rfind("}")
            if start < 0 or end <= start:
                return []
            data = json.loads(text[start:end + 1])
        else:
            data = json.loads(text[start:end + 1])
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _bit(flag):
    text = str(flag or "").strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    return None


def _table_entries(raw, allowed):
    found = []
    for line in str(raw or "").splitlines():
        text = line.strip().strip("`").strip("|")
        if not text or text.lower().startswith("sku"):
            continue
        parts = [part.strip() for part in text.replace("|", ",").replace("\t", ",").split(",")]
        if len(parts) < 11:
            parts = text.split()
        if len(parts) < 11:
            continue
        sku = parts[0]
        flags = [_bit(flag) for flag in parts[-10:]]
        if sku not in allowed or any(flag is None for flag in flags):
            continue
        entry = {"sku": sku}
        entry.update({code: flag for code, flag in zip(MARKETS, flags)})
        found.append(entry)
    return found


def judge_batch(items, complete):
    usable = [item for item in items if str(item.get("title") or "").strip() and str(item.get("sku") or "").strip()]
    if not usable or complete is None:
        return {}
    allowed = {str(item["sku"]) for item in usable}
    raw = complete(_prompt(usable))
    entries = _entries(raw)
    table = _table_entries(raw, allowed)
    if len(table) > len(entries):
        entries = table
    found = {}
    if len(usable) == 1 and len(entries) == 1 and not entries[0].get("sku"):
        entries[0]["sku"] = usable[0]["sku"]
    for entry in entries:
        sku = str(entry.get("sku") or "").strip()
        flags = parsed(entry)
        if sku in allowed and len(flags) == len(MARKETS):
            found[sku] = flags
    return found


def judge_one(sku, title, description, complete):
    found = judge_batch(
        [{"sku": sku, "title": title, "description": description}],
        complete,
    )
    return found.get(sku) or {}
