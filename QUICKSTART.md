# 🧬 CodeDNA — Quick Start

Get CodeDNA working in your project in under 2 minutes. Pick your AI tool below.

---

## Step 1 — Install for your AI tool

### Antigravity (this tool)

Add to your **system prompt** or your project's agent configuration:

```
You follow the CodeDNA v0.5 Annotation Standard (github.com/Larens94/codedna).

ON READ: parse the Manifest Header first (first 14 lines). Check AGENT_RULES before
writing. Follow every DEPENDS_ON edge. Follow every @REQUIRES-READ before writing logic.

ON WRITE: generate the manifest header (CODEDNA:0.4 format) before any imports.
Set CONTEXT_BUDGET (always/normal/minimal). Add @REQUIRES-READ and @MODIFIES-ALSO
to functions that cross file boundaries. Tag load-bearing symbols with @BREAKS-IF-RENAMED.
Use semantic naming: list_dict_users_from_db = get_users().

ON EDIT: first change = update LAST_MODIFIED. Then cascade all @MODIFIES-ALSO targets.

EXPORTS are public contracts — never rename without explicit instruction and updating
all REQUIRED_BY callers.
```

---

### Cursor

Create `.cursorrules` at the root of your project:

```
# CodeDNA v0.5 — cursor rules

ON READ
- Parse the Manifest Header (first 14 lines) before reading code.
- Respect AGENT_RULES as hard constraints.
- Follow all DEPENDS_ON references before editing.
- Follow every @REQUIRES-READ annotation before writing logic.

ON WRITE
- Generate the CODEDNA:0.4 manifest header before any imports.
- Set CONTEXT_BUDGET: always | normal | minimal.
- Add @REQUIRES-READ and @MODIFIES-ALSO to cross-file functions.
- Tag load-bearing symbols with @BREAKS-IF-RENAMED.
- Use semantic naming: list_dict_users_from_db = get_users()

ON EDIT
- First change must always be: update LAST_MODIFIED (≤8 words).
- Then propagate all @MODIFIES-ALSO cascade targets.

NEVER rename EXPORTS without explicit instruction and updating all REQUIRED_BY callers.
```

Or copy the full version: [`integrations/.cursorrules`](./integrations/.cursorrules)

---

### Claude Code

Create `CLAUDE.md` at the root of your project:

```markdown
# CodeDNA v0.5

This project follows the CodeDNA Annotation Standard (github.com/Larens94/codedna).

## On every READ
1. Parse the Manifest Header (first 14 lines) before reading code
2. Respect AGENT_RULES as absolute constraints
3. Follow DEPENDS_ON references before editing
4. Follow every @REQUIRES-READ before writing logic

## On every WRITE (new file)
1. Generate CODEDNA:0.4 manifest header before imports
2. Set CONTEXT_BUDGET: always / normal / minimal
3. Add @REQUIRES-READ and @MODIFIES-ALSO to cross-file functions
4. Tag load-bearing symbols with @BREAKS-IF-RENAMED
5. Use semantic naming: list_dict_users_from_db = get_users()

## On every EDIT
1. First line to change: LAST_MODIFIED (≤8 words describing the change)
2. Propagate all @MODIFIES-ALSO targets
3. Never rename EXPORTS without updating all REQUIRED_BY callers
```

Or copy the full version: [`integrations/CLAUDE.md`](./integrations/CLAUDE.md)

---

### GitHub Copilot

Create `.github/copilot-instructions.md`:

```markdown
# CodeDNA v0.5 Instructions

This repository uses the CodeDNA Annotation Standard.

When reading files: check the Manifest Header first (first 14 lines).
Respect AGENT_RULES. Follow @REQUIRES-READ before writing logic.

When writing new files: start with the CODEDNA:0.4 manifest header.
Set CONTEXT_BUDGET. Add @REQUIRES-READ and @MODIFIES-ALSO to cross-file calls.

When editing: first update LAST_MODIFIED. Then propagate @MODIFIES-ALSO.
Never rename EXPORTS without updating REQUIRED_BY callers.
```

Or copy the full version: [`integrations/copilot-instructions.md`](./integrations/copilot-instructions.md)

---

### Windsurf / Codeium

Create `.windsurfrules` at the root of your project (same format as Cursor):

```
# CodeDNA v0.5

ON READ: parse Manifest Header first. Respect AGENT_RULES. Follow @REQUIRES-READ.
ON WRITE: generate CODEDNA:0.4 header. Set CONTEXT_BUDGET. Add @REQUIRES-READ
  and @MODIFIES-ALSO to cross-file functions. Use semantic naming.
ON EDIT: update LAST_MODIFIED first. Propagate @MODIFIES-ALSO. Never rename EXPORTS.
```

---

### Any other LLM (ChatGPT, Gemini, etc.)

Paste this as system prompt or at the start of your conversation:

```
You follow the CodeDNA v0.5 Annotation Standard.

Rules:
1. READ: always parse the Manifest Header (first 14 lines). Respect AGENT_RULES hard constraints.
2. CROSS-FILE: follow every @REQUIRES-READ before writing; propagate every @MODIFIES-ALSO.
3. WRITE: new files start with CODEDNA:0.4 manifest. Set CONTEXT_BUDGET (always/normal/minimal).
4. EDIT: first change = update LAST_MODIFIED. Then cascade @MODIFIES-ALSO targets.
5. NAMING: use semantic names — list_dict_users_from_db = get_users(), int_cents_price_from_req = ...
6. CONTRACTS: never rename EXPORTS without updating all REQUIRED_BY callers.

Full spec: github.com/Larens94/codedna/blob/main/SPEC.md
```

---

## Step 2 — Annotate your first file

Ask your AI tool:

> *"Annotate this file following the CodeDNA v0.5 standard (github.com/Larens94/codedna). Add the CODEDNA:0.4 manifest header and any @REQUIRES-READ / @MODIFIES-ALSO inline hyperlinks where functions cross file boundaries."*

Or use the validate tool to check existing annotations:

```bash
python tools/validate_manifests.py ./your_project/
```

---

## The Manifest Header (reference)

```python
# === CODEDNA:0.4 =============================================
# FILE:           filename.py
# PURPOSE:        ≤15 words describing what this file does
# CONTEXT_BUDGET: always | normal | minimal
# DEPENDS_ON:     other_file.py :: function_name()
# EXPORTS:        public_function(arg) → return_type
# REQUIRED_BY:    consumer_file.py :: consumer_function()
# AGENT_RULES:    hard constraint agents must never violate
# LAST_MODIFIED:  ≤8 words describing the last change
# =============================================================
```

| Field | Required | Rule |
|---|---|---|
| `FILE` | ✅ | Exact filename |
| `PURPOSE` | ✅ | ≤15 words, what not how |
| `CONTEXT_BUDGET` | ✅ | `always` / `normal` / `minimal` |
| `DEPENDS_ON` | ✅ | `file :: symbol` or `none` |
| `EXPORTS` | ✅ | Public API with return type |
| `REQUIRED_BY` | — | Who consumes this file's exports |
| `AGENT_RULES` | — | Hard constraints scoped to this file |
| `LAST_MODIFIED` | ✅ | ≤8 words; first change on every edit |

---

## Inline Hyperlinks (reference)

```python
def my_function():
    # @REQUIRES-READ: config.py :: MAX_RATE    — read before writing logic
    # @MODIFIES-ALSO: report.py :: build_row() — cascade: update this too
    # @SEE: schema.py :: OrderModel            — helpful context
    # @BREAKS-IF-RENAMED: used by report.py via reflection
    pass
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
