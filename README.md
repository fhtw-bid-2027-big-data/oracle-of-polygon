# Oracle of Polygon

**Detecting Suspected Insider Trading on Polymarket via Account Trust Scores**
Big Data Analytics – Final Project, Group 4:
Muhammet Fatih Yildiz · Peyman Aparviz · Orlando Poensgen

**Research question:** Are there wallets on Polymarket that systematically
enter *against the crowd price*, early, and win – i.e. can suspected informed
(“insider”) trading be detected and scored with public data? And as a second
result: how good is the “wisdom of the crowd” on Polymarket actually?

> **Honest framing:** a high suspicion score is *not* proof of insider trading
> (skill, luck and multi-wallet users produce the same signature). We report
> anomalies and rankings, never accusations.

## Architecture (4 layers of the course)

| Layer | Here in the repo | Board issues |
|---|---|---|
| 1 – Data Source | `extract/` – Gamma API (markets), Data API **v2** (trades, positions), Etherscan/Polygon (wallet age, funding) | #2 #3a #4 #5 |
| 2 – Data Storage | raw JSON –> MongoDB (`clean/to_mongo.py`), cleaned –> Parquet (`clean/build_parquet.py`) | #6 #7 #23 |
| 3 – Analytics | `analyze/` – per-wallet features, crowd calibration, PySpark job | #8 #12 #19 |
| 4 – Output / Story | notebook `polymarket_delivery2.ipynb`, `output/` charts | #13 (final) |

The intermediate delivery (**class 6**) is documented in
`polymarket_delivery2.ipynb` (Jupyter Notebook = course documentation form:
code + description + results in one place).

## Setup

```bash
git clone https://github.com/fhtw-bid-2027-big-data/oracle-of-polygon.git
cd oracle-of-polygon
python -m venv venv && source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env        # insert your ETHERSCAN_API_KEY (free: etherscan.io/apidashboard)
docker run -d --name oop-mongo -p 27017:27017 mongo:7   # optional, local MongoDB
```

Run everything (resumeable, caches in `data/`):

```bash
python run_all.py --sample 20   # small sample first (recommended)
python run_all.py               # full scope (long, resume-able)
```

## Repo structure

```
common.py                   shared: .env loading, HTTP with retry/backoff, cache paths
run_all.py                  pipeline orchestration (#20)
extract/fetch_markets.py    closed markets from Gamma, crypto/noise filtered (#2)
extract/fetch_trades.py    v2 trades per market, cursor pagination, resume (#3a/#18)
extract/fetch_positions.py  positions per wallet (#4)
extract/fetch_wallet_age.py first on-chain tx per wallet, with cache (#5)
clean/to_mongo.py           raw docs -> MongoDB, upsert + indexes (#6)
clean/build_parquet.py      quality checks, merge, Parquet for Spark/pandas (#7)
analyze/features.py         per-wallet feature table (#8)
analyze/majority.py         crowd quality / calibration (#12)
analyze/spark_wallets.py    PySpark job: read Parquet, wallet features (#19)
docs/                       scoping, decisions, team split (#16 #9 #21)
data/                       raw + processed data (git-ignored; lives in Mongo/team server)
output/                     charts etc. (git-ignored)
polymarket_delivery2.ipynb  the notebook that documents the whole thing
```

## Data sources (all public)

| Source | URL | Key? |
|---|---|---|
| Polymarket Gamma API | `https://gamma-api.polymarket.com` | no |
| Polymarket Data API v2 | `https://data-api.polymarket.com/v2` | no |
| Polymarket CLOB API | `https://clob.polymarket.com` | no |
| Etherscan unified v2 (Polygon = chainid 137, former Polygonscan) | `https://api.etherscan.io/v2/api` | free key, .env |

**Keys and big data never go into git**: `.env`, `data/`, `output/` are in
`.gitignore`. Shared raw data lives on the team Mongo server (#23), not on GitHub.
