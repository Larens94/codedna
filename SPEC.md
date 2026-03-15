# CodeDNA — Technical Specification

**Version:** 0.2  
**Status:** Draft  
**Language:** Agnostic

---

## 1. Overview

CodeDNA is a two-level source-file annotation standard for AI-assisted development.

**Level 1 — The Manifest Header (Macro-Context):** A structured comment block at the top of every file describing the file's purpose, dependencies, public API, style conventions, and edit history.

**Level 2 — Inline Hyperlinks (Micro-Context):** Semantic annotations embedded at the function and variable level, enabling AI agents to navigate the codebase even when reading only partial file content via sliding windows.

Together, they make every code fragment self-sufficient: an AI extracting any part of a CodeDNA file finds enough context to act correctly without external lookup.

---

## 2. Goals

- **Zero token overhead**: context lives in the file, not the prompt
- **Zero drift**: annotations are co-located with what they describe
- **Zero retrieval latency**: no vector DB, no network call
- **Sliding-window safe**: Level 2 hyperlinks guide agents that skip the header
- **Language agnostic**: comment-based format works in any language
- **Human readable**: developers benefit as much as AI agents

---

## 3. Level 1 — The Manifest Header

### 3.1 Placement

The Manifest Header **must be the first content in the file**. It is placed before any imports, declarations, or code. A shebang line (`#!/usr/bin/env python`) may appear on line 1; the header starts on line 2.

A blank line must follow the closing delimiter before the first import or code statement.

### 3.2 Format

```
# ==============================================================
# FILE: <filename>
# PURPOSE: <one-line description>
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
| `DEPENDS_ON` | ✅ | `file → func1, func2` or `none` |
| `EXPORTS` | ✅ | Public API with signatures |
| `STYLE` | — | CSS + chart library, or `none` |
| `DB_TABLES` | — | Tables and relevant columns, or `none` |
| `LAST_MODIFIED` | ✅ | ≤8 words; updated on every edit as first change |

### 3.4 Examples by Language

**Python / Ruby / Shell**
```python
# ==============================================================
# FILE: dashboard.py
# PURPOSE: Monthly revenue KPI dashboard with chart and table
# DEPENDS_ON: utils.py → calculate_kpi(), format_currency()
# EXPORTS: render(execute_query_func) → HTML string
# STYLE: tailwind, chart.js
# DB_TABLES: orders (month, revenue, cost)
# LAST_MODIFIED: added margin column to table
# ==============================================================
```

**JavaScript / TypeScript / Go / Rust**
```javascript
// ==============================================================
// FILE: authService.ts
// PURPOSE: JWT authentication and session management
// DEPENDS_ON: db.ts → getUser(), config.ts → JWT_SECRET
// EXPORTS: login(credentials) → Promise<Token>, verify(token) → User
// STYLE: none
// DB_TABLES: users (id, email, password_hash)
// LAST_MODIFIED: added refresh token rotation
// ==============================================================
```

**SQL**
```sql
-- ==============================================================
-- FILE: monthly_revenue.sql
-- PURPOSE: Aggregated monthly revenue by category and region
-- DEPENDS_ON: none
-- EXPORTS: (month, category, revenue, cost)
-- DB_TABLES: orders, order_items, products
-- LAST_MODIFIED: filtered out cancelled orders
-- ==============================================================
```

---

## 4. Level 2 — Inline Hyperlinks

### 4.1 Motivation

AI agents operating in *sliding window* mode extract partial file content (e.g., lines 50–80) to reduce token consumption. This bypasses the Manifest Header entirely. Level 2 hyperlinks ensure that even a partial read delivers enough directional context.

### 4.2 Annotation Tags

| Tag | Semantics | Agent behavior |
|---|---|---|
| `@SEE: file → symbol` | Recommended context | Read if uncertain |
| `@REQUIRES-READ: file → symbol` | Mandatory prerequisite | MUST read before editing |
| `@MODIFIES-ALSO: file → symbol` | Cascade change required | MUST update that symbol too |

### 4.3 Placement Rules

Hyperlink annotations are placed **immediately inside the function or block they govern**, before the first executable line.

```python
def apply_discount(base_price: int, user_tier: str) -> float:
    # @REQUIRES-READ: config.py → MAX_DISCOUNT_ALLOWED (must not exceed this limit)
    # @REQUIRES-READ: db.py → UserSchema (valid values for user_tier)
    # @MODIFIES-ALSO: invoice.py → calculate_total() (recalculates if discount changes)

    if user_tier == "premium":
        return base_price * 0.8  # cast to int done in main.py
    return base_price
```

### 4.4 Inline Context Anchors

For individual lines with non-obvious constraints, use a trailing inline comment:

```python
BTN_COLOR = "#3B82F6"  # @SEE: style.css → --brand-primary (must stay in sync)
```

```python
rows = execute_query_func(sql)  # @REQUIRES-READ: schema.sql → orders (column types)
```

### 4.5 Semantic Variable Naming

Variables that carry structural information about their content reduce the agent's need to trace origins:

```python
# Standard — agent must trace back to understand the shape
data = get_users()

# CodeDNA — agent immediately knows type, source, shape
list_dict_users_from_db = get_users()
```

This is not mandatory but strongly recommended for data-carrying variables that flow across function boundaries.

---

## 5. The Biological Model

CodeDNA is designed around the holographic principle: **every fragment contains the whole**.

| Biology | CodeDNA |
|---|---|
| Genome | Complete set of project rules and conventions |
| Chromosome | A source file with its Manifest Header |
| Gene | A fully annotated function |
| Genetic Marker | An inline hyperlink (`@REQUIRES-READ`, `@SEE`) |

Cutting a hologram in half gives two complete images. Extracting 10 lines from a CodeDNA file gives 10 lines that still carry enough structure to navigate safely.

---

## 6. AI Interaction Protocol

### 6.1 On READ (edit mode)

1. Parse the Manifest Header first (Level 1)
2. Note `DEPENDS_ON` → constraints on what must not break
3. Note `EXPORTS` → symbols that must not be renamed or removed
4. At each annotated function, follow `@REQUIRES-READ` links before writing

### 6.2 On WRITE (generate mode)

1. Generate the Manifest Header as the **first output block**
2. Add `@REQUIRES-READ` / `@SEE` / `@MODIFIES-ALSO` to every function that has cross-file dependencies
3. Use descriptive variable names for data-carrying variables

### 6.3 On EDIT

1. **First change**: update `LAST_MODIFIED` in the Manifest Header
2. Follow all `@REQUIRES-READ` links before writing any logic
3. After editing, check `@MODIFIES-ALSO` links and cascade changes

---

## 7. Versioning

The spec version may be declared in the delimiter line:

```python
# === CODEDNA:0.2 =============================================
```

---

## Changelog

| Version | Date | Notes |
|---|---|---|
| 0.1 | 2026-03-16 | Initial draft — Level 1 Manifest Header |
| 0.2 | 2026-03-16 | Added Level 2 Inline Hyperlinks, biological model, semantic naming |
