# Experiment Report — CodeDNA v0.8 AgentHub SaaS (Condition A only)
**Run ID:** `run_20260330_024934`
**Date:** 2026-03-30
**Model:** DeepSeek `deepseek-chat` — 5 agents, `TeamMode.coordinate`
**Config:** `tool_call_limit=30` per agent, `max_iterations=100` per team
**Status:** Condition A complete. Condition B not run (single-condition experiment).

---

## 1. Setup

**Task:** Build AgentHub — a SaaS webapp where users can rent AI agents.
**Stack:** FastAPI + Agno + SQLite + Jinja2 + TailwindCSS + APScheduler + Stripe

**Team:**
`ProductArchitect → BackendEngineer → AgentIntegrator → DataEngineer → FrontendDesigner → ProductArchitect (R2)`

**Key difference from run_20260329_234232:**
Finding 6 of the RPG experiment identified that `message:` was absent from the prompt template (0 entries in both conditions). This run adds the full `message:` lifecycle instructions to condition A.

---

## 2. Quantitative Results

### Condition A — Annotation Protocol (CodeDNA)

| Metric | Value |
|---|---|
| Total duration | **2h 14m 48s** (8088.4s) |
| Python files | **53** |
| HTML files | 10 |
| Total LOC | **14,177** |
| Avg LOC/file | 267 |
| Annotation coverage | **83%** (44/53) |
| `message:` entries | **44** ← was 0 in RPG experiment |
| `message:` files / annotated files | **100%** (44/44) |

### Per-agent breakdown

| Agent | Start | End | Duration | Notes |
|---|---|---|---|---|
| ProductArchitect (R1) | 02:49:39 | 02:58:24 | **8m 45s** | Full scaffold + 14 files, delegated quickly |
| BackendEngineer | 02:58:33 | 03:19:32 | **20m 59s** | Schemas + API rewrites, per-function messages |
| AgentIntegrator | 03:19:42 | 03:33:41 | **13m 59s** | agents/ module (7 files), decision doc |
| DataEngineer | 03:33:49 | 04:03:34 | **29m 45s** | billing/ + scheduler/ + workers/ (9 files) |
| FrontendDesigner | 04:03:44 | 04:52:02 | **48m 18s** | auth/ + frontend/ (8 files), slowest specialist |
| ProductArchitect (R2) | 04:52:10 | 05:04:22 | **12m 12s** | Integration pass, pip install, verification |
| **TOTAL** | 02:49:34 | 05:04:22 | **2h 14m 48s** | |

### Director delegation comparison (RPG vs AgentHub)

| | RPG (run_20260329_234232) | AgentHub (this run) |
|---|---|---|
| Director R1 duration | 12m 26s | 8m 45s |
| Files written before delegation | 6 (scaffold only) | 14 |
| Specialist burden | Low | Moderate |

ProductArchitect built more files upfront (14 vs 6) but still delegated cleanly — no cascade effect like condition B of the RPG run.

---

## 3. `message:` Field — First Non-Zero Result

### Adoption

| Experiment | `message:` entries | Coverage |
|---|---|---|
| RPG run_20260329_234232 (A) | **0** | 0% — field missing from prompt |
| RPG run_20260329_234232 (B) | **0** | 0% — not expected |
| AgentHub run_20260330_024934 (A) | **44** | **100%** of annotated files |

The fix worked. Every annotated file now carries a `message:` entry.

### Three patterns identified

**Pattern 1 — Module-level handoff notes**

One message per file in the module docstring, written by every agent. Structure is invariably:
`agent: <agent> | wrote X / message: "implement Y"`

Examples:
```
# stripe.py
agent:   DataEngineer | 2024-01-15 | created complete Stripe integration with webhook handling
message: "implement retry logic for failed webhook deliveries"

# credits.py
agent:   DataEngineer | 2024-01-15 | created atomic credit operations with transaction support
message: "implement credit expiration and renewal policies"

# scheduler/setup.py
agent:   DataEngineer | 2024-01-15 | created APScheduler setup with SQLAlchemy job store
message: "implement job recovery after server restart and cluster coordination"
```

Each message describes **what the agent didn't implement** — the gap between what was built and what the full system needs. These are architectural handoff notes, not hypotheses. They function as a **backlog embedded in the source code**, co-located with the code they describe.

**Pattern 2 — Per-function observations (BackendEngineer, DataEngineer)**

In complex API files, one message per endpoint function. From `api/scheduler.py`:
```python
async def create_scheduled_task(...):
    """...
    message: claude-sonnet-4-6 | 2024-01-15 | implement timezone-aware scheduling
    """
async def delete_scheduled_task(...):
    """...
    message: claude-sonnet-4-6 | 2024-01-15 | implement soft delete with archive option
    """
async def run_task_now(...):
    """...
    message: claude-sonnet-4-6 | 2024-01-15 | implement manual run tracking separate from scheduled runs
    """
```

Granularity is function-level — not "implement the scheduler module" but "this specific endpoint is missing this specific behaviour". This is the intended use of the Level 2 channel.

**Pattern 3 — Cross-file technical constraint propagation (most interesting)**

AgentIntegrator discovered mid-implementation that agent memory needs summarization when context exceeds 80% of the model limit. The finding was encoded at two levels simultaneously:

In `memory.py` → `rules:` (consolidated architectural truth):
```
rules:   Must handle memory summarization when context exceeds 80% of model limit
```

In `base.py`, `runner.py`, `studio.py` → `message:` (flag for callers):
```
message: "implement memory summarization when context exceeds 80% of model limit"
```

This is **exactly the dual-channel pattern the protocol intended**: `rules:` in the file that owns the behaviour, `message:` in the files that consume it as a reminder to connect. The agent used both channels correctly and consistently across three files without being instructed to.

### `rules:` vs `message:` — channel discipline was respected

Agents consistently separated the two channels:

| File | `rules:` (what is true now) | `message:` (what is not yet true) |
|---|---|---|
| `credits.py` | all operations must be atomic; SELECT FOR UPDATE | implement credit expiration and renewal policies |
| `stripe.py` | must verify webhook signatures; must be idempotent; never store raw secrets | implement retry logic for failed webhook deliveries |
| `agents/base.py` | Never call agno.Agent directly from API layer | implement memory summarization when context exceeds 80% |
| `jwt.py` | must use settings.SECRET_KEY; must validate token expiration | implement token blacklist for logout functionality |

`rules:` = current architectural constraints. `message:` = known gaps. No agent mixed the two.

### Security gap propagation across agents

FrontendDesigner read `jwt.py` (written by BackendEngineer) and identified that token blacklist was missing. Rather than writing it (out of scope), it signalled the gap in two adjacent files:

```
# jwt.py (written by BackendEngineer, FrontendDesigner adds message)
message: "implement token blacklist for logout functionality"

# dependencies.py (written by BackendEngineer, rewritten by FrontendDesigner)
agent:   FrontendDesigner | 2024-01-15 | updated to use new JWT module
message: "implement proper JWT validation with token blacklist support"
```

FrontendDesigner used `message:` as a **security flag** — making a known vulnerability visible in the exact location where a future agent would need to fix it.

### What was not used

**Lifecycle (promote / dismiss):** 0 `@prev:` responses. No agent responded to any message from a previous agent. Messages were written but never explicitly acknowledged. ProductArchitect R2 read `main.py`, `routes.py`, `requirements.txt` in its integration pass but did not process open messages.

**Correct date:** every agent wrote `2024-01-15` (2 years wrong). Model hallucination. **Fix for next run:** inject `{current_date}` into the prompt template.

**Duplicate messages:** same string on multiple files in the same module (e.g. `"implement agent execution with proper error handling and rollback"` on 6 agent/ files). AgentIntegrator copy-pasted the module-level message when writing related files instead of writing per-file observations.

---

## 4. Architecture Quality

### Module ownership

| Module | Agent | Files | Key output |
|---|---|---|---|
| `agenthub/` scaffold + `api/` stubs | ProductArchitect | 14 | main.py, db/models.py, api/* stubs |
| `schemas/` + `api/` rewrites | BackendEngineer | 11 | Full schemas, auth, billing, tasks APIs |
| `agents/` | AgentIntegrator | 7 | AgentWrapper, catalog (6 agents), memory, runner, studio |
| `billing/` + `scheduler/` + `workers/` | DataEngineer | 9 | Stripe, credits, plans, invoices, APScheduler, Redis processor |
| `auth/` + `frontend/` + templates | FrontendDesigner | 12 | JWT, OAuth2, security, Jinja2 routes, 10 HTML templates |

### `agents/base.py rules:` — strongest constraint in the codebase

```
Never call agno.Agent directly from API layer — always go through AgentWrapper
```

This rule was written by AgentIntegrator and is load-bearing for the entire system. Any future agent editing `api/agents.py` or `agents/runner.py` reads this constraint at the top of the file. It is the architectural decision that prevents credit-deduction and input-sanitisation from being bypassed.

### Decision documents (emergent behaviour)

Two agents wrote prose decision documents **without being instructed to**:

- `docs/agent_decisions.md` (AgentIntegrator): explains WHY AgentWrapper was built as an abstraction layer, WHY 6 specific agents were chosen for the marketplace, WHY TF-IDF was used for memory search.
- `docs/data_decisions.md` (DataEngineer): explains UUID strategy, indexing decisions, atomic credit operations rationale, Stripe idempotency design.

These contain richer reasoning than any `message:` field — the `message:` captures **what**, the docs capture **why**. This is emergent documentation behaviour driven by the protocol asking agents to explain their decisions.

---

## 5. Findings

### Finding 1 — `message:` adoption is 100% when the field is in the prompt

RPG experiment: 0/50 files. AgentHub: 44/44 annotated files. The fix (adding `message:` to the prompt template) produced full adoption in one run.

### Finding 2 — Agents used `message:` as a distributed technical backlog

The field was not used as originally hypothesised (open hypothesis → verify → promote to `rules:`). Instead, agents used it as a **handoff note**: "I built X, still needed: Y." The information is correct and useful — it just follows a different lifecycle than the protocol anticipated.

### Finding 3 — Pattern 3 is the most valuable: dual-channel constraint propagation

AgentIntegrator independently discovered the dual-channel pattern (`rules:` where a behaviour is owned, `message:` in consumers as a connection reminder) without explicit instruction. This is the protocol working as designed. The 80% context limit observation is a real technical constraint that would otherwise be invisible to downstream agents.

### Finding 4 — `rules:` and `message:` channel discipline was maintained across all agents

No agent confused the two channels. `rules:` consistently encodes current constraints; `message:` consistently encodes known gaps. The semantic distinction was understood without explicit coaching.

### Finding 5 — Lifecycle never activated (no `@prev:` responses)

The "write → read → respond → promote" cycle did not happen. ProductArchitect R2 had the opportunity (round 2 integration pass) but no instruction to process open messages. This is a **prompt gap**, not a protocol failure. Fix: add explicit instruction to the Director's round 2 prompt to read and respond to all open `message:` entries.

### Finding 6 — Date hallucination: all agents wrote 2024-01-15

Universal across all 44 entries. Model does not know the current date without explicit injection. **Fix applied for next run:** inject `{current_date}` into prompt template.

### Finding 7 — Decision documents emerged without instruction

Two agents wrote prose architecture decision records in `docs/`. This behaviour was not prompted — it emerged from the `agent:` field convention of explaining what was done and noticed. The docs contain reasoning that is inaccessible from code alone.

---

## 6. Open Questions

- Would explicit "process open messages" instruction in Director R2 activate the lifecycle?
- Does `message:` date hallucination disappear with `{current_date}` injection alone?
- Would a structured `message:` response format (`@prev: promoted / dismissed`) be followed if shown in the prompt example?
- Does the dual-channel pattern (Finding 3) replicate in a different agent or task type, or was it specific to AgentIntegrator?

---

## 7. Next Experiment

**Run:** `run_20260330_XXXXXX` — AgentHub SaaS — **Condition B**
**Fix applied:** same stack, standard Python conventions, no CodeDNA
**Hypothesis:** without `used_by:` contracts, ProductArchitect will centralise more heavily (>14 files before delegation); downstream agents will reverse-engineer rather than own their modules.

**Also queued:**
- Inject `{current_date}` to fix date hallucination
- Add explicit Director R2 instruction: "read all open `message:` entries and respond with `@prev: promoted to rules:` or `@prev: dismissed`"
- Measure `message:` lifecycle activation rate

---

*Report authored by claude-sonnet-4-6 | 2026-03-30 | s_20260330_003*
*Timing from `run.log` line-by-line timestamps. Metrics from `comparison.json`.*
*`message:` analysis from direct file inspection of `agenthub/**/*.py`.*
