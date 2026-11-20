# Entscheidungen & API-Findings (laufend ergänzt)

## Label-/Zielgrößen-Entscheidung (Board issue #9)

**"Verdächtig" ist kein Ground-Truth-Label** – Insider-Trading kann aus
öffentlichen Daten nicht bewiesen werden. Deshalb zweiteilig:

1. **Primär (unsupervised):** Anomaly-Discovery auf der Wallet-Feature-Tabelle
   (analyze/features.py). Modell: **IsolationForest** (sklearn) auf
   standardisierten Features; Score = Anomalie-Score. Das Verfahren liefert
   ein Ranking, kein Urteil.
2. **Sekundär (schwaches Label fürs supervised Experiment):** Heuristik-Label
   `suspect_heuristic = 1` wenn ein Wallet **drei Bedingungen** erfüllt:
   - `account_age_days < 90` (frisch on-chain),
   - `contrarian_entry > 0.5` (Gewinner günstig eingekauft, gegen die Crowd),
   - `n_repeat_wins >= 2` (mehrfach wiederholt).
   Damit trainieren wir im Final einen **Decision Tree** (nachvollziehbar,
   gut präsentierbar) als Kontrollmodell und vergleichen sein Ranking mit dem
   IsolationForest. Wichtig (Doku): das Label ist eine **Proxy-Definition**,
   an der das Modell nur die eigene Heuristik lernt – wir nutzen es für
   Interpretierbarkeit, nicht als "Wahrheit".

## Dokumentierte API-Findings (hart getestet, Nov 2026)

| Beobachtung | Konsequenz im Code |
|---|---|
| Data API **v1 ist retired** (`/trades` gibt JSON-Error "Data API v1 has been retired", Verweis auf /v2/). Kein 410, kein verlässliches "retired am"-Datum dokumentiert. | alle Calls laufen über `/v2/` (common.py `DATA_URL`). |
| v2-Trades-Pagination ist **cursor-only**: `offset` wird mit Fehler abgewiesen ("pages are cursor-only, pass 'cursor' from a prior response's next_cursor"). Cursor zurück in `pagination.next_cursor`; **alle Filter-Parameter müssen auf jede Seite neu mitgeschickt werden**. | `fetch_market_trades()` folgt dem Cursor. |
| `limit` über ~200 verhält sich unzuverlässig (gemessen: limit=500 lieferte nur 17 Zeilen). limit=100/200 sauber. | Pages à 200 (extract/fetch_trades.py). |
| Gamma `/markets`: `order=volume` sortiert den Volume-**STRING** (alphabetisch!) – top-volume-Märkte kommen nur mit `order=volumeNum`. | fetch_markets.py + Notebook benutzen volumeNum. |
| Manche Endpoints antworten **403 ohne User-Agent-Header**. | globaler UA-Header in common.py. |
| **Polygonscan existiert als eigenständige API nicht mehr**; Polygon läuft über die Etherscan unified v2 API mit `chainid=137`, Key nötig. | extract/fetch_wallet_age.py benutzt ETHERSCAN_V2, chainid=137. |
| Gamma `/markets`: klassisches limit/offset; `outcomes`/`outcomePrices`/`clobTokenIds` sind **JSON-Strings im JSON**. | parse über json.loads (fetch_markets.py). |
| Data API `/v2/positions`: **user-Filter** gibt Wrapper `{"data": [...]}`, **condition-Filter** gibt ein plain Array zurück. Beide max. 100 je Call. | Form-Check in fetch_positions.py. |
| v2-Trades: `outcome_index` ist teils `999` (API-Default "unbekannt"), z. B. im Live-Feed. | Calibration/Features filtern auf `!= 999`. |
| CLOB `prices-history` (fidelity in Minuten) liefert vergangene Preise je Token (`clobTokenIds[0]` = Outcome 0). | Für "Crowd-Preis vor Auflösung"-Analysen im Final. |

## Kategorie-Tags (notiert für den Final)

`/markets` liefert keine brauchbare Tag-Liste mit (events[] haben keine
"tags"). Für kategorienspezifische Analysen: `/events?slug=...` (dort gibt es
tags wie "Politics", "Sports", "Crypto"). Vergleich-Prozedur bleibt gleich,
nur die Scope-Liste wird je Kategorie aufgebaut. Bis dahin: Regex-Filter
(Krypto raus), "Politik/Welt/Entscheidungen" implizit über die
Top-Volume-Reihenfolge.

## Architektur-/Tool-Entscheidungen

- **Raw = MongoDB** (schema-frei, genau die API-Dokumente, DB-seitige
  Aggregationen als Processing-Nachweis), **clean = Parquet** (kolumnar,
  Spark-Interface).
- **Cache/alles resume-fähig**: jede Rohantwort liegt als Datei in `data/raw/`
  – das ist gleichzeitig die "make data available"-Anforderung der LV.
- **.env** für Keys (nie committen), MONGO_URI zeigt lokal oder auf den
  Team-Server (issue #23).
