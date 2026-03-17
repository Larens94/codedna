# CodeDNA — AI System Prompts

Ready-to-paste system prompts that configure any AI coding assistant to follow the **CodeDNA v0.6 Annotation Standard** (Python-native format).

---

## Universal (Claude, GPT-4, Gemini, Mistral, any LLM)

Paste into your AI assistant's system prompt or project instructions:

```
You are operating under the CodeDNA v0.6 Annotation Standard (Python-native format).
Full spec: github.com/Larens94/codedna/blob/main/SPEC.md

READING FILES:
- Read the module docstring at the top of every Python file before reading any code.
- Check `used_by:` — these callers depend on this file.
- Parse `exports:` — symbols you must never rename or remove.
- Read `Depends:` and `Rules:` in function docstrings before writing logic there.
- At call-site inline comments (# includes X — filter Y below) — read and respect.

WRITING NEW FILES:
- Every new Python file must begin with a module docstring:
  """filename.py — <what it does, ≤15 words>.
  exports: function(arg) -> type
  exports: function(arg) -> return_type
  used_by: consumer.py → function
  tables:  table(col) | none
  rules:   <hard constraint never to violate>
  """
- For cross-file functions, add a Google-style docstring with Depends: and Rules:.
- At the dangerous call site, add: # includes X — filter Y below
- Use semantic variable naming: list_dict_users_from_db = get_users()

EDITING FILES:
- Your FIRST step: re-read `rules:` and `Rules:` in affected functions.
- Do not change `exports:` unless explicitly asked — other files depend on them.
- Cascade all Modifies: targets mentioned in docstrings and call-site comments.
```

---

## Antigravity

In your project's **agent configuration** or **system prompt settings**:

```
You follow the CodeDNA v0.6 Annotation Standard (github.com/Larens94/codedna).

ON READ: parse the module docstring first (first 8–12 lines). Check `rules:` before
writing. Check `used_by:` for impact. Read `Rules:` in function docstrings
before writing logic in that function.

ON WRITE: every new Python file must start with a module docstring:
  """filename.py — <purpose ≤15 words>.

  exports: function(arg) -> type
  used_by: consumer.py → function
  tables:  table(col) | none
  rules:   <hard constraint>
  """
  For cross-file functions, add a Google-style docstring with Depends: and Rules:.
  At the dangerous call site, add: # includes X — filter Y below

ON EDIT: first re-read `rules:` and `Rules:`. Then cascade all Modifies: targets.

EXPORTS are public contracts — never rename without explicit instruction and updating
all `used_by` callers.
```

---

## Cursor (.cursorrules)

Create `.cursorrules` at your repo root (or copy from `integrations/.cursorrules`):

```
# CodeDNA Annotation Standard v0.6

## Module Docstring (required in every Python file)
Every source file must begin with:
"""filename.py — <what it does, ≤15 words>.

exports: function(arg) -> return_type
used_by: consumer.py → function
tables:  table(col) | none
rules:   <hard constraint>
"""

## Function Docstring (required for cross-file functions)
def fn(arg: type) -> type:
    """Description.
    Depends: file.symbol — contract.
    Rules:   MUST/MUST NOT ...
    """
    raw = get_data()  # includes X — filter Y below

## On every edit
1. Re-read `rules:` first (always)
2. Check `used_by:` before making changes
3. Read Depends: / Rules: in function docstrings before writing logic
4. Cascade all Modifies: targets after your change
5. Never rename `exports:` without updating all `used_by` callers

## Variable naming
<type>_<shape>_<domain>_<origin>: list_dict_orders_from_db = db.query(sql)
```

---

## Claude Code (CLAUDE.md)

Create `CLAUDE.md` at your repo root (or copy from `integrations/CLAUDE.md`):

```
Project uses CodeDNA v0.6 Annotation Standard (Python-native format).
Full spec: github.com/Larens94/codedna

On READ: parse module docstring first. Respect `rules:` as absolute constraints.
Read `Depends:` / `Rules:` in function docstrings before writing logic.

On WRITE (new file): begin with module docstring (deps/exports/used_by/tables/rules).
For cross-file functions: add Google-style docstring with Depends: and Rules:.
Dangerous calls: annotate inline: # includes X — filter Y.
Use semantic naming: list_dict_users_from_db = get_users()

On EDIT: re-read `rules:` first. Cascade all Modifies: targets.
`exports:` are contracts — never rename or remove without explicit instruction.
```

---

## GitHub Copilot (copilot-instructions.md)

Create `.github/copilot-instructions.md` (or copy from `integrations/copilot-instructions.md`):

```markdown
# CodeDNA v0.6

This codebase uses the CodeDNA Annotation Standard (Python-native format).
Full spec: github.com/Larens94/codedna

## Module docstring
Required at the top of every Python file: deps / exports / used_by / tables / rules.

## When you edit a file
- Re-read `rules:` as your first step
- Check `used_by:` before modifying function signatures
- Read `Depends:` / `Rules:` in function docstrings before implementing logic
- Cascade all Modifies: targets

## When you create a file
- Write the module docstring before any imports
- Add Google-style function docstring for cross-file deps
- Add inline comment at dangerous call sites: # includes X — filter Y
```

---

## Windsurf / Codeium (.windsurfrules)

Create `.windsurfrules` at your repo root (or copy from `integrations/.windsurfrules`):

```
# CodeDNA v0.6

ON READ: parse module docstring first. Respect `rules:`. Read `Depends:`/`Rules:` in functions.
ON WRITE: begin new files with module docstring (deps/exports/used_by/tables/rules).
  For cross-file functions: add Google-style function docstring with Depends: and Rules:.
  At dangerous calls: add inline comment # includes X — filter Y.
  Use semantic naming: list_dict_users_from_db = get_users()
ON EDIT: re-read `rules:` first. Propagate Modifies: cascades.
NEVER rename `exports:` without updating all `used_by` callers.
```

---

## ChatGPT (Custom GPT or Project Instructions)

In **Custom Instructions** → "What would you like ChatGPT to know?" or a Project instruction:

```
This project uses CodeDNA v0.6 Annotation Standard (Python-native format).
Spec: github.com/Larens94/codedna

Rules:
1. READ: always parse the module docstring (first 8–12 lines). Respect `rules:` hard constraints.
2. CROSS-FILE: read `Depends:` / `Rules:` in function docstrings before writing logic there.
3. WRITE: new files start with module docstring (deps/exports/used_by/tables/rules).
   Cross-file functions: add Google-style docstring with Depends: and Rules:.
   Dangerous calls: add inline: # includes X — filter Y.
4. EDIT: re-read `rules:` first. Cascade all Modifies: targets.
5. NAMING: list_dict_users_from_db = get_users(), int_cents_price_from_req = ...
6. CONTRACTS: never rename `exports:` without updating all `used_by` callers.
```

---

## Gemini (Google AI Studio or Gemini API)

In **System Instructions** field:

```
You are working on a project that follows the CodeDNA v0.6 Annotation Standard.
Spec: github.com/Larens94/codedna/blob/main/SPEC.md

BEFORE READING CODE: parse the module docstring at the top of each Python file.
The fields `exports:`, `used_by:`, `tables:`, `rules:` encode the architecture.
`rules:` contains HARD CONSTRAINTS — never violate them.

WHEN WRITING A NEW FILE: the first block must be a module docstring with all fields.
WHEN EDITING: re-read `rules:` and `Depends:`/`Rules:` in the function being edited.
CASCADES: after any edit, check for `Modifies:` fields and inline call-site comments
that list follow-up files/functions to update.
CONTRACTS: `exports:` symbols are public contracts — never rename without explicit permission.
```

---

## Aider (`--system-prompt`)

```bash
aider --system-prompt "$(cat tools/codedna-prompt.txt)"
```

Save the Universal prompt above to `tools/codedna-prompt.txt`, then:

```bash
# One-time setup
python tools/codedna_setup.py install --tool cursor   # or claude, copilot, windsurf
```

---

## Quick Verification

To confirm your AI assistant is following CodeDNA:

1. Ask it to create a new Python file → confirm first block is a module docstring with `exports:`/`used_by:`/`rules:` fields
2. Ask it to edit an existing CodeDNA file that has a `rules:` constraint → confirm it reads and respects `rules:` before writing
3. Ask it to modify a function that has `Depends:` in its docstring → confirm it follows the constraint

If it passes all three: CodeDNA is active. ✅
