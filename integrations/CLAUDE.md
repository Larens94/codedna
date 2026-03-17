# CodeDNA v0.6 — Protocol for Claude Code

This project uses the **CodeDNA** annotation standard. Follow these rules on every file operation.

---

## Reading files

1. Read the **module docstring** at the top of every Python file before reading any code.
2. Parse `exports:` — these are symbols you **must never rename or remove** without explicit instruction.
3. Parse `used_by:` — these are callers that will be affected by your changes.
4. Parse `rules:` — hard constraints for every edit in this file; read **before writing any logic**.
5. For any function with a `Rules:` docstring, read and respect those before writing logic.

## Writing new files

Every new Python source file **must begin** with a CodeDNA module docstring:

```python
"""filename.py — <what it does, ≤15 words>.

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
| `exports:` | ✅ | Public API with return type |
| `used_by:` | ✅ | Who calls this file's exports |
| `tables:` | — | DB tables accessed |
| `rules:` | — | Hard constraints scoped to this file |

## Writing critical functions

For functions with non-obvious domain constraints, add a `Rules:` docstring:

```python
def my_function(arg: type) -> return_type:
    """Short description.

    Rules:   What the agent MUST or MUST NOT do here.
    """
```

## Editing files

1. **First step**: re-read `rules:` and the `Rules:` of the function you are editing.
2. Apply all file-level constraints before writing.
3. After editing, check `used_by:` and `cascade:` targets.
4. Never remove `exports:` symbols — they are contracts used by other files.
5. If you discover a constraint or fix a bug, add a `Rules:` annotation for the next agent.

## Planning across multiple files

Use manifest-only read mode: read only the module docstring (first 8–12 lines) of each file to build an architectural map before deciding which files to open fully.

Filter by priority:
- File has `used_by:` mentioning the file you're editing → always include
- File has `rules:` field mentioning the task domain → always include
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
