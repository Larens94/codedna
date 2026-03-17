# CodeDNA Inter-Agent Communication Protocol — Specification

**Version:** 0.6  
**Status:** Draft  
**Language:** Agnostic

---

## 1. Overview

CodeDNA is an **inter-agent communication protocol** implemented as a source-file annotation format that makes codebases AI-navigable. It provides information that **cannot be inferred from reading the code alone** — most critically, the *reverse dependency graph* (`used_by:`) and *domain rules* (`rules:`).

The protocol follows a **zoom metaphor** — like how the human eye works:

**Level 0 — Project Manifest (`.codedna`):** A single file at the repo root describing the project structure, package purposes, and inter-package dependencies. The agent reads this first — the view from far away.

**Level 1 — Module Header (Macro-Context):** A docstring at the top of every file encoding the file's public API (`exports:`), reverse dependencies (`used_by:`), and hard constraints (`rules:`). The view from close up.

**Level 2 — Function-Level Rules (Micro-Context):** `Rules:` docstrings on critical functions, written organically by agents as they discover domain constraints. The view from very close.

**Level 3 — Semantic Naming (Cognitive Compression):** Variable naming conventions that encode type, origin, and shape directly into the identifier.

The design principle: **only annotate what the code doesn't already tell you.** Import statements already declare dependencies — duplicating them in annotations wastes tokens. But *who depends on you* (`used_by:`) is impossible to know without reading every file in the project. That is where CodeDNA adds value.

### 1.1 The Inter-Agent Communication Model

CodeDNA is an annotation standard by *form*, but an **inter-agent communication protocol** by *function*. The file is the channel. The writing agent encodes architectural context as structured metadata; the reading agent decodes it at any point in the file.

This is qualitatively different from rule files (CLAUDE.md, .cursorrules, AGENTS.md), which are **human→agent** communication. CodeDNA is **agent→agent** communication, co-located with the code it describes.

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

In 1 read, Agent C knows exactly which 2 files call `format_currency()` and will be affected by the change. Total: 3 tool calls instead of 12. The `used_by` field is a navigation protocol — it answers the question *"who depends on me?"* which is impossible to know from the code of this file alone.

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
- **Language adaptable**: docstring / comment-based protocol designed to work across languages (currently validated on Python)
- **Agent-first**: designed for agentic code generation workflows — the agent writes and maintains the annotations, not the human; marginal annotation cost approaches zero
- **Human readable**: developers benefit as much as AI agents

---

## 2.5 Design Principle: Only Annotate What the Code Doesn't Tell You

In Python, `import` statements already declare dependencies — they are visible in the first lines of every file. Duplicating them in a `deps:` annotation wastes tokens and creates synchronisation risk. The same applies to `Depends:` at function level — the agent sees the imports when it reads the code.

What the code *doesn't* tell you:
- **`used_by:`** — Who imports this file? Impossible to know without reading every file in the project.
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
```

### 3.2 Generation

```bash
codedna init          # generates .codedna from project structure
codedna init --update # updates .codedna preserving manual edits
```

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

exports:   <symbol(signature)> → <return_type> | none
used_by:   <file> → <symbol> | none
cascade:   <file> → <symbol> (MUST update if this file's exports change) | none
tested_by: <test_file> → <TestClass> | none
tables:    <table>(<col1>, <col2>) | none
raises:    <ExceptionType1>, <ExceptionType2> | none
rules:     <hard constraints for AI agents; what to do and what to avoid> | none
"""
```

**For JavaScript / TypeScript / Go / Rust** (no native triple-string docstring), use a JSDoc-style block comment:

```javascript
/**
 * <filename> — <one-line purpose>.
 *
 * exports:   <symbol(signature)> → <return_type>
 * used_by:   <file> → <symbol>
 * cascade:   <file> → <symbol>
 * tested_by: <test_file> → <TestClass>
 * tables:    <table>(<col1>, <col2>)
 * raises:    <ErrorType1>, <ErrorType2>
 * rules:     <hard constraints for AI agents>
 */
```

### 4.3 Fields

| Field | Required | Rule |
|---|---|---|
| first line | ✅ | `<filename> — <purpose>` (≤15 words, describes *what*, not *how*) |
| `exports` | ✅ | Public API with signatures |
| `used_by` | ✅ | Inverse of deps; who calls this file's exports |
| `cascade` | — | Files that **MUST** be updated when this file's exports change |
| `tested_by` | — | Test file and class/function that covers this module |
| `tables` | — | Tables and relevant columns, or `none` |
| `raises` | — | Exceptions this module can propagate to callers |
| `rules` | — | Hard constraints for AI agents (e.g. "never re-apply TAX_RATE") |

### 4.4 `rules:` Field

The `rules:` field encodes hard constraints that apply agent-wide for this file. `rules:` applies to **every edit** in the file — it is the file's genome.

Common uses:
- Monetary constraints: `never hardcode prices; use config.py → PRICE_CONSTANTS`
- DB constraints: `always use parameterized queries; never concatenate SQL`
- Cross-file contracts: `MUST call is_suspended() before aggregating revenue (no filter in upstream function)`

### 4.5 `used_by:` Field (Inverse Dependency)

`used_by:` answers the question: **"who depends on me?"** This is the most valuable field in CodeDNA — it provides information that is impossible to obtain from reading the file alone. Without `used_by:`, the agent must grep every file in the project to find callers.

```python
"""utils/format.py — Currency and date formatting helpers.

exports: format_currency(n) -> str | format_date(d) -> str
used_by: views/dashboard.py → render | api/reports.py → revenue_route
"""
```

**Agent behaviour on edit**: when modifying an `exports:` symbol, check every file listed in `used_by:` and update callers as needed.

### 4.6 `cascade:` Field (Mandatory Update Targets)

`cascade:` is stronger than `used_by:`. While `used_by:` is informational ("these files call me"), `cascade:` is **imperative** ("these files **MUST** be updated if my exports change"). Typical targets: serializers, API schemas, type definitions, configuration files.

```python
cascade: api/serializers.py → RevenueSchema | docs/api_spec.yaml → /revenue
```

**Agent behaviour on edit**: after modifying an `exports:` symbol, the agent **MUST** open and update every file in `cascade:` before considering the task complete.

### 4.7 `tested_by:` Field (Test File Mapping)

`tested_by:` tells the agent where the tests for this module live. Without it, agents waste tool calls grepping for test files or create duplicate tests in wrong locations.

```python
tested_by: tests/test_revenue.py → TestMonthlyRevenue, TestAnnualSummary
```

**Agent behaviour on edit**: after modifying logic, open the `tested_by:` file and update or add test cases to cover the change.

### 4.8 `raises:` Field (Error Propagation)

`raises:` declares which exceptions this module can propagate to callers. Agents frequently ignore error handling or write generic try/except blocks because they don't know what can fail.

```python
raises: TenantSuspendedError, NoDataError, InsufficientFundsError
```

**Agent behaviour on edit**: when calling a function from a module with `raises:`, the agent must handle or propagate each declared exception.


### 4.9 Examples by Language

**Python**
```python
"""analytics/revenue.py — Monthly/annual revenue aggregation from paid invoices.

exports:   monthly_revenue(year,month)->dict | annual_summary(year)->list[dict]
used_by:   api/reports.py → revenue_route | workers/report_generator.py → generate
cascade:   api/serializers.py → RevenueSchema
tested_by: tests/test_revenue.py → TestMonthlyRevenue
tables:    invoices(tenant_id, amount_cents, status) | tenants(suspended_at, deleted_at)
raises:    TenantSuspendedError, NoDataError
rules:     get_invoices_for_period() returns ALL tenants, NO suspended filter →
           callers MUST call is_suspended() BEFORE aggregating revenue
"""
```

**JavaScript / TypeScript**
```javascript
/**
 * authService.ts — JWT authentication and session management.
 *
 * exports:   login(credentials)->Promise<Token> | verify(token)->User
 * used_by:   router.ts → authMiddleware()
 * cascade:   types/auth.d.ts → TokenPayload
 * tested_by: __tests__/authService.test.ts → AuthLoginSuite
 * tables:    users(id, email, password_hash, role)
 * raises:    InvalidCredentialsError, TokenExpiredError
 * rules:     never log tokens or passwords; role field is string not boolean
 */
```

**SQL**
```sql
-- monthly_revenue.sql — Aggregated monthly revenue by category and region.
--
-- exports: (month, category, revenue, cost)
-- tables:  orders, order_items, products
-- rules:   always filter cancelled orders (status != 'cancelled')
```

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
2. Populate fields: `exports`, `used_by`, `rules` (and optionally `cascade`, `tested_by`, `tables`, `raises`).
3. For critical functions with non-obvious domain constraints, add a `Rules:` docstring.
4. Apply semantic naming to data-carrying variables.

### 8.3 On EDIT
1. **First step**: re-read `rules:` and the `Rules:` of the function you are editing.
2. Apply all file-level constraints before writing.
3. After editing, check `used_by:` and `cascade:` targets.
4. If renaming an `exports:` symbol: update all `used_by:` callers.
5. If you discover a constraint or fix a bug, add a `Rules:` annotation for the next agent.

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

This creates a **self-improving codebase** where knowledge grows organically. Unlike documentation (which goes stale), `Rules:` annotations are co-located with the code they describe and are read every time the function is edited.

**The key insight:** agents don't need to understand the *entire* codebase — they need to understand the *constraints that aren't obvious from reading the code*. That is exactly what `Rules:` provides.

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

### 8.7 Maintenance Cost Model

Annotations have a maintenance cost — they can go stale, be wrong, or become outdated after refactoring. This is not free. But the ROI is clear:

| Without CodeDNA | With CodeDNA |
|---|---|
| N agents each spend ~X tokens rediscovering the same constraint | One agent writes `Rules:`, N agents save ~X tokens each |
| Bug is re-introduced every time an agent forgets the constraint | Constraint is preserved across all future sessions |
| Human must write detailed prompt every session | Annotations accumulate knowledge automatically |

**The trade-off:** annotations require maintenance agents (verification, updates after refactoring). But because the annotations themselves are structured and machine-readable, this maintenance can also be automated. The cost of a verification agent pass is far lower than the cost of N agents each making the same mistake.

**This is the same trade-off as documentation**, but with two key differences:
1. **Machine-readable:** a verification agent can cross-check annotations against code automatically
2. **Co-located:** unlike external docs, annotations are in the file — they are read every time the code is touched


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

The version of the standard is tracked in the repo tag (`v0.6`).

---

## Changelog

| Version | Date | Notes |
|---|---|---|
| 0.1 | 2026-03-16 | Initial draft — Level 1 Manifest Header (`# === CODEDNA:0.1 ===` format) |
| 0.2 | 2026-03-16 | Level 2 Inline Hyperlinks (`@REQUIRES-READ`, `@SEE`, `@MODIFIES-ALSO`), biological model |
| 0.3 | 2026-03-16 | Level 3 Semantic Naming, `CONTEXT_BUDGET` field, Planner Manifest-Only Read protocol |
| 0.4 | 2026-03-16 | `AGENT_RULES` field, `REQUIRED_BY` field, `CONTEXT_BUDGET` criteria, type prefix table |
| 0.5 | 2026-03-16 | Python-native module docstring format. Level 2 split into 2a/2b. `rules:` replaces `AGENT_RULES`. |
| **0.6** | **2026-03-18** | **Redundancy audit: removed `deps:` (redundant with import statements) and `Depends:` (redundant with visible imports). Added Level 0 `.codedna` project manifest. Level 2 simplified to `Rules:` only (organic, written by agents). `used_by:` promoted to required field. Zoom metaphor: far (.codedna) → close (file header) → very close (function Rules:).** |

