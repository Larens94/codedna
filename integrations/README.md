# CodeDNA — Integration Guide

Copy these files to the **root of your repository** to activate CodeDNA in your AI coding tool.

---

## Quick Install (all tools)

```bash
# Clone CodeDNA integrations into your project
curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh | bash
```

Or copy manually — one file per tool:

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
| AI creates files with no metadata | Every file gets a manifest header |
| AI edits break cross-file deps | AI reads DEPENDS_ON before editing |
| AI skips related files | AI follows @REQUIRES-READ links |
| Style drift between views | STYLE field enforces consistency |

---

## Verify it's working

Ask your AI tool to create a new file. The first output block should be the `# === CODEDNA:0.3` manifest header, before any imports.

If it starts with imports instead — paste the integration file content directly into the system prompt or chat context.
