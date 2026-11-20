"""Board issue #2 - Gamma API: closed markets, crypto markets filtered out.

Pulls closed markets (classic limit/offset pagination, sorted by volume),
filters out mechanical crypto price markets ("Up or Down" 5m/15m bets),
non-binary and ambiguously resolved markets, and saves the result as
data/raw/markets_scope.json.

IMPORTANT: sorting uses `order=volumeNum` (the NUMERIC field). `order=volume`
sorts the volume STRING, which produces alphabetical nonsense - measured!

Raw market dumps are cached as data/raw/markets_raw.json (re-run with
--refresh to force a re-download).

Usage:
    python extract/fetch_markets.py --n 500
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import CRYPTO_PRICE_PATTERN, GAMMA_URL, RAW_DIR, get_json, load_json, save_json

CRYPTO_RE = re.compile(CRYPTO_PRICE_PATTERN)


def winner_from_prices(prices):
    """Index of the winning side, or None (0.5/0.5 ties, cancelled, no clean 1)."""
    try:
        p = [float(v) for v in prices]
    except (TypeError, ValueError):
        return None
    if len(p) == 2 and p.count(1.0) == 1:
        return p.index(1.0)
    return None


def fetch_closed_markets(n=500, page_size=100, refresh=False):
    cache = RAW_DIR / "markets_raw.json"
    if cache.exists() and not refresh:
        print(f"markets raw cache found ({cache.name}), loading; use --refresh to re-fetch")
        return load_json(cache)
    mk, offset = [], 0
    while len(mk) < n:
        batch = get_json(f"{GAMMA_URL}/markets",
                         {"closed": "true", "limit": page_size, "offset": offset,
                          "order": "volumeNum", "ascending": "false"})
        if not batch:
            break
        mk.extend(batch)
        offset += page_size
        print(f"  {len(mk):5d} markets (next offset {offset})")
    save_json(cache, mk)
    return mk


def build_scope(markets, min_volume_usd=50_000):
    """Filter to binary, cleanly resolved, non-crypto, liquid markets."""
    scope, dropped = [], {"crypto": 0, "not_binary": 0, "ambiguous": 0,
                          "thin_volume": 0, "missing_id": 0}
    for m in markets:
        q = (m.get("question") or "").strip()
        cid = m.get("conditionId")
        if not cid:
            dropped["missing_id"] += 1
            continue
        if CRYPTO_RE.search(q):
            dropped["crypto"] += 1
            continue
        try:
            outcomes = json.loads(m.get("outcomes") or "[]")
            prices = json.loads(m.get("outcomePrices") or "[]")
        except (TypeError, ValueError):
            outcomes, prices = [], []
        if len(outcomes) != 2 or len(prices) != 2:
            dropped["not_binary"] += 1
            continue
        wi = winner_from_prices(prices)
        if wi is None:
            dropped["ambiguous"] += 1
            continue
        try:
            vol = float(m.get("volumeNum") or 0)
        except ValueError:
            vol = 0.0
        if vol < min_volume_usd:
            dropped["thin_volume"] += 1
            continue
        scope.append({
            "condition_id": cid.lower(),
            "question": q,
            "slug": m.get("slug"),
            "outcomes": outcomes,
            "winner_idx": wi,
            "final_prices": [float(p) for p in prices],
            "volume_usd": vol,
            "created_at": m.get("createdAt"),
            "end_date": m.get("endDate"),
            "closed_time": m.get("closedTime"),
        })
    return scope, dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500,
                    help="how many closed markets to pull (top-volume first)")
    ap.add_argument("--refresh", action="store_true",
                    help="ignore the raw cache and re-download")
    args = ap.parse_args()

    raw = fetch_closed_markets(args.n, refresh=args.refresh)
    scope, dropped = build_scope(raw)
    save_json(RAW_DIR / "markets_scope.json", scope)

    print(f"\nraw markets fetched : {len(raw)}")
    print(f"dropped             : {dropped}")
    print(f"scope markets       : {len(scope)} -> data/raw/markets_scope.json")


if __name__ == "__main__":
    main()
