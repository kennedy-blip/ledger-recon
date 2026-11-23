# LedgerRecon

LedgerRecon is a lightweight payment reconciliation workspace for comparing an internal ledger with gateway settlement exports. It highlights exact matches, tolerance-based amount differences, duplicate references, missing settlements, and unmatched gateway rows.

## Stack

- Vanilla HTML, CSS, and ES modules in `public/` (no TypeScript or bundler)
- Python 3.12 Vercel Functions in `api/`
- Python standard library + SQLite
- Tailwind CSS CDN for utility styling

## Local development

```bash
python -m pip install -r requirements.txt
python -m http.server 8080 --directory public
```

The static server demonstrates the browser-side fallback reconciler. For the API, run the project with the Vercel CLI (`vercel dev`) in an environment with the Vercel CLI installed.

## API

- `GET /api/batches` — seeded demo batch and ledger rows
- `POST /api/batches` — replace the current in-process batch or reset the demo data
- `POST /api/reconcile` — run matching or update an exception's workflow status

## Persistence note

The demo backend uses SQLite in-memory storage, as requested. Vercel serverless instances are ephemeral and may be reused independently; this is not durable production accounting storage. For production financial records, replace the in-memory connection with a managed persistent database and add authentication, authorization, audit retention, and idempotent ingestion.

## Deploy to Vercel

Import this repository into Vercel with the repository root as the project root. No Node build step is required. The `vercel.json` configuration serves `public/` and routes `/api/*` to the matching Python function.
