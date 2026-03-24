---
description: Annotate all unannotated source files in the project with CodeDNA module headers. Uses your current Claude session — no API key required.
---

# /codedna:init $ARGUMENTS

Annotate every unannotated source file in the project with a CodeDNA module header.

If `$ARGUMENTS` is provided, treat it as the target path. Otherwise use the current working directory.

---

## Step 1 — Discover unannotated files

Scan all source files under the target path. Skip: `venv/`, `.venv/`, `node_modules/`, `__pycache__/`, `.git/`, `dist/`, `build/`, `migrations/`.

Supported extensions: `.py`, `.ts`, `.tsx`, `.js`, `.mjs`, `.go`, `.rs`, `.java`, `.rb`

A file is **already annotated** if its first meaningful block contains all three fields: `exports:`, `used_by:`, `rules:`.

Print a summary before starting:
```
CodeDNA Init
============
Target:       ./
Files found:  42
Already annotated: 18
To annotate:  24

Proceeding to annotate 24 files...
```

If all files are already annotated, stop and print:
```
All files already annotated. Run /codedna:check for a full coverage report.
```

---

## Step 2 — Build used_by graph

Before annotating, read the import/require/use statements of ALL files to build the reverse dependency graph. This is needed to fill the `used_by:` field correctly.

For each file A that imports file B:
- File B's `used_by:` must include A → the_function_that_imports_it

Do this in a single pass before writing anything.

---

## Step 3 — Annotate each file

For each unannotated file, in order:

1. **Read the file** — full content.

2. **Extract exports** — identify all public top-level symbols:
   - Python: public functions (`def name`), classes (`class Name`), uppercase constants
   - TypeScript/JS: exported functions, classes, constants (`export function`, `export class`, `export const`)
   - Go: exported identifiers (start with uppercase)
   - Rust: `pub fn`, `pub struct`, `pub enum`
   - Java: `public` methods and classes
   - Ruby: public methods (not prefixed with `private`/`protected`)

3. **Fill used_by** — from the graph built in Step 2. Format: `caller_file.py → caller_function`. If no callers: `none`.

4. **Generate rules:** — read the file code and write 1-3 hard constraints a future agent must know before editing this file. Focus on:
   - Non-obvious return values or side effects
   - Required call order or preconditions
   - Global state mutations
   - Security or data integrity constraints
   - If no meaningful constraint exists: write `none`

5. **Build the annotation block** using the language-specific syntax:

**Python:**
```python
"""filename.py — <purpose ≤15 words>.

exports: fn1(arg) -> ReturnType | fn2(arg) -> ReturnType
used_by: caller.py → caller_fn
rules:   <constraint or none>
agent:   claude-sonnet-4-6 | <YYYY-MM-DD> | initial CodeDNA annotation
"""
```

**TypeScript/JS** (before first import):
```typescript
/**
 * filename.ts — <purpose ≤15 words>.
 *
 * exports: fn1(arg): ReturnType | fn2(arg): ReturnType
 * used_by: caller.ts → callerFn
 * rules:   <constraint or none>
 * agent:   claude-sonnet-4-6 | <YYYY-MM-DD> | initial CodeDNA annotation
 */
```

**Go** (before package declaration):
```go
// filename.go — <purpose ≤15 words>.
//
// exports: Fn1(arg Type) ReturnType | Fn2(arg Type) ReturnType
// used_by: caller.go → callerFn
// rules:   <constraint or none>
// agent:   claude-sonnet-4-6 | <YYYY-MM-DD> | initial CodeDNA annotation
```

**Rust** (inner doc at file top):
```rust
//! filename.rs — <purpose ≤15 words>.
//!
//! exports: fn1(arg: Type) -> ReturnType | fn2(arg: Type) -> ReturnType
//! used_by: caller.rs → caller_fn
//! rules:   <constraint or none>
//! agent:   claude-sonnet-4-6 | <YYYY-MM-DD> | initial CodeDNA annotation
```

**Java** (Javadoc before class, after package):
```java
/**
 * ClassName.java — <purpose ≤15 words>.
 *
 * exports: method1(arg): ReturnType | method2(arg): ReturnType
 * used_by: CallerClass.java → callerMethod
 * rules:   <constraint or none>
 * agent:   claude-sonnet-4-6 | <YYYY-MM-DD> | initial CodeDNA annotation
 */
```

6. **Write the file** with the annotation prepended (or replacing the existing non-CodeDNA docstring if present).

7. Print progress after each file:
```
[3/24] annotated: src/api/routes.py
[4/24] annotated: src/utils/format.ts
```

---

## Step 4 — Summary

After all files are annotated, print:

```
CodeDNA Init Complete
=====================
Annotated:  24 files
Skipped:    18 (already annotated)
Errors:     0

Run /codedna:check to verify coverage.
```

If any files could not be parsed or written, list them under `Errors:`.

---

## Important rules

- Never overwrite an existing CodeDNA annotation unless explicitly asked with `--force`
- Never annotate test files (`test_*.py`, `*.test.ts`, `*.spec.ts`) unless they are the explicit target
- The `agent:` field must use today's date in `YYYY-MM-DD` format
- Keep `exports:` concise — list only top-level public API, not every internal helper
- `used_by: none` is correct when no other file imports this one — do not omit the field
