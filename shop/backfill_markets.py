"""Judge published in-stock products that still have an empty markets column."""

import json
import sqlite3
import sys
import time

from shop.markets import judge_batch, push_line
from shop.writer import ai_pair

DB = "/opt/harbor/data/shop.sqlite"


def chinese_title(row):
    for raw in (row["source_zh"], row["listing"]):
        text = str(raw or "").strip()
        if not text:
            continue
        data = None
        if text[0] in "{[":
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                data = None
        if isinstance(data, dict):
            title = ""
            for key in ("name", "title", "zh"):
                found = str(data.get(key) or "").strip()
                if found:
                    title = found
                    break
            if title:
                return title, str(data.get("description") or "")[:400]
        elif raw == row["source_zh"]:
            return text, ""
    try:
        names = json.loads(row["names"] or "{}")
    except json.JSONDecodeError:
        names = {}
    if isinstance(names, dict):
        return str(names.get("zh") or "").strip(), ""
    return "", ""


def main():
    conn = sqlite3.connect(DB, timeout=30)
    conn.row_factory = sqlite3.Row
    columns = {row[1] for row in conn.execute("pragma table_info(products)")}
    if "markets" not in columns:
        print("NO_COLUMN", flush=True)
        return 1

    def setting(key):
        row = conn.execute("select value from settings where key = ?", (key,)).fetchone()
        return row["value"] if row else ""

    pair = ai_pair(setting("ai_key"), setting("ai_base"), setting("ai_model"))
    print(push_line(conn), flush=True)
    if not pair:
        print("NO_KEY", flush=True)
        return 0
    complete = pair[2]
    rows = conn.execute(
        """
        select sku, source_zh, listing, names
        from products
        where published = 1 and stock > 0 and trim(markets) = '' and markets_lock = 0
        """
    ).fetchall()
    pending = []
    for row in rows:
        title, description = chinese_title(row)
        if title:
            pending.append({"sku": row["sku"], "title": title, "description": description})
    print(f"PENDING {len(pending)}", flush=True)
    saved = 0
    for start in range(0, len(pending), 200):
        chunk = pending[start:start + 200]
        try:
            found = judge_batch(chunk, complete)
        except Exception as exc:
            response = getattr(exc, "response", None)
            body = response.text[:180] if response is not None else ""
            print(f"FAIL {start} {type(exc).__name__}", flush=True)
            if "usage_limit_exceeded" in body:
                print("LIMIT", flush=True)
                return 0
            time.sleep(8)
            continue
        if not found:
            print(f"EMPTY {start}", flush=True)
            continue
        for sku, flags in found.items():
            conn.execute(
                """
                update products
                set markets = ?
                where sku = ? and trim(markets) = '' and markets_lock = 0
                """,
                (json.dumps(flags, ensure_ascii=False), sku),
            )
            saved += 1
        conn.commit()
        print(f"SAVED {saved}/{len(pending)}", flush=True)
    print(push_line(conn), flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
