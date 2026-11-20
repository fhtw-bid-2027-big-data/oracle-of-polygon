"""Shared helpers for the Oracle of Polygon pipeline.

Central place for: .env loading, paths, HTTP with retry/back-off and
politeness pause, and the raw-response disk cache (that doubles as
checkpoint/resume storage for the batch pulls).
"""
import json
import os
import time
from pathlib import Path

import requests

# ---------------------------------------------------------------- paths ----
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
TRADES_DIR = RAW_DIR / "trades"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = ROOT / "output"
for d in (RAW_DIR, TRADES_DIR, PROCESSED_DIR, OUTPUT_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- .env -----
# Keys never go into the repo (see .gitignore). Values here are defaults.
ENV_PATH = ROOT / ".env"
ENV = {}
if ENV_PATH.exists():
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            ENV[k.strip()] = v.strip().strip('"').strip("'")

def env(key: str, default: str = "") -> str:
    """Environment variable, falling back to the .env file."""
    return os.environ.get(key, ENV.get(key, default))

# ---------------------------------------------------------------- config ---
GAMMA_URL = "https://gamma-api.polymarket.com"
DATA_URL = "https://data-api.polymarket.com"        # only /v2/... routes; v1 is retired
CLOB_URL = "https://clob.polymarket.com"
ETHERSCAN_V2 = "https://api.etherscan.io/v2/api"    # Polygonscan lives here now (chainid=137)
POLYGON_CHAIN_ID = 137

ETHERSCAN_KEY = env("ETHERSCAN_API_KEY")
MONGO_URI = env("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = env("MONGO_DB", "polymarket")

UA_HEADER = {"User-Agent": "oracle-of-polygon-student-project/0.2"}

# Mechanical short-term crypto price bets ("Up or Down" 5m/15m): no
# information edge possible and they flood the feed -> filtered out.
CRYPTO_PRICE_PATTERN = (
    r"(?i)(up.{0,4}down|updown)"
)

# ---------------------------------------------------------------- http -----


def get_json(url, params=None, retries=4, pause=1.0):
    """GET -> parsed JSON.

    Only retries what can succeed later (429 / 5xx / network errors).
    Other 4xx (bad params, retired endpoints) fail immediately so bugs are
    visible instead of being papered over. Respects Retry-After when present.
    """
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=UA_HEADER, timeout=30)
            if r.status_code == 429 or r.status_code >= 500:
                wait = float(r.headers.get("Retry-After", pause * 2 ** attempt))
                print(f"  {r.status_code}: backing off {wait:.1f}s ({url})")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except requests.HTTPError:
            code = getattr(r, "status_code", "?")
            print(f"  permanent HTTP {code} error on {url} with {params}")
            return None
        except requests.RequestException as e:      # timeouts, connection reset...
            print(f"  retry {attempt + 1}/{retries} on {url}: {e}")
            time.sleep(pause * 2 ** attempt)
    return None


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False))


def load_json(path: Path):
    return json.loads(path.read_text())
