# CodeDNA v0.9 — Protocol for Claude Code

This project uses the **CodeDNA** in-source communication protocol. Follow these rules on every file operation.

---

## Reading files

1. Read the **module docstring** at the top of every Python file before reading any code.
2. Parse `exports:` — these are symbols you **must never rename or remove** without explicit instruction.
3. Parse `used_by:` — callers that depend on this file. **Do not follow all of them blindly.** Ask: "does this caller's domain intersect with my current task?" Only explore callers relevant to the specific change you're making.
4. Parse `related:` — files sharing the same logic without importing each other. Same filter: is it relevant to this task?
5. Parse `rules:` — hard constraints for every edit in this file; read **before writing any logic**.
6. Parse `agent:` — session history written by previous agents; read to understand *why* the current state exists.
7. For any function with a `Rules:` docstring, read and respect those before writing logic.

## Writing new files

Every new Python source file **must begin** with a CodeDNA module docstring:

```python
"""filename.py — <what it does, ≤15 words>.

exports: public_function(arg) -> return_type
used_by: consumer_file.py → consumer_function
related: other_file.py — shares same pattern/logic (no import link)
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
| `used_by:` | ✅ | Who calls this file's exports (structural link via import) |
| `related:` | ⬜ | Files that share the same logic/pattern without importing each other (semantic link) |
| `wiki:` | ⬜ | Opt-in pointer to a deeper markdown doc under `docs/wiki/` (see below) |
| `rules:` | ✅ | Architectural truth — specific, actionable constraints (see examples below) |
| `agent:` | ✅ | Session narrative — rolling window of last 5 entries; drop the oldest when adding a 6th |
| `message:` | ⬜ | Inter-agent channel — open hypotheses, unverified observations |

## Writing good `rules:`

`rules:` must be **specific and actionable** — an agent reading it should know exactly what to do or not do. Never write vague rules.

```python
# ✅ Good rules: — specific, actionable, explains WHY
rules:   get_invoices() returns ALL tenants — caller MUST filter is_suspended() before aggregating
rules:   amount is in cents not euros — divide by 100 before display
rules:   this endpoint requires admin role — auth middleware is in routes.py, not here
rules:   soft-delete via deleted_at — NEVER use DELETE, always SET deleted_at = NOW()
rules:   SQLite has no ALTER COLUMN — schema changes must recreate the table

# ❌ Bad rules: — vague, not actionable
rules:   handle errors gracefully
rules:   follow best practices
rules:   be careful with this code
rules:   none  ← when there ARE constraints but nobody wrote them
```

**When to update rules:** every time you discover a constraint, fix a bug, or notice a non-obvious behavior — add it to `rules:` immediately. This is how you communicate with the next agent.

**`rules: none` is acceptable** only when a file truly has no domain constraints (e.g., a simple utility with no side effects). If you see `rules: none` on a file with business logic, add the missing constraints.

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

When writing or editing code blocks with non-obvious logic (complex conditions, algorithms, loops with business rules, edge cases), add a `# Rules:` or `# message:` comment **above** the block:

```python
# Rules: skip cancelled orders — status=4 means cancelled in legacy DB
active = [o for o in orders if o.status != 4]

for order in active:
    # message: exchange rate conversion uses daily rate, not real-time
    amount = order.amount * get_exchange_rate(order.currency)

    if amount > config.threshold:
        # Rules: threshold check MUST happen before tax — tax is on gross amount
        apply_tax(order)
```

**When to add inline annotations:**
- Conditional logic that encodes a business rule (`if status != 4`)
- Loops with non-obvious filtering or transformation
- Algorithm steps where the order matters
- Edge cases or workarounds with context that would be lost

**When NOT to add them:**
- Simple getters/setters
- Obvious control flow (`if not user: return None`)
- Standard library usage

## Editing files

1. **First step**: re-read `rules:`, the `agent:` history, and the `Rules:` of the function you are editing.
2. Apply all file-level constraints before writing.
3. After editing, check `used_by:` targets (especially `[cascade]`-tagged ones).
4. Never remove `exports:` symbols — they are contracts used by other files.
5. If you discover a constraint or fix a bug, **update `rules:` for the next agent** (architectural channel).
6. **Append a new `agent:` line** to the module docstring after editing: `model-id | provider | YYYY-MM-DD | session_id | what you did and what you noticed`. Keep only the last 5 entries — drop the oldest if adding a 6th. Full history is in git and `.codedna`.

## Session end protocol

At the end of every session that modifies files:

1. Append an `agent_sessions:` entry to `.codedna`:

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

## `message:` — Agent Chat Layer

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

## `wiki:` — Opt-in deeper context

The `wiki:` field is an **optional pointer** from a source file's docstring to a curated markdown document. It is **the signal, not the dump** — it exists only when a prior agent decided this file deserves context beyond what the terse docstring can hold.

**In the docstring:**
```python
"""cli.py — CodeDNA annotation tool.

exports: scan_file | run
used_by: tests/test_cli.py → FileInfo
wiki:    docs/wiki/cli.md        ← opt-in pointer
rules:   ...
agent:   ...
"""
```

**Agent workflow:**

- **Before editing a file, check its docstring for `wiki:`**
  - **Present** → read the pointed markdown. A prior agent put it there because editing this file without that context leads to bugs.
  - **Absent** → the docstring is sufficient; no extra read required.

**When to add `wiki:` yourself:**

- You discovered non-obvious architectural constraints that don't fit in `rules:` (too long, too narrative)
- You want to leave a history of decisions ("why we chose X over Y") for the next agent
- You have extension-point notes ("to add a new language, see section 4")
- Obvious: don't add `wiki:` for routine files. **Sparsity is the signal.**

**File layout:**

- Curated pages live under `docs/wiki/` (same tree as the source, e.g. `docs/wiki/codedna_tool/cli.md`)
- A single `<!-- AGENT NOTES -->` marker at the end of each auto-generated page preserves human/agent additions across regeneration
- The `codedna wiki` commands manage the vault (see below)

## `codedna wiki` — Commands

Two complementary subcommands:

- **`codedna wiki bootstrap [path] --out docs/wiki`** — generates one markdown page per annotated source file with `[[wikilinks]]` derived from `used_by:` and `related:` graphs. Open `docs/wiki/` in [Obsidian](https://obsidian.md) for a navigable graph. **Primarily a human tool**: agents already have the same info in the docstring.

- **`codedna wiki sync [path] --out docs/codedna-wiki.md`** — regenerates a single narrative project wiki (7 sections: identity, topology, workflows, hotspots, …). **Useful for agents entering the project cold** — they read this first to get the semantic sky-view that no single file contains.

Wire `codedna wiki sync` to a post-commit hook so the project wiki stays current without relying on an agent to remember.

## Planning across multiple files

Use manifest-only read mode: read only the module docstring (first 8–12 lines) of each file to build an architectural map before deciding which files to open fully.

At session start, also read the last 3 `agent_sessions:` entries in `.codedna` to understand recent project history. Older sessions are automatically pruned — full history is in git.

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
