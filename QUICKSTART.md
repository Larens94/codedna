# 🧬 CodeDNA — Quick Start

Get CodeDNA working in your project in under 2 minutes. Pick your AI tool below.

> **💡 No prompt engineering needed.** Once CodeDNA annotations are in your code, any AI agent — Cursor, Claude Code, Copilot, ChatGPT — will automatically follow the `used_by:` graph to find all files that need changes. You just describe the problem. The code guides the agent.

---

## Step 0 — Quick Install (CLI)

Run this from the root of your project:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh)
```

This installs CodeDNA rules for **all** supported tools (Claude Code, Cursor, Copilot, Cline, Windsurf, Antigravity).

To install for a **single tool** only:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh) cursor
```

Options: `claude` · `cursor` · `copilot` · `cline` · `windsurf` · `agents` · `all`

> After installing, skip to [Step 2 — Annotate your first file](#step-2--annotate-your-first-file).

---

## Step 1 — Install for your AI tool

### Antigravity (this tool)

Add to your **system prompt** or your project's agent configuration:

```
You follow the CodeDNA v0.6 Annotation Standard (github.com/Larens94/codedna).

ON READ: parse the module docstring first (first 8–12 lines). Check `rules:` before
writing. Check `used_by:` to understand who depends on this file. Read `Rules:` in
function docstrings before writing logic in that function.

ON WRITE: every new Python file must start with a module docstring:
  """filename.py — <purpose ≤15 words>.
  exports: function(arg) -> type
  used_by: consumer.py → function
  tables:  table(col) | none
  rules:   <hard constraint never to violate>
  """
  For critical functions, add a docstring with Rules:.

ON EDIT: first re-read `rules:` and `Rules:`. Check `used_by:` for affected callers.

EXPORTS are public contracts — never rename without explicit instruction and updating
all `used_by` callers.
```

---

### Cursor

Create `.cursorrules` at the root of your project:

```
# CodeDNA v0.6 — cursor rules

ON READ
- Parse the module docstring (first 8–12 lines) before reading code.
- Respect `rules:` as hard constraints.
- Check `used_by:` to understand who depends on this file.
- Read `Rules:` in function docstrings before writing logic.

ON WRITE
- Begin every new Python file with a module docstring (exports/used_by/tables/rules).
- For critical functions, add docstring with Rules:.
- Use semantic naming: list_dict_users_from_db = get_users()

ON EDIT
- First re-read `rules:` and any `Rules:` in function docstrings.
- Check `used_by:` and `cascade:` targets after editing.
- If you discover a constraint, add a Rules: annotation for the next agent.

NEVER rename `exports:` symbols without explicit instruction and updating all `used_by` callers.
```

Or copy the full version: [`integrations/.cursorrules`](./integrations/.cursorrules)

---

### Claude Code

Create `CLAUDE.md` at the root of your project:

```markdown
# CodeDNA v0.6

This project follows the CodeDNA Annotation Standard (github.com/Larens94/codedna).

## On every READ
1. Parse the module docstring (first 8–12 lines) before reading code
2. Respect `rules:` as absolute constraints
3. Check `used_by:` to understand impact of changes
4. Read `Rules:` in function docstrings before writing logic there

## On every WRITE (new file)
1. Begin with a module docstring: exports / used_by / tables / rules
2. For critical functions: add docstring with Rules:
3. Use semantic naming: list_dict_users_from_db = get_users()

## On every EDIT
1. Re-read `rules:` and `Rules:` before writing any logic
2. Check `used_by:` and `cascade:` targets after changes
3. Never rename `exports:` without updating all `used_by` callers
4. If you discover a constraint, add a Rules: annotation
```

Or copy the full version: [`integrations/CLAUDE.md`](./integrations/CLAUDE.md)

---

### GitHub Copilot

Create `.github/copilot-instructions.md`:

```markdown
# CodeDNA v0.6 Instructions

This repository uses the CodeDNA Annotation Standard.

When reading files: parse the module docstring first (first 8–12 lines).
Respect `rules:`. Check `used_by:` for impact. Read `Rules:` in function docstrings.

When writing new files: start with module docstring (exports/used_by/tables/rules).
For critical functions: add docstring with Rules:.

When editing: re-read `rules:` first. Check `used_by:` targets.
Never rename `exports:` without updating `used_by` callers.
```

Or copy the full version: [`integrations/copilot-instructions.md`](./integrations/copilot-instructions.md)

---

### Windsurf / Codeium

Create `.windsurfrules` at the root of your project (same format as Cursor):

```
# CodeDNA v0.6

ON READ: parse module docstring first. Respect `rules:`. Check `used_by:` for impact.
ON WRITE: begin new files with module docstring. Add Rules: to critical functions. Use semantic naming.
ON EDIT: re-read `rules:` first. Check `used_by:` targets. Never rename `exports:`.
```

---

### Any other LLM (ChatGPT, Gemini, etc.)

Paste this as system prompt or at the start of your conversation:

```
You follow the CodeDNA v0.6 Annotation Standard.

Rules:
1. READ: always parse the module docstring (first 8–12 lines). Respect `rules:` hard constraints.
2. IMPACT: check `used_by:` to understand which files depend on the one you're editing.
3. WRITE: new files start with module docstring (exports/used_by/tables/rules).
   Critical functions: add docstring with Rules:.
4. EDIT: re-read `rules:` first. Check `used_by:` and `cascade:` targets.
5. NAMING: list_dict_users_from_db = get_users(), int_cents_price_from_req = ...
6. CONTRACTS: never rename `exports:` without updating all `used_by` callers.
7. KNOWLEDGE: if you discover a constraint, add a Rules: annotation for the next agent.

Full spec: github.com/Larens94/codedna/blob/main/SPEC.md
```

---

## Step 2 — Annotate your first file

Ask your AI tool:

> *"Annotate this file following the CodeDNA v0.6 standard (github.com/Larens94/codedna). Add the module docstring header with exports, used_by, and rules."*

Or use the auto-annotator for existing codebases:

```bash
python tools/auto_annotate.py ./your_project/ --package your_package
```

---

## The Module Docstring (reference)

```python
"""filename.py — <≤15 words describing what this file does>.

exports: public_function(arg) -> return_type
used_by: consumer_file.py → consumer_function
tables:  table_name(col1, col2) | none
rules:   <hard constraint agents must never violate>
"""
```

| Field | Required | Rule |
|---|---|---|
| First line | ✅ | `filename.py — <purpose ≤15 words>` |
| `exports:` | ✅ | Public API with return type |
| `used_by:` | ✅ | Who calls this file's exports |
| `tables:` | — | DB tables accessed |
| `rules:` | — | Hard constraints scoped to this file |

---

## Function-Level Rules (reference)

Add `Rules:` to functions with non-obvious domain constraints:

```python
def my_function(arg: type) -> return_type:
    """Short description.

    Rules:   MUST cap value before returning; exceed = compliance bug.
    """
```

`Rules:` grow organically — agents add them as they discover constraints during their work.

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
