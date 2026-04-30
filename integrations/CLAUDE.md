# CodeDNA v0.9 — Protocol for Claude Code

This project uses the **CodeDNA** in-source communication protocol. Follow these rules on every file operation.

## Annotate your project (CLI)

```bash
pipx install git+https://github.com/Larens94/codedna.git   # isolated install (avoids global env conflicts)

codedna init .           # annotates all detected languages (auto-detects PHP, TS, Go, etc.)
codedna init . --no-llm  # free — structural only, no API key needed
codedna check .          # coverage report, no changes
```

For LLM-powered `rules:` annotations:

```bash
pipx install 'codedna[anthropic]' && export ANTHROPIC_API_KEY=sk-...
codedna init .

# Or with a local model (free, no API key):
pipx install 'codedna[litellm]'
codedna init . --model ollama/llama3
```

> **Why pipx?** It creates an isolated venv per tool, so codedna's transitive
> dependencies (e.g. via `[litellm]`) don't conflict with packages already
> installed in your global Python environment (issue #8). `uv tool install`
> works identically. If you prefer raw `pip`, run it inside a project venv.

---

## Annotation format by language

The format adapts to the language. Never use Python docstrings in non-Python files.

**Python / Ruby** — module docstring:
```python
"""revenue.py — Monthly revenue aggregation.

exports: monthly_revenue(year, month) -> dict
used_by: api/reports.py → revenue_route
related: billing/currency.py — shares multi-currency conversion logic
rules:   get_invoices() returns ALL tenants — MUST filter is_suspended() before sum
agent:   claude-sonnet-4-6 | anthropic | 2026-04-15 | s_001 | initial implementation
"""
```

**PHP / TypeScript / Go / Java / Kotlin / Ruby / Rust / C#** — `//` block comment at file top:
```php
<?php
// UserController.php — Handles user CRUD endpoints.
//
// exports: UserController::index() -> Response
//          UserController::store(Request) -> JsonResponse
// used_by: routes/web.php -> Route::resource('users', UserController::class)
// rules:   must extend App\Http\Controllers\Controller
// agent:   claude-sonnet-4-6 | anthropic | 2026-04-15 | s_001 | initial scaffold
```

**Blade / Jinja2 / Twig / Volt** — `{{-- --}}` or `{# #}` block:
```
{{-- layout.blade.php — Base application layout. --}}
{{--
rules:   @yield('content') is required — child views must define this section
agent:   claude-sonnet-4-6 | anthropic | 2026-04-15 | s_001 | initial layout
--}}
```

---

## Reading files

1. Read the **module header** at the top of every source file before reading any code.
2. Parse `exports:` — symbols you **must never rename or remove** without explicit instruction.
3. Parse `used_by:` — callers that depend on this file. **Do not follow all blindly.** Ask: "does this caller intersect with my current task?" Only explore relevant callers.
4. Parse `related:` — files sharing the same logic without importing each other. Same filter: is it relevant to this task?
5. Parse `rules:` — hard constraints; read **before writing any logic**.
6. Parse `agent:` — session history; read to understand *why* the current state exists.
7. For any function with a `Rules:` docstring, read and respect those before writing logic.

## Writing new files

Every new source file **must begin** with a CodeDNA header in the correct format for the language (see above).

| Field | Required | Rule |
|---|---|---|
| First line | ✅ | `filename — <purpose ≤15 words>` |
| `exports:` | ✅ | Public API with return type |
| `used_by:` | ✅ | Who calls this file's exports (structural link) |
| `related:` | ⬜ | Files sharing the same logic without importing each other (semantic link) |
| `rules:` | ✅ | Hard constraints — specific and actionable |
| `agent:` | ✅ | Rolling window of last 5 entries |
| `message:` | ⬜ | Inter-agent channel — open hypotheses |

## Writing good `rules:`

`rules:` must be **specific and actionable** — never vague.

```
# ✅ Good
rules:   get_invoices() returns ALL tenants — caller MUST filter is_suspended() before aggregating
rules:   amount is in cents not euros — divide by 100 before display
rules:   soft-delete via deleted_at — NEVER use DELETE, always SET deleted_at = NOW()

# ❌ Bad
rules:   handle errors gracefully
rules:   follow best practices
```

## Writing critical functions (Python / Ruby only — L2)

Public functions **must** have a `Rules:` docstring:

```python
def my_function(arg: type) -> return_type:
    """Short description.

    Rules:   What the agent MUST or MUST NOT do here.
    message: model-id | YYYY-MM-DD | observation for next agent
    """
```

## Editing files

1. **First step**: re-read `rules:`, the `agent:` history, and any `Rules:` in the function you are editing.
2. Apply all file-level constraints before writing.
3. After editing, check `used_by:` targets (especially `[cascade]`-tagged ones).
4. Never remove `exports:` symbols — they are contracts used by other files.
5. If you discover a constraint, **update `rules:`** immediately.
6. **Append a new `agent:` line** after editing. Keep only the last 5 entries.

## Session end protocol

Append an `agent_sessions:` entry to `.codedna`:

```yaml
agent_sessions:
  - agent: <your-model-id>
    provider: <anthropic|google|openai|...>
    date: <YYYY-MM-DD>
    session_id: <s_YYYYMMDD_NNN>
    task: "<brief task description ≤15 words>"
    changed: [list, of, modified, files]
    visited: [all, files, read, during, session]
    message: >
      What you did, what you discovered, what the next agent should know.
```

Commit with AI git trailers:

```
<imperative summary>

AI-Agent:    <model-id>
AI-Provider: <provider>
AI-Session:  <session_id>
AI-Visited:  <comma-separated files read>
AI-Message:  <one-line summary>
```

## Semantic naming (Python / Ruby)

Format: `<type>_<shape>_<domain>_<origin>`

```python
list_dict_users_from_db = get_users()
int_cents_price_from_req = request.json["price"]
bool_is_admin_from_db    = user["role"] == "admin"
```

## Full spec

→ [SPEC.md](https://github.com/Larens94/codedna/blob/main/SPEC.md)
