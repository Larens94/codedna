---
description: Annotate all unannotated source files in the project with CodeDNA module headers. Uses your current Claude session — no API key required.
---

# /codedna:init $ARGUMENTS

Annotate every unannotated source file in the project with a CodeDNA module header.

If `$ARGUMENTS` is provided, treat it as the target path. Otherwise use the current working directory.

---

## Step 0 — Silent scan + present choices

### 0a — Auto-detect (silent, no output yet)

1. Scan the target directory for all source files. Skip: `vendor/`, `node_modules/`, `venv/`, `.venv/`, `__pycache__/`, `.git/`, `dist/`, `build/`, `migrations/`.
2. Detect extensions present: `.py`, `.php`, `.blade.php`, `.ts`, `.tsx`, `.js`, `.mjs`, `.go`, `.rs`, `.java`, `.kt`, `.rb`, `.cs`, `.vue`, `.svelte`
3. Count total files to annotate (exclude already-annotated files).
4. Check if CodeDNA CLI is installed: `python3 -c "import codedna_tool; print('ok')" 2>/dev/null`

### 0b — Present first choice: execution mode

Print this box and wait for the user's answer:

```
┌─────────────────────────────────────────────────┐
│ CodeDNA Init — <path>                           │
│ Languages detected: .php, .blade.php, .ts, .tsx │
│ Files to annotate: 230                          │
│                                                 │
│ How should I annotate?                          │
│                                                 │
│   [A] Use this Claude session                   │
│        Deep rules: via LLM, uses session tokens │
│        ~<estimate based on file count>          │
│                                                 │
│   [B] Use codedna CLI (tree-sitter + AST)  ✓   │
│        Fast structural pass, zero LLM cost      │
│        Requires: pip install git+https://github.com/Larens94/codedna.git │
│                                                 │
└─────────────────────────────────────────────────┘

Choice [A/B]:
```

If CLI is **not installed**, mark option B with `(not installed)` instead of `✓` and note it requires Python 3.11+.

**If user picks B but CLI is not installed:**
Do NOT silently fall back to A. Instead print:
```
CodeDNA CLI is required for option B. Install it with:

  pip install git+https://github.com/Larens94/codedna.git

Requires Python 3.11+. After installing, run /codedna:init again.
```
Stop here — do not proceed.

**If user picks B and CLI is installed:** go to Step 0c.

**If user picks A:** go to Step 0c.

### 0c — Present second choice: depth mode

```
┌─────────────────────────────────────────────────┐
│ What depth?                                     │
│                                                 │
│   [1] human  — minimal (exports + used_by only) │
│   [2] semi   — balanced (default, recommended)  │
│   [3] agent  — full protocol + semantic naming   │
│                                                 │
└─────────────────────────────────────────────────┘

Choice [1/2/3] (default: 2):
```

### 0d — Execute based on choices

**If user picked B (CLI):**
Run the CLI command and stream output:
```bash
python3 -m codedna_tool.cli init <path> --no-llm
```
Then run refresh to populate cross-file used_by:
```bash
python3 -m codedna_tool.cli refresh <path>
```
Print the summary from CLI output. **Done — skip Steps 1–4.**

**If user picked A (Claude session):** continue to Step 1.

---

## Step 1 — Discover unannotated files (Option A only)

Print:
```
CodeDNA Init
============
Target:       <path>
Mode:         <human|semi|agent>
Files found:  <N>
Already annotated: <N>
To annotate:  <N>

Proceeding to annotate <N> files...
```

If all files are already annotated, stop and print:
```
All files already annotated. Run /codedna:check for a full coverage report.
```

---

## Step 2 — Build used_by graph (Option A only)

Before annotating, read the import/require/use statements of ALL files to build the reverse dependency graph.

For each file A that imports file B:
- File B's `used_by:` must include `A → the_function_that_imports_it`

Language-specific imports:
- **PHP**: `use App\Models\User;` → resolve via PSR-4 (`App\` → `app/`)
- **TypeScript/JS**: `import { X } from './path'` or `require('./path')`
- **Python**: `from module import X` or `import module`
- **Go**: `import "package/path"`
- **Java/Kotlin**: `import com.package.Class;`
- **Ruby**: `require_relative 'path'`
- **Blade**: `@extends('layout')`, `@include('partial')` → resolve to view path

Do this in a single pass before writing anything.

---

## Step 3 — Annotate each file (Option A only)

For each unannotated file:

1. **Read the file** — full content.

2. **Extract exports** — public top-level symbols:
   - Python: `def name`, `class Name`, uppercase constants
   - PHP: `class`, `public function`, `interface`, `trait`, `enum`
   - TypeScript/JS: `export function`, `export class`, `export const`, `export default`
   - Go: uppercase-start identifiers
   - Rust: `pub fn`, `pub struct`, `pub enum`
   - Java/Kotlin: `public` methods and classes
   - Ruby: public methods
   - Blade/templates: `none`

3. **Fill used_by** from the graph built in Step 2. If no callers: `none`.

4. **Generate rules:** (skip if mode is `human`):
   - Write 1-3 **specific, actionable** constraints
   - Never vague ("handle errors gracefully" ❌)
   - If no constraint exists: `none`

5. **Build the annotation** in the correct language format:

**Python:**
```python
"""filename.py — <purpose ≤15 words>.

exports: fn1(arg) -> ReturnType | fn2(arg) -> ReturnType
used_by: caller.py → caller_fn
rules:   <constraint or none>
agent:   claude-opus-4-6 | anthropic | <YYYY-MM-DD> | codedna-init | initial CodeDNA annotation
"""
```

**PHP** (after `<?php`, using `//` comments — NOT PHPDoc):
```php
<?php
// UserController.php — Handles user CRUD endpoints.
//
// exports: UserController | UserController::index() | UserController::store(Request $request)
// used_by: routes/web.php
// rules:   must extend App\Http\Controllers\Controller
// agent:   claude-opus-4-6 | anthropic | <YYYY-MM-DD> | codedna-init | initial CodeDNA annotation
```

**Blade** (using `{{-- --}}` comments):
```blade
{{-- layout.blade.php — Base application layout.
--
-- exports: none
-- used_by: none
-- rules:   @yield('content') is required — child views must define this section
-- agent:   claude-opus-4-6 | anthropic | <YYYY-MM-DD> | codedna-init | initial CodeDNA annotation
--}}
```

**TypeScript/JS** (using `//` comments, before first import):
```typescript
// Dashboard.tsx — Main dashboard page component.
//
// exports: Dashboard
// used_by: app/routes.tsx → AppRoutes
// rules:   requires AuthContext — must be wrapped in AuthProvider
// agent:   claude-opus-4-6 | anthropic | <YYYY-MM-DD> | codedna-init | initial CodeDNA annotation
```

**Go** (before package declaration):
```go
// handler.go — HTTP request handlers for user endpoints.
//
// exports: HandleGetUser(w, r) | HandleCreateUser(w, r)
// used_by: router.go → SetupRoutes
// rules:   all handlers must call ValidateToken() before accessing request body
// agent:   claude-opus-4-6 | anthropic | <YYYY-MM-DD> | codedna-init | initial CodeDNA annotation
```

**Rust:**
```rust
//! handler.rs — HTTP request handlers.
//!
//! exports: handle_get_user(req) -> Response
//! used_by: router.rs → setup_routes
//! rules:   all handlers must validate auth token before processing
//! agent:   claude-opus-4-6 | anthropic | <YYYY-MM-DD> | codedna-init | initial CodeDNA annotation
```

**Java/Kotlin:**
```java
/**
 * UserService.java — Business logic for user operations.
 *
 * exports: UserService::findById(Long) | UserService::create(UserDTO)
 * used_by: UserController.java → handleGetUser
 * rules:   all mutations must be wrapped in @Transactional
 * agent:   claude-opus-4-6 | anthropic | <YYYY-MM-DD> | codedna-init | initial CodeDNA annotation
 */
```

**Ruby:**
```ruby
# user_service.rb — Business logic for user operations.
#
# exports: UserService#find_by_id | UserService#create
# used_by: users_controller.rb → index
# rules:   all DB queries must use .includes() to prevent N+1
# agent:   claude-opus-4-6 | anthropic | <YYYY-MM-DD> | codedna-init | initial CodeDNA annotation
```

**C#:**
```csharp
// UserService.cs — Business logic for user operations.
//
// exports: UserService.FindById(int) | UserService.Create(UserDTO)
// used_by: UserController.cs → GetUser
// rules:   all mutations must be wrapped in a transaction scope
// agent:   claude-opus-4-6 | anthropic | <YYYY-MM-DD> | codedna-init | initial CodeDNA annotation
```

6. **Write the file** with the annotation prepended.

7. Print progress:
```
[3/147] annotated: app/Models/User.php
[4/147] annotated: resources/views/app.blade.php
```

---

## Step 4 — Summary (Option A only)

```
CodeDNA Init Complete
=====================
Mode:       semi
Annotated:  147 files
Skipped:    0 (already annotated)
Errors:     0

Run /codedna:check to verify coverage.
Run /codedna:manifest to generate the .codedna project map.
```

---

## Important rules

- Never overwrite an existing CodeDNA annotation unless explicitly asked with `--force`
- Never annotate files in `vendor/`, `node_modules/`, `dist/`, `build/`, `migrations/`, `__pycache__/`, `.git/`
- The `agent:` field must use today's date in `YYYY-MM-DD` format
- Keep `exports:` concise — list only top-level public API, not every internal helper
- `used_by: none` is correct when no other file imports this one — do not omit the field
- For `mode: human` — omit `rules:` and `agent:` fields, only write `exports:` and `used_by:`
- For `mode: agent` — add `message:` field after `agent:` for inter-agent observations
- If user picks B but Python/CLI not installed — BLOCK and explain, never auto-fallback to A
