# Status

The pilot is being built from `docs/PLAN.md`. Phases 1 and 2 of 6 are done.

## Built

- `backend/`: FastAPI on SQLite. `uv run -m backend.seed` resets the database at `backend/undercover.db` from `data/`, and the backend seeds it on startup if the file is missing. Read operations: `list_claims`, `get_claim`, `get_policy`, `get_claim_history`, `list_handlers` and `health`. Write operations: `start_claim`, `add_step`, `list_steps`, `record_decision`, `pay_claim` and `sign_off`. A claim moves from `waiting` to `in_progress`, then to `decided`, or to `waiting_for_sign_off` when it's approved for more than $1,000. Payments go through one function that pays only an approved claim, only the approved amount, only once, and over $1,000 only after a handler's sign-off.
- `agent/`: still the skeleton, `run(claim_id, thread_id)` with one tool that calls the health route
- `dashboard/`: still the skeleton page that shows whether the backend is up
- `e2e/`: one test of that page

## Run it

- `npm run dev` starts the backend on port 8000 and the dashboard on port 5173
- `uv run -m backend.seed` resets the queue
- `npm run check` runs every check
