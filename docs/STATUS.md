# Status

The pilot from `docs/PLAN.md` is built: all six phases are done.

## Built

- `backend/`: FastAPI on SQLite. `uv run -m backend.seed` resets the database at `backend/undercover.db` from `data/`, and the backend seeds it on startup if the file is missing. It never reads `data/evals/`, `data/security/` or the claims manual.
  - Read operations: `list_claims`, `get_claim`, `get_policy`, `get_claim_history` (name, customer-since date and earlier claims, no contact details), `list_handlers`, `get_instructions` and `health`.
  - Write operations: `start_claim`, `add_step`, `list_steps`, `record_decision`, `pay_claim` and `sign_off`.
  - A claim moves from `waiting` to `in_progress`, then to `decided`, or to `waiting_for_sign_off` when it's approved for more than $1,000. A handler's sign-off moves it to `decided`.
  - Payments go through one function that pays only an approved claim, only the approved amount, only once, and over $1,000 only after a handler's sign-off. A sign-off releases the payment through the same function.
- `backend/instructions.md`: the agent's instructions. The seed stores them with the policy wording after them, and `get_instructions` serves them. Reseed after you change them.
- `agent/`: `run(claim_id, thread_id)` runs the UnderCover Agent on one claim, with five tools over the API: `get_claim`, `get_policy`, `get_claim_history`, `record_decision` and `pay_claim`. It posts each tool call, result and message to the backend as a step while it works. It uses `openai/gpt-6-luna` at low reasoning effort, or the model in `MODEL_NAME`.
- `dashboard/`: React in the brand's colors and fonts, in light and dark mode, refreshing every 2 seconds.
  - The queue: the count in each state, and every claim with its status and decision.
  - A claim's page: the claim in full with its policy and the customer's history, the decision with its reason and policy section, a handler's sign-off for payouts over $1,000, and the agent's steps as it works.
  - The instructions: what the agent reads, read only.
- `e2e/`: Playwright tests on their own servers, a backend on port 8001 with `e2e/e2e.db` seeded fresh each run and Vite on port 5174, so they never touch the dev data.

## Run it

- `npm run dev` starts the backend on port 8000 and the dashboard on http://localhost:5173
- `uv run -m agent` works every claim not yet decided, and `uv run -m agent CLM-1001` works one claim. The backend must be running.
- `uv run -m backend.seed` resets the queue
- `npm run check` runs every check

## Last run

The whole queue on `openai/gpt-6-luna`, at about 13 seconds a claim: every claim ended decided or waiting for sign-off, and no payment over $1,000 was made without a sign-off. The decisions haven't been scored against the handlers' decisions in `data/evals/`.
