---
description: CodeDNA architectural map — read all module docstrings and return the full project dependency graph in one pass
---

# /codedna:manifest

Build a complete architectural map of the project by reading only the module docstrings (first 10-15 lines) of every source file. Do NOT read full file contents.

1. **Scan all source files** (exclude `venv/`, `node_modules/`, `.git/`, `__pycache__/`, `dist/`, `build/`).

2. **For each file**, extract only the module-level annotation fields:
   - `exports:` — public API
   - `used_by:` — reverse dependency graph
   - `rules:` — hard constraints
   - `agent:` — last session entry

3. **Output a structured map** grouped by directory:

```
CodeDNA Architectural Map
=========================

api/routes.py
  exports:  revenue_route(req) -> Response
  used_by:  workers/report.py → generate
  rules:    all routes require auth middleware before handler
  agent:    claude-sonnet-4-6 | 2026-03-20 | added rate limiting

utils/format.py
  exports:  format_currency(n) -> str | format_date(d) -> str
  used_by:  api/routes.py → revenue_route | views/dashboard.py → render
  rules:    format_currency uses locale from request context, never hardcode

[unannotated]
  migrations/001.py
  new_feature.py
```

4. After the map, output a one-line summary:
```
<N> files mapped | <N> unannotated | <N> dependency edges
```

This command is designed to replace 10-20 individual file reads at the start of a session. Use it as the first step before any multi-file task.
