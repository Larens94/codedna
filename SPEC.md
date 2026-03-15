# CodeDNA — Technical Specification

**Version:** 0.3  
**Status:** Draft  
**Language:** Agnostic

---

## 1. Overview

CodeDNA is a two-level source-file annotation standard for AI-assisted development.

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
- **Language agnostic**: comment-based format works in any language
- **Human readable**: developers benefit as much as AI agents

---

## 3. Level 1 — The Manifest Header

### 3.1 Placement

The Manifest Header **must be the first content in the file**. A shebang line (`#!/usr/bin/env python`) may appear on line 1; the header starts on line 2.

A blank line must follow the closing delimiter before the first import or code statement.

### 3.2 Format

```
# === CODEDNA:0.3 =============================================
# FILE: <filename>
# PURPOSE: <one-line description, max 15 words>
# CONTEXT_BUDGET: <always | normal | minimal>
# DEPENDS_ON: <file> → <symbol1>, <symbol2> | none
# EXPORTS: <symbol(signature)> → <return type>
# STYLE: <css framework>, <chart library> | none
# DB_TABLES: <table> (<col1>, <col2>) | none
# LAST_MODIFIED: <8-word max description of last change>
# ==============================================================
```

### 3.3 Fields

| Field | Required | Rule |
|---|---|---|
| `FILE` | ✅ | Exact filename including extension |
| `PURPOSE` | ✅ | ≤15 words, describes *what*, not *how* |
| `CONTEXT_BUDGET` | ✅ | `always` / `normal` / `minimal` — see §3.4 |
| `DEPENDS_ON` | ✅ | `file → func1, func2` or `none` |
| `EXPORTS` | ✅ | Public API with signatures |
| `STYLE` | — | CSS + chart library, or `none` |
| `DB_TABLES` | — | Tables and relevant columns, or `none` |
| `LAST_MODIFIED` | ✅ | ≤8 words; updated on every edit as first change |

### 3.4 CONTEXT_BUDGET Values

| Value | Semantics | Planner behavior |
|---|---|---|
| `always` | Core file — always needed | Include in every planning context |
| `normal` | Standard file | Include when relevant to the task |
| `minimal` | Utility / rarely changes | Skip unless explicitly referenced |

This field enables **Planner Manifest-Only Read mode** (§6): the planner reads only the first 12 lines of each file, uses `CONTEXT_BUDGET` to filter, and builds a full architectural map in as little as 60 tokens per file.

### 3.5 Examples by Language

**Python / Ruby / Shell**
```python
# === CODEDNA:0.3 ==============================================
# FILE: dashboard.py
# PURPOSE: Monthly revenue KPI dashboard with chart and table
# CONTEXT_BUDGET: always
# DEPENDS_ON: utils.py → calculate_kpi(), format_currency()
# EXPORTS: render(execute_query_func) → HTML string
# STYLE: tailwind, chart.js
# DB_TABLES: orders (month, revenue, cost)
# LAST_MODIFIED: added margin column to table
# ==============================================================
```

**JavaScript / TypeScript / Go / Rust**
```javascript
// === CODEDNA:0.3 =============================================
// FILE: authService.ts
// PURPOSE: JWT authentication and session management
// CONTEXT_BUDGET: always
// DEPENDS_ON: db.ts → getUser(), config.ts → JWT_SECRET
// EXPORTS: login(credentials) → Promise<Token>, verify(token) → User
// STYLE: none
// DB_TABLES: users (id, email, password_hash)
// LAST_MODIFIED: added refresh token rotation
// =============================================================
```

**SQL**
```sql
-- === CODEDNA:0.3 ============================================
-- FILE: monthly_revenue.sql
-- PURPOSE: Aggregated monthly revenue by category and region
-- CONTEXT_BUDGET: minimal
-- DEPENDS_ON: none
-- EXPORTS: (month, category, revenue, cost)
-- DB_TABLES: orders, order_items, products
-- LAST_MODIFIED: filtered out cancelled orders
-- ============================================================
```

---

## 4. Level 2 — Inline Hyperlinks

### 4.1 Motivation

AI agents operating in *sliding window* mode extract partial file content (e.g., lines 50–80) to reduce token consumption. This bypasses the Manifest Header entirely. Level 2 hyperlinks ensure that even a partial read delivers enough directional context.

### 4.2 Annotation Tags

| Tag | Semantics | Agent behavior |
|---|---|---|
| `@SEE: file → symbol` | Recommended context | Read when uncertain |
| `@REQUIRES-READ: file → symbol` | Mandatory prerequisite | MUST read before editing |
| `@MODIFIES-ALSO: file → symbol` | Cascade change required | MUST update that symbol too |

### 4.3 Placement

Annotations go **inside the function**, before the first executable line:

```python
def apply_discount(base_price: int, user_tier: str) -> float:
    # @REQUIRES-READ: config.py → MAX_DISCOUNT_ALLOWED
    # @REQUIRES-READ: db.py → UserSchema (valid values for user_tier)
    # @MODIFIES-ALSO: invoice.py → calculate_total()

    if user_tier == "premium":
        return base_price * 0.8
    return base_price
```

### 4.4 Inline Context Anchors

For individual lines with non-obvious constraints:

```python
BTN_COLOR = "#3B82F6"  # @SEE: style.css → --brand-primary (must stay in sync)
rows = execute_query(sql)  # @REQUIRES-READ: schema.sql → orders (column types)
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

Purely local computation variables (`i`, `tmp`, `acc`) do not need renaming.

---

## 6. Planner Manifest-Only Read Protocol

When an AI agent must plan edits across a multi-file codebase, it should:

1. Read only the **first 12 lines** of each file (the manifest)
2. Filter by `CONTEXT_BUDGET`:
   - Include `always` files unconditionally
   - Include `normal` files if they match the task domain
   - Skip `minimal` files unless explicitly referenced in `DEPENDS_ON`
3. Build a dependency graph from `DEPENDS_ON` and `EXPORTS`
4. Identify the **minimum set of files** that must be read in full
5. Load only those files for the edit phase

**Token cost:** ~60 tokens per file × N files = complete codebase map for planning.

---

## 7. AI Interaction Protocol

### 7.1 On READ (edit mode)
1. Parse the Manifest Header (Level 1)
2. Note `DEPENDS_ON` → must not break these
3. Note `EXPORTS` → must not rename or remove
4. Follow `@REQUIRES-READ` tags before writing

### 7.2 On WRITE (generate mode)
1. Generate the Manifest Header as the **first output block**
2. Add `@REQUIRES-READ` / `@SEE` / `@MODIFIES-ALSO` to cross-file functions
3. Apply Semantic Naming to data-carrying variables

### 7.3 On EDIT
1. **First change**: update `LAST_MODIFIED`
2. Follow all `@REQUIRES-READ` links before writing logic
3. After editing, cascade `@MODIFIES-ALSO` changes

---

## 8. Validation

Run `tools/validate_manifests.py` to check:
- Every file has a manifest header
- All required fields are present and non-empty
- `FILE` field matches the actual filename
- `DEPENDS_ON` symbols exist in the referenced files' `EXPORTS`
- `LAST_MODIFIED` is not empty

Pre-commit hook available in `tools/pre-commit`.

---

## 9. Versioning

Declared in the delimiter line:

```python
# === CODEDNA:0.3 =============================================
```

---

## Changelog

| Version | Date | Notes |
|---|---|---|
| 0.1 | 2026-03-16 | Initial draft — Level 1 Manifest Header |
| 0.2 | 2026-03-16 | Level 2 Inline Hyperlinks, biological model |
| 0.3 | 2026-03-16 | Level 3 Semantic Naming, CONTEXT_BUDGET field, Planner Manifest-Only Read protocol |
