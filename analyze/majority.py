"""Board issue #12 - "Wie oft hat die Mehrheit recht?" (crowd quality).

Calibration view: every BUY trade pays a price that should equal the true
probability of the outcome (perfectly calibrated crowd -> win rate in each
price bucket equals the bucket's implied probability). We bucket all bought
trades by price and compare actual win rate against implied probability.

Outputs (output/):
  crowd_calibration.png    price vs. actual win rate + diagonal (ideal)
  crowd_calibration.csv    the bucket table (n, avg price, win rate, gap)

This is the second headline result of the project: even if we find few
insiders, we can quantify how good the crowd (and thus market prices) is.

Usage:
    python analyze/majority.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")                       # no display needed on servers
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import OUTPUT_DIR, PROCESSED_DIR


def main():
    t = pd.read_parquet(PROCESSED_DIR / "trades_clean.parquet")
    t = t[t["side"] == "BUY"].copy()
    t = t[t["outcome_index"] != 999]        # unknown outcome index -> not scoreable
    t["bin"] = pd.cut(t["price"], bins=[i / 10 for i in range(11)])

    cal = (t.groupby("bin", observed=True)
             .agg(avg_price=("price", "mean"),
                  win_rate=("won", "mean"),
                  n=("won", "size"))
             .reset_index())
    cal["gap"] = cal["win_rate"] - cal["avg_price"]
    cal["bucket"] = cal["bin"].astype(str)

    major = t[t["price"] > 0.5]
    print("=== Crowd quality (per price bucket) ===")
    print(cal[["bucket", "n", "avg_price", "win_rate", "gap"]]
          .to_string(index=False, float_format=lambda x: f"{x:,.3f}"))
    if len(major):
        rate = major["won"].mean()
        print(f"\nTrades that bought the favourite (price > 0.5): {len(major):,}")
        print(f"  -> those favourites won in {rate:.1%} of bought trades")
    under = t[t["price"] <= 0.2]
    if len(under):
        print(f"Trades that bought heavy underdogs (<= 0.2): {len(under):,}")
        print(f"  -> underdogs won in {under['won'].mean():.1%} of bought trades")

    fig, ax = plt.subplots(figsize=(6.5, 5))
    ax.plot([0, 1], [0, 1], "--", color="gray", label="perfect calibration")
    ax.plot(cal["avg_price"], cal["win_rate"], "o-", label="Polymarket crowd")
    for _, r in cal.iterrows():
        ax.annotate(f"{int(r['n'])}", (r["avg_price"], r["win_rate"]),
                    fontsize=7, alpha=0.6, xytext=(3, -8),
                    textcoords="offset points")
    ax.set_xlabel("price paid (= implied probability)")
    ax.set_ylabel("actual share that won")
    ax.set_title("Wisdom of the crowd: price vs. outcome (n per bucket annotated)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "crowd_calibration.png", dpi=150)

    cal.to_csv(OUTPUT_DIR / "crowd_calibration.csv", index=False)
    print(f"\ncharts + table written to output/ (buckets: {len(cal)})")


if __name__ == "__main__":
    main()
