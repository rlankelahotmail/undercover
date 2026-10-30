# Status

The pilot is being built from `docs/PLAN.md`. Phase 1 of 6 is done.

## Built

- `backend/`: FastAPI on SQLite. `uv run -m backend.seed` resets the database at `backend/undercover.db` from `data/`, and the backend seeds it on startup if the file is missing. Read operations: `list_claims`, `get_claim`, `get_policy`, `get_claim_history`, `list_handlers` and `health`.
- `agent/`: still the skeleton, `run(claim_id, thread_id)` with one tool that calls the health route
- `dashboard/`: still the skeleton page that shows whether the backend is up
- `e2e/`: one test of that page

## Run it

- `npm run dev` starts the backend on port 8000 and the dashboard on port 5173
- `uv run -m backend.seed` resets the queue
- `npm run check` runs every check
