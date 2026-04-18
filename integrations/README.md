# CodeDNA — Integration Guide

One command installs everything your AI tool needs — instructions + real-time enforcement.

---

## Install for your tool

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh) <tool>
```

| Tool | Option | What gets installed | Enforcement |
|---|---|---|---|
| **Claude Code** ⭐ | **`claude-hooks`** | **`CLAUDE.md` + 4 hooks + `.claude/settings.local.json`** | ✅ Active |
| **Cursor** | **`cursor-hooks`** | **`.cursorrules` + hook scripts in `.cursor/hooks/`** | ✅ Active (v1.7+) |
| **GitHub Copilot** | **`copilot-hooks`** | **`copilot-instructions.md` + `.github/hooks/`** | ✅ Active |
| **Cline** | **`cline-hooks`** | **`.clinerules` + hook scripts in `.clinerules/hooks/`** | ✅ Active (v3.36+) |
| **OpenCode** | **`opencode`** | **`AGENTS.md` + `.opencode/plugins/codedna.js`** | ✅ Active |
| Windsurf | `windsurf` | `.windsurfrules` | ⚠️ Instructions only |
| Antigravity / custom agents | `agents` | `.agents/workflows/codedna.md` | ⚠️ Instructions only |
| Aider | `claude` | `CLAUDE.md` | ⚠️ Instructions only |

> **Active enforcement** = the tool validates annotations automatically on every file write/edit, without relying on the agent remembering to do it.

> **`all`** — installs every file and hook above at once. Only useful for teams where each developer uses a different tool.

Or copy the files manually — one file per tool:

---

## Claude Code

Use `claude-hooks` — it installs `CLAUDE.md` **and** the enforcement hooks in one shot:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh) claude-hooks
```

> **Why hooks matter:** without them the agent reads the instructions but nothing validates compliance — annotations get skipped on complex or long sessions. Hooks enforce the protocol automatically on every write and edit.

### What the four hooks do

| Hook | Event | What it does |
|---|---|---|
| `SessionStart` | When a session begins | Reads `.codedna`, injects project name and module count into context |
| `PreToolUse` on `Write`/`Edit` | Before every `.py` write/edit | Reminds agent to check docstring / exports / used_by / rules / agent |
| `PostToolUse` on `Write`/`Edit` | After every `.py` write/edit | Validates all 4 CodeDNA fields exist and `agent:` has today's date |
| `Stop` | When the agent finishes | Reminds to update `.codedna` with a new `agent_sessions` entry |

**Prerequisite:** `jq` must be installed (`brew install jq` / `apt install jq`).

---

#### Where to put the settings file

| File | Committed? | Use when |
|---|---|---|
| `.claude/settings.local.json` | ❌ gitignored | Personal setup — each developer configures locally |
| `.claude/settings.json` | ✅ committed | Team setup — shared with everyone via the repo |

> **For agents running in CI or automated pipelines:** use `.claude/settings.json` so the hooks are always present without manual setup.

---

#### Install hooks (one command)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh) claude-hooks
```

This downloads the hook scripts to `tools/` and writes `.claude/settings.local.json` if it does not already exist.

---

#### Manual setup — full hooks config

If `.claude/settings.local.json` already exists, **merge** this `"hooks"` block into it (do not replace the whole file):

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [{
          "type": "command",
          "command": "codedna=\".codedna\"; if [[ -f \"$codedna\" ]]; then pkgs=$(grep -c 'purpose:' \"$codedna\"); proj=$(grep '^project:' \"$codedna\" | head -1 | cut -d' ' -f2-); echo \"{\\\"hookSpecificOutput\\\":{\\\"hookEventName\\\":\\\"SessionStart\\\",\\\"additionalContext\\\":\\\"[CodeDNA] Project: $proj — $pkgs documented modules. Read .codedna and CLAUDE.md before editing Python files. Every .py edit requires updating agent: with today's date.\\\"}}\"; fi",
          "timeout": 5
        }]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{
          "type": "command",
          "command": "f=$(jq -r '.tool_input.file_path // empty'); [[ \"$f\" == *.py ]] && echo '{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"additionalContext\":\"[CodeDNA] Python file. Before editing: (1) read the docstring, (2) verify exports/used_by/rules/agent, (3) plan agent: update with the current session.\"}}' || true",
          "timeout": 5
        }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [{ "type": "command", "command": "bash tools/claude_hook_codedna.sh", "timeout": 10, "statusMessage": "CodeDNA v0.9 — validating annotations..." }]
      },
      {
        "matcher": "Edit",
        "hooks": [{ "type": "command", "command": "bash tools/claude_hook_codedna.sh", "timeout": 10, "statusMessage": "CodeDNA v0.9 — validating annotations..." }]
      },
      {
        "matcher": "Write|Edit",
        "hooks": [{
          "type": "command",
          "command": "f=$(jq -r '.tool_input.file_path // empty'); [[ \"$f\" == *.py ]] && [[ -f \"$f\" ]] && { today=$(date +%Y-%m-%d); header=$(head -30 \"$f\"); issues=(); echo \"$header\" | grep -q 'exports:' || issues+=(\"missing exports:\"); echo \"$header\" | grep -q 'used_by:' || issues+=(\"missing used_by:\"); echo \"$header\" | grep -q 'rules:' || issues+=(\"missing rules:\"); echo \"$header\" | grep -q 'agent:' || issues+=(\"missing agent:\"); echo \"$header\" | grep -q \"agent:.*$today\" || issues+=(\"agent: not updated to $today\"); if [[ ${#issues[@]} -gt 0 ]]; then msg=$(IFS=', '; echo \"${issues[*]}\"); echo \"{\\\"hookSpecificOutput\\\":{\\\"hookEventName\\\":\\\"PostToolUse\\\",\\\"additionalContext\\\":\\\"[CodeDNA] $f — $msg\\\"}}\"; fi; } || true",
          "timeout": 5
        }]
      }
    ],
    "Stop": [
      {
        "hooks": [{ "type": "command", "command": "bash tools/claude_hook_stop.sh", "timeout": 5, "statusMessage": "CodeDNA v0.9 — checking session end protocol..." }]
      },
      {
        "hooks": [{
          "type": "command",
          "command": "echo '{\"systemMessage\": \"[CodeDNA] Remember: update .codedna with a new agent_sessions entry (agent, provider, date, session_id, task, changed, visited, message).\"}'",
          "timeout": 5
        }]
      }
    ]
  }
}
```

The hook scripts (`tools/claude_hook_codedna.sh`, `tools/claude_hook_stop.sh`) are downloaded by `install.sh claude-hooks` or available at [`tools/`](../tools/).

---

#### Troubleshooting for agents

- **Hook not firing?** Verify `.claude/settings.local.json` (or `.claude/settings.json`) is valid JSON: `jq . .claude/settings.local.json`
- **`jq` not found?** Install it: `brew install jq` (macOS) or `apt install jq` (Linux)
- **`bash tools/claude_hook_codedna.sh` fails?** Run `install.sh claude-hooks` to download the scripts, or check they exist in `tools/`
- **Settings file already exists and hooks are missing?** Merge the `"hooks"` block manually — never overwrite the whole file, existing permissions will be lost
- **SessionStart not triggering?** This hook only fires when a new session starts. Open `/hooks` in Claude Code UI to reload config, or restart the session

---

## Cursor

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh) cursor-hooks
```

Installs `.cursorrules` + enforcement hooks in `.cursor/hooks/` — Cursor runs them automatically on every file edit and when the agent stops. Requires **Cursor v1.7+**.

| Hook | Event | What it does |
|---|---|---|
| `after-file-edit.sh` | After every file edit | Validates CodeDNA header on source files |
| `stop.sh` | When agent finishes | Reminds to update `.codedna` and commit with AI trailers |

For Cursor v0.43+, you can also place `.cursorrules` under `.cursor/rules/`:
```bash
mkdir -p .cursor/rules && cp .cursorrules .cursor/rules/codedna.mdc
```

---

## GitHub Copilot

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh) copilot-hooks
```

Installs `copilot-instructions.md` + enforcement hooks in `.github/hooks/` — Copilot runs them automatically at session start/end and after every tool use.

| Hook | Event | What it does |
|---|---|---|
| `session_start` | Session begins | Reads `.codedna`, injects project context |
| `post_tool_use` | After every file write/edit | Validates CodeDNA header on source files |
| `session_end` | Session finishes | Reminds to update `.codedna` and commit with AI trailers |

---

## Cline (VSCode Extension)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh) cline-hooks
```

Installs `.clinerules` + enforcement hooks in `.clinerules/hooks/` — Cline runs them automatically on task start and after every file write/edit. Requires **Cline v3.36+**.

| Hook | Event | What it does |
|---|---|---|
| `TaskStart.sh` | Task begins | Reads `.codedna`, injects project context |
| `PostToolUse.sh` | After every file write/edit | Validates CodeDNA header on source files |

---

## Windsurf (Codeium)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh) windsurf
```

Installs `.windsurfrules` in your repo root — Windsurf reads it automatically and applies CodeDNA rules to Cascade sessions.

---

## OpenCode

Install with one command — installs **both** the instruction file and the enforcement plugin:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh) opencode
```

This creates two files in your project:

| File | Purpose |
|---|---|
| `AGENTS.md` | CodeDNA v0.9 instructions — loaded automatically by OpenCode as system prompt |
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
bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh) claude
```

Installs `CLAUDE.md` in your repo root, then pass it as system prompt at launch:

```bash
aider --system-prompt "$(cat CLAUDE.md)"
```

Or add it permanently to `.aider.conf.yml`:
```yaml
system_prompt: CLAUDE.md
```

---

## Antigravity / Custom Agents

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh) agents
```

Installs `.agents/workflows/codedna.md` — Antigravity and compatible agent frameworks read workflow files from `.agents/workflows/` automatically.

---

## What changes after install?

| Before | After (instructions only) | After (with hooks) |
|---|---|---|
| AI creates files with no metadata | AI knows the format and tries to annotate | AI is reminded on every write — annotations validated automatically |
| AI edits break cross-file deps | AI reads `used_by:` and `Rules:` before editing | Same, plus PostToolUse validates the edit |
| AI skips related files | AI follows `used_by:` graph | Same |
| AI forgets annotations on long sessions | Possible — depends on context window | Impossible — hooks fire regardless of session length |
| No session audit trail | Agent writes `.codedna` entry at end | Hook reminds at stop, blocks commit without AI trailers |

**Tools with active enforcement (hooks):** Claude Code, Cursor (v1.7+), GitHub Copilot, Cline (v3.36+), OpenCode
**Tools with instructions only:** Windsurf, Aider, Antigravity

---

## Verify it's working

Ask your AI tool to create a new Python file. The first block should be the module docstring with `exports:`, `used_by:`, and `rules:` fields, before any imports.

If it starts with imports instead — paste the integration file content directly into the system prompt or chat context.
