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
# Options: claude | claude-hooks | cursor | copilot | cline | windsurf | agents | opencode | all
```

Or copy the files manually — one file per tool:

---

## Claude Code

**File location:** `/CLAUDE.md` (repo root)

Claude Code reads `CLAUDE.md` automatically before every session.

→ Copy [`integrations/CLAUDE.md`](./CLAUDE.md) to your repo root.

### Claude Code Hooks (active enforcement)

Claude Code supports **hooks** — shell commands that run automatically during agent sessions.
CodeDNA provides two hooks that enforce protocol compliance in real time:

| Hook | Event | What it does |
|---|---|---|
| `PostToolUse` on `Write`/`Edit` | After every file write/edit | Validates CodeDNA v0.8 header on `.py`, `.ts`, `.go`, etc. |
| `Stop` | When the agent finishes | Reminds to update `.codedna` and use git trailers |

**Install hooks:**

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh) claude-hooks
```

Or manually — add to `.claude/settings.local.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [{ "type": "command", "command": "bash tools/claude_hook_codedna.sh", "timeout": 10 }]
      },
      {
        "matcher": "Edit",
        "hooks": [{ "type": "command", "command": "bash tools/claude_hook_codedna.sh", "timeout": 10 }]
      }
    ],
    "Stop": [
      {
        "hooks": [{ "type": "command", "command": "bash tools/claude_hook_stop.sh", "timeout": 5 }]
      }
    ]
  }
}
```

The hook scripts are in [`tools/claude_hook_codedna.sh`](../tools/claude_hook_codedna.sh) and [`tools/claude_hook_stop.sh`](../tools/claude_hook_stop.sh).

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

Install with one command — installs **both** the instruction file and the enforcement plugin:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh) opencode
```

This creates two files in your project:

| File | Purpose |
|---|---|
| `AGENTS.md` | CodeDNA v0.8 instructions — loaded automatically by OpenCode as system prompt |
| `.opencode/plugins/codedna.js` | Active enforcement plugin — warns on missing headers, reminds at session end |

**What the plugin does:**
- After every file write → warns if `exports:` / `used_by:` header is missing (11 languages: Python, TypeScript, JavaScript, Go, PHP, Rust, Java, Kotlin, Ruby, C#, Swift)
- At session end → reminds to update `.codedna` and commit with AI git trailers

Both files load automatically at next `opencode` startup — no further configuration required.

> **Fallback:** if no `AGENTS.md` is found, OpenCode automatically falls back to `CLAUDE.md` — projects using the Claude Code integration already work out of the box.

**Manual install (alternative):**
```bash
# Instruction file
curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/AGENTS.md > AGENTS.md

# Plugin
mkdir -p .opencode/plugins
curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/opencode-plugin/codedna.js > .opencode/plugins/codedna.js
```

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
