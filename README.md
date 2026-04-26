# Phase App Vertical Slice

This repository now includes a runnable 1-week MVP vertical slice for:
- logging bench sessions and sets
- reading back raw session data
- computing live bench metrics (top set e1RM + bench volume)

## Run tests

```bash
pytest -q
```

## Run demo script

```bash
python scripts/demo_vertical_slice.py
```

## Run local HTTP server + UI

```bash
python -m phase_app.http_server
```

Then open `http://127.0.0.1:8000`.
