---
description: CodeDNA impact analysis — show the full dependency chain for a file before editing or refactoring
---

# /codedna:impact $ARGUMENTS

Perform a cascade impact analysis for the file at path `$ARGUMENTS`.

If no argument is provided, ask: "Which file do you want to analyze? Provide the path relative to the project root."

Steps:

1. **Read the target file's module docstring** (first 15 lines only). Extract its `exports:` and `used_by:` fields.

2. **For each file listed in `used_by:`**, read only its module docstring and extract its own `used_by:` (to find second-level callers).

3. **Build the cascade chain** — stop at 3 levels deep to avoid infinite loops.

4. **Output the impact tree**:

```
Impact Analysis: utils/format.py
=================================
Direct callers (Level 1):
  - api/routes.py
      exports: revenue_route(req) -> Response
      rules:   all routes require auth middleware
  - views/dashboard.py
      exports: render(ctx) -> str
      rules:   none

Second-level callers (Level 2):
  - workers/report.py  (calls api/routes.py)
      exports: generate(period) -> None

Cascade summary:
  Editing utils/format.py may affect 3 files.
  Check rules: in api/routes.py before changing format_currency signature.
```

5. If the file has no `used_by:` entries or is not annotated, output:
```
utils/new_file.py has no used_by: entries — no cascade impact detected.
Note: file may not be annotated yet. Run /codedna:check to verify.
```

Use this command before any refactor, signature change, or deletion.
