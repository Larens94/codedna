# CodeDNA Inter-Agent Communication Protocol — Specification

**Version:** 0.5  
**Status:** Draft  
**Language:** Agnostic

---

## 1. Overview

CodeDNA is an **inter-agent communication protocol** implemented as a source-file annotation format that makes codebases AI-navigable.

**Level 1 — Module Header (Macro-Context):** A Python-native module docstring at the top of every file, encoding the file's purpose, dependencies, public API, and hard constraints for AI agents.

**Level 2 — Sliding-Window Annotations (Micro-Context):** Two sub-layers — (2a) Google-style function docstrings summarising cross-file deps and rules, and (2b) inline call-site comments at dangerous call points — ensuring agents reading only partial file content still receive critical context.

**Level 3 — Semantic Naming (Cognitive Compression):** Variable naming conventions that encode type, origin, and shape directly into the identifier, eliminating the need to trace data flows.

Together, they make every code fragment self-sufficient: an AI extracting any part of a CodeDNA file finds enough context to act correctly without external lookup. This is CodeDNA's *holographic property* — named after the biological analogy: just as DNA encodes the entire organism blueprint in every cell, every CodeDNA file carries complete architectural context in every fragment.

### 1.1 The Inter-Agent Communication Model

CodeDNA is an annotation standard by *form*, but an **inter-agent communication protocol** by *function*. The file is the channel. The writing agent encodes architectural context as structured metadata; the reading agent decodes it at any point in the file.

This is qualitatively different from rule files (CLAUDE.md, .cursorrules, AGENTS.md), which are **human→agent** communication. CodeDNA is **agent→agent** communication, co-located with the code it describes.

Three examples illustrate the model:

**Example A — The Writing Agent Warns the Reading Agent**

Agent A generates `analytics/revenue.py`. It knows (from its own generation context) that `get_invoices_for_period()` returns ALL tenants with no suspension filter. Agent A writes:

```python
"""analytics/revenue.py — Monthly revenue aggregation.

deps:    payments/models.py → get_invoices_for_period
rules:   get_invoices_for_period() returns ALL tenants, NO suspended filter →
         callers MUST call is_suspended() BEFORE aggregating
"""
```

Two weeks later, Agent B (a different LLM, different session, different prompt) is asked to add a quarterly report. Agent B reads `revenue.py`, sees `rules:`, and immediately knows that any code calling `get_invoices_for_period()` must filter suspended tenants — without reading `payments/models.py`, without RAG, without external context. The file was the channel. Agent A transmitted. Agent B received.

**Example B — The Dependency Graph as a Navigation Map**

Agent C is asked to fix a bug: "revenue numbers are wrong." Without CodeDNA, it must: `list_files` → grep "revenue" → read 10 files → trace imports → guess the entry point (8–12 tool calls). With CodeDNA, Agent C reads `analytics/revenue.py` and sees:

```python
deps:    payments/models.py → get_invoices_for_period
used_by: api/reports.py → revenue_route
```

In 1 read, Agent C has a complete map: data comes from `payments/models.py`, output goes to `api/reports.py`. The bug is in this chain of 3 files. Total: 3 tool calls instead of 12. The `deps`/`used_by` graph is a navigation protocol — the writing agent mapped the territory, the reading agent follows the map.

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

## 3. Level 1 — The Manifest Header

### 3.1 Placement

The Manifest Header **must be the first content in the file**. A shebang line (`#!/usr/bin/env python`) may appear on line 1; the header starts on line 2.

A blank line must follow the closing delimiter before the first import or code statement.

### 3.2 Format

The Manifest Header is written as a **Python module docstring** (triple-quoted string). This format is already deeply embedded in LLM training data, which makes it significantly more effective than a custom comment block — models apply existing pattern recognition instead of processing unfamiliar syntax.

```python
"""<filename> — <one-line purpose, max 15 words>.

deps:      <file> → <symbol1>, <symbol2> | none
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
 * deps:      <file> → <symbol>
 * exports:   <symbol(signature)> → <return_type>
 * used_by:   <file> → <symbol>
 * cascade:   <file> → <symbol>
 * tested_by: <test_file> → <TestClass>
 * tables:    <table>(<col1>, <col2>)
 * raises:    <ErrorType1>, <ErrorType2>
 * rules:     <hard constraints for AI agents>
 */
```

### 3.3 Fields

| Field | Required | Rule |
|---|---|---|
| first line | ✅ | `<filename> — <purpose>` (≤15 words, describes *what*, not *how*) |
| `deps` | ✅ | `file → func1, func2` or `none` |
| `exports` | ✅ | Public API with signatures |
| `used_by` | — | Inverse of deps; who calls this file's exports |
| `cascade` | — | Files that **MUST** be updated when this file's exports change |
| `tested_by` | — | Test file and class/function that covers this module |
| `tables` | — | Tables and relevant columns, or `none` |
| `raises` | — | Exceptions this module can propagate to callers |
| `rules` | — | Hard constraints for AI agents (e.g. "never re-apply TAX_RATE") |

### 3.4 `rules:` Field

The `rules:` field encodes hard constraints that apply agent-wide for this file. Unlike Level 2 function docstrings (which are function-scoped), `rules:` applies to **every edit** in the file — it is the file's genome: readable anywhere without navigating to a specific function.

Common uses:
- Monetary constraints: `never hardcode prices; use config.py → PRICE_CONSTANTS`
- DB constraints: `always use parameterized queries; never concatenate SQL`
- Cross-file contracts: `MUST call is_suspended() before aggregating revenue (no filter in upstream function)`

### 3.5 `used_by:` Field (Inverse Dependency)

`used_by:` is the inverse of `deps:`. It enables top-down navigation: when reading `utils.py`, the agent immediately knows which callers depend on its exports.

```python
"""utils/format.py — Currency and date formatting helpers.

deps:    none
exports: format_currency(n) -> str | format_date(d) -> str
used_by: views/dashboard.py → render | api/reports.py → revenue_route
"""
```

**Agent behaviour on edit**: when modifying an `exports:` symbol, check every file listed in `used_by:` and update callers as needed.

### 3.6 `cascade:` Field (Mandatory Update Targets)

`cascade:` is stronger than `used_by:`. While `used_by:` is informational ("these files call me"), `cascade:` is **imperative** ("these files **MUST** be updated if my exports change"). Typical targets: serializers, API schemas, type definitions, configuration files.

```python
cascade: api/serializers.py → RevenueSchema | docs/api_spec.yaml → /revenue
```

**Agent behaviour on edit**: after modifying an `exports:` symbol, the agent **MUST** open and update every file in `cascade:` before considering the task complete.

### 3.7 `tested_by:` Field (Test File Mapping)

`tested_by:` tells the agent where the tests for this module live. Without it, agents waste tool calls grepping for test files or create duplicate tests in wrong locations.

```python
tested_by: tests/test_revenue.py → TestMonthlyRevenue, TestAnnualSummary
```

**Agent behaviour on edit**: after modifying logic, open the `tested_by:` file and update or add test cases to cover the change.

### 3.8 `raises:` Field (Error Propagation)

`raises:` declares which exceptions this module can propagate to callers. Agents frequently ignore error handling or write generic try/except blocks because they don't know what can fail.

```python
raises: TenantSuspendedError, NoDataError, InsufficientFundsError
```

**Agent behaviour on edit**: when calling a function from a module with `raises:`, the agent must handle or propagate each declared exception.


### 3.9 Examples by Language

**Python**
```python
"""analytics/revenue.py — Monthly/annual revenue aggregation from paid invoices.

deps:      payments/models.py → get_invoices_for_period | tenants/models.py → is_suspended
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
 * deps:      db.ts → getUser() | config.ts → JWT_SECRET
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
-- deps:    none
-- exports: (month, category, revenue, cost)
-- tables:  orders, order_items, products
-- rules:   always filter cancelled orders (status != 'cancelled')
```

---

## 4. Level 2 — Sliding-Window Annotations

### 4.1 Motivation

AI agents operating in *sliding window* mode extract partial file content (e.g., lines 50–80) to reduce token consumption. This bypasses the Level 1 header entirely. Level 2 ensures that the **body of every critical function is self-documenting**, even when read in isolation.

Level 2 relies on:
- **Function Docstring**: Google-style docstring summarizing dependencies and rules

### 4.2 Level 2 — Function Docstring (Google style)

Add a structured docstring to any function that:
- calls a dependency with a non-obvious contract
- has a rule that an AI agent could violate without context
- is part of a multi-file workflow

```python
def monthly_revenue(year: int, month: int) -> dict:
    """Aggregate paid invoices into monthly revenue total.

    Depends: payments.models.get_invoices_for_period — returns ALL invoices, NO suspended filter.
    Rules:   MUST filter is_suspended() from tenants.models BEFORE summing.
             Failure to filter inflates revenue with suspended-tenant invoices.
    Raises:  TenantSuspendedError if all tenants in period are suspended.
             NoDataError if no invoices exist for the period.
    Returns: {year, month, total_cents, by_tenant: {id: [invoices]}}
    """
```
    invoices = get_invoices_for_period(year, month)  # includes suspended tenants — filter below
    total = sum(i['amount_cents'] for i in invoices)
```



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

## 6. Planner Manifest-Only Read Protocol

When an AI agent must plan edits across a multi-file codebase, it should:

1. Read only the **module docstring** of each file (first 8–12 lines)
2. Filter by relevance:
   - Include files whose `rules:` field mentions the task domain
   - Include files that appear in another file's `deps:` for this task
   - Skip others unless explicitly referenced
3. Build a dependency graph from `deps:`, `exports:`, and `used_by:`
4. Identify the **minimum set of files** that must be read in full
5. Load only those files for the edit phase

**Token cost:** ~70 tokens per file × N files = complete codebase map for planning.

---

## 7. AI Interaction Protocol

### 7.1 On READ (edit mode)
1. Parse the module docstring (Level 1) — first 8–12 lines.
2. Note `deps:` → these are contracts you must not break.
3. Note `exports:` → must not rename or remove without explicit instruction.
4. Note `rules:` → hard constraints for every edit in this file; read **before writing any logic**.
5. For any function you are about to modify: read its `Depends:` / `Rules:` docstring first.
6. Read call-site inline comments at any dangerous call you are near.

### 7.2 On WRITE (generate mode)
1. Generate the module docstring as the **first output block**, before any imports.
2. Populate all fields: `deps`, `exports`, `used_by`, `tables`, `rules`.
3. For cross-file functions, add a Google-style function docstring with `Depends:` and `Rules:`.
4. At dangerous call sites, add inline: `# includes X — filter Y below`.
5. Apply semantic naming to data-carrying variables.

### 7.3 On EDIT
1. **First step**: re-read `rules:` and the `Depends:` / `Rules:` of the function you are editing.
2. Apply all file-level constraints before writing.
3. After editing, cascade any `Modifies:` or call-site-annotated cascade targets.
4. If renaming an `exports:` symbol: update all `used_by:` callers.
5. If the `rules:` field needs to reflect the change, update it.

### 7.4 Migration

Migration of an existing codebase is a **one-time investment**. Any AI agent can annotate a pre-existing codebase by reading each file's imports, function signatures, and call sites, then generating the CodeDNA module docstring. Once annotated, maintenance cost approaches zero: the same agents that modify the code are responsible for updating the annotations in place.

CodeDNA targets **agentic code generation workflows** — environments where an LLM agent both generates and modifies source files. However, any legacy codebase can be migrated by delegating the annotation work to an agent. The initial annotation pass is the investment; all subsequent maintenance is a natural byproduct of code generation.


---

## 8. Validation

Run `tools/validate_manifests.py` to check:
- Every file has a module docstring with the CodeDNA fields
- All required fields are present and non-empty
- First line matches the pattern `<filename> — <purpose>`
- `deps:` symbols exist in the referenced files' `exports:`
- `used_by:` is consistent with `deps:` in the referenced files

Pre-commit hook available in `tools/pre-commit`.

---

## 9. Versioning

Declared in the module docstring first line:

```python
"""filename.py — <purpose>.

deps: ...
"""
```

The version of the standard being used is tracked in the repo tag (`v0.5`).

---

## Changelog

| Version | Date | Notes |
|---|---|---|
| 0.1 | 2026-03-16 | Initial draft — Level 1 Manifest Header (`# === CODEDNA:0.1 ===` format) |
| 0.2 | 2026-03-16 | Level 2 Inline Hyperlinks (`@REQUIRES-READ`, `@SEE`, `@MODIFIES-ALSO`), biological model |
| 0.3 | 2026-03-16 | Level 3 Semantic Naming, `CONTEXT_BUDGET` field, Planner Manifest-Only Read protocol |
| 0.4 | 2026-03-16 | `AGENT_RULES` field, `REQUIRED_BY` field, `CONTEXT_BUDGET` criteria, type prefix table |
| **0.5** | **2026-03-16** | **Python-native module docstring format (replaces custom `# ===` block). Level 2 split into 2a (Google-style function docstring) and 2b (call-site inline comment). `rules:` replaces `AGENT_RULES`, `used_by:` replaces `REQUIRED_BY`, `deps:` replaces `DEPENDS_ON`. Agent-first framing: marginal annotation cost ≈ zero in agentic workflows.** |
