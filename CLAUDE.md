# CodeDNA v0.8 — Protocol for Claude Code

This project uses the **CodeDNA** in-source communication protocol. Follow these rules on every file operation.

---

## Reading files

1. Read the **module docstring** at the top of every Python file before reading any code.
2. Parse `exports:` — these are symbols you **must never rename or remove** without explicit instruction.
3. Parse `used_by:` — these are callers that will be affected by your changes.
4. Parse `rules:` — hard constraints for every edit in this file; read **before writing any logic**.
5. Parse `agent:` — session history written by previous agents; read to understand *why* the current state exists.
6. For any function with a `Rules:` docstring, read and respect those before writing logic.

## Writing new files

Every new Python source file **must begin** with a CodeDNA module docstring:

```python
"""filename.py — <what it does, ≤15 words>.

exports: public_function(arg) -> return_type
used_by: consumer_file.py → consumer_function
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
| `rules:` | ✅ | Architectural truth — hard constraints, updated in-place |
| `agent:` | ✅ | Session narrative — rolling window of last 5 entries; drop the oldest when adding a 6th |
| `message:` | ⬜ | Inter-agent channel — open hypotheses, unverified observations (v0.8) |

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

## `message:` — Agent Chat Layer *(v0.8 experimental)*

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

At session start, also read the last 3–5 `agent_sessions:` entries in `.codedna` to understand recent project history.

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
