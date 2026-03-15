# Beacon Framework — Technical Specification

**Version:** 0.1  
**Status:** Draft  
**Language:** Agnostic

---

## 1. Overview

The Beacon Header is a structured comment block placed at the very top of every source file. It provides a compact, machine-readable description of the file's purpose, dependencies, public API, style conventions, and edit history.

Its primary consumer is an AI model. Secondary consumers are human developers.

---

## 2. Goals

- **Zero token overhead**: context lives in the file, not the prompt
- **Zero drift**: the header is co-located with what it describes
- **Zero retrieval latency**: no lookup, no embedding, no network call
- **Language agnostic**: comment-based format works in any language
- **Human readable**: a developer reading the file gets the same benefit

---

## 3. Header Format

### 3.1 Structure

```
DELIMITER
FIELD: value
...
DELIMITER
```

The delimiter is a line of `=` characters (≥20), prefixed by the language's single-line comment token.

### 3.2 Python / Ruby / Shell

```python
# ==============================================================
# FILE: dashboard.py
# PURPOSE: Monthly KPI dashboard with revenue chart and table
# DEPENDS_ON: utils.py → calculate_kpi(), format_currency()
# EXPORTS: render(execute_query_func) → HTML string
# STYLE: tailwind, chart.js
# DB_TABLES: orders (month, revenue, cost)
# LAST_MODIFIED: added margin percentage column
# ==============================================================
```

### 3.3 JavaScript / TypeScript / Go / Rust / C

```javascript
// ==============================================================
// FILE: authService.ts
// PURPOSE: JWT authentication and session management
// DEPENDS_ON: db.ts → getUser(), models/User.ts → UserSchema
// EXPORTS: login(credentials) → Promise<Token>, verify(token) → User
// STYLE: none (pure logic)
// DB_TABLES: users (id, email, password_hash, last_login)
// LAST_MODIFIED: added refresh token rotation
// ==============================================================
```

### 3.4 SQL

```sql
-- ==============================================================
-- FILE: monthly_revenue.sql
-- PURPOSE: Aggregated monthly revenue by category and region
-- DEPENDS_ON: none
-- EXPORTS: result_set (month, category, region, revenue, cost)
-- STYLE: BigQuery dialect
-- DB_TABLES: orders, order_items, products, regions
-- LAST_MODIFIED: filtered out cancelled orders
-- ==============================================================
```

---

## 4. Field Specification

### 4.1 FILE *(required)*

Exact filename including extension. Must match the actual filename on disk.

```
# FILE: dashboard.py
```

Used by orchestrators that read only the header (first 12 lines) to build a file map without loading the full file.

### 4.2 PURPOSE *(required)*

One line, maximum 15 words. Describes **what** the file does, not **how**.

```
# PURPOSE: Monthly KPI dashboard with revenue chart and table
```

**Good:** `Monthly KPI dashboard with revenue chart and table`  
**Bad:** `Uses Chart.js to render a canvas element inside a div`

### 4.3 DEPENDS_ON *(required)*

Comma-separated list of external dependencies with the symbol(s) used from each.

```
# DEPENDS_ON: utils.py → calculate_kpi(), format_currency()
```

Multiple dependencies:
```
# DEPENDS_ON: utils.py → calculate_kpi(), db.py → get_connection()
```

No dependencies:
```
# DEPENDS_ON: none
```

This field is the primary guard against breaking cross-file contracts. AI models read it before making any changes.

### 4.4 EXPORTS *(required)*

Public-facing API: functions, classes, or constants that other files import from this one. Include signatures.

```
# EXPORTS: render(execute_query_func) → HTML string
```

Multiple exports:
```
# EXPORTS: calculate_kpi(rows) → dict, format_currency(n) → str
```

### 4.5 STYLE *(optional)*

UI/CSS conventions used in the file. Helps the AI maintain visual consistency across edits.

```
# STYLE: tailwind, chart.js, dark-mode
```

For non-UI files:
```
# STYLE: none
```

### 4.6 DB_TABLES *(optional)*

Database tables accessed by this file, with the relevant columns.

```
# DB_TABLES: orders (month, revenue, cost), customers (id, name)
```

No DB access:
```
# DB_TABLES: none
```

### 4.7 LAST_MODIFIED *(required)*

A brief description of the most recent change, maximum 8 words. **Must be updated on every edit**, as the first change an AI model applies.

```
# LAST_MODIFIED: added margin percentage column
```

This field doubles as an inline edit log — each change overwrites the previous. For a full history, use version control.

---

## 5. Placement Rules

- The Beacon Header **must be the first thing in the file**
- No shebang lines, encoding declarations, or other comments before it
  - Exception: shebang (`#!/usr/bin/env python`) may appear on line 1, header starts on line 2
- The header must be followed by a blank line before the first import or code statement
- No inline code within the header block

---

## 6. AI Interaction Protocol

### 6.1 On READ (edit mode)

The AI model **must** read the Beacon Header before reading the file body. Specifically:

1. Parse `DEPENDS_ON` → know what must not be broken
2. Parse `EXPORTS` → know what the file exposes (do not rename or remove)
3. Parse `PURPOSE` → understand scope of expected changes
4. Parse `STYLE` → maintain visual conventions

### 6.2 On WRITE (generate mode)

The AI model **must** generate the header as the first output block, before any imports or code.

### 6.3 On EDIT

The first change applied must update `LAST_MODIFIED`. This is non-negotiable.

---

## 7. Versioning

The spec version is declared as a comment in the header delimiter line (optional):

```python
# === BEACON:0.1 ================================================
```

---

## 8. Validation

A compliant file satisfies:
- Header is present and starts at line 1 (or line 2 after shebang)
- All required fields (`FILE`, `PURPOSE`, `DEPENDS_ON`, `EXPORTS`, `LAST_MODIFIED`) are present
- `FILE` matches the actual filename
- `LAST_MODIFIED` is not empty

Validation can be performed with a simple regex or AST comment scan. A reference validator will be published in `tools/`.

---

## 9. Non-Goals

- Beacon is **not** a replacement for docstrings or inline comments
- Beacon is **not** a build system or module resolver
- Beacon does **not** enforce API contracts at runtime — it is documentation
- Beacon does **not** require any runtime library

---

## Changelog

| Version | Date | Notes |
|---|---|---|
| 0.1 | 2026-03-16 | Initial draft |
