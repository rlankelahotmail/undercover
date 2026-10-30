# Plan: the claims pilot

The pilot from `docs/SPEC.md`: a backend that holds the claims queue, the UnderCover Agent that works the queue through the backend's API, and a dashboard where the handlers see the queue, each claim in full, the agent's steps as it works and its instructions.

## How it fits together

```
data/ --seed--> backend (FastAPI + SQLite) <--HTTP-- agent (create_agent on OpenRouter)
                        ^
                        |  HTTP, refreshed every 2 seconds
                    dashboard (React + Vite)
```

The main choices, and why:

1. **The backend is the only door to the data.** `uv run -m backend.seed` loads `data/` into SQLite. It reads only the files it needs and never `data/evals/`, `data/security/` or the claims manual. The agent and the dashboard both go through the API, so the agent can't read the answer key, and the payment rule can't be bypassed.
2. **A claim has four states**, the ones the spec names: `waiting`, `in_progress`, `waiting_for_sign_off` and `decided`. The seed turns the data's `open` into `waiting`. The agent's run starts a claim. Its decision moves the claim to `decided`, or to `waiting_for_sign_off` when it approves more than $1,000. A sign-off moves it to `decided`. A refer is a decision, so a referred claim is `decided` with the outcome `refer`.
3. **The payment rule lives in one backend function.** `pay_claim` pays only an approved claim, only the approved amount, only once, and over $1,000 only after a sign-off. A handler's sign-off goes through the same function, which then releases the payment. That's the only way a payment gets made, so the agent can't get around the block, whatever it tries.
4. **The agent is `create_agent` with five tools.** Each tool wraps one API operation. Its system prompt comes from `GET /api/instructions`, which is the instructions in `backend/instructions.md` followed by the policy wording. `data/README.md` says the wording is short enough for a prompt, and the dashboard can then show exactly what the agent reads. `run(claim_id, thread_id)` streams the agent and posts each step to the backend as it happens. The dashboard polls for steps, which is how the team watches the agent work, live.
5. **The dashboard adds no packages.** It uses hash routes (`#/`, `#/claims/CLM-1001`, `#/instructions`), one small hook that fetches and refreshes every 2 seconds, and one stylesheet with the brand's colors in light and dark mode.
6. **The end-to-end tests run on their own servers and database.** That's a backend on port 8001 with `e2e/e2e.db`, seeded fresh on every run, and Vite on port 5174. The tests can then sign off and pay claims and still pass on the next run, without touching the data you use in `npm run dev`. Tests never call a model, so the e2e tests play the agent's part through the API.
7. **Customer data is kept to what's needed.** The API returns a customer's name, customer-since date and claim history. It doesn't return the email, phone, address or date of birth, because neither the agent nor the handlers need them for the pilot.

## The API

Every operation has an `operation_id`, a one-line docstring and only required inputs. Paying is its own operation and takes the amount.

| Operation | Method and path | What it does |
|---|---|---|
| `health` | `GET /api/health` | Checks that the backend is running (already built) |
| `list_claims` | `GET /api/claims` | The queue: each claim's id, customer name, type, summary, submitted date, amount claimed, status, outcome, payout and whether it's paid |
| `get_claim` | `GET /api/claims/{claim_id}` | One claim in full: story, items, documents, status, and its decision, sign-off and payment |
| `get_policy` | `GET /api/policies/{policy_id}` | A policy: plan, add-ons, purchase date, trip and travelers |
| `get_claim_history` | `GET /api/customers/{customer_id}/history` | A customer's name, customer-since date and earlier claims |
| `list_handlers` | `GET /api/handlers` | The claims handlers |
| `get_instructions` | `GET /api/instructions` | The agent's instructions, with the policy wording |
| `start_claim` | `POST /api/claims/{claim_id}/start` | Marks a claim in progress and clears the steps of an earlier, unfinished run |
| `add_step` | `POST /api/claims/{claim_id}/steps` | Records one step of the agent's work: thread id, kind (`call`, `result` or `message`), name and content |
| `list_steps` | `GET /api/claims/{claim_id}/steps` | The agent's steps on a claim, in order |
| `record_decision` | `POST /api/claims/{claim_id}/decision` | Records approve, decline or refer, with the payout, a reason and the policy section |
| `pay_claim` | `POST /api/claims/{claim_id}/payment` | Pays an approved claim the given amount, if the payment rule allows it |
| `sign_off` | `POST /api/claims/{claim_id}/sign-off` | A handler signs off a payout over $1,000, which releases the payment |

The rules the backend enforces, each with a test:

- `start_claim`: only on a `waiting` or `in_progress` claim, so a decided claim can't be worked again. A rerun of an unfinished claim starts clean. `uv run -m backend.seed` resets everything.
- `record_decision`: only on an `in_progress` claim, so there's one decision per claim. An approve needs a payout above $0. A decline or a refer needs a payout of $0.
- `pay_claim` checks that the claim is approved, that the amount equals the approved payout, and that it isn't paid yet. A payout over the `payout_approval_limit` in `data/company.json` ($1,000.00) also needs a sign-off. A payout of exactly $1,000.00 doesn't.
- `sign_off`: only on a claim `waiting_for_sign_off`, and only by a handler whose `can_approve_over_limit` is true.
- A refusal is a 409, or a 403 for a handler who isn't allowed, with a short message that says why. Unknown ids are a 404.

## The data

SQLite at `backend/undercover.db`, or the path in `UNDERCOVER_DB` (the tests and e2e use their own). The backend creates and seeds the file on startup if it doesn't exist, so a fresh clone works with `npm run dev`.

- `claims`: `claim_id`, `policy_id`, `customer_id`, `status`, and the claim's record from `claims.json` as JSON
- `policies`, `customers`, `handlers`: the id and the record as JSON
- `settings`: the company settings and the agent's instructions
- `decisions`: `claim_id`, `outcome`, `payout`, `reason`, `policy_section`, `decided_at`
- `sign_offs`: `claim_id`, `handler_id`, `signed_off_at`
- `payments`: `claim_id` (the primary key, so the database itself allows only one payment per claim), `amount`, `paid_at`
- `steps`: `id`, `claim_id`, `thread_id`, `kind`, `name`, `content`, `created_at`

Records are stored whole as JSON because the claims' items and documents are nested and nothing queries them field by field. The fields we filter and join on, the ids and the status, are real columns.

## The agent

- **Tools:** `get_claim`, `get_policy`, `get_claim_history`, `record_decision` and `pay_claim`, each one call to the API. When the backend refuses, the tool returns the refusal's message as its result, so the agent sees why, for example that a payment needs a sign-off.
- **Instructions** (`backend/instructions.md`): read the claim, its policy and the customer's claim history. Check the claim against the policy wording: the benefit and its conditions, the trip dates, the purchase date, the 90-day filing window, the exclusions and the documents. Approve, decline or refer. Refer when the claim needs a person's judgment or more information, such as a missing document. Work out the payout as section 10 of the wording sets out. Record the decision with a reason in two or three sentences and the relevant section. Pay an approved claim of $1,000 or less. Leave a larger one for a handler's sign-off. The instructions don't use the claims manual, which is out of scope for the pilot.
- **`run(claim_id, thread_id)`** fetches the instructions, starts the claim, streams the agent, posts each tool call, tool result and message as a step, and returns the final reply. It uses the model in `MODEL_NAME`, or `openai/gpt-6-luna` at low reasoning effort, as the skeleton does now.
- **`uv run -m agent`** works every claim that isn't decided yet, in queue order, each with a new thread id, and prints one line per claim with its outcome, payout and status. `uv run -m agent CLM-1001` works one claim. Both need the backend running (`npm run dev`).

## How I'll check the criteria

API checks run against the dev backend at `http://127.0.0.1:8000` from `npm run dev` (in PowerShell use `curl.exe` or `Invoke-RestMethod`, as `curl` there is a different command). Browser checks use the Playwright MCP server on the dashboard at `http://localhost:5173`. After a live agent run, `uv run -m backend.seed` resets the queue.

## Phase 1: The backend's data and read API

**Builds:** `backend/db.py` (the schema, a connection per request, the database path), `backend/seed.py` (`uv run -m backend.seed` recreates the database from `data/`), startup seeding when the file is missing, and the read operations `list_claims`, `get_claim`, `get_policy`, `get_claim_history` and `list_handlers`. Tests use a fresh database in a temporary folder.

**Why first:** everything else reads from it, and it settles the shapes the agent and the dashboard work with.

- [x] `uv run -m backend.seed` prints `Seeded 25 claims, 50 policies, 49 customers and 3 handlers` and creates `backend/undercover.db`
- [x] `GET /api/claims` returns 25 claims, CLM-1001 to CLM-1025, all `waiting`, each with the customer's name, the type, summary, submitted date and amount claimed
- [x] `GET /api/claims/CLM-1001` returns the full claim: the story, 3 items, 4 documents, status `waiting` and no decision
- [x] `GET /api/policies/POL-2001` returns the Premium plan with no add-ons, the Rome trip from 2026-06-10 to 2026-06-18 and a trip cost of 3100.0
- [x] `GET /api/customers/CUS-3001/history` returns Maya Patel with one earlier claim, CLM-0412, and no email, phone, address or date of birth
- [x] `GET /api/handlers` returns HND-01, HND-02 and HND-03
- [x] An unknown claim, policy or customer id returns a 404 with a short message
- [x] Starting the backend with no database file creates and seeds it
- [x] A test checks that every operation in `app.openapi()` has an `operation_id`, a one-line docstring and only required inputs
- [x] A search for `evals`, `security` and `claims_manual` in `backend/` finds nothing
- [x] `npm run check:python` passes, with coverage at 80% or more

## Phase 2: Decisions, payments and sign-off

**Builds:** the write operations `start_claim`, `add_step`, `list_steps`, `record_decision`, `pay_claim` and `sign_off`, with the state rules and the payment rule above. Request bodies are Pydantic models with no optional fields. `list_claims` and `get_claim` now include the decision, sign-off and payment.

**Why now:** the payment block is the spec's hardest rule, so it's built and tested in the backend before any agent exists to try to get around it.

- [ ] `POST /api/claims/CLM-1001/start` moves the claim to `in_progress`. Starting a decided claim returns a 409
- [ ] `POST /api/claims/CLM-1001/steps` adds a step, and `GET /api/claims/CLM-1001/steps` returns the steps in order with their thread id, kind, name and content. Starting the claim again clears them
- [ ] Approving CLM-1001 for $420.00 moves it to `decided`, and the claim shows the outcome, payout, reason and policy section
- [ ] A second decision, or a decision on a claim that isn't in progress, returns a 409. A decline or refer with a payout above $0, or an approve with $0, returns a 422
- [ ] Paying CLM-1001 $420.00 records the payment. Paying it again, paying an amount other than the approved payout, or paying a declined or referred claim each returns a 409, and no payment is recorded
- [ ] Approving CLM-1003 for $1,250.00 moves it to `waiting_for_sign_off`. Paying it returns a 409 whose message says it needs a handler's sign-off, and no payment is recorded
- [ ] An approve of exactly $1,000.00 moves to `decided` and can be paid without a sign-off
- [ ] HND-01 signing off CLM-1003 records the sign-off and a payment of $1,250.00, and moves the claim to `decided`. Signing off a claim that isn't waiting for sign-off returns a 409, an unknown handler a 404, and a handler without `can_approve_over_limit` a 403.The test adds its own handler with can_approve_over_limit false to its temporary database, since the seed handlers all have it.
- [ ] `GET /api/claims` shows each claim's outcome, payout and whether it's paid
- [ ] The OpenAPI test passes for the new operations
- [ ] `npm run check:python` passes, with coverage at 80% or more

## Phase 3: The UnderCover Agent

**Builds:** `backend/instructions.md`, stored by the seed with the policy wording after it, and served by `get_instructions`. In `agent/main.py`, the five tools, the system prompt from the API, and `run(claim_id, thread_id)` streaming the agent and posting its steps. `agent/__main__.py` for `uv run -m agent`. Tests use a stub model with scripted tool calls against the real backend app on a temporary database.

**Why now:** the backend's operations and rules are in place, so the agent is a thin layer of tools over them, and the tests can show the backend holding the line against a misbehaving agent.

- [ ] `GET /api/instructions` returns the instructions followed by the policy wording, version 2026.1, with nothing from the claims manual
- [ ] Stub test: a scripted run on CLM-1001 calls `get_claim`, `get_policy`, `get_claim_history`, `record_decision` (approve, $420.00) and `pay_claim`. The claim ends `decided` and paid, its steps are recorded in order under the run's thread id, and `run` returns the final reply
- [ ] Stub test: a scripted run that approves CLM-1003 for $1,250.00 and then calls `pay_claim` gets the backend's refusal as the tool's result. The claim ends `waiting_for_sign_off` with no payment
- [ ] Stub test: the system prompt the agent gets is the text from `GET /api/instructions`
- [ ] Stub test: `uv run -m agent` works only claims that aren't decided, each with its own thread id, and given a claim id it works just that claim
- [ ] `agent/` reads nothing from disk. Outside its tests, a search finds no `open(`, `Path` or `data/` in `agent/`
- [ ] Live, with `npm run dev` running: `uv run -m agent CLM-1001` on the real model prints one line with the outcome, payout and status. `GET /api/claims/CLM-1001` shows a decision with a reason of two or three sentences and a policy section. `GET /api/claims/CLM-1001/steps` shows each tool call and its result
- [ ] Live: after `uv run -m agent CLM-1003`, whatever the agent decided, there's no payment over $1,000.00 without a sign-off
- [ ] `npm run check:python` passes, with coverage at 80% or more

## Phase 4: The dashboard's frame and the queue

**Builds:** the brand in `dashboard/index.html` (the Google Fonts) and `dashboard/src/styles.css` (the colors, surfaces, and light and dark mode). The header with the UnderCover name and navigation to Queue and Instructions. Hash routing. `api.ts` with the response types, the refreshing fetch hook and a `post` helper. `format.ts` for money ($1,250.00), dates and labels. The queue page: four tiles with the count in each state, then a table of claims with the claim id, customer, type, summary, submitted date, amount claimed, status, and outcome with payout, each row linking to its claim. It refreshes every 2 seconds, and if the backend doesn't answer it says so. The e2e setup moves to its own backend (port 8001, `e2e/e2e.db` seeded fresh) and its own Vite (port 5174), and `vite.config.ts` reads the backend's address from `BACKEND_URL`. The skeleton's health page and its e2e test give way to the queue.

**Brand colors for states and outcomes:** Waiting in Cerulean, In progress in Coral, Waiting for sign-off in Marigold, Decided in Sea Green. Approve in Sea Green, Refer in Marigold, Decline in Coral. Ids, money and dates are in JetBrains Mono.

**Why now:** the API is complete, so the dashboard is built against real responses, and the frame and the queue come before the pages that hang off them.

- [ ] Vitest: the queue renders claims from a stubbed fetch with the right status labels, the counts in each tile, money as `$1,150.00`, and each row linking to `#/claims/<id>`
- [ ] Vitest: the queue shows a message when the backend doesn't answer
- [ ] E2E: the queue shows 25 claims and the Waiting tile shows 25
- [ ] `npm run e2e` passes twice in a row, and the dev database at `backend/undercover.db` is unchanged by it
- [ ] Browser, at 1440 by 900: the queue uses Instrument Sans with ids and money in JetBrains Mono, the page background is `#F0F4F5`, the panels are white and rounded with no outline, and there are no one-edge borders or lines across the top. Screenshot taken
- [ ] Browser, with dark mode emulated: the page background is `#04232E`, the panels are black, and the text is Sea Mist. Screenshot taken
- [ ] Browser, with `npm run dev` running: after `uv run -m agent CLM-1001`, the tiles and the CLM-1001 row change within a few seconds, without a reload
- [ ] `npm run check:ts` passes, with coverage at 80% or more

## Phase 5: The claim page and the instructions page

**Builds:** the claim page, with the claim in full (summary, story, incident date and place, items with amounts, documents with their text), the policy (plan, add-ons, purchase date, trip dates, trip cost and travelers) and the customer's claim history. The decision panel shows the outcome, payout, reason, policy section and payment. While a claim is waiting for sign-off it adds a handler picker and a "Sign off and pay $1,250.00" button. The steps panel shows the agent's calls, results and messages in order, each result folded away until opened, and it refreshes while the agent works. The instructions page shows the agent's instructions and the policy wording as read-only text.

**Why now:** these are the remaining screens in "What the team needs to see", built on the frame from Phase 4.

- [ ] Vitest: the claim page renders the story, items, documents, policy, history and decision from stubbed responses
- [ ] Vitest: the sign-off control appears only while a claim is waiting for sign-off, and it posts the chosen handler to `/api/claims/<id>/sign-off`
- [ ] Vitest: steps render in order, and each result is folded until opened
- [ ] Vitest: the instructions page renders the text and has no inputs or buttons
- [ ] E2E: clicking CLM-1001 in the queue opens its page, which shows the story, the 3 items, the 4 documents, the Premium policy and the earlier claim CLM-0412
- [ ] E2E, playing the agent through the API: start CLM-1003 and add three steps. The page shows In progress and the steps in order. Record an approve of $1,250.00, and the page shows Waiting for sign-off with the reason and section. Choose Dana Whitfield and sign off, and the page shows Decided, paid $1,250.00, signed off by Dana Whitfield
- [ ] E2E: the instructions page shows the instructions and the policy wording, with no inputs or buttons
- [ ] Browser: the claim page and the instructions page in light and dark mode follow the brand. Screenshots taken
- [ ] `npm run check:ts` passes, with coverage at 80% or more

## Phase 6: The pilot end to end

**Builds:** no new features. A fresh queue and a run of the agent on all 25 claims with the real model, watched in the browser, with fixes to the instructions or the code for whatever goes wrong. Then `docs/STATUS.md` finished with what's built and how to run it.

**Why last:** it's the first time the whole system runs together on the real queue, so it finds the problems the stubbed tests can't. On `openai/gpt-6-luna` .

- [ ] After `uv run -m backend.seed`, with `npm run dev` running, `uv run -m agent` works all 25 claims and prints one line for each
- [ ] Afterward, `GET /api/claims` shows every claim `decided` or `waiting_for_sign_off`, with none `waiting` or `in_progress`
- [ ] Every approve has a payout above $0, every decline and refer $0, and every decision has a reason of two or three sentences and a policy section
- [ ] No claim has a payment over $1,000.00 without a sign-off, and every approved claim of $1,000.00 or less is paid
- [ ] Browser: while the queue runs, the page of the claim being worked shows its steps arriving without a reload. Screenshot taken
- [ ] Browser: signing off a claim that's waiting for sign-off moves it to Decided and paid, on its page and in the queue
- [ ] `docs/STATUS.md` says what's built and how to run it: `npm run dev`, `uv run -m agent`, `uv run -m backend.seed` and `npm run check`
- [ ] `npm run check` passes: ruff, pyright, pytest with coverage at 80% or more, ESLint, Prettier, tsc, vitest with coverage at 80% or more, and Playwright

## Not in this plan

- Scoring the agent against `data/evals/`. The spec keeps the handlers' decisions as the team's check on the agent's work. This build keeps them out of the agent's reach and doesn't open them.
- The claims manual, sign-in, real payments and messages to customers, which the spec leaves out for now.
- `data/knowledge.json` and `data/policy_wording_short.md`, which the spec doesn't mention.
- Running the agent from the dashboard. The spec asks for the team to see the agent's work, so the agent runs from the command line.
- A handler changing the agent's decision, or refusing a sign-off. The spec asks only for the sign-off.
