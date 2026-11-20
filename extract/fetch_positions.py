"""Board issue #4 - Data API v2: positions per wallet.

/v2/positions needs a `user` (wallet) or `condition` filter. Per wallet it
returns the doc-style wrapper {"data": [...]}, per condition a plain array
(annoying inconsistency, handled here).

Only wallets that appear in our fetched trades are queried (they are the
relevant universe for our story), deduplicated, 100 rows per call.

Usage:
    python extract/fetch_positions.py --top 200
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import DATA_URL, RAW_DIR, TRADES_DIR, get_json, save_json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=200,
                    help="only the N most active wallets (rate limit!)")
    args = ap.parse_args()

    # ---- collect wallets from the trade caches ----------------------------
    activity = {}
    for p in sorted(TRADES_DIR.glob("*.json")):
        for t in json.loads(p.read_text()):
            w = t.get("proxy_wallet")
            if w:
                activity[w] = activity.get(w, 0) + 1
    if not activity:
        print("no trades found - run extract/fetch_trades.py first")
        return
    wallets = sorted(activity, key=activity.get, reverse=True)[:args.top]
    print(f"{len(activity)} unique wallets in trades, fetching positions for "
          f"top {len(wallets)}")

    # ---- pull positions per wallet ----------------------------------------
    positions = {}
    for i, w in enumerate(wallets, 1):
        resp = get_json(f"{DATA_URL}/v2/positions", {"user": w, "limit": 100})
        rows = resp.get("data", []) if isinstance(resp, dict) else (resp or [])
        positions[w] = rows
        time.sleep(0.2)
        if i % 25 == 0:
            print(f"  {i}/{len(wallets)} wallets done "
                  f"({sum(len(v) for v in positions.values()):,} positions)")

    save_json(RAW_DIR / "positions.json", positions)
    print(f"saved {sum(len(v) for v in positions.values()):,} positions "
          f"for {len(positions)} wallets -> data/raw/positions.json")


if __name__ == "__main__":
    main()
