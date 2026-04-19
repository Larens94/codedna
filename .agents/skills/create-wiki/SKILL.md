---
name: create-wiki
description: Maintain `codedna-wiki.md` as the semantic companion to `.codedna` (L0) for CodeDNA projects.
model: haiku
preferred-model: haiku
model-hint: "Use the smallest available model. This task is read-heavy markdown synthesis — Haiku or equivalent (GPT-4o-mini, Gemini Flash, Qwen-turbo). Never use Opus/o3/Pro for wiki-only tasks."
---

# Create Wiki

Use this skill when the user asks to create, refresh, repair, or extend the project wiki, or when a major structural change means the semantic map is now stale.

## Core idea

This skill follows the `llm-wiki` pattern: the wiki is a persistent compiled knowledge artifact, not a retrieval cache rebuilt from scratch at every question.

For CodeDNA projects:

- `.codedna` is Level 0 structural truth
- source file docstrings are local truth
- `codedna-wiki.md` is the semantic synthesis layer

The wiki should explain how the codebase actually hangs together, where the hotspots are, and what an agent should understand before making changes.

---

## Sub-agent dispatch (Claude Code)

**In Claude Code: do not perform wiki work inline.** Spawn the dedicated wiki-keeper sub-agent to keep wiki maintenance isolated from your context window:

```
Use the Agent tool with subagent_type="codedna-wiki-keeper"
```

The wiki-keeper runs on a lightweight model (Haiku), isolates all wiki reads from the caller's context, and returns a compact summary when done.

Use the wiki-keeper for:
- Refreshing or updating `codedna-wiki.md` after refactors or architecture changes
- Reading and summarizing the codebase at a high level
- Answering onboarding questions using the wiki as the primary source

Pass the task as a clear prompt, for example:
- `"Refresh codedna-wiki.md — a major refactor just landed in codedna_tool/cli.py"`
- `"Read codedna-wiki.md and summarize the architecture for onboarding"`
- `"Update the hotspots section — we just added the wiki subcommand"`

If the `.claude/agents/codedna-wiki-keeper.md` file is missing, run `codedna wiki` first to scaffold it.

---

## Direct workflow (Codex, OpenCode, other runtimes)

When sub-agent spawning is not available, perform wiki work directly using this workflow.

### Inputs

Read in this order:

1. `.codedna`
2. `.planning/codebase/*.md` when available
3. `README.md`, `SPEC.md`, `QUICKSTART.md`, `AGENTS.md` when relevant
4. only the module docstrings or focused files needed for the current update

### Output

Update exactly one semantic artifact:

- `codedna-wiki.md`

### Rules

- Treat `.codedna` as authoritative for package structure and session history
- Do not invent structural relationships that contradict `.codedna`
- Do not dump raw file inventories into the wiki unless they help navigation
- Prefer semantic synthesis: workflows, subsystem boundaries, contradictions, hotspots, and maintenance cues
- If `.planning/codebase/` exists, use it as intermediate context but keep `codedna-wiki.md` shorter and higher-signal
- Preserve any explicit "open questions", "contradictions", or "maintenance hotspots" sections
- When you discover drift between L0 and the semantic view, call it out explicitly

### Recommended structure for `codedna-wiki.md`

- Project identity
- Relationship to L0 (`.codedna`)
- Semantic topology
- Operational workflows
- Testing and validation model
- Hotspots and likely drift
- Refresh protocol

### Update workflow

1. Re-read `.codedna`
2. Re-read `.planning/codebase/*.md` if present
3. Inspect only the files needed to refresh the affected semantic sections
4. Update `codedna-wiki.md`
5. Make sure the wiki still complements `.codedna` instead of duplicating it

### When to refresh

- after `codedna init` on a repo
- after major refactors
- after architecture or CLI workflow changes
- after generating or refreshing `.planning/codebase/`
- when a user asks for onboarding, architecture explanation, or a repo map
