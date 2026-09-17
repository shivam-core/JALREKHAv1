# Deployment

JALREKHA uses Vercel for hosting both the static frontend and the FastAPI backend on the same domain.

## Project Structure
- `public/`: Static HTML, CSS, JS, and prepared JSONs. Served by Vercel static router.
- `api/`: Re-routed to `app.py` via `vercel.json` as a Python Serverless Function.
- `data/processed/`: The minimum necessary graph data for the backend algorithm.

## Pre-requisites
- Node.js & Vercel CLI (`npm i -g vercel`)
- Python 3.12 (Local)

## How to Deploy
1. Run local prep scripts (`scripts/prepare_*.py`) if the geographic extent changes.
2. Ensure data in `data/processed` and `public/data/water` is up-to-date.
3. Use the Vercel CLI:
```bash
vercel deploy --prod
```

## Vercel Configuration
- `vercel.json` configures the static/API routing and excludes large raw files (e.g. `data/raw`, `tests/`) from the Python bundle to stay within Hobby tier limits (max 250MB uncompressed).
- Fast execution is ensured because the Python script relies on precomputed Graph nodes and simple in-memory execution of NetworkX algorithms.
