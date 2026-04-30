---
description: CodeDNA v0.9 — how to read, write, and edit Python files in this project
---

# CodeDNA v0.9 — In-Source Communication Protocol

This project uses **CodeDNA**. Every source file carries its own context in a Python-native module docstring. Agents communicate across sessions through structured annotations co-located with the code.

## CodeDNA + native memory — additive, not replacing

CodeDNA is the **shared** layer — git-tracked, visible to every agent and every tool. It does not replace any tool's native memory. Use both:

- `.codedna` + file annotations → shared architectural truth, survives `git clone`, readable by any agent
- Native agent memory → user preferences and tool-specific context — local to that agent

## Session start

1. Read `.codedna` at repo root — project map and last 3 `agent_sessions:` entries
2. Read only the module docstring (first 8–12 lines) of each file you plan to touch — build an `exports:` → `used_by:` graph before opening any file in full

## Reading a file

1. Read the **module docstring** at the top of the file first (first 8–12 lines)
2. Note `exports:` → symbols you must not rename or remove
3. Note `used_by:` → callers that depend on this file's exports
4. Note `rules:` → hard constraints that apply everywhere in this file
5. Note `agent:` → session history from previous agents; read to understand *why* the current state exists
6. For any function, check its docstring for `Rules:` before writing logic there

## Creating a file

Every new Python source file must start with:

```python
"""filename.py — <what it does, ≤15 words>.

exports: public_function(arg) -> return_type
used_by: consumer_file.py → consumer_function
rules:   <hard constraint agents must never violate>
agent:   <model-id> | <provider> | <YYYY-MM-DD> | <session_id> | <what you implemented and what you noticed>
         message: "<open hypothesis or observation for the next agent>"
"""
```

| Field | Required | Rule |
|---|---|---|
| First line | ✅ | `filename.py — <purpose ≤15 words>` |
| `exports:` | ✅ | Public API with return type |
| `used_by:` | ✅ | Who calls this file's exports |
| `rules:` | ✅ | Architectural truth — hard constraints, updated in-place |
| `agent:` | ✅ | Session narrative — rolling window of last 5 entries; drop the oldest when adding a 6th |

## Editing a file

1. **First step**: re-read `rules:`, the `agent:` history, and any function-level `Rules:` before writing
2. Apply all file-level constraints before writing any logic
3. Check `used_by:` targets after changes — update callers if signatures change
4. Never remove `exports:` symbols — they are contracts
5. If you discover a constraint or fix a bug, **update `rules:`** for the next agent
6. **Append a new `agent:` line** after editing: `model-id | YYYY-MM-DD | what you did and noticed`. Keep only the last 5 entries — drop the oldest if adding a 6th. Full history is in git and `.codedna`.

## Critical functions

For functions with non-obvious domain constraints, add a `Rules:` docstring:

```python
def my_function(arg: type) -> return_type:
    """Short description.

    Rules:   What the agent MUST or MUST NOT do here.
    message: <model-id> | <YYYY-MM-DD> | open observation for next agent (optional)
    """
```

## `message:` — Agent Chat Layer *(v0.9)*

Use `message:` for observations not yet certain enough to become `rules:`, open questions, and notes for the next agent.

**In module docstrings (Level 1):**
```python
agent:   claude-sonnet-4-6 | 2026-03-20 | Implemented X.
         message: "noticed Y behaviour — not yet sure if this should be a rule"
```

**In function docstrings (Level 2) — sliding-window safety:**
```python
def my_function():
    """Short description.

    Rules:   hard constraint here
    message: claude-sonnet-4-6 | 2026-03-20 | open observation for next agent
    """
```

**Lifecycle:** promote to `rules:` with `@prev: promoted to rules:` or dismiss with `@prev: verified, not applicable because...`. Always append-only — never delete.

## Semantic variable naming

```python
# ✅ CodeDNA style — type + shape + domain + origin
list_dict_orders_from_db = db.query(sql)
str_html_view_rendered = render(query_fn)
int_cents_price_from_request = req.json["price"]

# ❌ avoid
data = db.query(sql)
result = render(query_fn)
price = req.json["price"]
```

## Session end protocol

1. Append an `agent_sessions:` entry to `.codedna`:

```yaml
- agent: <model-id>
  provider: <anthropic|google|openai|...>
  date: <YYYY-MM-DD>
  session_id: <s_YYYYMMDD_NNN>
  task: "<brief task description ≤15 words>"
  changed: [list, of, modified, files]
  visited: [all, files, read, during, session]
  message: >
    What you did, what you discovered, what the next agent should know.
```

2. **Commit with AI git trailers** — every commit from an AI session must include:

```
<imperative summary of changes>

AI-Agent:    <model-id>
AI-Provider: <provider>
AI-Session:  <session_id>
AI-Visited:  <comma-separated list of files read>
AI-Message:  <one-line summary of what was found or left open>
```

Git is the authoritative audit log. `.codedna` and file-level `agent:` fields are lightweight navigation caches — git trailers are the source of truth for history and verification.
