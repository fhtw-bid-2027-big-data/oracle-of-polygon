# Team-Aufgabenverteilung (Board issue #21 – Vorschlag, im Board abzunicken)

Team: Muhammet Fatih Yildiz, Peyman Aparviz, Orlando Poensgen

Der Plan folgt den 4 Layern der Projektangabe; jeder Layer hat einen
Hauptverantwortlichen, die anderen beiden reviewen (PR-Review). Entscheidungen
(Scope, Label-Definition, ...) treffen wir gemeinsam im Board.

| Phase (bis)              | Fatih                        | Peyman                      | Orlando                   |
|--------------------------|------------------------------|-----------------------------|---------------------------|
| Zwischenabgabe (Class 6) | extract/ (Gamma, Trades,      | clean/ (to_mongo.py,        | Notebook-Aufbau, Story,   |
|                          | Positions, Wallet-Age) &     | build_parquet.py,           | Crowd-Calibration         |
|                          | API-Doku in docs/decisions   | Qualitaets-Checks           | (analyze/majority.py)     |
| Final (Class 8)          | Spark-Pipeline               | ML: Features -> Label ->    | Visualisierung & Story:   |
|                          | (analyze/spark_wallets.py,   | IsolationForest + Decision  | Ranking-Charts, Timing,   |
|                          | Skalierung, run_all-Lauf)    | Tree (analyze/train.py,    | Praesentation (10 min)    |
|                          |                              | score.py)                   | + Kurzbericht (docs)      |

Orga-Regeln:
- Pipeline-Aenderungen immer ueber Branch + PR, mindestens 1 Reviewer.
- Data-Rohdaten liegen NICHT im Repo (zu gross), sondern lokal / auf dem
  Team-Mongo-Server (Issue #23). `data/` ist per .gitignore ignoriert.
- API-Keys nur in `.env` (Issue #17), niemals committen.
