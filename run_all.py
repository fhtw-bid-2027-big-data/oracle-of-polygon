"""Board issue #20 - Pipeline orchestration: Extract -> Clean -> Analyze.

One command runs the whole pipeline; every step skips work that is already
done (caches in data/raw), so the run is cheap to repeat and resumeable.

    python run_all.py --sample 20      # small sample first (recommended)
    python run_all.py                 # full scope (long! resume-able)

Prerequisites: .env with ETHERSCAN_API_KEY (wallet-age step skips itself
without it), MongoDB via MONGO_URI (its step warns if unreachable).
"""
import shlex
import subprocess
import sys

STEPS = [
    ("1", "extract/fetch_markets.py --n 500"),
    ("2", "extract/fetch_trades.py --scope"),          # resume-capable batch (#18)
    ("3", "extract/fetch_positions.py --top 200"),
    ("4", "extract/fetch_wallet_age.py --top 200"),   # needs ETHERSCAN_API_KEY
    ("5", "clean/to_mongo.py"),                        # needs MongoDB
    ("6", "clean/build_parquet.py"),
    ("7", "analyze/features.py"),
    ("8", "analyze/majority.py"),
    ("9", "analyze/spark_wallets.py"),                # needs pyspark
]


def main():
    sample = None
    if "--sample" in sys.argv:
        sample = sys.argv[sys.argv.index("--sample") + 1]

    for num, cmd in STEPS:
        run = cmd
        if sample and "fetch_trades.py" in cmd:
            run = f"extract/fetch_trades.py --scope --sample-markets {sample} --max-pages 30"
        print(f"\n{'=' * 70}\nstep {num}: {run}\n{'=' * 70}")
        rc = subprocess.call([sys.executable] + shlex.split(run))
        if rc != 0:
            print(f"\nstep {num} failed (exit {rc}) - fix and re-run; "
                  "the pipeline resumes where it stopped.")
            sys.exit(rc)
    print("\nAll steps done. Deliverable notebook: polymarket_delivery2.ipynb")


if __name__ == "__main__":
    main()
