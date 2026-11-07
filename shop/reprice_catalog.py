"""One-shot: set list_rate=2, sale_rate=1.3 and reprice all products/offers from source_cents."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from decimal import Decimal
from pathlib import Path

# Allow running from /opt/harbor or D:\1010
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

from shop.alibaba import hold_reason, sku_price  # noqa: E402


LIST_RATE = Decimal("2")
SALE_RATE = Decimal("1.3")
HOLD_PERCENT = Decimal("20")
GRAMS_PER_DOLLAR = Decimal("25")


def plain_decimal(number):
    text = format(Decimal(number), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def store_pricing(conn):
    for key, value in (
        ("price_list_rate", LIST_RATE),
        ("price_sale_rate", SALE_RATE),
        ("price_hold_percent", HOLD_PERCENT),
        ("price_grams_per_dollar", GRAMS_PER_DOLLAR),
    ):
        conn.execute(
            "insert into settings (key, value) values (?, ?) on conflict(key) do update set value = excluded.value",
            (key, plain_decimal(value)),
        )


def reprice_offer(offer):
    source = int(offer.get("source_cents") or 0)
    if source <= 0:
        return offer, False
    grams = offer.get("grams")
    # sku_price/grams_from_weight treats bare numbers <30 as kg; pass explicit grams.
    if grams in (None, ""):
        weight = 0
    else:
        weight = f"{grams}g"
    priced = sku_price(
        source,
        weight,
        offer.get("source_label") or "",
        LIST_RATE,
        SALE_RATE,
        GRAMS_PER_DOLLAR,
        HOLD_PERCENT,
    )
    changed = (
        int(offer.get("price_cents") or 0) != priced["price_cents"]
        or int(offer.get("original_cents") or 0) != priced["original_cents"]
        or bool(offer.get("hold")) != bool(priced["hold"])
    )
    offer = dict(offer)
    offer["price_cents"] = priced["price_cents"]
    offer["original_cents"] = priced["original_cents"]
    offer["hold"] = bool(priced["hold"])
    if priced.get("grams") and not offer.get("grams"):
        offer["grams"] = priced["grams"]
    return offer, changed


def reprice_product(row):
    offers = json.loads(row["offers"] or "[]")
    if not isinstance(offers, list) or not offers:
        return None
    new_offers = []
    any_changed = False
    for offer in offers:
        if not isinstance(offer, dict):
            new_offers.append(offer)
            continue
        updated, changed = reprice_offer(offer)
        new_offers.append(updated)
        any_changed = any_changed or changed
    sellable = [o for o in new_offers if isinstance(o, dict) and not o.get("hold")]
    pool = sellable or [o for o in new_offers if isinstance(o, dict)]
    if not pool:
        return None
    chosen = min(pool, key=lambda o: (int(o.get("price_cents") or 0), int(o.get("original_cents") or 0)))
    new_price = int(chosen["price_cents"])
    new_original = int(chosen["original_cents"])
    if (
        not any_changed
        and int(row["price_cents"] or 0) == new_price
        and int(row["original_cents"] or 0) == new_original
    ):
        return None
    return {
        "sku": row["sku"],
        "price_cents": new_price,
        "original_cents": new_original,
        "offers": json.dumps(new_offers, ensure_ascii=False),
        "all_held": not sellable,
        "before": (int(row["price_cents"] or 0), int(row["original_cents"] or 0), row["offers"]),
        "sample_source": int(chosen.get("source_cents") or 0),
    }


def main():
    db = os.environ.get("SHOP_DB") or str(ROOT.parent / "data" / "shop.sqlite")
    if len(sys.argv) > 1:
        db = sys.argv[1]
    path = Path(db)
    if not path.is_file():
        raise SystemExit(f"missing db: {path}")
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row

    before = {
        r["key"]: r["value"]
        for r in conn.execute("select key, value from settings where key like 'price_%'")
    }
    print("SETTINGS_BEFORE", before)
    store_pricing(conn)
    after = {
        r["key"]: r["value"]
        for r in conn.execute("select key, value from settings where key like 'price_%'")
    }
    print("SETTINGS_AFTER", after)

    samples = []
    updated = 0
    for row in conn.execute(
        "select sku, price_cents, original_cents, offers, listing from products"
    ):
        result = reprice_product(row)
        if result is None:
            continue
        if result["all_held"]:
            listing = json.loads(row["listing"] or "{}")
            if not listing.get("hold"):
                listing["hold"] = hold_reason(HOLD_PERCENT)
            conn.execute(
                "update products set price_cents = ?, original_cents = ?, offers = ?, listing = ?, published = 0 where sku = ?",
                (
                    result["price_cents"],
                    result["original_cents"],
                    result["offers"],
                    json.dumps(listing, ensure_ascii=False),
                    result["sku"],
                ),
            )
        else:
            conn.execute(
                "update products set price_cents = ?, original_cents = ?, offers = ? where sku = ?",
                (result["price_cents"], result["original_cents"], result["offers"], result["sku"]),
            )
        updated += 1
        if len(samples) < 8:
            src = result["sample_source"]
            samples.append(
                {
                    "sku": result["sku"],
                    "source_cents": src,
                    "before_price": result["before"][0],
                    "before_original": result["before"][1],
                    "after_price": result["price_cents"],
                    "after_original": result["original_cents"],
                    "expect_sale": int((Decimal(src) * SALE_RATE).to_integral_value()) if src else None,
                    "expect_list": int((Decimal(src) * LIST_RATE).to_integral_value()) if src else None,
                }
            )
    conn.commit()
    print("UPDATED", updated)
    for s in samples:
        print("SAMPLE", json.dumps(s, ensure_ascii=False))
    # verify ratios on a few non-floor products
    checked = 0
    ok = 0
    for row in conn.execute(
        "select sku, price_cents, original_cents, offers from products limit 200"
    ):
        offers = json.loads(row["offers"] or "[]")
        for o in offers:
            if not isinstance(o, dict) or o.get("hold"):
                continue
            src = int(o.get("source_cents") or 0)
            if src <= 0:
                continue
            by_cost = int((Decimal(src) * SALE_RATE).quantize(Decimal("1")))
            # only check offers not lifted by weight floor
            if int(o["price_cents"]) != by_cost:
                continue
            checked += 1
            sale_ok = int(o["price_cents"]) == by_cost
            list_ok = int(o["original_cents"]) == int((Decimal(src) * LIST_RATE).quantize(Decimal("1"))) or int(o["original_cents"]) >= int(o["price_cents"])
            if sale_ok and list_ok:
                ok += 1
            if checked >= 20:
                break
        if checked >= 20:
            break
    print("VERIFY_COST_BASED", ok, "/", checked)
    # floor-affected samples: sell > 1.3×source
    from shop.alibaba import markup_cents, weight_floor_cents
    floor_n = 0
    shown = 0
    for row in conn.execute("select sku, price_cents, original_cents, offers from products"):
        offers = json.loads(row["offers"] or "[]")
        for o in offers:
            if not isinstance(o, dict):
                continue
            src = int(o.get("source_cents") or 0)
            grams = int(o.get("grams") or 0)
            if src <= 0:
                continue
            by_cost = markup_cents(src, SALE_RATE)
            by_weight = weight_floor_cents(grams, GRAMS_PER_DOLLAR)
            if int(o.get("price_cents") or 0) > by_cost and by_weight >= by_cost:
                floor_n += 1
                if shown < 8:
                    print(
                        "FLOOR_SAMPLE",
                        json.dumps(
                            {
                                "sku": row["sku"],
                                "grams": grams,
                                "source_cents": src,
                                "cost_sale": by_cost,
                                "weight_sale": int(by_weight),
                                "sell": int(o["price_cents"]),
                                "list": int(o["original_cents"]),
                            },
                            ensure_ascii=False,
                        ),
                    )
                    shown += 1
    print("FLOOR_OFFERS", floor_n)
    conn.close()


if __name__ == "__main__":
    main()
