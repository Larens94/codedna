# 🧬 CodeDNA — Quick Start

Get CodeDNA working in your project in under 2 minutes. Pick your AI tool below.

---

## Step 1 — Install for your AI tool

### Antigravity (this tool)

Add to your **system prompt** or your project's agent configuration:

```
You follow the CodeDNA v0.5 Annotation Standard (github.com/Larens94/codedna).

ON READ: parse the module docstring first (first 8–12 lines). Check `rules:` before
writing. Follow every `deps:` edge. Read `Depends:` / `Rules:` in function docstrings
before writing logic in that function.

ON WRITE: every new Python file must start with a module docstring:
  """filename.py — <purpose ≤15 words>.
  deps:    other.py → symbol | none
  exports: function(arg) -> type
  used_by: consumer.py → function
  tables:  table(col) | none
  rules:   <hard constraint never to violate>
  """
  For cross-file functions, add a Google-style docstring with Depends: and Rules:.
  At the dangerous call site, add: # includes X — filter Y below

ON EDIT: first re-read `rules:` and `Rules:`. Then cascade all Modifies: targets.

EXPORTS are public contracts — never rename without explicit instruction and updating
all `used_by` callers.
```

---

### Cursor

Create `.cursorrules` at the root of your project:

```
# CodeDNA v0.5 — cursor rules

ON READ
- Parse the module docstring (first 8–12 lines) before reading code.
- Respect `rules:` as hard constraints.
- Follow all `deps:` references before editing.
- Read `Depends:` / `Rules:` in function docstrings before writing logic.

ON WRITE
- Begin every new Python file with a module docstring (deps/exports/used_by/tables/rules).
- For cross-file functions, add Google-style docstring with Depends: and Rules:.
- At the dangerous call site, add inline: # includes X — filter Y.
- Use semantic naming: list_dict_users_from_db = get_users()

ON EDIT
- First re-read `rules:` and any `Rules:` in function docstrings.
- Propagate all cascade targets mentioned in Modifies: and call-site comments.

NEVER rename `exports:` symbols without explicit instruction and updating all `used_by` callers.
```

Or copy the full version: [`integrations/.cursorrules`](./integrations/.cursorrules)

---

### Claude Code

Create `CLAUDE.md` at the root of your project:

```markdown
# CodeDNA v0.5

This project follows the CodeDNA Annotation Standard (github.com/Larens94/codedna).

## On every READ
1. Parse the module docstring (first 8–12 lines) before reading code
2. Respect `rules:` as absolute constraints
3. Follow `deps:` references before editing
4. Read `Depends:` / `Rules:` in function docstrings before writing logic there

## On every WRITE (new file)
1. Begin with a module docstring: deps / exports / used_by / tables / rules
2. For critical cross-file functions: add Google-style docstring with Depends: and Rules:
3. At the dangerous call site: add inline comment describing what to filter
4. Use semantic naming: list_dict_users_from_db = get_users()

## On every EDIT
1. Re-read `rules:` and `Rules:` before writing any logic
2. Propagate all Modifies: targets and call-site-annotated cascades
3. Never rename `exports:` without updating all `used_by` callers
```

Or copy the full version: [`integrations/CLAUDE.md`](./integrations/CLAUDE.md)

---

### GitHub Copilot

Create `.github/copilot-instructions.md`:

```markdown
# CodeDNA v0.5 Instructions

This repository uses the CodeDNA Annotation Standard (Python-native format).

When reading files: parse the module docstring first (first 8–12 lines).
Respect `rules:`. Read `Depends:` / `Rules:` in function docstrings before writing logic.

When writing new files: start with a module docstring (deps/exports/used_by/tables/rules).
For cross-file functions: add Google-style docstring. At dangerous calls: add inline comment.

When editing: re-read `rules:` first. Then propagate Modifies: cascades.
Never rename `exports:` without updating `used_by` callers.
```

Or copy the full version: [`integrations/copilot-instructions.md`](./integrations/copilot-instructions.md)

---

### Windsurf / Codeium

Create `.windsurfrules` at the root of your project (same format as Cursor):

```
# CodeDNA v0.5

ON READ: parse module docstring first. Respect `rules:`. Read `Depends:`/`Rules:` in functions.
ON WRITE: begin new files with module docstring. Add Google-style function docstring for
  cross-file deps. Add call-site inline comment at dangerous calls. Use semantic naming.
ON EDIT: re-read `rules:` first. Propagate Modifies: cascades. Never rename `exports:`.
```

---

### Any other LLM (ChatGPT, Gemini, etc.)

Paste this as system prompt or at the start of your conversation:

```
You follow the CodeDNA v0.5 Annotation Standard.

Rules:
1. READ: always parse the module docstring (first 8–12 lines). Respect `rules:` hard constraints.
2. CROSS-FILE: read `Depends:` / `Rules:` in function docstrings before writing logic there.
3. WRITE: new files start with module docstring (deps/exports/used_by/tables/rules).
   Cross-file functions: add Google-style docstring with Depends: and Rules:.
   Dangerous calls: add inline: # includes X — filter Y.
4. EDIT: re-read `rules:` first. Cascade all Modifies: targets.
5. NAMING: list_dict_users_from_db = get_users(), int_cents_price_from_req = ...
6. CONTRACTS: never rename `exports:` without updating all `used_by` callers.

Full spec: github.com/Larens94/codedna/blob/main/SPEC.md
```

---

## Step 2 — Annotate your first file

Ask your AI tool:

> *"Annotate this file following the CodeDNA v0.5 standard (github.com/Larens94/codedna). Add the module docstring header and Google-style function docstrings for any cross-file function calls."*

Or use the validate tool to check existing annotations:

```bash
python tools/validate_manifests.py ./your_project/
```

---

## The Module Docstring (reference)

```python
"""filename.py — <≤15 words describing what this file does>.

deps:    other_file.py → symbol | none
exports: public_function(arg) -> return_type
used_by: consumer_file.py → consumer_function
tables:  table_name(col1, col2) | none
rules:   <hard constraint agents must never violate>
"""
```

| Field | Required | Rule |
|---|---|---|
| First line | ✅ | `filename.py — <purpose ≤15 words>` |
| `deps:` | ✅ | `file → symbol` or `none` |
| `exports:` | ✅ | Public API with return type |
| `used_by:` | — | Who calls this file's exports |
| `tables:` | — | DB tables accessed |
| `rules:` | — | Hard constraints scoped to this file |

---

## Sliding-Window Annotations (reference)

**Level 2a — Function docstring:**

```python
def my_function(arg: type) -> return_type:
    """Short description.

    Depends: config.MAX_RATE — read before writing logic.
    Rules:   MUST cap value before returning; exceed = compliance bug.
    Modifies: report.py → build_row  — update after changing this.
    """
```

**Level 2b — Call-site inline comment:**

```python
    raw = get_all_orders()  # includes cancelled orders — filter status != 'cancelled' below
```

---

## Semantic Naming (reference)

Format: `<type>_<shape>_<domain>_<origin>`

| Type prefix | Means |
|---|---|
| `int_` | integer |
| `str_` | string |
| `list_` | list |
| `dict_` | dict |
| `list_dict_` | list of dicts |
| `bool_` | boolean |

Origin suffixes: `_from_db`, `_from_req`, `_from_env`, `_from_cache`

```python
# Examples
int_cents_price_from_req     = request.json["price"]
list_dict_orders_from_db     = get_active_orders()
str_email_user_from_session  = session["email"]
bool_is_admin_from_db        = user["role"] == "admin"
```

---

## Full Spec

→ [`SPEC.md`](./SPEC.md)

## Scientific Paper

→ [`paper/codedna_paper.pdf`](./paper/codedna_paper.pdf)

## Benchmark Code

→ [`benchmark_agent/`](./benchmark_agent/)
