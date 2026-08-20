# CodeDNA v0.9 — Protocol for OpenCode

This project uses the **CodeDNA** in-source communication protocol. Follow these rules on every file operation.

## Annotate your project (CLI)

```bash
pipx install git+https://github.com/Larens94/codedna.git
codedna install --path . --tools opencode --no-wiki-sync
codedna init . --no-llm  # free structural pass; all supported languages
codedna update .         # incremental: only unannotated files
codedna check .          # coverage report, no changes
codedna doctor --path .  # onboarding health gate
codedna impact FILE --path .  # pre-edit impact gate
codedna verify .         # post-edit structural drift gate
```

No model API key is required for the structural workflow. OpenCode loads this `AGENTS.md` and `.opencode/plugins/codedna.js` automatically after installation.

---

## Reading files

1. Read the **CodeDNA module header** at the top of every supported source file before reading any code.
2. Parse `exports:` — these are symbols you **must never rename or remove** without explicit instruction.
3. Parse `used_by:` — inspect only callers relevant to the current task.
4. Parse `related:` — inspect semantic siblings only when their domain intersects the task.
5. Parse `rules:` — hard constraints for every edit in this file; read **before writing any logic**.
6. Parse `agent:` — session history written by previous agents; read to understand *why* the current state exists.
7. If `wiki:` is present, read the referenced curated page before editing.
8. For any function with a `Rules:` docstring, read and respect those before writing logic.

## Required audit workflow

Run `doctor` on onboarding, `impact` before a public change, and `verify` after structural edits. Resolve exit 1 before continuing. Use `--json` in automation. `verify` checks structural `exports:`/`used_by:` consistency only; it does not certify semantic rules.

## Writing new files

Every new source file must begin with a CodeDNA header using that language's native comment syntax. Python uses this canonical module docstring:

```python
"""filename.py — <what it does, ≤15 words>.

exports: public_function(arg) -> return_type
used_by: consumer_file.py → consumer_function
related: other_file.py — shares the same logic without importing this file
wiki:    docs/wiki/filename.md
rules:   <hard constraint agents must never violate>
agent:   <your-model-id> | <provider> | <YYYY-MM-DD> | <session_id> | <what you implemented and what you noticed>
         message: "<open hypothesis or observation for the next agent>"
"""
```

Field guide:

| Field | Required | Rule |
|---|---|---|
| First line | ✅ | `filename.py — <purpose ≤15 words>` |
| `exports:` | ✅ | Public API with return type |
| `used_by:` | ✅ | Who calls this file's exports |
| `related:` | ⬜ | Semantic siblings without an import link |
| `wiki:` | ⬜ | Opt-in pointer to curated context under `docs/wiki/` |
| `rules:` | ✅ | Architectural truth — hard constraints, updated in-place |
| `agent:` | ✅ | Session narrative — rolling window of last 5 entries; drop the oldest when adding a 6th |
| `message:` | ⬜ | Inter-agent channel — open hypotheses, unverified observations (v0.9) |

## Writing good `rules:`

`rules:` must be **specific and actionable** — never vague.

```python
# ✅ Good rules:
rules:   get_invoices() returns ALL tenants — caller MUST filter is_suspended() before aggregating
rules:   amount is in cents not euros — divide by 100 before display
rules:   soft-delete via deleted_at — NEVER use DELETE, always SET deleted_at = NOW()

# ❌ Bad rules:
rules:   handle errors gracefully
rules:   follow best practices
rules:   none  ← when there ARE constraints but nobody wrote them
```

Update rules: every time you discover a constraint, fix a bug, or notice a non-obvious behavior.

## Writing critical functions

Every public function **must** have a `Rules:` docstring:

```python
def my_function(arg: type) -> return_type:
    """Short description.

    Rules:   What the agent MUST or MUST NOT do here.
    message: model-id | YYYY-MM-DD | observation for next agent
    """
```

## Inline annotations on complex logic

When writing or editing code blocks with non-obvious logic, add a `# Rules:` or `# message:` comment above the block:

```python
# Rules: skip cancelled orders — status=4 means cancelled in legacy DB
active = [o for o in orders if o.status != 4]

# message: exchange rate uses daily rate, not real-time
amount = order.amount * get_exchange_rate(order.currency)
```

When to add: business-rule conditionals, loops with filtering, algorithm steps where order matters, edge cases.
When NOT to add: simple getters, obvious control flow, standard library usage.

## Editing files

1. **First step**: re-read `rules:`, the `agent:` history, and the `Rules:` of the function you are editing.
2. Apply all file-level constraints before writing.
3. After editing, check `used_by:` targets (especially `[cascade]`-tagged ones).
4. Never remove `exports:` symbols — they are contracts used by other files.
5. If you discover a constraint or fix a bug, **update `rules:` for the next agent** (architectural channel).
6. **Append a new `agent:` line** to the module docstring after editing: `model-id | provider | YYYY-MM-DD | session_id | what you did`. Keep only the last 5 entries — drop the oldest if adding a 6th. Full history is in git and `.codedna`.

## Session end protocol

At the end of every session that modifies files:

1. Append through the canonical writer; never edit `agent_sessions:` manually:

```bash
codedna session append --agent <model-id> --provider <provider> \
  --session-id <s_YYYYMMDD_NNN> --task "<brief task>" \
  --changed <modified files...> --visited <read files...> \
  --message "<what the next agent should know>"
```

The writer locks `.codedna`, writes atomically, and retains the configured recent-session window. Git trailers remain the complete audit log.

Canonical stored shape:

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
      Constraints found → already added to rules: in the relevant files.
```

2. If you discovered new packages or dependencies, update `packages:` in `.codedna`.

3. **Commit with AI git trailers** — every commit produced by an AI session must include:

```
<imperative summary of changes>

AI-Agent:    <model-id>
AI-Provider: <provider>
AI-Session:  <session_id>
AI-Visited:  <comma-separated list of files read>
AI-Message:  <one-line summary of what was found or left open>
```

Git is the authoritative audit log. The `.codedna` entry and file-level `agent:` fields are lightweight caches for agent navigation — git trailers are the source of truth for history and verification.

## `message:` — Agent Chat Layer *(v0.9)*

The `message:` sub-field adds a conversational layer to `agent:` entries. Use it for observations not yet certain enough to become `rules:`, open questions, and notes for the next agent.

**In module docstrings (Level 1):**
```python
agent:   claude-sonnet-4-6 | anthropic | 2026-03-20 | s_20260320_001 | Implemented X.
         message: "noticed Y behaviour — not yet sure if this should be a rule"
```

**In function docstrings (Level 2) — for sliding window safety:**
```python
def my_function():
    """Short description.

    Rules:   hard constraint here
    message: claude-sonnet-4-6 | 2026-03-20 | open observation for next agent
    """
```

**Lifecycle:** a `message:` is either promoted to `rules:` (reply `"@prev: promoted to rules:"`) or dismissed (`"@prev: verified, not applicable because..."`). Always append-only — never delete.

## Planning across multiple files

Use manifest-only read mode: read only the module docstring (first 8–12 lines) of each file to build an architectural map before deciding which files to open fully.

At session start, read the retained `agent_sessions:` entries in `.codedna` to understand recent project history.

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
