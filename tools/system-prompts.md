# CodeDNA — AI System Prompts

Ready-to-paste system prompts that configure any AI coding assistant to follow the **CodeDNA v0.9 Annotation Standard** (Python-native format).

---

## Universal (Claude, GPT-4, Gemini, Mistral, any LLM)

Paste into your AI assistant's system prompt or project instructions:

```
You are operating under the CodeDNA v0.9 Annotation Standard (Python-native format).
Full spec: github.com/Larens94/codedna/blob/main/SPEC.md

READING FILES:
- Read the module docstring at the top of every Python file before reading any code.
- Check `used_by:` — these callers depend on this file.
- Parse `exports:` — symbols you must never rename or remove.
- Read `rules:` — hard constraints for every edit in this file.
- For any function with a `Rules:` docstring, read and respect those before writing logic.

WRITING NEW FILES:
- Every new Python file must begin with a module docstring:
  """filename.py — <what it does, ≤15 words>.
  exports: function(arg) -> return_type
  used_by: consumer.py → function
  rules:   <hard constraint never to violate>
  """
- For critical functions, add a docstring with Rules:.
- Use semantic variable naming: list_dict_users_from_db = get_users()

EDITING FILES:
- Your FIRST step: re-read `rules:` and `Rules:` in affected functions.
- Do not change `exports:` unless explicitly asked — other files depend on them.
- Check `used_by:` targets after editing (especially [cascade]-tagged ones).
- If you discover a constraint or fix a bug, UPDATE `rules:` for the next agent.
```

---

## Antigravity

Recommended: run `codedna install --tools agents` (writes `AGENTS.md` at repo root + `.agent/workflows/codedna.md`). For a manual setup, drop the protocol into one of the paths Antigravity v1.20.3+ reads:

- `<project>/AGENTS.md` — always-on, cross-vendor (also read by OpenCode/Cursor/Claude Code)
- `~/.gemini/GEMINI.md` — always-on, global, highest priority
- `<project>/.agent/rules/codedna.md` — always-on, Antigravity-specific (note: `.agent/` is **singular**)

Paste in the chosen file:

```
You follow the CodeDNA v0.9 Annotation Standard (github.com/Larens94/codedna).

ON READ: parse the module docstring first (first 8–12 lines). Check `rules:` before
writing. Check `used_by:` for impact. Read `Rules:` in function docstrings
before writing logic in that function.

ON WRITE: every new Python file must start with a module docstring:
  """filename.py — <purpose ≤15 words>.
  exports: function(arg) -> type
  used_by: consumer.py → function
  rules:   <hard constraint>
  """
  For critical functions, add a docstring with Rules:.

ON EDIT: first re-read `rules:` and `Rules:`. Check `used_by:` targets
(especially [cascade]-tagged ones). If you discover a constraint, update `rules:`.

EXPORTS are public contracts — never rename without explicit instruction and updating
all `used_by` callers.
```

---

## Cursor (.cursorrules)

Create `.cursorrules` at your repo root (or copy from `integrations/.cursorrules`):

```
# CodeDNA Annotation Standard v0.9

## Module Docstring (required in every Python file)
Every source file must begin with:
"""filename.py — <what it does, ≤15 words>.

exports: function(arg) -> return_type
used_by: consumer.py → function
rules:   <hard constraint>
"""

## Function Docstring (required for critical functions)
def fn(arg: type) -> type:
    """Description.
    Rules:   MUST/MUST NOT ...
    """

## On every edit
1. Re-read `rules:` first (always)
2. Check `used_by:` before making changes
3. Read `Rules:` in function docstrings before writing logic
4. If you discover a constraint, update `rules:` for the next agent
5. Never rename `exports:` without updating all `used_by` callers

## Variable naming
<type>_<shape>_<domain>_<origin>: list_dict_orders_from_db = db.query(sql)
```

---

## Claude Code (CLAUDE.md)

Create `CLAUDE.md` at your repo root (or copy from `integrations/CLAUDE.md`):

```
Project uses CodeDNA v0.9 Annotation Standard (Python-native format).
Full spec: github.com/Larens94/codedna

On READ: parse module docstring first. Respect `rules:` as absolute constraints.
Read `Rules:` in function docstrings before writing logic.

On WRITE (new file): begin with module docstring (exports/used_by/rules).
For critical functions: add docstring with Rules:.
Use semantic naming: list_dict_users_from_db = get_users()

On EDIT: re-read `rules:` first. Check `used_by:` targets (especially [cascade]-tagged).
If you discover a constraint, update `rules:` for the next agent.
`exports:` are contracts — never rename or remove without explicit instruction.
```

---

## GitHub Copilot (copilot-instructions.md)

Create `.github/copilot-instructions.md` (or copy from `integrations/copilot-instructions.md`):

```markdown
# CodeDNA v0.9

This codebase uses the CodeDNA Annotation Standard (Python-native format).
Full spec: github.com/Larens94/codedna

## Module docstring
Required at the top of every Python file: exports / used_by / rules.

## When you edit a file
- Re-read `rules:` as your first step
- Check `used_by:` before modifying function signatures
- Read `Rules:` in function docstrings before implementing logic
- If you discover a constraint, update `rules:` for the next agent

## When you create a file
- Write the module docstring before any imports
- Add `Rules:` docstring to functions with non-obvious domain constraints
```

---

## Windsurf / Codeium (.windsurfrules)

Create `.windsurfrules` at your repo root:

```
# CodeDNA v0.9

ON READ: parse module docstring first. Respect `rules:`. Read `Rules:` in functions.
ON WRITE: begin new files with module docstring (exports/used_by/rules).
  For critical functions: add docstring with Rules:.
  Use semantic naming: list_dict_users_from_db = get_users()
ON EDIT: re-read `rules:` first. Check `used_by:` targets. Update `rules:` on discovery.
NEVER rename `exports:` without updating all `used_by` callers.
```

---

## ChatGPT (Custom GPT or Project Instructions)

In **Custom Instructions** → "What would you like ChatGPT to know?" or a Project instruction:

```
This project uses CodeDNA v0.9 Annotation Standard (Python-native format).
Spec: github.com/Larens94/codedna

Rules:
1. READ: always parse the module docstring (first 8–12 lines). Respect `rules:` hard constraints.
2. CROSS-FILE: read `Rules:` in function docstrings before writing logic there.
3. WRITE: new files start with module docstring (exports/used_by/rules).
   Critical functions: add docstring with Rules:.
4. EDIT: re-read `rules:` first. Check `used_by:` targets (especially [cascade]-tagged).
5. NAMING: list_dict_users_from_db = get_users(), int_cents_price_from_req = ...
6. CONTRACTS: never rename `exports:` without updating all `used_by` callers.
7. KNOWLEDGE: if you discover a constraint, update `rules:` for the next agent.
```

---

## Gemini (Google AI Studio or Gemini API)

In **System Instructions** field:

```
You are working on a project that follows the CodeDNA v0.9 Annotation Standard.
Spec: github.com/Larens94/codedna/blob/main/SPEC.md

BEFORE READING CODE: parse the module docstring at the top of each Python file.
The fields `exports:`, `used_by:`, `rules:` encode the architecture.
`rules:` contains HARD CONSTRAINTS — never violate them. `rules:` is the inter-agent
communication channel — if you discover a constraint, update `rules:` for the next agent.

WHEN WRITING A NEW FILE: the first block must be a module docstring with all fields.
WHEN EDITING: re-read `rules:` and `Rules:` in the function being edited.
AFTER EDITING: check `used_by:` targets (especially [cascade]-tagged ones).
CONTRACTS: `exports:` symbols are public contracts — never rename without explicit permission.
```

---

## Aider (`--system-prompt`)

```bash
aider --system-prompt "$(cat tools/codedna-prompt.txt)"
```

Save the Universal prompt above to `tools/codedna-prompt.txt`.

---

## Quick Verification

To confirm your AI assistant is following CodeDNA:

1. Ask it to create a new Python file → confirm first block is a module docstring with `exports:`/`used_by:`/`rules:` fields
2. Ask it to edit an existing CodeDNA file that has a `rules:` constraint → confirm it reads and respects `rules:` before writing
3. Ask it to modify a function that has `Rules:` in its docstring → confirm it follows the constraint

If it passes all three: CodeDNA is active. ✅
