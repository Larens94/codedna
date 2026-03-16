# CodeDNA v0.5 — GitHub Copilot Instructions

This codebase uses the CodeDNA annotation standard (v0.5 — Python-native format). Apply these rules in every suggestion.

## Module header (required in every Python file)

Every file must begin with a module docstring:

```python
"""filename.py — <what it does, ≤15 words>.

deps:    other_file.py → symbol | none
exports: public_function(arg) -> return_type
used_by: consumer_file.py → consumer_function
tables:  table_name(col1, col2) | none
rules:   <hard constraint agents must never violate>
"""
```

## Function docstring (required for cross-file functions)

```python
def critical_function(arg: type) -> return_type:
    """Short description.

    Depends: other_file.symbol — contract it imposes.
    Rules:   What MUST or MUST NOT happen here.
    """
    raw = get_external_data()  # includes X — filter Y below
```

## On edit: always do these in order

1. Check `rules:` in the module docstring — never violate these constraints
2. Check `deps:` — don't break those symbols
3. Read `Depends:` / `Rules:` in any function docstring before writing logic
4. Add call-site comment at any dangerous call: `# includes X — filter Y below`

## On generate: always do these

1. Write module docstring before imports
2. Add Google-style function docstring to functions with cross-file deps
3. Use semantic names: `list_dict_orders_from_db = query(sql)` not `data = query(sql)`

## Exports are contracts

`exports:` symbols must not be renamed or removed — other files declare them in `deps:`.
