# CodeDNA v0.5 — Protocol for Claude Code

This project uses the **CodeDNA** annotation standard. Follow these rules on every file operation.

---

## Reading files

1. Read the **module docstring** at the top of every Python file before reading any code.
2. Parse `deps:` — these are symbols you **must never break**.
3. Parse `exports:` — these are symbols you **must never rename or remove** without explicit instruction.
4. For any function with a `Depends:` / `Rules:` docstring, read and respect those before writing logic.
5. After editing, apply every cascade mentioned in `Modifies:` or inline call-site comments.

## Writing new files

Every new Python source file **must begin** with a CodeDNA module docstring:

```python
"""filename.py — <what it does, ≤15 words>.

deps:    other_file.py → symbol | none
exports: public_function(arg) -> return_type
used_by: consumer_file.py → consumer_function
tables:  table_name(col1, col2) | none
rules:   <hard constraint agents must never violate>
"""
```

Field guide:

| Field | Required | Rule |
|---|---|---|
| First line | ✅ | `filename.py — <purpose ≤15 words>` |
| `deps:` | ✅ | `file → symbol` or `none` |
| `exports:` | ✅ | Public API with return type |
| `used_by:` | — | Who calls this file's exports |
| `tables:` | — | DB tables accessed |
| `rules:` | — | Hard constraints scoped to this file |

## Writing critical functions

For functions that cross file boundaries, add a Google-style docstring:

```python
def my_function(arg: type) -> return_type:
    """Short description.

    Depends: other_file.symbol — what contract it imposes.
    Rules:   What the agent MUST or MUST NOT do here.
    """
```

And annotate the exact dangerous call:

```python
    raw = get_data_from_source()  # includes X — filter Y below
```

## Editing files

1. **First change**: update `rules:` or add a `# modified: <what changed>` comment if the rules change.
2. Read all `Depends:` / `Rules:` fields in the docstring before writing logic.
3. After your edit, apply all cascade targets mentioned in `Modifies:` and call-site comments.
4. Never remove `exports:` symbols — they are contracts used by `deps:` in other files.

## Planning across multiple files

Use manifest-only read mode: read only the module docstring (first 8–12 lines) of each file to build an architectural map before deciding which files to open fully.

Filter by priority:
- File has `rules:` field mentioning the task domain → always include
- File appears in another file's `deps:` for this task → include
- Otherwise → skip unless referenced

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
