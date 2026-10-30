# My claims pilot: Rajasekhara (Shekar) Lankela

I planned the claims pilot with Claude Code, reviewed the plan myself, then had it build all six phases. This write-up covers what I did, what I learned, and where the code is.

## My repo

https://github.com/rlankelahotmail/undercover/tree/week1day3-RajasekharaLankela

My plan is in this folder as `PLAN.md`.

## What I did

1. **Planned first.** I asked Claude Code to "plan the pilot". It wrote `docs/PLAN.md`: six phases, each with checkbox success criteria, and no code.
2. **Reviewed the plan before building.** I checked it against `SPEC.md`, `PROCESS.md` and the `data/` files (counts, ids, handlers). I found three problems and had them fixed before the build (see takeaways).
3. **Built all six phases** with Claude Code (planning on Opus, building on Sonnet), one commit per phase:
   - Phase 1: backend data and read API (FastAPI, SQLite, seeded from `data/`)
   - Phase 2: decisions, payments and sign-off, with the $1,000 payment block
   - Phase 3: the UnderCover Agent (LangChain `create_agent` on OpenRouter, five tools)
   - Phase 4: dashboard frame and the queue (React, Vite, brand colours, light and dark mode)
   - Phase 5: the claim page, the agent's live steps, sign-off, and the instructions page
   - Phase 6: the whole queue run end to end with the real model
4. **Ran the real model on the whole queue.** On `openai/gpt-6-luna` it took about 13 seconds per claim. Every claim ended decided or waiting for sign-off, and no payment over $1,000 was made without a sign-off.

`npm run check` result: [PASTE THE RESULT FROM YOUR LAST RUN HERE, e.g. "ruff, pyright, pytest, ESLint, Prettier, tsc, vitest and Playwright all pass, coverage above 80%"]

## What I built

- **Backend** is the only door to the data. The agent and the dashboard both go through its API, so the agent can't read `data/evals/` or the claims manual.
- **Payment rule in one function.** It pays only an approved claim, only the approved amount, only once, and over $1,000 only after a handler signs off. The `payments` table also uses the claim id as its key, so the database itself refuses a second payment.
- **Agent** has five tools (`get_claim`, `get_policy`, `get_claim_history`, `record_decision`, `pay_claim`). Its instructions come from the backend, so the dashboard shows exactly what it reads. Each tool call, result and message is posted as a step, and the dashboard shows them live.
- **Dashboard** shows the queue with counts in each state, each claim in full with the agent's decision and reasons, a handler sign-off button, and the instructions read-only.

## My takeaways

- **Review the plan before saying go.** Reading the plan against the spec caught three things. The agent's queue filter would have tried to restart claims already waiting for sign-off. The "handler not allowed" test (403) needed a handler the seed data doesn't have, because all three real handlers can approve. And a cost estimate in the plan was a guess, so it came out.
- **Put the hard rule in the backend, not in the prompt.** The $1,000 block holds even if the agent tries to pay, because the code and the database enforce it. The agent's job is only to make a decision.
- **Tests never call a model.** A stub model with scripted tool calls proved the rules, including an agent that tries to pay too early. The real model was only used for the live checks.
- **Checkbox success criteria make the work checkable.** Claude Code had to prove each one with a test, a command or a screenshot, so I could tell what was really done.
- **A plain-English copy of the plan helped me review.** Printing it and ticking the boxes made the review easier than reading the markdown.
- **Not done yet:** I haven't scored the agent's decisions against the handlers' decisions in `data/evals/`. That is the next step for judging how accurate it is.
