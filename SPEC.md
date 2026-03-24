# CodeDNA: An In-Source Communication Protocol for AI Coding Agents — Specification

**Version:** 0.8
**Status:** Draft
**Language:** Python (canonical), TypeScript, JavaScript, Go, Rust, Java, Ruby, C/C++

---

## 1. Overview

CodeDNA is an **inter-agent communication protocol** implemented as a source-file annotation format that makes codebases AI-navigable. It provides information that **cannot be inferred from reading the code alone** — most critically, the *reverse dependency graph* (`used_by:`) and *domain rules* (`rules:`).

The protocol follows a **zoom metaphor** — like how the human eye works:

**Level 0 — Project Manifest (`.codedna`):** A single file at the repo root describing the project structure, package purposes, and inter-package dependencies. The agent reads this first — the view from far away.

**Level 1 — Module Header (Macro-Context):** A docstring at the top of every file encoding the file's public API (`exports:`), reverse dependencies (`used_by:`), and hard constraints (`rules:`). The view from close up.

**Level 2 — Function-Level Rules (Micro-Context):** `Rules:` docstrings on critical functions, written organically by agents as they discover domain constraints. The view from very close.

**Level 3 — Semantic Naming (Cognitive Compression):** Variable naming conventions that encode type, origin, and shape directly into the identifier.

The design principle: **only annotate what the code doesn't already tell you.** Import statements already declare dependencies — duplicating them in annotations wastes tokens. But *who depends on you* (`used_by:`) is hard to determine without reading many files in the project. That is where CodeDNA adds value.

### 1.1 The Inter-Agent Communication Model

CodeDNA is an annotation standard by *form*, but an **inter-agent communication protocol** by *function*. The file is the channel. The writing agent encodes architectural context as structured metadata; the reading agent decodes it at any point in the file.

This is different in nature from rule files (CLAUDE.md, .cursorrules, AGENTS.md), which are **human→agent** communication. CodeDNA is **agent→agent** communication, co-located with the code it describes.

Three examples illustrate the model:

**Example A — The Writing Agent Warns the Reading Agent**

Agent A generates `analytics/revenue.py`. It knows (from its own generation context) that `get_invoices_for_period()` returns ALL tenants with no suspension filter. Agent A writes:

```python
"""analytics/revenue.py — Monthly revenue aggregation.

exports: monthly_revenue(year, month) → dict | annual_summary(year) → list[dict]
used_by: api/reports.py → revenue_route | workers/report_generator.py → generate
rules:   get_invoices_for_period() returns ALL tenants, NO suspended filter →
         callers MUST call is_suspended() BEFORE aggregating
"""
```

Two weeks later, Agent B (a different LLM, different session, different prompt) is asked to add a quarterly report. Agent B reads `revenue.py`, sees `rules:`, and immediately knows that any code calling `get_invoices_for_period()` must filter suspended tenants — without reading `payments/models.py`, without RAG, without external context. The file was the channel. Agent A transmitted. Agent B received.

**Example B — The Reverse Dependency Graph as a Navigation Map**

Agent C is asked to fix a bug in `format_currency()`. Without CodeDNA, it must grep all 500 files to find who calls it (8–12 tool calls). With CodeDNA, Agent C reads `utils/format.py` and sees:

```python
exports: format_currency(n) → str | format_date(d) → str  
used_by: views/dashboard.py → render | api/reports.py → revenue_route
```

In 1 read, Agent C knows which 2 files call `format_currency()` and may be affected by the change. Total: 3 tool calls instead of ~12. The `used_by` field is a navigation aid — it answers the question *"who depends on me?"* which is hard to determine from the code of this file alone.

**Example C — Sliding Window as a Self-Healing Channel**

Agent D extracts only lines 50–80 of a 300-line file (sliding window mode) and never sees the Level 1 header. Without CodeDNA, it sees raw code with no context and writes a sum of all invoices — bug introduced. With CodeDNA, at line 55 it encounters:

```python
def monthly_revenue(year: int, month: int) -> dict:
    """Aggregate paid invoices into monthly revenue.

    Depends: payments.models.get_invoices_for_period — returns ALL invoices, NO suspended filter.
    Rules:   MUST filter is_suspended() BEFORE summing.
    """
```

Level 2 exists because the channel must work even when the receiver sees only a fragment. The message is repeated at every danger point — this is the holographic property in action.

---

## 2. Goals

- **Zero token overhead**: context lives in the file, not the prompt
- **Minimal drift**: annotations are co-located with what they describe, reducing (but not eliminating) synchronisation risk
- **Zero retrieval latency**: no vector DB, no network call
- **Sliding-window safe**: Level 2 sub-layers guide agents that skip the header
- **Planner efficient**: docstring-only reads give a full codebase map in ~70 tok/file
- **Python-native**: module docstring format, deeply embedded in LLM training data (other languages planned)
- **Agent-first**: designed for agentic code generation workflows — the agent writes and maintains the annotations, not the human; marginal annotation cost approaches zero
- **Human readable**: developers benefit as much as AI agents

---

## 2.4 Annotation Design Principle: Architecture, Not Answers

The `rules:` field must describe **architectural mechanisms and relationships** — never the solution to a specific task. This distinction is critical for benchmark validity and for real-world usefulness.

**Wrong — prescribes the solution:**
```python
rules:   Fix mysql/operations.py, oracle/operations.py, and sqlite3/base.py
         to handle tzname in date_trunc_sql().
```
An agent reading this can generate a plausible-sounding final answer by copying the file list without opening any file. The annotation replaces exploration with recall, breaking the causal chain that makes CodeDNA useful.

**Correct — describes the mechanism:**
```python
rules:   Trunc.as_sql() delegates to connection.ops.date_trunc_sql() and
         time_trunc_sql(), passing tzname. Each backend implements these
         methods independently with its own timezone strategy.
```
The agent reads this, understands the delegation pattern, uses `.codedna` to locate the backends, and **reasons from context** about which ones are relevant to the current task.

**The test:** a `rules:` annotation is well-formed if an agent reading it still needs to open files to complete its task. If the annotation alone is sufficient to write the final answer, it is too prescriptive.

### `used_by:` as a Navigation Map

`used_by:` lists **all real structural consumers** of a module — not just those relevant to the current task. The agent uses the problem description and `.codedna` manifest to reason which consumers matter. It should **not** open every `used_by:` target automatically: doing so wastes tokens and reduces precision.

The correct navigation model:
1. Read `used_by:` — know who depends on this file
2. Read `.codedna` — know the project structure
3. Read the problem description — understand the task domain
4. **Reason** — open only the consumers that are architecturally relevant to the task

This is why CodeDNA improves both F1 and efficiency simultaneously. Empirically (SWE-bench, 5 tasks, Gemini 2.5 Flash, ≥5 runs/task): CodeDNA runs achieve P=100% on dependency-chain tasks while Control runs scatter across irrelevant files.

### When `used_by:` Navigation Is Most Effective

Benchmark results across 5 SWE-bench tasks reveal that CodeDNA's navigation benefit is task-type dependent:

- **Dependency chain tasks** (A→B→C call path, one entry point): CodeDNA Δ = +14% to +27%. The agent follows `used_by:` links from the entry point to all affected files along the chain.
- **Cross-cutting tasks** (same fix in N unrelated files): CodeDNA Δ ≈ 0%. No natural chain exists; the agent must discover all files by pattern rather than by navigation. `used_by:` graphs with no shared ancestor do not help.

**Implication for annotators:** for cross-cutting concerns, consider annotating a central file (e.g., a base class) with `used_by:` pointing to all affected subclasses, even if the subclasses do not directly import the base for this specific change.

### Cross-Cutting Patterns: Benchmark Transparency Note

The SWE-bench task set used in this benchmark deliberately includes one cross-cutting task (django__django-11808: `__eq__` returning `NotImplemented` across 10 independent classes). This was intentional — to expose the limits of the protocol, not to hide them.

**The benchmark annotations for 11808 do NOT include any cross-cutting pattern hints** — no list of affected files in `.codedna`, no `rules:` enumerating all 10 classes. The annotations describe only the local architectural context of each file (`__eq__` must follow Python data model conventions). The agent must discover all 10 files by reasoning, not by reading a list.

This is the honest baseline: CodeDNA v0.7 as currently specified shows **Δ ≈ 0%** on cross-cutting tasks. This result is reported transparently in the benchmark.

**The proposed extension for v0.8:** a `cross_cutting_patterns:` section in the `.codedna` manifest, written by agents as they encounter such patterns during development — not pre-populated for evaluation tasks. Example:

```yaml
cross_cutting_patterns:
  python_data_model_eq:
    description: "Classes with __eq__ must return NotImplemented for unknown types, not False"
    affected_files:
      - django/db/models/base.py
      - django/db/models/constraints.py
      - django/db/models/indexes.py
      - django/db/models/query.py
      - django/db/models/query_utils.py
      - django/db/models/expressions.py
      - django/core/validators.py
      - django/template/context.py
      - django/contrib/messages/storage/base.py
      - django/contrib/postgres/constraints.py
```

This would be written by an agent **after** implementing the fix — knowledge deposited for future agents who encounter the same pattern. It is not "cheating" because the annotation encodes a discovered architectural truth, not a task-specific answer. A reviewer asking "did you pre-populate this to help the benchmark?" has a clear answer: no, the entry was not present during evaluation; it represents what the protocol *would enable* post-fix.

### Annotation Integrity Audit (all 5 tasks)

The benchmark annotations were audited post-hoc to verify that no `codedna/` file encodes a task-specific solution. The audit methodology: for every ground-truth file in each task, classify each `used_by:` target as GT or non-GT, and evaluate whether `rules:` describes an architectural mechanism or prescribes the fix.

**The test** (from §2.4): a `rules:` annotation is well-formed if an agent reading it still needs to open files to complete its task. If the annotation alone is sufficient to write the final answer, it is too prescriptive.

#### django__django-11808 (`__eq__` returning `NotImplemented`)

`used_by:` is not a factor — the 10 affected classes have no shared ancestor and no dependency relationship. The `rules:` field in each file states "must follow Python data model conventions — return NotImplemented for unknown types, not False." This describes a Python language rule, not a list of files to modify. The agent must discover all 10 files independently. Δ≈0% confirms the annotations provided no navigation advantage.

#### django__django-14480 (XOR connector support)

`query_utils.py` has 16 `used_by:` targets; 2 are GT (`expressions.py`, `query.py`) because they genuinely import `Q`. The remaining 14 are non-GT. The `rules:` field states "new connectors need support in sql/where.py and sql/__init__.py" — this describes the connector registration architecture (true for any new connector, not specific to XOR). The agent still needs to reason about `features.py` and the backend implications.

#### django__django-13495 (Trunc tzinfo on non-DateTimeField)

`base/operations.py` lists all 4 backend operations classes in `used_by:` — they are the complete set of subclasses that exist in Django. No cherry-picking is possible when the set has exactly 4 members. The `_convert_field_to_tz()` mention in each backend's `rules:` is an accurate description of how timezone wrapping is implemented per backend; it is not present in `sqlite3/operations.py` because SQLite does not use that method — matching the actual architectural difference, not the fix.

#### django__django-11991 (INCLUDE clause in indexes)

**Annotation correction made during audit:** `base/schema.py` in the `codedna/` directory initially listed only `postgresql/schema.py` in `used_by:`. All four backend schema editors (`mysql`, `oracle`, `postgresql`, `sqlite3`) inherit from `BaseDatabaseSchemaEditor`. The annotation was incomplete and was corrected to include all four backends, making the `used_by:` graph consistent with the actual inheritance hierarchy. The incomplete annotation was an omission, not an intentional hint toward the PostgreSQL-specific solution.

#### django__django-12508 (dbshell -c flag)

`base/client.py` lists all 4 backend client classes in `used_by:` — again, the complete set. `dbshell.py` has a 6-line `handle()` method. Its `rules:` states "Argument definitions live in base.py create_parser()/add_arguments()". This is the only non-obvious architectural fact about the file — it accurately describes how Django management command arguments work. No other `rules:` content was possible given the file's body. A generic LLM shown this file explains what the code does but does not navigate to `base.py` or `BaseDatabaseClient` as the next files to open. A CodeDNA-aware agent reads the `rules:` and navigates directly — not because the fix is prescribed, but because the delegation chain is described.

**Audit conclusion:** all 5 tasks pass the annotation integrity test. `used_by:` targets are real structural relationships; `rules:` fields describe mechanisms, not solutions. The one incomplete annotation found (11991 `base/schema.py`) was corrected. The benchmark results — positive Δ on chain tasks, Δ≈0% on the cross-cutting task — are consistent with annotations that aid navigation without encoding answers.

---

### Anticipated Reviewer Objection: The `.codedna` Manifest as a Confound

A reviewer may observe that the benchmark injects the `.codedna` project manifest into the agent's first message in the CodeDNA condition but not in the control condition, and argue that the manifest alone — not the per-file annotations — explains the improvement.

**This objection misunderstands the design of the protocol.**

The `.codedna` manifest is Level 0 of CodeDNA — it is not a separate advantage bolted onto the experiment, it is an integral layer of the system being tested. The four levels are inseparable:

- **Level 0 (`.codedna`):** the view from far away — package structure, purposes, inter-package dependencies
- **Level 1 (module headers):** the view from close up — `exports:`, `used_by:`, `rules:` per file
- **Level 2 (function `Rules:`):** the view from very close — constraints on critical functions
- **Level 3 (semantic naming):** type and origin encoded in variable names

Removing the manifest from the CodeDNA condition would not produce a cleaner control — it would test an incomplete protocol. The correct comparison is: *no CodeDNA at all* (control) vs *full CodeDNA* (codedna). That is what the benchmark measures.

**The manifest is not pre-written by a human.** In a real deployment the `.codedna` file is generated by agents as they explore the codebase — each agent that maps a new package deposits that knowledge into the manifest for every subsequent agent. On a large codebase with hundreds of packages, an agent without CodeDNA must spend dozens of tool calls reconstructing the project structure from scratch on every session. The manifest eliminates that cost entirely. This is the point of Level 0.

**The objection applied to any structured tool would invalidate it.** If you gave one agent a map of a city and another no map, and the first agent found its destination faster, you would not conclude that "the map is a confound" — you would conclude that maps help navigation. CodeDNA is a map. The control condition is the absence of a map. The experiment is valid by design.

**The system prompt objection** — that `CODEDNA_PROMPT` is more detailed than `SYSTEM_PROMPT` and therefore the improvement comes from prompt quality — is similarly circular. The navigation instructions in `CODEDNA_PROMPT` (read the first 15 lines, follow `used_by:`, act on `rules:`) are only meaningful because the annotations exist in the files. Giving those instructions to the control agent would produce no benefit — there is nothing to follow. The prompt and the annotations are co-designed and inseparable. Testing one without the other is not a cleaner experiment; it is a broken one.

## 2.5 CodeDNA File Format: Docstring + Full Source

A `codedna/` variant file **must contain the annotated docstring plus the complete original source code**. Stripping code from annotated files — leaving only the docstring — is a critical mistake: the agent reads the stub, has no pattern context, and either stops early or navigates to wrong files.

**Wrong — docstring only (stub):**
```python
"""features.py — BaseDatabaseFeatures: boolean capability flags for all DB backends.

exports: BaseDatabaseFeatures
used_by: postgresql/features.py → BaseDatabaseFeatures
rules:   New DDL features need a flag here first.
"""
# (empty — no code)
```
An agent reading this cannot see what existing flags look like, has no pattern to follow, and may not understand that this file needs modification.

**Correct — docstring + full source:**
```python
"""features.py — BaseDatabaseFeatures: boolean capability flags for all DB backends.

exports: BaseDatabaseFeatures
used_by: postgresql/features.py → BaseDatabaseFeatures
rules:   New DDL features need a flag here first.
"""

class BaseDatabaseFeatures:
    gis_enabled = False
    supports_deferrable_unique_constraints = False
    # ... full class body from control ...
```
The agent sees both the annotation and all existing flags. Pattern recognition is possible. Navigation is accurate.

**Rule:** `codedna_file = annotated_docstring + "\n\n" + control_file_verbatim`

---

## 2.6 Design Principle: Only Annotate What the Code Doesn't Tell You

In Python, `import` statements already declare dependencies — they are visible in the first lines of every file. Duplicating them in a `deps:` annotation wastes tokens and creates synchronisation risk. The same applies to `Depends:` at function level — the agent sees the imports when it reads the code.

What the code *doesn't* tell you:
- **`used_by:`** — Who imports this file? Hard to determine without reading many files in the project.
- **`exports:`** — Quick index of a file's public API without reading the entire file.
- **`rules:`** — Domain constraints that no static analysis can extract ("always filter suspended tenants before aggregating revenue").

These are the fields that survive the redundancy test. Everything else is either visible in the source or inferrable by the agent.

---

## 3. Level 0 — Project Manifest (`.codedna`)

### 3.0 Purpose

The `.codedna` file sits at the repo root and gives agents the **view from far away** — the project's package structure, what each package does, and how packages relate. The agent reads this first, before opening any source file.

### 3.1 Format

```yaml
# .codedna — Project structure manifest (auto-generated by codedna init)
project: myapp
description: E-commerce platform with multi-tenant billing

packages:
  payments/:
    purpose: "Invoice generation, payment processing, Stripe integration"
    key_files: [models.py, stripe_client.py, webhooks.py]

  analytics/:
    purpose: "Revenue reports, KPI dashboards, data aggregation"
    depends_on: [payments/, tenants/]

  tenants/:
    purpose: "Multi-tenant management, suspension, soft-delete"
    key_files: [models.py, middleware.py]

agent_sessions:
  - agent: claude-sonnet-4-6
    date: 2026-03-10
    task: "Implement monthly revenue aggregation"
    changed: [analytics/revenue.py]
    message: >
      Implemented monthly_revenue(). Found that get_invoices_for_period() returns ALL tenants
      with no suspended filter. Added rule to analytics/revenue.py. annual_summary() not yet
      implemented — left TODO in file.

  - agent: gemini-2.5-pro
    date: 2026-03-18
    task: "Add annual_summary to revenue module"
    changed: [analytics/revenue.py, api/serializers.py]
    message: >
      Added annual_summary(). Updated RevenueSchema in serializers.py [cascade].
      Discovered TenantSuspendedError case when all tenants suspended — added to rules.
      Note: the suspended filter is NOT idempotent — calling is_suspended() twice on the same
      result set causes double-exclusion. Added this to rules.
```

### 3.2 `agent_sessions:` Field

`agent_sessions:` is the **project-level session log** — the manifest-scope counterpart to the file-level `agent:` entries. Each entry captures what an agent did in a session and why, at project scope.

**Required subfields per entry:**

| Field | Description |
|---|---|
| `agent` | Model identifier (e.g., `claude-sonnet-4-6`, `gemini-2.5-pro`) |
| `date` | ISO date of the session (`YYYY-MM-DD`) |
| `task` | Brief description of the task (≤15 words) |
| `changed` | List of files meaningfully modified |
| `message` | Narrative: what was done, what was discovered, what the next agent should know |

**Agent behaviour:**
- On session start: read the last 3–5 `agent_sessions:` entries to understand recent project history
- On session end: append a new entry — never edit existing ones
- If new packages were discovered: also update `packages:` with their `purpose:` and `depends_on:`

### 3.3 Generation

```bash
pip install git+https://github.com/Larens94/codedna.git
export ANTHROPIC_API_KEY=sk-...

codedna init PATH     # first-time: L1 module headers + L2 Rules: on every .py file
codedna update PATH   # incremental: only unannotated files (safe to re-run)
codedna check PATH    # coverage report, no file changes
```

Options: `--model` (default: `claude-haiku-4-5-20251001`), `--dry-run`, `--no-llm`, `--repo-root`, `-v`

Cost: ~$1–3 for a Django-sized project (~500 files) with the default Haiku model.

---

## 4. Level 1 — The Module Header

### 4.1 Placement

The Module Header **must be the first content in the file**. A shebang line (`#!/usr/bin/env python`) may appear on line 1; the header starts on line 2.

A blank line must follow the closing delimiter before the first import or code statement.

### 4.2 Format

The Module Header is written as a **Python module docstring** (triple-quoted string). This format is already deeply embedded in LLM training data, which makes it significantly more effective than a custom comment block — models apply existing pattern recognition instead of processing unfamiliar syntax.

> **Note:** `deps:` is intentionally omitted — import statements already declare dependencies and are visible in the first lines of the file. See §2.5.

```python
"""<filename> — <one-line purpose, max 15 words>.

exports: <symbol(signature)> → <return_type> | none
used_by: <file> → <symbol> | none
rules:   <hard constraints for AI agents; what to do and what to avoid> | none
agent:   <model-id> | <YYYY-MM-DD> | <what I did and what I noticed — one or two lines>
"""
```

The `agent:` field is **multi-entry with a rolling window** — each agent session that significantly touches this file adds a new `agent:` line. Keep only the last 5 entries; drop the oldest when adding a 6th. Full history is preserved in git and `.codedna`. The field is the recent session history of the file, not a permanent log.



### 4.3 Fields

| Field | Required | Rule |
|---|---|---|
| first line | ✅ | `<filename> — <purpose>` (≤15 words, describes *what*, not *how*) |
| `exports` | ✅ | Public API with signatures |
| `used_by` | ✅ | Inverse of deps; who calls this file's exports. Optional `[cascade]` tag marks targets that **MUST** be updated when exports change. |
| `rules` | ✅ | **Architectural truth channel.** Hard constraints, domain knowledge, what to do and what to avoid. Updated in-place — always reflects the current correct state. |
| `agent` | ✅ | **Session narrative channel.** Rolling window of the last 5 agent entries. Format: `model-id \| YYYY-MM-DD \| message`. Drop the oldest when adding a 6th. Full history in git and `.codedna`. |

### 4.4 `rules:` Field — The Inter-Agent Communication Channel

`rules:` is **the most important field in CodeDNA**. It is the channel through which agents communicate with each other across time. When Agent A discovers a constraint, it writes it in `rules:`. When Agent B reads the file weeks later, it receives that knowledge instantly — without re-discovering it, without RAG, without external context.

**`rules:` is required.** Every file must have a `rules:` field — even if it's `none`. This signals to agents that the field is always expected and should always be checked and updated.

`rules:` applies to **every edit** in the file — it is the file's genome.

**What goes in `rules:`:**
- Domain constraints: `MUST call is_suspended() before aggregating revenue (no filter in upstream function)`
- Monetary constraints: `never hardcode prices; use config.py → PRICE_CONSTANTS`
- DB constraints: `soft-delete via users.deleted_at — MUST filter before aggregating`
- Security constraints: `never log tokens or passwords`
- Data shape: `get_invoices_for_period() returns ALL tenants, NO suspended filter`
- Cross-file contracts: `if changing monthly_revenue() signature → update api/serializers.py → RevenueSchema`

**Agent behaviour:**
- **On read**: always read `rules:` before writing any logic in this file
- **On edit**: respect all constraints in `rules:` — violations are bugs
- **On discovery**: if you discover a new constraint, fix a bug, or learn something non-obvious about this file — **add it to `rules:`**. This is how you communicate with the next agent.

`rules:` annotations grow **organically**. They are not generated in batch — they are written by agents as they work. Each agent that fixes a bug or learns something important leaves a `rules:` annotation for the next agent. This creates a **knowledge accumulation cycle**: the codebase gets smarter with every agent interaction.

### 4.5 `used_by:` Field (Inverse Dependency)

`used_by:` answers the question: **"who depends on me?"** This is one of the most useful fields in CodeDNA — it provides information that is hard to obtain from reading the file alone. Without `used_by:`, the agent would need to search across the project to find callers.

```python
"""utils/format.py — Currency and date formatting helpers.

exports: format_currency(n) -> str | format_date(d) -> str
used_by: views/dashboard.py → render | api/reports.py → revenue_route
rules:   none
"""
```

**Agent behaviour on edit**: when modifying an `exports:` symbol, check every file listed in `used_by:` and update callers as needed.

#### The `[cascade]` Tag

Some `used_by:` targets are critical — they **MUST** be updated when exports change (serializers, API schemas, type definitions). Mark these with `[cascade]`:

```python
used_by: api/reports.py → revenue_route | api/serializers.py → RevenueSchema [cascade]
```

**Agent behaviour**: after modifying an `exports:` symbol, the agent **MUST** open and update every `[cascade]`-tagged file before considering the task complete. Non-tagged `used_by:` targets should be checked but may not need changes.

### 4.6 Example

```python
"""analytics/revenue.py — Monthly/annual revenue aggregation from paid invoices.

exports: monthly_revenue(year, month) -> dict | annual_summary(year) -> list[dict]
used_by: api/reports.py → revenue_route | api/serializers.py → RevenueSchema [cascade]
rules:   get_invoices_for_period() returns ALL tenants, NO suspended filter →
         callers MUST call is_suspended() BEFORE aggregating revenue.
         DB: invoices(tenant_id, amount_cents, status), tenants(suspended_at, deleted_at).
         Raises TenantSuspendedError if all tenants in period are suspended.
agent:   claude-sonnet-4-6 | 2026-03-10 | Implemented monthly_revenue. Discovered NO suspended
         filter in upstream — added rule above. annual_summary not yet implemented.
agent:   gemini-2.5-pro    | 2026-03-18 | Added annual_summary. Reused monthly_revenue loop.
         TenantSuspendedError now raised when all tenants in period are suspended — added to rules.
"""
```

---

### 4.7 `message:` — The Agent Chat Layer *(v0.8 — Experimental, not yet tested)*

> **Status:** design proposal. Not validated in benchmark. Behaviour and format may change before finalisation.

The `agent:` field is a **narrative log** — what the agent did and what it noticed. The `message:` sub-field extends this with a **conversational layer**: observations not yet certain enough to become `rules:`, open questions, and explicit forward-looking notes for the next agent.

**Three channels, three purposes:**

| Field | Nature | Update policy |
|---|---|---|
| `rules:` | Architectural truth — hard constraints | updated in-place, always current |
| `agent:` | Session log — what happened and when | rolling window (last 5); drop oldest when adding a 6th |
| `message:` | Agent-to-agent chat — soft observations and open questions | append-only, resolved by reply |

`rules:` is the **law**. `agent:` is the **diary**. `message:` is the **conversation that precedes the law**.

#### Format at Level 1 (module docstring)

```python
"""analytics/revenue.py — Monthly/annual revenue aggregation from paid invoices.

exports: monthly_revenue(year, month) -> dict | annual_summary(year) -> list[dict]
used_by: api/reports.py → revenue_route | api/serializers.py → RevenueSchema [cascade]
rules:   get_invoices_for_period() returns ALL tenants, NO suspended filter →
         callers MUST call is_suspended() BEFORE aggregating revenue.
agent:   claude-sonnet-4-6 | anthropic | 2026-03-10 | Implemented monthly_revenue.
         message: "rounding edge case in multi-currency — not certain enough for rules:,
                  investigate before next release"
agent:   gemini-2.5-pro    | google    | 2026-03-18 | Added annual_summary.
         message: "@prev: confirmed rounding issue → promoted to rules:. New open item:
                  timezone handling in January rollover — check utils/dates.py first"
"""
```

#### Format at Level 2 (function docstring) — sliding window safe

The same `message:` field can appear in function-level docstrings. This is critical for agents that read the file via a sliding window and never see the module header:

```python
def monthly_revenue(year: int, month: int) -> dict:
    """Aggregate paid invoices into monthly revenue total.

    Rules:   MUST filter is_suspended() BEFORE summing.
    message: claude-sonnet-4-6 | 2026-03-10 | rounding edge case in multi-currency,
             investigate before next release — not yet promoted to Rules:
    message: gemini-2.5-pro    | 2026-03-18 | @prev: confirmed, promoted to Rules:.
             New: timezone rollover in January — check utils/dates.py
    """
```

An agent reading only lines 55–90 receives both the `Rules:` constraint and the active `message:` thread — no need to scroll to the top.

#### Lifecycle

1. Agent A leaves a `message:` — observation, open question, or soft warning
2. Agent B reads it, investigates, then:
   - **Confirmed as truth** → promotes to `rules:` (or `Rules:`), replies `"@prev: promoted to rules:"`
   - **Irrelevant** → replies `"@prev: verified, not applicable because..."` and closes the thread
   - **Still open** → extends the thread with a new `message:` and additional information
3. Old `message:` entries are never deleted — append-only, part of the permanent history

---

### 4.8 Agent Telemetry via Git Trailers *(v0.8 — Experimental, not yet tested)*

> **Status:** design proposal. Not validated in benchmark conditions. Format may change before finalisation.

#### Design principle: git is the audit log

Git is already immutable, append-only, diff-complete, and universally available. No additional infrastructure is needed. The only missing piece is a **structured commit message convention** that makes AI agent sessions filterable by model, provider, and session.

CodeDNA uses **git trailers** — the same standard mechanism as `Co-Authored-By:`, natively recognised by GitHub and GitLab — to embed agent metadata in every commit produced by an AI session.

#### Commit message format

```
implement monthly revenue aggregation

AI-Agent:    claude-sonnet-4-6
AI-Provider: anthropic
AI-Session:  s_a1b2c3
AI-Visited:  analytics/revenue.py, payments/models.py, api/reports.py
AI-Message:  found rounding edge case in multi-currency — investigate before next release
```

`AI-Visited:` is the only field not natively tracked by git. Git records files **changed** (the diff); `AI-Visited:` adds files **read** during the session. This is the critical distinction:
- `AI-Visited:` = navigation trace — where the agent looked
- git diff = modification trace — what the agent changed

All other audit data (exact diff, date, author, changed files) is already in git.

#### Queries available immediately via git

```bash
# all commits produced by AI agents
git log --grep="AI-Agent:"

# commits by a specific model
git log --grep="AI-Agent: claude-sonnet-4-6"

# all models that have touched a specific file, with diffs
git log --grep="AI-Agent:" -p -- analytics/revenue.py

# model distribution across the project
git log --format="%b" | grep "AI-Agent:" | sort | uniq -c | sort -rn

# full session reconstruction: what the agent read and changed
git show <commit-hash>
```

#### Three-tier architecture

```
git log (AI trailers)       ← authoritative audit log — immutable, diff-complete
        ↕ session_id
.codedna agent_sessions:    ← last N sessions, lean summary for agent navigation
        ↕ session_id
file agent: field           ← one-liner per file, sliding-window safe
```

The `session_id` is the link across all three tiers. The **authoritative source** for history is git. The `agent:` docstring field and `agent_sessions:` in `.codedna` are lightweight caches — read by agents during work, not the source of truth for audit.

#### Extended `agent:` entry in module docstring

The file-level `agent:` field gains `provider` and `session_id` to enable cross-referencing with git:

```python
# v0.7
agent:   claude-sonnet-4-6 | 2026-03-10 | Implemented monthly_revenue.

# v0.8 proposed
agent:   claude-sonnet-4-6 | anthropic | 2026-03-10 | s_a1b2c3 | Implemented monthly_revenue.
         message: "rounding edge case in multi-currency — investigate before next release"
```

Fields in order: `model-id | provider | YYYY-MM-DD | session_id | narrative`

#### Extended `agent_sessions:` in `.codedna`

```yaml
agent_sessions:
  - agent: claude-sonnet-4-6
    provider: anthropic
    date: 2026-03-10
    session_id: s_a1b2c3          # links to git commit with matching AI-Session trailer
    task: "implement monthly revenue aggregation"
    changed: [analytics/revenue.py]
    visited:  [analytics/revenue.py, utils/dates.py, payments/models.py, api/reports.py]
    message: >
      Implemented monthly_revenue(). Found rounding edge case in multi-currency —
      not yet a rule. Investigate before next release.
```

#### VSCode Extension (planned, M3)

The git trailers are the data source for a planned VSCode extension:

- **CodeLens inline** — last AI agent + commit count per file and function (from `git log`)
- **File Explorer overlay** — heat map of AI sessions per file, provider badge
- **Agent Timeline panel** — chronological session log with git diff per session
- **Stats panel** — model distribution chart, most visited files, navigation efficiency per model (`AI-Visited` length vs changed files ratio)

This is **`git blame` for AI agents**: not just who changed a line, but which model, which session, and the full navigation path that preceded the change.

---

## 5. Level 2 — Function-Level Rules

### 5.1 Motivation

Level 1 headers provide file-level context. But critical domain constraints often apply to **specific functions** — especially large functions (100+ lines) where the agent must read hundreds of lines before encountering a danger point.

Level 2 annotations are **`Rules:` docstrings** on functions. Unlike `deps:` or `Depends:` (which duplicate information already visible in imports), `Rules:` encode domain knowledge that **cannot be inferred from the code**.

### 5.2 When to Add `Rules:`

Add a `Rules:` docstring to any function that:
- has a constraint an AI agent could violate without domain context
- is part of a multi-file workflow with non-obvious contracts
- was the source of a previous bug (the agent documents the fix for the next agent)

> **Note:** `Depends:` is intentionally omitted at function level — import statements are already visible in the file header or inline. The only exception: if a function contains a **local import** (inside the function body, not at file level), a `Depends:` annotation is appropriate.

### 5.3 Format

```python
def monthly_revenue(year: int, month: int) -> dict:
    """Aggregate paid invoices into monthly revenue total.

    Rules:   MUST filter is_suspended() from tenants.models BEFORE summing.
             Failure to filter inflates revenue with suspended-tenant invoices.
    Raises:  TenantSuspendedError if all tenants in period are suspended.
    Returns: {year, month, total_cents, by_tenant: {id: [invoices]}}
    """
```

### 5.4 Organic Growth

`Rules:` annotations grow **organically**. They are not generated in batch — they are written by agents as they discover constraints during their work. Each agent that fixes a bug or learns something important leaves a `Rules:` annotation for the next agent.

```python
def annotate(self, *args, **kwargs):
    """Rules: if annotation name collides with a Model field → FieldError.
             After fix #14480, nested annotations are also checked.
             See also: values() — same collision logic."""
```

This creates a **knowledge accumulation cycle**: the codebase gets smarter with every agent interaction.



---

## 5. Level 3 — Semantic Naming

### 5.1 Motivation

**This is an agent-first convention, not a human style guide.** Traditional naming conventions (PEP 8, clean code) optimise for human readability in an IDE where type hints, hover tooltips, and "Go to Definition" are one click away. LLM agents have none of these — they see raw text in a fixed-size context window.

When an agent reads lines 200–250 of a file, a variable named `data` forces it to trace backwards to the function signature or import to understand what it holds. A variable named `list_dict_users_from_db` is **self-documenting in any 10-line window** — type, shape, and origin are encoded in the identifier itself.

This follows the same design logic as Level 2: Level 1 headers may be outside the sliding window → Level 2 repeats context at function scope. Native type hints may be outside the sliding window → Level 3 repeats type information in the variable name.

### 5.2 Convention

Format: `<type>_<shape>_<domain>_<origin>` (use relevant parts only)

```python
# ❌ Standard — agent must trace back to understand
data = get_users()
result = db.query(sql)
price = request.json["price"]

# ✅ CodeDNA — agent immediately knows type, shape, origin
list_dict_users_from_db = get_users()
list_dict_orders_raw_from_db = db.query(sql)
str_html_dashboard_rendered = render(execute_query)
int_cents_price_from_request = request.json.get("price")
```

### 5.3 When to Apply

Apply Semantic Naming to variables that:
- Cross function boundaries (returned or passed as arguments)
- Come from an external source (DB, API, request)
- Have a non-obvious type (e.g., integer representing cents, not euros)
- Are ambiguous at the point of use (e.g., `data`, `result`, `value`)

Purely local computation variables (`i`, `tmp`, `acc`) do not need renaming.

### 5.4 Type Prefix Reference

| Prefix | Meaning | Example |
|---|---|---|
| `str` | string | `str_html_page_rendered` |
| `int` | integer | `int_cents_price_from_request` |
| `float` | float | `float_pct_margin_computed` |
| `bool` | boolean | `bool_is_premium_from_db` |
| `list` | list | `list_dict_orders_from_db` |
| `dict` | dict | `dict_kpi_computed` |
| `df` | pandas DataFrame | `df_revenue_by_month_from_db` |

---

## 7. Planner Read Protocol

When an AI agent must plan edits across a multi-file codebase, it should:

1. Read **`.codedna`** — understand the project structure (which packages exist, what they do)
2. Read only the **module docstring** of relevant files (first 8–12 lines)
3. Filter by relevance:
   - Include files whose `used_by:` mentions the file being edited
   - Include files whose `rules:` field mentions the task domain
   - Skip others unless explicitly referenced
4. Build a dependency graph from `exports:` and `used_by:`
5. Identify the **minimum set of files** that must be read in full
6. Load only those files for the edit phase

**Token cost:** `.codedna` (~200 tok) + ~50 tokens per file header × N files = complete codebase map for planning.

---

## 8. AI Interaction Protocol

### 8.1 On READ (opening a project)
1. Read **`.codedna`** — understand the project structure.
2. Parse the module docstring (Level 1) of relevant files — first 8–12 lines.
3. Note `exports:` → must not rename or remove without explicit instruction.
4. Note `used_by:` → these callers will be affected by changes.
5. Note `rules:` → hard constraints for every edit in this file; read **before writing any logic**.
6. For any function you are about to modify: read its `Rules:` docstring first.

### 8.2 On WRITE (generate mode)
1. Generate the module docstring as the **first output block**, before any imports.
2. Populate all four fields: `exports`, `used_by`, `rules`, `agent`.
3. For critical functions with non-obvious domain constraints, add a `Rules:` docstring.
4. Apply semantic naming to data-carrying variables.
5. At session end: append an `agent_sessions:` entry to `.codedna` describing what was created and why.

### 8.3 On EDIT
1. **First step**: re-read `rules:`, the existing `agent:` log, and the `Rules:` of the function you are editing. The `agent:` history tells you why the current state exists.
2. Apply all file-level constraints before writing.
3. After editing, check `used_by:` targets (especially `[cascade]`-tagged ones).
4. If renaming an `exports:` symbol: update all `used_by:` callers.
5. **If you discover a constraint or fix a bug, update `rules:` for the next agent.** This is the architectural channel.
6. **After editing, append an `agent:` line** to the module docstring: `model-id | YYYY-MM-DD | what you did and what you noticed`. Keep only the last 5 entries — drop the oldest if adding a 6th. Full history is in git and `.codedna`.
7. At session end: append an `agent_sessions:` entry to `.codedna`.

### 8.4 Migration

Migration of an existing codebase is a **two-step process**:

1. **`codedna init`** (automatic): generates `.codedna` manifest and Module Headers (`exports:`, `used_by:`) by static analysis of imports. This takes seconds for a project with hundreds of files.
2. **Organic `Rules:`** (incremental): agents add `Rules:` annotations as they work on the code. No upfront investment — knowledge accumulates naturally over time.

CodeDNA targets **agentic code generation workflows** — environments where an LLM agent both generates and modifies source files. The structural annotations are auto-generated; the semantic annotations grow organically.

### 8.5 Inter-Agent Knowledge Accumulation

CodeDNA is designed for environments where **multiple AI agents work on the same codebase over time**, potentially different models, different tools, different sessions. Each agent leaves knowledge for the next:

1. **Writing agent** discovers a constraint (e.g., a soft-delete filter) → writes a `Rules:` annotation
2. **Next agent** reads the annotation → avoids the bug without re-discovering it
3. **Third agent** fixes a related bug → adds to the `Rules:` with more detail

This creates a **codebase that accumulates knowledge** over time. Unlike external documentation (which tends to go stale), `Rules:` annotations are co-located with the code they describe and are read each time the function is edited.

**The practical benefit:** agents don't need to understand the *entire* codebase — they need to understand the *constraints that aren't obvious from reading the code*. That is what `Rules:` helps with.

### 8.6 Verification Agents

Because `Rules:` annotations are written by AI agents, they may contain **hallucinated or incorrect information**. A single wrong `Rules:` annotation — e.g., "MUST filter by tenant_id" when no such filter is needed — could propagate into every future agent's output.

**Solution: periodic verification agents.** A verification agent:

1. Reads each `Rules:` annotation in the codebase
2. Cross-checks it against the actual code (tests, database schema, import graph)
3. Flags annotations that contradict the code or other annotations
4. Optionally removes or corrects annotations with evidence

This is analogous to code review for comments: the cost of reviewing is justified by the cost of wrong information propagating.

**When to run verification:**
- After a major refactor
- Before a release
- On a periodic schedule (e.g., weekly for active codebases)
- When an agent's edit produces unexpected failures

#### 8.6.1 Git Telemetry as Verification Input *(v0.8 — Experimental, not yet tested)*

> **Status:** design proposal. Not validated in benchmark conditions.

The git trailer convention described in §4.8 transforms verification agents from reactive (checking annotations after the fact) to **proactive** — able to audit agent behaviour systematically using structured telemetry from every AI session.

A verification agent with access to `git log` AI trailers can perform five distinct audit types:

**Audit 1 — Navigation correctness**

Did the agent read the files it should have given the `used_by:` graph?

```bash
git log --grep="AI-Agent:" --format="%H %b" | extract AI-Visited
# compare AI-Visited against used_by: targets of each changed file
```

If a commit modifies `analytics/revenue.py` (which has `used_by: api/serializers.py [cascade]`) but `api/serializers.py` is absent from both `AI-Visited:` and the diff — the verification agent flags a **cascade violation**.

**Audit 2 — Rule compliance from diff**

Did the agent respect the `rules:` of every file it modified?

The verification agent reads the diff of each AI commit and cross-checks it against the `rules:` field of the modified files. Because `rules:` is structured and co-located with the code, this check is automatable — no manual review required.

**Audit 3 — Annotation accuracy**

Are the `rules:` still accurate after the change?

If a commit modifies `get_invoices_for_period()` but does not update the `rules:` that describes its behaviour, the verification agent flags a **stale annotation** — the field describes code that no longer exists.

**Audit 4 — `message:` lifecycle**

Are there `message:` entries that have been open for too long without resolution?

```bash
git log --grep="AI-Message:" --format="%ai %b"
# find messages with no @prev: reply in any subsequent AI commit touching the same file
```

A `message:` unresolved for N sessions signals either a known open issue (acceptable) or a forgotten observation (verification agent bumps it into `rules:` or closes it with a reply).

**Audit 5 — Navigation efficiency per model**

```
navigation_efficiency = len(changed_files) / len(AI-Visited)
```

Aggregated per model over time, this is a real signal of navigational quality — not a proxy metric. An agent that reads 20 files and changes 1 is navigating poorly relative to the `used_by:` graph. The verification agent can surface this per model and per file domain.

**The verification agent as a first-class consumer of telemetry**

| Consumer | Reads | Purpose |
|---|---|---|
| Operational agent | `.codedna` + file `agent:` | navigate the codebase during work |
| Verification agent | `git log` AI trailers | audit compliance, flag violations, close message: threads |
| VSCode extension | `git log` AI trailers | visualise history for the human team |

The verification agent closes the quality loop: operational agents write code and annotations; the verification agent checks that both are coherent and flags divergences before they propagate.

### 8.7 Maintenance Cost Model

Annotations have a maintenance cost — they can go stale, be wrong, or become outdated after refactoring. This is not free. But the ROI is clear:

| Without CodeDNA | With CodeDNA |
|---|---|
| N agents each spend ~X tokens rediscovering the same constraint | One agent writes `Rules:`, N agents save ~X tokens each |
| Bug is re-introduced when an agent forgets the constraint | Constraint is preserved across sessions |
| Human must write detailed prompt every session | Annotations accumulate knowledge automatically |

**The trade-off:** annotations require maintenance agents (verification, updates after refactoring). But because the annotations themselves are structured and machine-readable, this maintenance can also be automated. The cost of a verification agent pass is far lower than the cost of N agents each making the same mistake.

**This is the same trade-off as documentation**, but with two key differences:
1. **Machine-readable:** a verification agent can cross-check annotations against code automatically
2. **Co-located:** unlike external docs, annotations are in the file — they are read every time the code is touched


---

## 8.5 Fine-Tuning Potential

All benchmark results in this specification are **zero-shot**: models read CodeDNA annotations with no prior training on the protocol. They interpret `exports:`, `used_by:`, and `rules:` through general language understanding — yet still show consistent F1 improvements over unannotated codebases.

This establishes a performance floor. The ceiling is substantially higher.

A foundation model fine-tuned specifically on CodeDNA-annotated codebases would:

- Recognize `exports:` / `used_by:` / `rules:` as **native structured signals**, not free text requiring interpretation
- Execute `used_by:` graph traversal as a **learned navigation primitive** rather than a reasoned inference — reducing the variance observed in zero-shot runs (e.g., ±33% F1 on a single task)
- Know precisely when to stop exploring (precision maximization) and when to follow another link (recall maximization)
- Treat the `.codedna` manifest as a **structured index**, not prose to parse

This is fundamentally different from Retrieval-Augmented Generation (RAG) or tool-augmented code completion. RAG retrieves fragments by semantic similarity — a statistical process with no awareness of architectural relationships. CodeDNA encodes those relationships structurally in the source, so the agent navigates by graph traversal, not by similarity search. A fine-tuned model would navigate a CodeDNA-annotated codebase the way a human senior engineer navigates a well-documented one: immediate orientation, minimal reading, maximum coverage.

### Asynchronous Agent Communication at Scale

`rules:` is an **asynchronous message channel** between agents with no shared memory and no coordination protocol. Agent A writes architectural context into a file; Agent B reads it in a different session, with a different model, weeks later. The file is the channel. The protocol is the format.

This extends naturally to multi-agent pipelines:

```
Planning agent  → annotates while exploring  → leaves rules: for implementation agent
Implementation  → reads rules:, acts         → updates rules: with discovered constraints
Review agent    → reads updated rules:       → validates consistency, extends annotations
```

Each agent leaves the codebase more navigable for the next. Unlike documentation, annotations are co-located with the code they describe — they are read every time the file is edited, not forgotten in a wiki.

### CodeDNA as a Self-Generating Training Corpus

A less obvious but consequential property: a CodeDNA-annotated codebase with active agent usage constitutes a **self-generating training corpus** across three complementary levels of supervision signal.

#### Level 1 — SFT (Supervised Fine-Tuning)

The append-only `agent:` field records an ordered, file-scoped narrative of correct navigational decisions. Each line encodes — in natural language — what an agent did, what constraint it discovered, and what it left for the next session. Across thousands of files and sessions, this is a dense demonstration dataset of expert codebase navigation grounded in real task outcomes. No labelling cost; the annotations are produced as a side effect of normal agent work.

#### Level 2 — DPO / Preference Alignment

The git history with AI trailers (§4.8) produces naturally occurring `(rejected, chosen)` pairs. When Agent A introduces an incorrect annotation or violates a domain constraint, and Agent B subsequently corrects it and updates `rules:`, the two commits form a labeled preference pair:

```
commit a3f2b1                            ← rejected
AI-Agent:   gemini-flash
AI-Message: "added invoice logic — skipped suspension check"

commit b7c903                            ← chosen
AI-Agent:   claude-sonnet
AI-Message: "FIXED: suspension check was missing — bug from prev agent"
rules: updated → "Suspension check REQUIRED before billing"
```

The pair is complete with visited-file lists (`AI-Visited:`), session IDs (`AI-Session:`), and agent-written rationale (`AI-Message:`). Unlike synthetic preference data, these pairs are grounded in the actual codebase state at the time of each decision. They are produced at zero marginal cost during normal development.

#### Level 3 — PRM (Process Reward Model)

The session trace infrastructure (`traces_to_training.py`) records the full ordered sequence of tool calls per session. Combined with the binary task outcome (patch applied successfully or not), each trace becomes a labelled reasoning trajectory. Steps on a successful session receive positive reward; steps on a failed session can be assigned negative signal — enabling a process-level reward model trained on real agent behaviour, not on human-generated chain-of-thought.

#### The Data Flywheel

These three levels are mutually reinforcing:

```
Better models
    → more accurate annotations
    → more informative preference pairs (DPO)
    → better process reward models (PRM)
    → sharper navigational policy
    → better models  ↺
```

Each agent session that writes or corrects a CodeDNA annotation improves the training signal available to all future model generations — without additional human labelling or dedicated data collection infrastructure. The codebase is simultaneously the environment, the protocol, and the training dataset.

---

## 1.2 Session Continuity and the Agent Chat

### The Session Problem

Every agent session starts cold. The agent has no memory of what previous sessions did, why they made specific choices, or what they discovered along the way. `rules:` addresses the *what* — the architectural constraints. But it does not address the *who*, the *when*, or the *why I did it this way*.

A `rules:` field like `MUST filter is_suspended() before aggregating` tells the next agent what to do. It does not tell them:
- Which agent wrote this rule
- When it was discovered
- What went wrong before the rule was added
- What the agent was trying to accomplish when it found this

This temporal, narrative layer is what the `agent:` field provides.

### `rules:` vs `agent:` — Two Distinct Channels

| | `rules:` | `agent:` |
|---|---|---|
| **Nature** | Architectural truth | Session narrative |
| **Time** | Timeless — always valid | Temporal — stamped with date and model |
| **Update mode** | In-place — always the current correct state | Append-only — history is preserved |
| **Content** | Constraints: what to do, what to avoid | Messages: what I did, what I noticed, what surprised me |
| **Recipient** | Any future agent about to edit this file | Any future agent wanting to understand the history |

Think of `rules:` as a shared wiki page — it is updated to always be correct. `agent:` is a chat log — it accumulates entries, each timestamped, each signed.

### Session Continuity Model

A CodeDNA-aware agent session has a defined lifecycle:

```
Session Start:
  1. Read .codedna manifest — understand current project state + session history
  2. Read module docstrings — collect rules: and agent: logs for relevant files
  3. Read function Rules: on functions to edit

During Session:
  4. Respect rules: constraints
  5. Discover new constraints → update rules: immediately (do not wait until end)

Session End:
  6. Append agent: entry to every file significantly touched
  7. Append agent_sessions: entry to .codedna manifest
  8. Update manifest packages: if new structure was discovered
```

The manifest becomes a **living document** — not a static snapshot generated by `codedna init`, but a continuously updated record of the project's evolution through agent sessions.

### The Persistent Chat in Code

When multiple agents work on the same file over time, the `agent:` entries form a **conversation embedded in the source**:

```python
"""analytics/revenue.py — Monthly/annual revenue aggregation from paid invoices.

exports: monthly_revenue(year, month) -> dict | annual_summary(year) -> list[dict]
used_by: api/reports.py → revenue_route | api/serializers.py → RevenueSchema [cascade]
rules:   get_invoices_for_period() returns ALL tenants, NO suspended filter →
         callers MUST call is_suspended() BEFORE aggregating.
         Suspended filter is NOT idempotent — calling twice causes double-exclusion.
agent:   claude-sonnet-4-6 | 2026-03-10 | Implemented monthly_revenue. Found no suspended filter
         in get_invoices_for_period — added rule above. Verified with test_revenue_suspended.
agent:   gemini-2.5-pro    | 2026-03-18 | Added annual_summary. Reused monthly loop.
         Noticed double-exclusion risk on suspended filter — updated rules above.
agent:   deepseek-chat      | 2026-04-02 | Refactored to batch DB call. Rules unchanged.
         Perf note: old version made N queries per tenant — now 1 query total.
"""
```

This is not documentation. This is a **chat between agents who never shared a session**, reconstructed from entries left over time. A new agent reading this file instantly knows the history of decisions made, problems encountered, and solutions applied — without access to any external system.

---

## 9. Validation

Run `tools/auto_annotate.py --dry-run` to check:
- Every file has a module docstring with the CodeDNA fields
- All required fields are present and non-empty
- First line matches the pattern `<filename> — <purpose>`
- `used_by:` is consistent with imports across the project

Pre-commit hook available in `tools/pre-commit`.

---

## 10. Versioning

The version of the standard is tracked in the repo tag (`v0.7`).

---

## 11. Language Adaptations

The CodeDNA field names (`exports:`, `used_by:`, `rules:`, `agent:`, `message:`) are identical across all languages. Only the comment syntax and placement rules differ.

### Design rules for all languages

1. The annotation must be the **first meaningful block** in the file (before imports, after mandatory declarations such as `package`).
2. **Level 1** (module header) uses the language's native documentation comment syntax.
3. **Level 2** (function-level `Rules:`) uses the same syntax on individual functions.
4. Semantic naming adapts to the language's casing convention, but retains the `type_shape_domain_origin` structure.

---

### Python *(canonical)*

```python
"""filename.py — purpose ≤15 words.

exports: public_fn(arg) -> ReturnType
used_by: caller.py → caller_fn
rules:   hard constraint agents must never violate
agent:   claude-sonnet-4-6 | 2026-03-24 | what was done
         message: "open hypothesis for the next agent"
"""
```

**Level 2:**
```python
def my_function(arg: type) -> ReturnType:
    """Short description.

    Rules:   constraint
    message: model-id | YYYY-MM-DD | observation
    """
```

**Semantic naming:** `list_dict_users_from_db`, `str_html_report_rendered`

---

### TypeScript / JavaScript

Annotation goes **before the first import**, as a JSDoc block.

```typescript
/**
 * filename.ts — purpose ≤15 words.
 *
 * exports: publicFn(arg): ReturnType | AnotherFn(arg): ReturnType
 * used_by: caller.ts → callerFn
 * rules:   hard constraint agents must never violate
 * agent:   claude-sonnet-4-6 | 2026-03-24 | what was done
 *          message: "open hypothesis for the next agent"
 */

import { something } from './something';
```

**Level 2:**
```typescript
/**
 * Short description.
 *
 * Rules:   constraint
 * message: model-id | YYYY-MM-DD | observation
 */
function myFunction(arg: Type): ReturnType {
```

**Semantic naming (camelCase):** `arrUsersFromDb`, `mapPricesByIdFromApi`, `strHtmlReportRendered`

**Note:** plain `.js` files use the same format. For `.jsx`/`.tsx` files, place the annotation before the first import, not inside the component.

---

### Go

Go convention allows a comment block before the `package` declaration — this is the package documentation. CodeDNA uses this slot.

```go
// filename.go — purpose ≤15 words.
//
// exports: PublicFn(arg Type) ReturnType | AnotherFn(arg Type) ReturnType
// used_by: caller.go → callerFn
// rules:   hard constraint agents must never violate
// agent:   claude-sonnet-4-6 | 2026-03-24 | what was done
//          message: "open hypothesis for the next agent"
package mypackage

import "something"
```

**Level 2:**
```go
// MyFunction does X.
//
// Rules:   constraint
// message: model-id | YYYY-MM-DD | observation
func MyFunction(arg Type) ReturnType {
```

**Semantic naming (camelCase):** `usersSliceFromDB`, `priceMapByIDFromAPI`, `htmlReportStr`

**Note:** Go's `godoc` tool reads the comment immediately before `package` as the package doc — CodeDNA is fully compatible with this convention.

---

### Rust

Rust `//!` (inner doc comments) at the top of a file document the module itself. This is the canonical slot for the CodeDNA annotation.

```rust
//! filename.rs — purpose ≤15 words.
//!
//! exports: public_fn(arg: Type) -> ReturnType | another_fn(arg: Type) -> ReturnType
//! used_by: caller.rs → caller_fn
//! rules:   hard constraint agents must never violate
//! agent:   claude-sonnet-4-6 | 2026-03-24 | what was done
//!          message: "open hypothesis for the next agent"

use std::collections::HashMap;
```

**Level 2:**
```rust
/// Short description.
///
/// # Rules
/// constraint
///
/// # Message
/// model-id | YYYY-MM-DD | observation
pub fn my_function(arg: Type) -> ReturnType {
```

**Semantic naming (snake_case, same as Python):** `vec_users_from_db`, `map_prices_by_id_from_api`, `str_html_report_rendered`

**Note:** `///` (outer doc comments) are for exported functions. `//!` (inner doc comments) are for modules and files. Both are rendered by `rustdoc`.

---

### Java

Java's `package` declaration must be the first statement. The CodeDNA annotation goes as a Javadoc block **between the package declaration and the class**, which is standard Javadoc placement for class-level documentation.

```java
package com.example.mypackage;

/**
 * ClassName.java — purpose ≤15 words.
 *
 * exports: publicMethod(arg): ReturnType | anotherMethod(arg): ReturnType
 * used_by: CallerClass.java → callerMethod
 * rules:   hard constraint agents must never violate
 * agent:   claude-sonnet-4-6 | 2026-03-24 | what was done
 *          message: "open hypothesis for the next agent"
 */
public class ClassName {
```

**Level 2:**
```java
/**
 * Short description.
 *
 * Rules:   constraint
 * message: model-id | YYYY-MM-DD | observation
 */
public ReturnType myMethod(Type arg) {
```

**Semantic naming (camelCase):** `userListFromDb`, `priceMapByIdFromApi`, `htmlReportStr`

---

### Ruby

```ruby
# filename.rb — purpose ≤15 words.
#
# exports: public_method(arg) -> ReturnType | another_method(arg) -> ReturnType
# used_by: caller.rb → caller_method
# rules:   hard constraint agents must never violate
# agent:   claude-sonnet-4-6 | 2026-03-24 | what was done
#          message: "open hypothesis for the next agent"

require 'something'
```

**Level 2:**
```ruby
# Short description.
#
# Rules:   constraint
# message: model-id | YYYY-MM-DD | observation
def my_method(arg)
```

**Semantic naming (snake_case):** `list_users_from_db`, `hash_prices_by_id_from_api`

---

### C / C++

```cpp
/**
 * filename.cpp — purpose ≤15 words.
 *
 * exports: public_fn(Type arg) -> ReturnType | another_fn(Type arg) -> ReturnType
 * used_by: caller.cpp → caller_fn
 * rules:   hard constraint agents must never violate
 * agent:   claude-sonnet-4-6 | 2026-03-24 | what was done
 *          message: "open hypothesis for the next agent"
 */

#include <something>
```

**Level 2:**
```cpp
/**
 * Short description.
 *
 * Rules:   constraint
 * message: model-id | YYYY-MM-DD | observation
 */
ReturnType myFunction(Type arg) {
```

---

### Language Support Matrix

| Language | Level 1 syntax | Level 2 syntax | Naming convention | Status |
|---|---|---|---|---|
| Python | `"""..."""` module docstring | `"""Rules: ..."""` function docstring | `snake_case` prefixed | Canonical |
| TypeScript/JS | `/** ... */` JSDoc before imports | `/** Rules: ... */` on function | `camelCase` prefixed | Supported |
| Go | `// ...` block before `package` | `// Rules: ...` before `func` | `camelCase` prefixed | Supported |
| Rust | `//! ...` inner doc at file top | `/// # Rules` on `pub fn` | `snake_case` prefixed | Supported |
| Java | `/** ... */` Javadoc before class | `/** Rules: ... */` on method | `camelCase` prefixed | Supported |
| Ruby | `# ...` block before requires | `# Rules: ...` before `def` | `snake_case` prefixed | Supported |
| C/C++ | `/** ... */` before includes | `/** Rules: ... */` before function | `snake_case` prefixed | Supported |

---

## Changelog

| Version | Date | Notes |
|---|---|---|
| 0.1 | 2026-03-16 | Initial draft — Level 1 Manifest Header (`# === CODEDNA:0.1 ===` format) |
| 0.2 | 2026-03-16 | Level 2 Inline Hyperlinks (`@REQUIRES-READ`, `@SEE`, `@MODIFIES-ALSO`), biological model |
| 0.3 | 2026-03-16 | Level 3 Semantic Naming, `CONTEXT_BUDGET` field, Planner Manifest-Only Read protocol |
| 0.4 | 2026-03-16 | `AGENT_RULES` field, `REQUIRED_BY` field, `CONTEXT_BUDGET` criteria, type prefix table |
| 0.5 | 2026-03-16 | Python-native module docstring format. Level 2 split into 2a/2b. `rules:` replaces `AGENT_RULES`. |
| 0.6 | 2026-03-18 | Redundancy audit: removed `deps:` and `Depends:`. Added Level 0 `.codedna` manifest. Level 2 simplified to `Rules:` only. `used_by:` promoted to required field. Zoom metaphor. |
| **0.7** | **2026-03-18** | **Header reduced to 3 fields: `exports:`, `used_by:`, `rules:`. `rules:` promoted to required — the inter-agent communication channel. `cascade:` absorbed into `used_by:` as `[cascade]` tag. Removed redundant fields: `tested_by:`, `tables:`, `raises:` (all inferrable from code). Python-only focus.** |
| **0.7.1** | **2026-03-18** | **Added §2.5 codedna file format requirement (docstring + full source). Added §2.4 task-type analysis (dependency chains vs cross-cutting). Benchmark extended to 5 tasks, ≥5 runs/task, multi-model. Tool harness hardened with `list_files`/`read_file` directory guards.** |
| **0.8 (proposed)** | — | **`cross_cutting_patterns:` section in `.codedna` manifest. Written by agents post-fix to capture patterns that span files with no dependency relationship. Enables navigation for cross-cutting tasks where `used_by:` graphs have no shared ancestor.** |
| **0.9 (proposed)** | — | **Multi-language support: TypeScript/JS, Go, Rust, Java, Ruby, C/C++. Each language uses its native documentation comment syntax. Field names (`exports:`, `used_by:`, `rules:`, `agent:`, `message:`) are identical across all languages. See §11.** |

