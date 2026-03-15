# CodeDNA — AI System Prompts

Ready-to-paste system prompts that configure any AI coding assistant to follow the CodeDNA v0.3 protocol.

---

## Universal (works with Claude, GPT-4, Gemini, Mistral)

Paste this into your AI assistant's system prompt or project instructions:

```
You are operating under the CodeDNA v0.3 protocol.

READING FILES:
- Read the CodeDNA manifest header (lines starting with # === CODEDNA) before reading any code.
- Parse DEPENDS_ON: these are symbols you must never break.
- Parse EXPORTS: these are symbols you must never rename or remove.
- Follow every @REQUIRES-READ annotation before writing any logic.
- After editing, follow every @MODIFIES-ALSO annotation and cascade changes.

WRITING FILES:
- Every new file must begin with a CodeDNA manifest header.
- Include all fields: FILE, PURPOSE, CONTEXT_BUDGET, DEPENDS_ON, EXPORTS, STYLE (or none), DB_TABLES (or none), LAST_MODIFIED.
- Add @REQUIRES-READ/@SEE/@MODIFIES-ALSO to functions that have cross-file dependencies.
- Use semantic variable naming for data-carrying variables: list_dict_users_from_db = get_users()

EDITING FILES:
- Your FIRST change must always update the LAST_MODIFIED field.
- Do not change EXPORTS unless explicitly asked — other files depend on them.
- Do not remove DEPENDS_ON entries — they are contracts, not just comments.
```

---

## Cursor (.cursorrules)

Create `.cursorrules` at your repo root:

```
# CodeDNA v0.3 Protocol

## Manifest Header (required in every file)
Every source file must begin with a CodeDNA manifest:
```
# === CODEDNA:0.3 =============================================
# FILE: <exact filename>
# PURPOSE: <what it does, max 15 words>
# CONTEXT_BUDGET: <always | normal | minimal>
# DEPENDS_ON: <file → symbol> or none
# EXPORTS: <symbol(args) → type>
# STYLE: <framework> or none
# DB_TABLES: <table (cols)> or none
# LAST_MODIFIED: <last change, max 8 words>
# ==============================================================
```

## On every edit
1. Update LAST_MODIFIED first (always)
2. Read DEPENDS_ON before making changes
3. Follow @REQUIRES-READ annotations before writing logic
4. Cascade @MODIFIES-ALSO annotations after your change

## Variable naming
Data-carrying variables use: <type>_<shape>_<domain>_<origin>
Example: list_dict_orders_from_db = db.query(sql)
```

---

## Claude Projects (Project Instructions)

```
Project uses CodeDNA v0.3. Rules:

1. Every file starts with `# === CODEDNA:0.3` manifest block.
2. Required manifest fields: FILE, PURPOSE, CONTEXT_BUDGET, DEPENDS_ON, EXPORTS, LAST_MODIFIED.
3. When editing: update LAST_MODIFIED first. Read DEPENDS_ON. Follow @REQUIRES-READ links.
4. When generating: write manifest first, then code. Add @REQUIRES-READ/@MODIFIES-ALSO to cross-file functions.
5. EXPORTS are contracts — never rename or remove without explicit instruction.
6. CONTEXT_BUDGET: always=core file, normal=standard, minimal=utility/rarely changes.
```

---

## GitHub Copilot (copilot-instructions.md)

Create `.github/copilot-instructions.md`:

```markdown
# CodeDNA v0.3

This codebase uses the CodeDNA annotation standard.

## Manifest header
Required at the top of every source file. Fields: FILE, PURPOSE, CONTEXT_BUDGET, DEPENDS_ON, EXPORTS, [STYLE], [DB_TABLES], LAST_MODIFIED.

## When you edit a file
- Update LAST_MODIFIED as your first change
- Check DEPENDS_ON before modifying function signatures
- Follow @REQUIRES-READ annotations before implementing logic
- Update all @MODIFIES-ALSO targets after your change

## When you create a file
- Write the manifest header before any imports
- Set CONTEXT_BUDGET appropriately (always/normal/minimal)
- Add inline @REQUIRES-READ and @MODIFIES-ALSO to cross-file functions
```

---

## Aider (`--system-prompt`)

```bash
aider --system-prompt "$(cat tools/system-prompts.md | grep -A 20 '## Universal' | tail -n +3)"
```

Or save the universal prompt to a file and use:
```bash
aider --system-prompt-file tools/codedna-system-prompt.txt
```

---

## Quick Test

To verify your AI assistant is following CodeDNA:

1. Ask it to create a new file
2. Check that the first lines are the `# === CODEDNA:0.3` header
3. Ask it to edit an existing CodeDNA file
4. Check that LAST_MODIFIED was updated as the first change

If it passes both checks, CodeDNA is active. ✅
