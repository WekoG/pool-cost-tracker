# pool-cost-tracker

Lokale WebApp (FastAPI + Streamlit) zur Auswertung von Pool-Kosten aus Paperless-ngx (Tag-Filter `Pool`) plus manuellen Kostenpositionen.

## Features

- Sync von Paperless-ngx per REST API (`POST /sync`)
- Filtert nur Dokumente mit Tag `POOL_TAG_NAME` (Default: `Pool`)
- OCR-Extraktion: `Firma` + `Brutto/Endbetrag (EUR)` mit Heuristik, Confidence, Debug-Infos
- Speicherung in SQLite (`invoices`, `manual_costs`)
- Manuelle Kostenpositionen ohne Dokument
- Dashboard mit KPIs, Top Vendors, Kosten nach Kategorie
- CSV-Export über alle Kosten (`invoices` + `manual_costs`)
- Optionaler Hintergrund-Scheduler (Auto-Sync)
- Alembic Migrationen enthalten

## Tech-Stack

- Backend: Python 3.12, FastAPI, httpx, SQLAlchemy, Alembic
- UI: Streamlit
- DB: SQLite (Volume `/data`)
- Tests: pytest

## Paperless Token beschaffen

In Paperless-ngx im Benutzerprofil einen API-Token erzeugen (User-Profil -> API Token) und in `.env` als `PAPERLESS_TOKEN` eintragen.

## Environment Variablen

Alle Paperless-Zugriffe laufen ausschließlich über `settings.PAPERLESS_BASE_URL`.
Keine IP ist im Request-Code hardcodiert.

Verbindliche Variablen:

- `PAPERLESS_BASE_URL` (Default: `http://172.16.10.10:8000`)
- `PAPERLESS_TOKEN` (required)
- `POOL_TAG_NAME` (Default: `Pool`)
- `SYNC_PAGE_SIZE` (Default: `100`)
- `SYNC_LOOKBACK_DAYS` (Default: `365`)
- `DATABASE_URL` (Default: `sqlite:////data/app.db`)
- `SCHEDULER_ENABLED` (Default: `false`)
- `SCHEDULER_INTERVAL_MINUTES` (Default: `360`)
- `SCHEDULER_RUN_ON_STARTUP` (Default: `true`)

## `.env.example`

Enthaltene Defaults in `/Users/weko/Documents/Codex/Pool_Kosten/.env.example`:

```env
PAPERLESS_BASE_URL=http://172.16.10.10:8000
PAPERLESS_TOKEN=dein_token
POOL_TAG_NAME=Pool
SYNC_PAGE_SIZE=100
SYNC_LOOKBACK_DAYS=365
DATABASE_URL=sqlite:////data/app.db
SCHEDULER_ENABLED=false
SCHEDULER_INTERVAL_MINUTES=360
SCHEDULER_RUN_ON_STARTUP=true
```

## Start mit Docker Compose

1. Datei kopieren: `.env.example` -> `.env`
2. `PAPERLESS_TOKEN` eintragen
3. Optional `PAPERLESS_BASE_URL` auf deinen Host/IP ändern
4. Starten:

```bash
docker compose up --build
```

## Aufruf

- UI (Streamlit, Standardport): `http://<host>:8501`
- API (falls Port-Mapping aktiv): `http://<host>:8000`

Docker Compose mappt standardmäßig:

- `ui: 8501:8501`
- `api: 8000:8000`

## Paperless Base URL ändern (wichtig)

Nur die `.env` anpassen, z. B.:

```env
PAPERLESS_BASE_URL=http://192.168.1.50:8000
```

Danach neu starten:

```bash
docker compose up -d --build
```

## Scheduler (Auto-Refresh)

Optionaler Hintergrund-Scheduler im API-Service:

- `SCHEDULER_ENABLED=false`: kein Background-Job/Thread läuft
- `SCHEDULER_ENABLED=true`: Sync läuft beim Start optional (`SCHEDULER_RUN_ON_STARTUP`) und danach alle `SCHEDULER_INTERVAL_MINUTES`

Beispiel:

```env
SCHEDULER_ENABLED=true
SCHEDULER_INTERVAL_MINUTES=60
SCHEDULER_RUN_ON_STARTUP=true
```

## Alembic Migrationen

Migrationen liegen unter `/Users/weko/Documents/Codex/Pool_Kosten/alembic/versions`.

Lokal ausführen:

```bash
alembic upgrade head
```

Im API-Container (optional):

```bash
docker compose exec api alembic upgrade head
```

## Hintergrundbild (optional, lokal)

- Lege ein lokales Bild unter `/Users/weko/Documents/Codex/Pool_Kosten/ui/assets/pool_bg.jpg` ab.
- Die UI nutzt es automatisch als Hintergrund, wenn die Datei existiert.
- Kein automatischer Download externer Bilder ist implementiert.
- Nur verwenden, wenn Nutzungsrechte vorliegen (z. B. eigenes Bild / korrekt lizenzierte Quelle; Beispielhinweis: Poolakademie Rechteckpool Seite).

## API Endpoints

- `POST /sync`
- `GET /invoices` (Filter: `needs_review`, `search`, `sort`)
- `PUT /invoices/{id}`
- `POST /manual-costs`
- `GET /manual-costs`
- `PUT /manual-costs/{id}`
- `DELETE /manual-costs/{id}`
- `GET /summary`
- `GET /export.csv`
- `GET /config`

## Tests

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-api.txt -r requirements-dev.txt
PYTHONPATH=. pytest -q
```

## Paperless API Nutzung (Tag-Filter)

Die App verwendet:

1. `GET ${PAPERLESS_BASE_URL}/api/tags/` (paginierend), exakter Match `name == POOL_TAG_NAME`
2. `GET ${PAPERLESS_BASE_URL}/api/documents/?tags__id=<pool_tag_id>&page_size=<SYNC_PAGE_SIZE>&ordering=-created&truncate_content=false` (paginierend)

Wenn der Tag nicht gefunden wird, bricht der Sync mit einer klaren Fehlermeldung ab (`Tag '<name>' nicht gefunden`).
Wichtig: Der Tag muss in Paperless exakt existieren (Groß-/Kleinschreibung relevant) und die gewünschten Dokumente müssen diesen Tag tragen.
