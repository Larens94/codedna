# CodeDNA v0.3 — Protocol for Claude Code

This project uses the **CodeDNA** annotation standard. Follow these rules on every file operation.

---

## Reading files

1. Read the `# === CODEDNA:0.3` manifest header **before** reading any code.
2. Parse `DEPENDS_ON` — these are symbols you **must never break**.
3. Parse `EXPORTS` — these are symbols you **must never rename or remove** without explicit instruction.
4. Follow every `# @REQUIRES-READ: file → symbol` annotation before writing logic in that function.
5. After editing, follow every `# @MODIFIES-ALSO: file → symbol` and cascade the change.

## Writing new files

Every new source file **must begin** with a CodeDNA manifest header:

```
# === CODEDNA:0.3 =============================================
# FILE: <exact filename with extension>
# PURPOSE: <what it does, max 15 words>
# CONTEXT_BUDGET: <always | normal | minimal>
# DEPENDS_ON: <file → symbol, symbol> | none
# EXPORTS: <symbol(args) → return_type>
# STYLE: <css-framework, chart-lib> | none
# DB_TABLES: <table (col1, col2)> | none
# LAST_MODIFIED: <max 8 words describing last change>
# ==============================================================
```

**CONTEXT_BUDGET rules:**
- `always` — core file, always include in planning context
- `normal` — standard file, include when relevant
- `minimal` — utility file, skip unless directly referenced

## Editing files

1. **First change**: update `LAST_MODIFIED` in the manifest header.
2. Read all `@REQUIRES-READ` links before writing logic.
3. After your edit, apply all `@MODIFIES-ALSO` changes in the same response.
4. Never remove `EXPORTS` symbols — they are contracts used by `DEPENDS_ON` in other files.

## Planning across multiple files

Use manifest-only read mode: read only the first 12–15 lines (the manifest) of each file to build an architectural map before deciding which files to open fully.

Filter by `CONTEXT_BUDGET`:
- `always` → always include
- `normal` → include if relevant to task
- `minimal` → skip unless referenced in `DEPENDS_ON`

## Inline hyperlink tags

| Tag | Meaning |
|---|---|
| `@SEE: file → symbol` | Read this if uncertain |
| `@REQUIRES-READ: file → symbol` | Read BEFORE writing any logic here |
| `@MODIFIES-ALSO: file → symbol` | After editing this, update that symbol too |

## Semantic naming convention

For data-carrying variables, use: `<type>_<shape>_<domain>_<origin>`

```python
# ✅ CodeDNA style
list_dict_users_from_db = get_users()
str_html_dashboard_rendered = render(query_fn)
int_cents_price_from_request = request.json["price"]

# ❌ avoid
data = get_users()
result = render(query_fn)
price = request.json["price"]
```
