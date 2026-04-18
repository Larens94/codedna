---
description: CodeDNA coverage report — find unannotated files and stale used_by references
---

# /codedna:check

Perform a CodeDNA compliance check on the current project. Do the following:

1. **Find all source files** in the project (`.py`, `.php`, `.blade.php`, `.ts`, `.tsx`, `.js`, `.go`, `.java`, `.kt`, `.rb`, `.rs`, `.cs`) — exclude `vendor/`, `node_modules/`, `venv/`, `.venv/`, `.git/`, `__pycache__/`, `dist/`, `build/`, `migrations/`.

2. **Check each file** for a CodeDNA module annotation:
   - Python: first token must be a string literal (module docstring) containing `exports:`, `used_by:`, and `rules:` fields.
   - Other languages: first comment block must contain `exports:`, `used_by:`, `rules:` fields.

3. **Check for stale `used_by:` references**: for every `used_by:` entry in every annotated file, verify the referenced file exists. Flag any references to files that no longer exist.

4. **Check for missing `agent:` field** in annotated Python files.

5. **Output a report** in this format:

```
CodeDNA Coverage Report
=======================
Total files:        <N>
Annotated:          <N> (<pct>%)
Unannotated:        <N>
Stale used_by refs: <N>

Unannotated files:
  - path/to/file.py
  - path/to/file.ts

Stale used_by references:
  - utils/format.py → used_by references deleted_file.py (file not found)
```

If all files are annotated and no stale references exist, output:
```
CodeDNA: all <N> files annotated, no stale references. Coverage: 100%
```
