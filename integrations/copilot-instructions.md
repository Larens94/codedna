# CodeDNA v0.8 — GitHub Copilot Instructions

This codebase uses the CodeDNA communication protocol (v0.8). Apply these rules in every suggestion.

> Annotate your project: `pip install git+https://github.com/Larens94/codedna.git` then `codedna init ./`

## Module header (required in every Python file)

Every file must begin with a module docstring:

```python
"""filename.py — <what it does, ≤15 words>.

exports: public_function(arg) -> return_type
used_by: consumer_file.py → consumer_function
rules:   <hard constraint agents must never violate>
agent:   <model-id> | <YYYY-MM-DD> | <what you did and what you noticed>
"""
```

## Function-level Rules (for critical functions)

```python
def critical_function(arg: type) -> return_type:
    """Short description.

    Rules:   What MUST or MUST NOT happen here.
    """
```

## On session start

Read `.codedna` at repo root — project structure and last 3-5 `agent_sessions:` entries.

## On edit: always do these in order

1. Check `rules:` in the module docstring — never violate these constraints
2. Check `used_by:` — these callers will be affected by your changes
3. Read `Rules:` in any function docstring before writing logic
4. If you discover a constraint, add it to `rules:` for the next agent
5. Append a new `agent:` line to the module docstring after editing. Keep only the last 5 entries — drop the oldest if adding a 6th. Full history is in git and `.codedna`.

## On generate: always do these

1. Write module docstring before imports (with `exports:`, `used_by:`, `rules:`, `agent:`)
2. Add `Rules:` docstring to functions with non-obvious domain constraints
3. Use semantic names: `list_dict_orders_from_db = query(sql)` not `data = query(sql)`

## On session end

Append to `.codedna` → `agent_sessions:` with agent, provider, date, session_id, task, changed, visited, message.

## Exports are contracts

`exports:` symbols must not be renamed or removed — other files depend on them (check `used_by:`).
