# CodeDNA Plugin for Claude Code

Extends Claude Code with the [CodeDNA](https://github.com/Larens94/codedna) in-source AI communication protocol.

## What it does

- **/codedna:init** — annotate all unannotated files in the project
- **/codedna:check** — coverage report: which files lack annotation, which `used_by:` references are stale
- **/codedna:manifest** — full architectural map in one pass (replaces 10-20 file reads)
- **/codedna:impact `<file>`** — cascade dependency chain before a refactor
- **4 automatic hooks** — SessionStart (reads `.codedna`), PreToolUse (reminds to read docstring), PostToolUse (validates L1 + L2 annotations on every Write/Edit), Stop (session end reminder)
- **codedna-reviewer agent** — on-demand compliance reviewer, invokable via `/agents`

## Install

```bash
claude plugin marketplace add Larens94/codedna
claude plugin install codedna@codedna
```

Or test locally:

```bash
claude --plugin-dir ./codedna-plugin
```

## Usage

```
/codedna:init               # annotate all unannotated files
/codedna:check              # find unannotated files and stale used_by: refs
/codedna:manifest           # show project architecture map
/codedna:impact <file>      # show who depends on this file
```

## What is CodeDNA?

CodeDNA is an inter-agent communication protocol embedded in source files. Every file carries a structured annotation that tells AI agents:

- **`exports:`** — what this file provides publicly
- **`used_by:`** — who depends on it (reverse dependency graph)
- **`rules:`** — hard constraints that must never be violated
- **`agent:`** — append-only session log from previous AI agents
- **`message:`** — agent-to-agent chat: open observations, promoted to `rules:` or dismissed

This gives any AI agent instant architectural context without reading dozens of files. Supports 9 languages + 7 template engines.

See the [full spec](https://github.com/Larens94/codedna/blob/main/SPEC.md) for details.

## Requirements

- Claude Code
- Python 3.11+ (for the annotation check hook)
