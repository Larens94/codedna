# CodeDNA Annotation Standard — Specification

**Version:** 0.5  
**Status:** Draft  
**Language:** Agnostic

---

## 1. Overview

CodeDNA is the **CodeDNA Annotation Standard** — a source-file annotation format that makes codebases AI-navigable.

**Level 1 — The Manifest Header (Macro-Context):** A structured comment block at the top of every file describing the file's purpose, dependencies, public API, style conventions, and edit history.

**Level 2 — Inline Hyperlinks (Micro-Context):** Semantic annotations embedded at the function and variable level, enabling AI agents to navigate the codebase even when reading only partial file content via sliding windows.

**Level 3 — Semantic Naming (Cognitive Compression):** Variable and function naming conventions that encode type, origin, and shape directly into the identifier, eliminating the need to trace data flows.

Together, they make every code fragment self-sufficient: an AI extracting any part of a CodeDNA file finds enough context to act correctly without external lookup.

---

## 2. Goals

- **Zero token overhead**: context lives in the file, not the prompt
- **Zero drift**: annotations are co-located with what they describe
- **Zero retrieval latency**: no vector DB, no network call
- **Sliding-window safe**: Level 2 hyperlinks guide agents that skip the header
- **Planner efficient**: manifest-only reads give a full codebase map in ~60 tok/file
- **Language agnostic**: comment-based protocol works in any language
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

### 3.4 CONTEXT_BUDGET Values

| Value | Semantics | Criteria | Planner behavior |
|---|---|---|---|
| `always` | Core file — always needed | Imported by ≥ 3 other files OR defines the main entry point | Include in every planning context |
| `normal` | Standard file | Feature-specific logic; imported by 1–2 files | Include when relevant to the task |
| `minimal` | Utility / rarely changes | Pure helpers; ≤ 5 declared dependents; no side effects | Skip unless explicitly referenced |

This field enables **Planner Manifest-Only Read mode** (§6): the planner reads only the first 14 lines of each file, uses `CONTEXT_BUDGET` to filter, and builds a full architectural map in as little as 60 tokens per file.

### 3.5 AGENT_RULES Field

`AGENT_RULES` encodes hard constraints that apply agent-wide for this file. Unlike inline annotations (which are function-scoped), `AGENT_RULES` applies to **every edit** in the file.

```python
# AGENT_RULES: never hardcode monetary values; always read config.py → MAX_DISCOUNT_RATE
```

Common uses:
- Monetary constraints: `never hardcode prices; use config.py → PRICE_CONSTANTS`
- Encoding constraints: `all strings are UTF-8; never use latin-1`
- DB constraints: `always use parameterized queries; never concatenate SQL`

### 3.6 REQUIRED_BY Field (Inverse Dependency)

`REQUIRED_BY` is the inverse of `DEPENDS_ON`. It enables top-down navigation: when reading `utils.py`, the agent immediately knows which callers depend on its exports.

```python
# REQUIRED_BY: main.py → render(), api.py → endpoint_report()
```

**Agent behaviour on edit**: when modifying an `EXPORTS` symbol, the agent must check every file listed in `REQUIRED_BY` and apply `@MODIFIES-ALSO` cascade.

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

1. Read only the **first 14 lines** of each file (the manifest)
2. Filter by `CONTEXT_BUDGET`:
   - Include `always` files unconditionally
   - Include `normal` files if they match the task domain
   - Skip `minimal` files unless explicitly referenced in `DEPENDS_ON`
3. Build a dependency graph from `DEPENDS_ON`, `EXPORTS`, and `REQUIRED_BY`
4. Identify the **minimum set of files** that must be read in full
5. Load only those files for the edit phase

**Token cost:** ~70 tokens per file × N files = complete codebase map for planning.

---

## 7. AI Interaction Protocol

### 7.1 On READ (edit mode)
1. Parse the Manifest Header (Level 1)
2. Note `DEPENDS_ON` → must not break these
3. Note `EXPORTS` → must not rename or remove (check `@BREAKS-IF-RENAMED` tags)
4. Note `AGENT_RULES` → hard constraints for every edit in this file
5. Follow `@REQUIRES-READ` tags before writing

### 7.2 On WRITE (generate mode)
1. Generate the Manifest Header as the **first output block** (v0.4 format)
2. Set `CONTEXT_BUDGET` using criteria in §3.4
3. Add `@REQUIRES-READ` / `@SEE` / `@MODIFIES-ALSO` to cross-file functions
4. Add `@BREAKS-IF-RENAMED` to any symbol serialized externally
5. Apply Semantic Naming to data-carrying variables
6. Populate `REQUIRED_BY` if you know the callers

### 7.3 On EDIT
1. **First change**: update `LAST_MODIFIED` in the manifest header
2. Check `AGENT_RULES` — apply file-level constraints before writing
3. Read all `@REQUIRES-READ` links before writing logic
4. After editing, cascade `@MODIFIES-ALSO` changes
5. If renaming a symbol, check `@BREAKS-IF-RENAMED` and update all `REQUIRED_BY` callers

---

## 8. Validation

Run `tools/validate_manifests.py` to check:
- Every file has a manifest header
- All required fields are present and non-empty
- `FILE` field matches the actual filename
- `DEPENDS_ON` symbols exist in the referenced files' `EXPORTS`
- `REQUIRED_BY` is consistent with `DEPENDS_ON` in the referenced files
- `LAST_MODIFIED` is not empty

Pre-commit hook available in `tools/pre-commit`.

---

## 9. Versioning

Declared in the delimiter line:

```python
# === CODEDNA:0.4 =============================================
```

---

## Changelog

| Version | Date | Notes |
|---|---|---|
| 0.1 | 2026-03-16 | Initial draft — Level 1 Manifest Header |
| 0.2 | 2026-03-16 | Level 2 Inline Hyperlinks, biological model |
| 0.3 | 2026-03-16 | Level 3 Semantic Naming, CONTEXT_BUDGET field, Planner Manifest-Only Read protocol |
| 0.4 | 2026-03-16 | `AGENT_RULES` field, `REQUIRED_BY` field, `@BREAKS-IF-RENAMED` tag, objective `CONTEXT_BUDGET` criteria, type prefix table |
