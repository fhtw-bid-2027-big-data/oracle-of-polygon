"""Board issue #6 - Raw JSON into MongoDB.

Collections (schema-free, original API documents, upsert = idempotent):

| collection    | key                                        | content                    |
|---------------|--------------------------------------------|----------------------------|
| markets_raw   | conditionId                                | Gamma market documents     |
| trades_raw    | transaction_hash + token_id + proxy_wallet | v2 trade documents         |
| positions_raw | proxy_wallet + token_id                    | positions per wallet       |
| wallets_raw   | address                                    | first-tx (age, funding)    |

Why MongoDB / what we exploit: the documents are nested and stringly-typed
(outcomes as JSON-in-JSON); a document store keeps them exactly as the API
returned them, so any future question can be answered without re-fetching
or schema migration. We also run one aggregation INSIDE the DB to show the
DB is a processing interface, not just a dump.

The team Mongo lives on the cloud server (issue #23) - set MONGO_URI in .env.

Usage:
    python clean/to_mongo.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import DB_NAME, MONGO_URI, RAW_DIR, TRADES_DIR


def upsert(coll, docs, key_fn):
    """Idempotent insert: re-running updates existing docs instead of duplicating them."""
    from pymongo import UpdateOne
    ops = [UpdateOne(key_fn(d), {"$set": d}, upsert=True) for d in docs]
    if ops:
        coll.bulk_write(ops, ordered=False)


def main():
    from pymongo import MongoClient
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]

    markets = json.loads((RAW_DIR / "markets_raw.json").read_text()) \
        if (RAW_DIR / "markets_raw.json").exists() else []
    trades = [t for p in sorted(TRADES_DIR.glob("*.json"))
              for t in json.loads(p.read_text())]
    positions = []
    if (RAW_DIR / "positions.json").exists():
        positions = [dict(doc, proxy_wallet=w)
                     for w, docs in json.loads((RAW_DIR / "positions.json").read_text()).items()
                     for doc in docs]
    wallets = [{"address": w, **v}
               for w, v in (json.loads((RAW_DIR / "wallet_ages.json").read_text())
                            if (RAW_DIR / "wallet_ages.json").exists() else {}).items()]

    if not markets and not trades:
        print("no raw data found - run the extract/ scripts first")
        return

    upsert(db.markets_raw, markets, lambda d: {"conditionId": d.get("conditionId")})
    upsert(db.trades_raw, trades,
           lambda d: {"transaction_hash": d.get("transaction_hash"),
                      "token_id": d.get("token_id"),
                      "proxy_wallet": d.get("proxy_wallet")})
    upsert(db.positions_raw, positions,
           lambda d: {"proxy_wallet": d.get("proxy_wallet"), "token_id": d.get("token_id")})
    upsert(db.wallets_raw, wallets, lambda d: {"address": d.get("address")})

    # typical access paths -> indexes (trades per market over time / per wallet)
    db.trades_raw.create_index([("condition_id", 1), ("timestamp", 1)])
    db.trades_raw.create_index("proxy_wallet")

    print({c: f"{db[c].count_documents({}):,}" for c in
           ["markets_raw", "trades_raw", "positions_raw", "wallets_raw"]})

    # DB-side aggregation demo: wallets that traded the most USD so far
    pipe = [{"$group": {"_id": "$proxy_wallet",
                        "n_trades": {"$sum": 1},
                        "usd": {"$sum": {"$multiply": ["$size", "$price"]}}}},
            {"$sort": {"usd": -1}}, {"$limit": 5}]
    print("top wallets (aggregation INSIDE MongoDB):")
    for d in db.trades_raw.aggregate(pipe):
        print(f"  {d['_id'][:14]}... {d['n_trades']:6d} trades  ${d['usd']:>12,.0f}")


if __name__ == "__main__":
    main()
