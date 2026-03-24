# Plugin Submission — claude.com/plugins

Submit at: https://claude.ai/settings/plugins/submit

---

## Fields to fill

**Plugin name**
codedna

**Tagline** (1 sentence)
Annotate any codebase with AI context in one command — no API key, no extra cost.

**Description** (shown in directory listing)
CodeDNA adds four commands to Claude Code that make any codebase AI-navigable.
/codedna:init annotates every file with exports:, used_by:, and rules: — Claude reads
and writes directly using your existing subscription, zero extra cost.
Supports Python, TypeScript, Go, Rust, Java, and Ruby.

**Repository URL**
https://github.com/Larens94/codedna

**Plugin directory in repo**
codedna-plugin/

**Homepage / docs**
https://github.com/Larens94/codedna

**Category**
Developer Tools

**Keywords**
codedna, annotations, ai-agents, multi-file, context, protocol, architecture

---

## Commands included

| Command | Description |
|---|---|
| `/codedna:init [path]` | Annotate all unannotated source files using the current Claude session |
| `/codedna:check [path]` | Coverage report — find unannotated files and stale used_by references |
| `/codedna:manifest [path]` | Full architectural map in one pass |
| `/codedna:impact <file>` | Cascade dependency chain before refactoring |

## Hook included

PostToolUse on Write/Edit/MultiEdit — notifies Claude when a saved file is missing
a CodeDNA annotation.

## Agent included

codedna-reviewer — lightweight compliance reviewer (Haiku, read-only).

---

## Why users should install this

Without CodeDNA, every AI session starts from scratch. The agent re-reads files,
re-discovers constraints, and repeats the same mistakes across sessions.

With CodeDNA:
- used_by: tells Claude which files to check before editing
- rules: encodes constraints discovered by previous agents
- agent: logs what each AI session found and changed

One install. Every future Claude session benefits from the annotations.
Zero API key. Zero extra cost.
