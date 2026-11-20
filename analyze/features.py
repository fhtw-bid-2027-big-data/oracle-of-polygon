"""Board issue #8 - Feature table per wallet (basis for the suspicion score).

Reads data/processed/trades_clean.parquet (+ wallet ages) and builds one row
per wallet. These features are the input for the ML step:

  account_age_days     first on-chain tx -> market close (red flag if tiny)
  avg_winner_price     avg entry price on winning trades (low = contrarian)
  contrarian_entry     1 - avg_winner_price (HIGH = won by betting against
                       the crowd at low prices)
  win_rate             share of the wallet's trades that won
  volume_usd, n_trades, n_markets
  concentration        share of volume on the wallet's single biggest market
  n_repeat_wins        how often the wallet won with a cheap (< 0.5) entry

Minimal trades per wallet (default 3) filters noise; a trust score needs
repetition to mean anything.

Usage:
    python analyze/features.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import PROCESSED_DIR

MIN_TRADES = 3
CONTRARIAN_THRESHOLD = 0.5     # entry below 0.5 on a winner = contrarian


def main():
    t = pd.read_parquet(PROCESSED_DIR / "trades_clean.parquet")
    wa_path = PROCESSED_DIR / "wallet_ages.parquet"
    wa = pd.read_parquet(wa_path) if wa_path.exists() else pd.DataFrame()

    t = t[t["side"] == "BUY"].copy()           # entry behaviour = buys
    t = t.assign(usd=t["price"] * t["size"])
    t = t.assign(closed_ts=pd.to_datetime(t["closed_time"], errors="coerce",
                                          utc=True, format="ISO8601"))
    t = t[t["outcome_index"] != 999]           # unknown outcome not scoreable

    g = t.groupby("proxy_wallet")
    feats = g.agg(
        n_trades=("price", "count"),
        n_markets=("condition_id", "nunique"),
        volume_usd=("usd", "sum"),
        win_rate=("won", "mean"),
        avg_winner_price=("price",
                          lambda p: p[t.loc[p.index, "won"] == 1].mean()),
        n_repeat_wins=("won",
                       lambda w: int(((t.loc[w.index, "price"] < CONTRARIAN_THRESHOLD)
                                      & (w == 1)).sum())),
    )
    feats["contrarian_entry"] = 1 - feats["avg_winner_price"]
    mk_vol = g.apply(lambda x: x.groupby("condition_id")["usd"].sum().max(),
                     include_groups=False)
    feats["concentration"] = (mk_vol / feats["volume_usd"]).fillna(0)

    if len(wa):
        wa2 = wa.copy()
        wa2["first_tx_dt"] = pd.to_datetime(
            pd.to_numeric(wa2["first_tx_ts"], errors="coerce"), unit="s", utc=True)
        last_ts = g["closed_ts"].max()
        feats = feats.join(wa2.set_index("proxy_wallet")["first_tx_dt"])
        feats["account_age_days"] = (
            (last_ts - feats["first_tx_dt"]).dt.total_seconds() / 86400)

    feats = feats[feats["n_trades"] >= MIN_TRADES] \
        .sort_values("volume_usd", ascending=False)
    feats.to_parquet(PROCESSED_DIR / "wallet_features.parquet")

    print(f"wallet features: {len(feats)} wallets "
          f"(>= {MIN_TRADES} buys) -> wallet_features.parquet")
    cols = [c for c in ["account_age_days", "contrarian_entry", "win_rate",
                        "n_repeat_wins", "volume_usd", "n_markets"]
            if c in feats.columns]
    print("\ntop 10 by contrarian_entry (bought eventual winners CHEAP):")
    print(feats.sort_values("contrarian_entry", ascending=False)[cols].head(10))


if __name__ == "__main__":
    main()
