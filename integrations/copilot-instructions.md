# CodeDNA v0.7 — GitHub Copilot Instructions

This codebase uses the CodeDNA communication protocol (v0.7). Apply these rules in every suggestion.

## Module header (required in every Python file)

Every file must begin with a module docstring:

```python
"""filename.py — <what it does, ≤15 words>.

exports: public_function(arg) -> return_type
used_by: consumer_file.py → consumer_function
rules:   <hard constraint agents must never violate>
"""
```

## Function-level Rules (for critical functions)

```python
def critical_function(arg: type) -> return_type:
    """Short description.

    Rules:   What MUST or MUST NOT happen here.
    """
```

## On edit: always do these in order

1. Check `rules:` in the module docstring — never violate these constraints
2. Check `used_by:` — these callers will be affected by your changes
3. Read `Rules:` in any function docstring before writing logic
4. If you discover a constraint, add a `Rules:` annotation for the next agent

## On generate: always do these

1. Write module docstring before imports (with `exports:`, `used_by:`, `rules:`)
2. Add `Rules:` docstring to functions with non-obvious domain constraints
3. Use semantic names: `list_dict_orders_from_db = query(sql)` not `data = query(sql)`

## Exports are contracts

`exports:` symbols must not be renamed or removed — other files depend on them (check `used_by:`).
