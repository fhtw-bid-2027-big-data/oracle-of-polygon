# Scoping – wie viel Daten ziehen wir? (Board issue #16)

**Entschieden (Zwischenabgabe):** Wir starten mit den **500 volumenstärksten
geschlossenen Märkten**, gefiltert auf binäre, sauber aufgelöste, nicht-Krypto,
Volumen ≥ $50k – daraus zieht der Batch-Lauf (`extract/fetch_trades.py --scope`)
alle Trades. Kategorien-Filter (nur Politik/Welt/Entscheidungen) bewerten wir
im Final: die Gamma `/markets`-Antworte tragen keine nützliche Tag-Liste mit;
kategorienspezifische Analysen brauchen den `/events`-Endpoint (notiert in
docs/decisions.md).

**Wichtig bei der Sortierung:** `order=volumeNum` (numerisch) verwenden, NICHT
`order=volume` – das sortiert den Volume-STRING und liefert alphabetischen
Unsinn (gemessen: gleiche Abfrage liefert völlig andere, kleine Märkte).

## Gemessene Datenmengen (Probeläufe, Nov 2026)

| Messung | Wert |
|---|---|
| Gamma: Seiten à 100 Märkte bis 500 geladen | 5 Requests, ~2 s |
| Volumenstärkster Markt (Trump 2024) | > 6.000 Trades in 60 Cursor-Seiten, Pagination noch nicht am Ende |
| Scope-Filter (Top 300, binär + resolved + ≥ $50k) | 299 von 300 Märkten überleben den Filter |
| Top-50-Märkte, geschätzte Trades je Markt | ~1.000 – 10.000+ |
| **Scope-Schätzung: 50 Märkte** | **~100.000 – 300.000 Trades, ~50–150 MB JSON** |
| **Scope-Schätzung: 500 Märkte** | **~1–3 Mio. Trades, ~0,5–1,5 GB JSON** |
| Requests (200 Trades je Request) | 50 Märkte ≈ 1.500 Requests ≈ 15–30 min bei Politeness-Pause |
| Etherscan (Wallet-Alter) | ~3.000–10.000 einzigartige Wallets je nach Scope; bei 4 req/s ≈ 15–40 min → deshalb Cache/Resume (#5) |

## Warum das nicht explodiert

- Der Batch-Lauf ist **je Markt gecached** (data/raw/trades/<cid>.json):
  Abbruch = Weitermachen, Wiederholung = gratis. Für schnelle Tests gibt es
  `--max-pages` (Seitencap pro Markt).
- MongoDB speichert die Rohdokumente; Parquet nur die sauberen, flachen
  Tabellen (Spark-fähig).
- Für den Final laufen wir denselben Code mit größerem `--n`, nichts anderes.

## Guardrails

- Rate-Limits: pause 0,2 s/Request (Data API), 0,25 s (Etherscan free tier).
- Krypto-5m/15m-Märkte fluten den Feed ("Up or Down"-Bets) und sind für unsere
  Fragestellung wertlos → rausgefiltert (Regex, siehe common.py).
- Dünne Märkte (< $50k) haben keine stabile Crowd-Preis-Basis → raus.
