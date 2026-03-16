# CodeDNA Annotation Standard — Specification

**Version:** 0.5  
**Status:** Draft  
**Language:** Agnostic

---

## 1. Overview

CodeDNA is the **CodeDNA Annotation Standard** — a source-file annotation format that makes codebases AI-navigable.

**Level 1 — Module Header (Macro-Context):** A Python-native module docstring at the top of every file, encoding the file's purpose, dependencies, public API, and hard constraints for AI agents.

**Level 2 — Sliding-Window Annotations (Micro-Context):** Two sub-layers — (2a) Google-style function docstrings summarising cross-file deps and rules, and (2b) inline call-site comments at dangerous call points — ensuring agents reading only partial file content still receive critical context.

**Level 3 — Semantic Naming (Cognitive Compression):** Variable naming conventions that encode type, origin, and shape directly into the identifier, eliminating the need to trace data flows.

Together, they make every code fragment self-sufficient: an AI extracting any part of a CodeDNA file finds enough context to act correctly without external lookup. This is CodeDNA's *holographic property* — named after the biological analogy: just as DNA encodes the entire organism blueprint in every cell, every CodeDNA file carries complete architectural context in every fragment.

---

## 2. Goals

- **Zero token overhead**: context lives in the file, not the prompt
- **Zero drift**: annotations are co-located with what they describe
- **Zero retrieval latency**: no vector DB, no network call
- **Sliding-window safe**: Level 2 sub-layers guide agents that skip the header
- **Planner efficient**: docstring-only reads give a full codebase map in ~70 tok/file
- **Language agnostic**: docstring / comment-based protocol works in any language
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

deps:    <file> → <symbol1>, <symbol2> | none
exports: <symbol(signature)> → <return_type> | none
used_by: <file> → <symbol> | none
tables:  <table>(<col1>, <col2>) | none
rules:   <hard constraints for AI agents; what to do and what to avoid> | none
"""
```

**For JavaScript / TypeScript / Go / Rust** (no native triple-string docstring), use a JSDoc-style block comment:

```javascript
/**
 * <filename> — <one-line purpose>.
 *
 * deps:    <file> → <symbol>
 * exports: <symbol(signature)> → <return_type>
 * used_by: <file> → <symbol>
 * tables:  <table>(<col1>, <col2>)
 * rules:   <hard constraints for AI agents>
 */
```

### 3.3 Fields

| Field | Required | Rule |
|---|---|---|
| first line | ✅ | `<filename> — <purpose>` (≤15 words, describes *what*, not *how*) |
| `deps` | ✅ | `file → func1, func2` or `none` |
| `exports` | ✅ | Public API with signatures |
| `used_by` | — | Inverse of deps; who calls this file's exports |
| `tables` | — | Tables and relevant columns, or `none` |
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


### 3.7 Examples by Language

**Python**
```python
"""analytics/revenue.py — Monthly/annual revenue aggregation from paid invoices.

deps:    payments/models.py → get_invoices_for_period | tenants/models.py → is_suspended
exports: monthly_revenue(year,month)->dict | annual_summary(year)->list[dict]
used_by: api/reports.py → revenue_route | workers/report_generator.py → generate
tables:  invoices(tenant_id, amount_cents, status) | tenants(suspended_at, deleted_at)
rules:   get_invoices_for_period() returns ALL tenants, NO suspended filter →
         callers MUST call is_suspended() BEFORE aggregating revenue
"""
```

**JavaScript / TypeScript**
```javascript
/**
 * authService.ts — JWT authentication and session management.
 *
 * deps:    db.ts → getUser() | config.ts → JWT_SECRET
 * exports: login(credentials)->Promise<Token> | verify(token)->User
 * used_by: router.ts → authMiddleware()
 * tables:  users(id, email, password_hash, role)
 * rules:   never log tokens or passwords; role field is string not boolean
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

Level 2 has two sub-layers:
- **2a — Function Docstring**: Google-style docstring summarizing dependencies and rules
- **2b — Call-site Inline Comment**: comment on the exact line where a dangerous call happens

### 4.2a Level 2a — Function Docstring (Google style)

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
    Returns: {year, month, total_cents, by_tenant: {id: [invoices]}}
    """
```

### 4.2b Level 2b — Call-site Inline Comment (sliding-window safe)

Annotate the **exact line** of a dangerous call. This is the last line of defense: even if the model sees only 10 lines around the call, it receives the critical context.

```python
    invoices = get_invoices_for_period(year, month)  # includes suspended tenants — filter below
    total = sum(i['amount_cents'] for i in invoices)  # BUG ZONE: no suspension filter applied
```

### 4.3 Legacy Tags (still valid)

The `@SEE`, `@REQUIRES-READ`, `@MODIFIES-ALSO`, `@BREAKS-IF-RENAMED` tag syntax is still valid for explicit machine-readable annotations:

```python
def apply_discount(base_price: int, user_tier: str) -> float:
    # @REQUIRES-READ: config.py → MAX_DISCOUNT_ALLOWED
    # @REQUIRES-READ: db.py → UserSchema (valid values for user_tier)
    # @MODIFIES-ALSO: invoice.py → calculate_total()

    if user_tier == "premium":
        return base_price * 0.8
    return base_price
```

### 4.4 `@BREAKS-IF-RENAMED` Tag

Use this on any symbol whose **name is load-bearing** — serialized to JSON/DB, referenced in config files, or called by string (`getattr`, `importlib`):

```python
def format_currency(n: float) -> str:  # @BREAKS-IF-RENAMED: name serialized in API response schema
    return f"€{n:,.0f}".replace(",", ".")

REPORT_VIEW = "monthly_revenue"  # @BREAKS-IF-RENAMED: key stored in users.saved_views table
```

**Agent behavior**: when asked to rename, the agent must first search all `REQUIRED_BY` callers and external config/DB references before applying the rename.

### 4.5 Inline Context Anchors

For individual lines with non-obvious constraints:

```python
BTN_COLOR = "#3B82F6"  # @SEE: style.css → --brand-primary (must stay in sync)
rows = execute_query(sql)  # @REQUIRES-READ: schema.sql → orders (column types)
int_cents_price_from_request = request.json["price"]  # @SEE: api_spec.md → price is always in cents
```

---

## 5. Level 3 — Semantic Naming

### 5.1 Motivation

Variable names that encode type, origin, and shape reduce the AI's need to trace data flows. Even in a 10-line extracted fragment, a well-named variable is self-documenting.

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
6. Add `@BREAKS-IF-RENAMED` to any symbol serialized externally.

### 7.3 On EDIT
1. **First step**: re-read `rules:` and the `Depends:` / `Rules:` of the function you are editing.
2. Apply all file-level constraints before writing.
3. After editing, cascade any `Modifies:` or call-site-annotated cascade targets.
4. If renaming an `exports:` symbol: update all `used_by:` callers.
5. If the `rules:` field needs to reflect the change, update it.


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
| 0.4 | 2026-03-16 | `AGENT_RULES` field, `REQUIRED_BY` field, `@BREAKS-IF-RENAMED` tag, objective `CONTEXT_BUDGET` criteria, type prefix table |
| **0.5** | **2026-03-16** | **Python-native module docstring format (replaces custom `# ===` block). Level 2 split into 2a (Google-style function docstring) and 2b (call-site inline comment). `rules:` replaces `AGENT_RULES`, `used_by:` replaces `REQUIRED_BY`, `deps:` replaces `DEPENDS_ON`. Agent-first framing: marginal annotation cost ≈ zero in agentic workflows. Legacy `@`-tags remain valid.** |
