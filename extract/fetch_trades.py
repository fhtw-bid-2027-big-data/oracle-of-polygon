"""Board issues #3a + #18 - Data API v2 trades, prototype + batch with resume.

v2 specifics (v1 is retired, see docs/decisions.md):
  - route  /v2/trades
  - filter per market via `condition` (NOT `market`)
  - cursor pagination: first page without cursor, then repeat ALL filters
    plus `cursor` = pagination.next_cursor until pagination.has_more is false
  - limit: we use 200 per page (much larger values misbehave; measured)

Prototype for exactly ONE market (issue #3a):
    python extract/fetch_trades.py --condition 0xdd2247...910917

Batch over the whole scope with checkpoint/resume (issue #18):
    python extract/fetch_trades.py --scope
    python extract/fetch_trades.py --scope --sample-markets 5 --max-pages 30   # quick test

Resume behaviour: every market's trades land in data/raw/trades/<cid>.json;
existing files are skipped, so an interrupted run simply continues. A full
pull of the top markets takes a while (biggest markets have 6.000+ trades,
see docs/scoping.md) - that is exactly what the resume design is for.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import DATA_URL, RAW_DIR, TRADES_DIR, get_json, load_json, save_json


def fetch_market_trades(condition_id, max_rows=None, page=200, max_pages=None,
                        pause=0.2):
    """Trades of one market, following the cursor. max_rows/max_pages = safety caps."""
    out, cursor, pages = [], None, 0
    while pages < (max_pages or 10 ** 9):
        params = {"condition": condition_id, "limit": page}
        if cursor:
            params["cursor"] = cursor         # cursor carries ONLY the position
        resp = get_json(f"{DATA_URL}/v2/trades", params)
        if resp is None:
            break
        data = resp.get("data", []) if isinstance(resp, dict) else resp
        if not data:
            break
        out.extend(data)
        pages += 1
        pg = (resp.get("pagination") or {}) if isinstance(resp, dict) else {}
        if not pg.get("has_more"):
            break
        cursor = pg.get("next_cursor")
        if not cursor:
            break
        time.sleep(pause)                     # be polite, avoid 429s
        if max_rows is not None and len(out) >= max_rows:
            break
    return out[:max_rows] if max_rows else out


def trades_path(condition_id: str) -> Path:
    return TRADES_DIR / f"{condition_id[:42]}.json"


def run_condition(cid: str, label: str = "", max_pages=None):
    p = trades_path(cid)
    if p.exists():
        print(f"  [skip] {label[:50]:50s} already fetched ({p.name})")
        return
    tr = fetch_market_trades(cid, max_pages=max_pages)
    save_json(p, tr)
    print(f"  [ ok ] {label[:50]:50s} {len(tr):6d} trades")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--condition", help="single condition id (prototype mode, #3a)")
    ap.add_argument("--scope", action="store_true",
                    help="batch over all scope markets (resume mode, #18)")
    ap.add_argument("--sample-markets", type=int, default=0,
                    help="batch over only the first N scope markets")
    ap.add_argument("--max-pages", type=int, default=None,
                    help="cap cursor pages per market (quick tests; default: full history)")
    args = ap.parse_args()

    if args.condition:
        cid = args.condition.lower().strip()
        tr = fetch_market_trades(cid, max_pages=args.max_pages)
        save_json(trades_path(cid), tr)
        print(f"{len(tr)} trades for {cid} -> {trades_path(cid)}")

    elif args.scope or args.sample_markets:
        scope = load_json(RAW_DIR / "markets_scope.json")
        todo = scope if not args.sample_markets else scope[:args.sample_markets]
        print(f"batch: {len(todo)} scope markets (existing files = resume points)")
        for i, m in enumerate(todo, 1):
            print(f"({i}/{len(todo)})", end="")
            run_condition(m["condition_id"], m["question"], max_pages=args.max_pages)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
