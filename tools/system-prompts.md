# CodeDNA — AI System Prompts

Ready-to-paste system prompts that configure any AI coding assistant to follow the **CodeDNA v0.5 Annotation Standard** (Python-native format).

---

## Universal (works with Claude, GPT-4, Gemini, Mistral)

Paste this into your AI assistant's system prompt or project instructions:

```
You are operating under the **CodeDNA v0.5 Annotation Standard** (Python-native format).

READING FILES:
- Read the module docstring at the top of every Python file before reading any code.
- Parse `deps:` — symbols you must never break.
- Parse `exports:` — symbols you must never rename or remove.
- Read `Depends:` and `Rules:` in function docstrings before writing logic there.
- Apply all cascade changes mentioned in `Modifies:` and call-site inline comments.

WRITING FILES:
- Every new Python file must begin with a module docstring:
  """filename.py — <what it does, ≤15 words>.
  deps:    file → symbol | none
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

## Cursor (.cursorrules)

Create `.cursorrules` at your repo root:

```
# CodeDNA Annotation Standard v0.5

## Module Docstring (required in every Python file)
Every source file must begin with:
"""filename.py — <what it does, ≤15 words>.
deps:    file → symbol | none
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
2. Follow `deps:` before making changes
3. Read Depends: / Rules: in function docstrings before writing logic
4. Cascade all Modifies: targets after your change

## Variable naming
Data-carrying variables use: <type>_<shape>_<domain>_<origin>
Example: list_dict_orders_from_db = db.query(sql)
```

---

## Claude Projects (Project Instructions)

```
Project uses **CodeDNA v0.5 Annotation Standard** (Python-native format). Rules:

1. Every Python file starts with a module docstring (deps/exports/used_by/tables/rules).
2. When editing: re-read `rules:` first. Follow deps:. Cascade Modifies: targets.
3. When generating: write module docstring first, then imports, then code.
   Cross-file functions: add Google-style docstring with Depends: and Rules:.
   Dangerous calls: annotate inline: # includes X — filter Y.
4. `exports:` are contracts — never rename or remove without explicit instruction.
5. Use semantic naming: list_dict_users_from_db = get_users()
```

---

## GitHub Copilot (copilot-instructions.md)

Create `.github/copilot-instructions.md`:

```markdown
# CodeDNA v0.5

This codebase uses the **CodeDNA Annotation Standard** (Python-native format).

## Module docstring
Required at the top of every Python file: deps / exports / used_by / tables / rules.

## When you edit a file
- Re-read `rules:` as your first step
- Check `deps:` before modifying function signatures
- Read `Depends:` / `Rules:` in function docstrings before implementing logic
- Cascade all Modifies: targets

## When you create a file
- Write the module docstring before any imports
- Add Google-style function docstring for cross-file deps
- Add inline comment at dangerous call sites: # includes X — filter Y
```

---

## Aider (`--system-prompt`)

```bash
aider --system-prompt "$(cat tools/system-prompts.md | grep -A 30 '## Universal' | tail -n +3)"
```

Or save the universal prompt to a file and use:
```bash
aider --system-prompt-file tools/codedna-system-prompt.txt
```

---

## Quick Test

To verify your AI assistant is following CodeDNA:

1. Ask it to create a new Python file
2. Check that the first block is a module docstring with `deps:`/`exports:`/`rules:` fields
3. Ask it to edit an existing CodeDNA file that has a `rules:` constraint
4. Check that it reads and respects the `rules:` field before writing

If it passes both checks, CodeDNA is active. ✅
