"""Board issue #19 (+ Processing Layer core) - first PySpark job.

Local Spark (local[*]), reads the cleaned Parquet files and aggregates per
wallet: n_trades, n_markets, volume, win rate, contrarian entry score.
Same result as analyze/features.py but through Spark - the pattern that
scales to the full dataset in the final delivery (all we change later is
the input size, not the job).

DoD of #19: PySpark runs, reads Parquet, shows count/schema. This script
does that AND the first wallet features computation.

Usage:
    python analyze/spark_wallets.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import PROCESSED_DIR

from pyspark.sql import SparkSession, functions as F


def main():
    spark = (SparkSession.builder
             .appName("oracle-of-polygon-wallets")
             .master("local[*]")
             .getOrCreate())
    spark.sparkContext.setLogLevel("ERROR")

    st = spark.read.parquet(str(PROCESSED_DIR / "trades_clean.parquet"))
    print("schema:")                        # DoD #19: count + schema
    st.printSchema()
    print(f"row count: {st.count():,}")

    # --- DoD of #19 ends here; below is the actual first wallet aggregation --
    buys = (st.filter(F.col("side") == "BUY")
              .filter(F.col("outcome_index") != 999)
              .withColumn("usd", F.col("price") * F.col("size")))

    wallet_feat = (buys.groupBy("proxy_wallet")
        .agg(F.count("*").alias("n_trades"),
             F.countDistinct("condition_id").alias("n_markets"),
             F.sum("usd").alias("volume_usd"),
             F.avg("won").alias("win_rate"),
             # high value = wallet won while buying at LOW prices
             #             = betting against the crowd (contrarian)
             F.avg(F.when(F.col("won") == 1, 1 - F.col("price")))
              .alias("contrarian_entry"))
        .filter("n_trades >= 3")
        .orderBy(F.desc("contrarian_entry")))

    wallet_feat.show(10, truncate=False)
    out = PROCESSED_DIR / "wallet_features_spark.parquet"
    wallet_feat.write.mode("overwrite").parquet(str(out))
    print(f"wallet features (Spark) -> {out}")
    spark.stop()


if __name__ == "__main__":
    main()
