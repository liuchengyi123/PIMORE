"""Cancel unpaid pending orders older than N minutes. For Linux cron/systemd."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shop.checkout import expire_pending_orders
from shop.db import connect


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minutes", type=int, default=30)
    parser.add_argument("--db", default=os.environ.get("SHOP_DB", str(ROOT / "data" / "shop.sqlite")))
    args = parser.parse_args(argv)
    conn = connect(args.db)
    cancelled = expire_pending_orders(conn, minutes=args.minutes)
    print(f"cancelled={len(cancelled)} ids={cancelled}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
