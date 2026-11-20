"""Board issue #7 - Clean + merge -> Parquet flat files for Spark/pandas.

Reads the raw JSON caches (markets + trades + wallet ages), checks data
quality (completeness, duplicates, ambiguous resolutions, the
outcome_index==999 API default), merges trades with their market's winner
(join key: condition_id), and writes:

  data/processed/markets_clean.parquet   one row per scope market
  data/processed/trades_clean.parquet    one row per trade (+ winner_idx, won)
  data/processed/wallet_ages.parquet     one row per wallet (first_tx, funding)

Parquet cannot store nested list/dict columns -> raw docs stay in MongoDB.

Usage:
    python clean/build_parquet.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import PROCESSED_DIR, RAW_DIR, TRADES_DIR


def main():
    #  load ------------------------------------------------------------------
    scope = json.loads((RAW_DIR / "markets_scope.json").read_text())
    mk = pd.DataFrame(scope)
    raw_trades = [t for p in sorted(TRADES_DIR.glob("*.json"))
                  for t in json.loads(p.read_text())]
    if not raw_trades:
        print("no trades found - run extract/fetch_trades.py first")
    tr = pd.DataFrame(raw_trades)

    ages = (json.loads((RAW_DIR / "wallet_ages.json").read_text())
            if (RAW_DIR / "wallet_ages.json").exists() else {})
    wa = pd.DataFrame([{"proxy_wallet": w, **v} for w, v in ages.items()])

    #  quality checks ---------------------------------------------------------
    print("=== data quality report ===")
    print(f"markets in scope      : {len(mk)}")
    print(f"trades fetched        : {len(tr)}")
    if len(tr):
        dup_key = ["transaction_hash", "token_id", "proxy_wallet"]
        dups = tr.duplicated(subset=dup_key).sum()
        print(f"duplicate trades      : {dups}")
        print(f"trades w/o wallet     : {tr['proxy_wallet'].isna().sum()}")
        bad_ps = (pd.to_numeric(tr['price'], errors='coerce').isna()
                  | pd.to_numeric(tr['size'], errors='coerce').isna())
        print(f"trades w/o price/size : {bad_ps.sum()}")
        oi = pd.to_numeric(tr.get("outcome_index"), errors="coerce")
        print(f"outcome_index == 999  : {(oi == 999).sum()} "
              "(999 = API default 'unknown' -> not winner-usable)")
    print(f"markets w/ winner_idx : {mk['winner_idx'].notna().sum()} of {len(mk)}")
    print(f"wallet ages known     : {len(wa)}")

    #  clean -----------------------------------------------------------------
    if len(tr):
        tr["condition_id"] = tr["condition_id"].str.lower()
        tr["price"] = pd.to_numeric(tr["price"], errors="coerce")
        tr["size"] = pd.to_numeric(tr["size"], errors="coerce")
        tr["timestamp"] = pd.to_numeric(tr["timestamp"], errors="coerce")
        tr["outcome_index"] = pd.to_numeric(tr["outcome_index"], errors="coerce")
        tr = tr.dropna(subset=["price", "size", "timestamp", "proxy_wallet"])

    # merge: trade + its market's winner (only scope markets survive the join)
    if len(tr):
        t = tr.merge(mk[["condition_id", "winner_idx", "question", "slug",
                         "volume_usd", "closed_time"]],
                     on="condition_id", how="inner")
        t["won"] = (t["outcome_index"] == t["winner_idx"]).astype(int)
    else:
        t = tr

    #  describe --------------------------------------------------------------
    print("\n=== descriptive stats (cleaned trades) ===")
    if len(t):
        print(f"markets with trades   : {t['condition_id'].nunique()}")
        print(f"trades kept           : {len(t):,}")
        print(f"wallets               : {t['proxy_wallet'].nunique():,}")
        print(f"USD volume (sample)   : ${(t['price'] * t['size']).sum():,.0f}")
        print(f"price mean/median     : {t['price'].mean():.3f} / {t['price'].median():.3f}")
        print(f"win share of trades   : {t['won'].mean():.3f}")

    #  export ----------------------------------------------------------------
    mk_out = mk.drop(columns=["outcomes", "final_prices"], errors="ignore")
    mk_out.to_parquet(PROCESSED_DIR / "markets_clean.parquet", index=False)
    if len(t):
        t.to_parquet(PROCESSED_DIR / "trades_clean.parquet", index=False)
    if len(wa):
        wa.to_parquet(PROCESSED_DIR / "wallet_ages.parquet", index=False)

    print(f"\nwrote: {sorted(p.name for p in PROCESSED_DIR.glob('*.parquet'))}")
    print("next: analyze/features.py, analyze/majority.py, analyze/spark_wallets.py")


if __name__ == "__main__":
    main()
