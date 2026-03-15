# CodeDNA v0.3 — GitHub Copilot Instructions

This codebase uses the CodeDNA annotation standard. Apply these rules in every suggestion.

## Manifest header (required in every file)

```
# === CODEDNA:0.3 =============================================
# FILE: filename.ext
# PURPOSE: what it does (max 15 words)
# CONTEXT_BUDGET: always | normal | minimal
# DEPENDS_ON: file → symbol | none
# EXPORTS: symbol(args) → return_type
# LAST_MODIFIED: last change description (max 8 words)
# ==============================================================
```

## On edit: always do these in order

1. Update `LAST_MODIFIED` first
2. Check `DEPENDS_ON` — don't break those symbols
3. Follow `@REQUIRES-READ` before writing logic
4. Update `@MODIFIES-ALSO` targets after your change

## On generate: always do these

1. Write manifest header before imports
2. Add `@REQUIRES-READ` to functions with cross-file deps
3. Use semantic names: `list_dict_orders_from_db = query(sql)` not `data = query(sql)`

## Exports are contracts

`EXPORTS` symbols must not be renamed or removed — other files declare them in `DEPENDS_ON`.
