# CodeDNA — Integration Guide

Copy these files to the **root of your repository** to activate CodeDNA in your AI coding tool.

---

## Quick Install (all tools)

```bash
# Install CodeDNA rules for ALL supported tools
bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh)
```

Install for a **single tool** only:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh) claude
# Options: claude | agents | cursor | copilot | cline | windsurf | all
```

Or copy the files manually — one file per tool:

---

## Claude Code

**File location:** `/CLAUDE.md` (repo root)

Claude Code reads `CLAUDE.md` automatically before every session.

→ Copy [`integrations/CLAUDE.md`](./CLAUDE.md) to your repo root.

---

## Cursor

**File location:** `/.cursorrules` (repo root)

Cursor reads `.cursorrules` and applies it to all AI completions and chat.

→ Copy [`integrations/.cursorrules`](./.cursorrules) to your repo root.

For Cursor v0.43+, you can also use `.cursor/rules/codedna.mdc`:
```bash
mkdir -p .cursor/rules
cp integrations/.cursorrules .cursor/rules/codedna.mdc
```

---

## GitHub Copilot

**File location:** `/.github/copilot-instructions.md`

→ Copy [`integrations/copilot-instructions.md`](./copilot-instructions.md):
```bash
mkdir -p .github
cp integrations/copilot-instructions.md .github/copilot-instructions.md
```

---

## Cline (VSCode Extension)

**File location:** `/.clinerules` (repo root)

→ Copy [`integrations/.clinerules`](./.clinerules) to your repo root.

---

## Windsurf (Codeium)

**File location:** `/.windsurfrules` (repo root)

→ Copy [`integrations/.windsurfrules`](./.windsurfrules) to your repo root.

---

## OpenCode

**File location:** `/AGENTS.md` (repo root)

OpenCode reads `AGENTS.md` automatically before every session. Multiple instruction files can be referenced via `opencode.json`.

→ Copy [`integrations/AGENTS.md`](./AGENTS.md) to your repo root.

Optional — add to `opencode.json` to load it explicitly:
```json
{
  "$schema": "https://opencode.ai/config.json",
  "instructions": ["AGENTS.md"]
}
```

> **Fallback:** if no `AGENTS.md` is found, OpenCode automatically falls back to `CLAUDE.md` — so projects using the Claude Code integration already work out of the box.

### OpenCode Plugin (active enforcement)

For stronger enforcement, install the CodeDNA plugin. It hooks into OpenCode's event system to:

- **Warn after every file write** if `exports:` / `used_by:` header is missing
- **Remind at session end** to update `.codedna` and commit with AI git trailers

Supported languages: Python, TypeScript, JavaScript, Go, PHP, Rust, Java, Kotlin, Ruby, C#, Swift

```bash
mkdir -p .opencode/plugins
cp integrations/opencode-plugin/codedna.js .opencode/plugins/codedna.js
```

The plugin loads automatically at next `opencode` startup — no configuration required.

---

## Aider

```bash
# Pass as system prompt at launch
aider --system-prompt "$(cat integrations/CLAUDE.md)"
```

Or add to your `.aider.conf.yml`:
```yaml
system_prompt: integrations/CLAUDE.md
```

---

## Antigravity / Custom Agents

**File location:** `/.agents/workflows/codedna.md`

→ Copy [`integrations/.agents/workflows/codedna.md`](./.agents/workflows/codedna.md):
```bash
mkdir -p .agents/workflows
cp integrations/.agents/workflows/codedna.md .agents/workflows/codedna.md
```

---

## What changes after install?

| Before | After |
|---|---|
| AI creates files with no metadata | Every file gets a module docstring (exports/used_by/rules) |
| AI edits break cross-file deps | AI reads `used_by:` and `Rules:` before editing |
| AI skips related files | AI follows `used_by:` graph and function-level `Rules:` |
| No constraint memory in long files | `rules:` in docstring repeats at every function scope |

---

## Verify it's working

Ask your AI tool to create a new Python file. The first block should be the module docstring with `exports:`, `used_by:`, and `rules:` fields, before any imports.

If it starts with imports instead — paste the integration file content directly into the system prompt or chat context.
