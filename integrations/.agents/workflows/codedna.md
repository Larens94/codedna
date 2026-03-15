---
description: CodeDNA v0.3 — how to read, write, and edit files in this project
---

# CodeDNA v0.3 Protocol

This project uses CodeDNA. Every source file carries its own context.

## Reading a file

1. Read the `# === CODEDNA:0.3` manifest header first (first 12–15 lines)
2. Note `DEPENDS_ON` → symbols you must not break
3. Note `EXPORTS` → symbols you must not rename or remove
4. `CONTEXT_BUDGET: always` = always include in planning; `normal` = when relevant; `minimal` = skip unless referenced

## Editing a file

1. Update `LAST_MODIFIED` as your very first change
2. For each function with `@REQUIRES-READ`: read the target before writing logic
3. For each function with `@MODIFIES-ALSO`: apply that change too, in the same session
4. Do not change `EXPORTS` signatures without explicit user instruction

## Creating a file

Every new source file must start with:

```
# === CODEDNA:0.3 =============================================
# FILE: <exact filename.ext>
# PURPOSE: <what it does, ≤15 words>
# CONTEXT_BUDGET: <always | normal | minimal>
# DEPENDS_ON: <file → symbol, symbol> | none
# EXPORTS: <symbol(args) → return_type>
# STYLE: <css-framework, chart-lib> | none
# DB_TABLES: <table (col1, col2)> | none
# LAST_MODIFIED: <≤8 words describing first commit>
# ==============================================================
```

## Planning across a codebase

Read only the manifest (first 12 lines) of each file. Build a dependency graph from DEPENDS_ON/EXPORTS. Load only the relevant files in full.

## Inline hyperlink tags

```python
def my_function():
    # @REQUIRES-READ: other.py → symbol_name  (must read before writing)
    # @MODIFIES-ALSO: another.py → fn()        (update after editing this)
    # @SEE: config.py → CONSTANT              (read if uncertain)
```

## Semantic variable naming

```python
# CodeDNA style — type + shape + domain + origin
list_dict_orders_from_db = db.query(sql)
str_html_view_rendered = render(query_fn)
int_cents_price_from_request = req.json["price"]
```
