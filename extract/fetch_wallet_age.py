"""Board issue #5 - Wallet age + funding source (2nd, independent source).

Wallet age = timestamp of the first on-chain transaction of the address
(Polygon chain). A wallet created days before betting against the crowd
and winning is a classic red flag for the trust score.

API: Polygonscan is served through the Etherscan unified v2 API now
(chainid=137). Free key required -> .env: ETHERSCAN_API_KEY=...

Cache: fetched wallets are kept in data/raw/wallet_ages.json and never
queried again (free tier is ~5 req/s, thousands of wallets would take
hours otherwise). Resume = re-run, only new wallets are queried.

Usage:
    python extract/fetch_wallet_age.py --top 100
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import (ETHERSCAN_KEY, ETHERSCAN_V2, POLYGON_CHAIN_ID,
                    RAW_DIR, TRADES_DIR, get_json, save_json)

CACHE = RAW_DIR / "wallet_ages.json"


def wallets_from_trades():
    activity = {}
    for p in sorted(TRADES_DIR.glob("*.json")):
        for t in json.loads(p.read_text()):
            w = t.get("proxy_wallet")
            if w:
                activity[w] = activity.get(w, 0) + 1
    return activity


def first_tx(address):
    """First transaction of a wallet (exactly one row, sorted asc)."""
    res = get_json(ETHERSCAN_V2, {
        "chainid": POLYGON_CHAIN_ID, "module": "account", "action": "txlist",
        "address": address, "page": 1, "offset": 1, "sort": "asc",
        "apikey": ETHERSCAN_KEY})
    if res and res.get("status") == "1" and res.get("result"):
        tx = res["result"][0]
        return {"first_tx_ts": int(tx.get("timeStamp", 0)),
                "funding_from": tx.get("from"),
                "first_tx_hash": tx.get("hash")}
    return {"first_tx_ts": None, "funding_from": None, "first_tx_hash": None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=100,
                    help="only the N most active wallets")
    args = ap.parse_args()

    if not ETHERSCAN_KEY:
        print("No ETHERSCAN_API_KEY set (.env) - put a free key from "
              "etherscan.io/apidashboard in .env, then re-run.")
        return

    activity = wallets_from_trades()
    if not activity:
        print("no trades found - run extract/fetch_trades.py first")
        return

    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    todo = [w for w in sorted(activity, key=activity.get, reverse=True)
            if w not in cache][:args.top]
    print(f"{len(activity)} wallets in trades | {len(cache)} already cached | "
          f"fetching {len(todo)}")

    for i, w in enumerate(todo, 1):
        cache[w] = first_tx(w)
        time.sleep(0.25)                       # ~4 req/s, free tier limit
        if i % 20 == 0:
            save_json(CACHE, cache)            # early checkpoint
            print(f"  {i}/{len(todo)}")

    save_json(CACHE, cache)
    known = sum(1 for v in cache.values() if v["first_tx_ts"])
    print(f"wallet ages: {len(cache)} total, {known} with on-chain history "
          f"-> data/raw/wallet_ages.json")


if __name__ == "__main__":
    main()
