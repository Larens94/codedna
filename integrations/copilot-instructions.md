# CodeDNA v0.9 — GitHub Copilot Instructions

This codebase uses the CodeDNA communication protocol (v0.9). Apply these rules in every suggestion.

> Annotate your project: `pip install git+https://github.com/Larens94/codedna.git` then `codedna init ./`

## Module header (required in every Python file)

Every file must begin with a module docstring:

```python
"""filename.py — <what it does, ≤15 words>.

exports: public_function(arg) -> return_type
used_by: consumer_file.py → consumer_function
rules:   <hard constraint agents must never violate>
agent:   <model-id> | <provider> | <YYYY-MM-DD> | <session_id> | <what you did and what you noticed>
"""
```

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
def critical_function(arg: type) -> return_type:
    """Short description.

    Rules:   What MUST or MUST NOT happen here.
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

## On session start

Read `.codedna` at repo root — project structure and last 3 `agent_sessions:` entries.

## On edit: always do these in order

1. Check `rules:` in the module docstring — never violate these constraints
2. Check `used_by:` — these callers will be affected by your changes
3. Read `Rules:` in any function docstring before writing logic
4. If you discover a constraint, add it to `rules:` for the next agent
5. Append a new `agent:` line to the module docstring after editing. Keep only the last 5 entries — drop the oldest if adding a 6th. Full history is in git and `.codedna`.

## On generate: always do these

1. Write module docstring before imports (with `exports:`, `used_by:`, `rules:`, `agent:`)
2. Every public function **must** have a `Rules:` docstring
3. Use semantic names: `list_dict_orders_from_db = query(sql)` not `data = query(sql)`

## `message:` — Agent Chat Layer (v0.9)

Use `message:` for observations not yet certain enough to become `rules:`:

```python
agent:   <model-id> | <provider> | <YYYY-MM-DD> | <session_id> | Implemented X.
         message: "noticed Y behaviour — not yet sure if this should be a rule"
```

```python
def my_function():
    """Short description.

    Rules:   hard constraint here
    message: <model-id> | <date> | open observation for next agent
    """
```

**Lifecycle:** promote to `rules:` with `@prev: promoted to rules:` or dismiss with `@prev: verified, not applicable because...`. Always append-only — never delete.

## On session end

Append to `.codedna` → `agent_sessions:` with agent, provider, date, session_id, task, changed, visited, message.

Commit with AI git trailers: `AI-Agent`, `AI-Provider`, `AI-Session`, `AI-Visited`, `AI-Message`.

## CodeDNA + native memory — additive, not replacing

CodeDNA is the **shared** layer — git-tracked, readable by every agent and tool. It does not replace Copilot's native context or any other tool's memory. Use both:

- `.codedna` + file annotations → shared architectural truth, survives `git clone`
- Copilot native context → session-specific, tool-local context

## Exports are contracts

`exports:` symbols must not be renamed or removed — other files depend on them (check `used_by:`).
