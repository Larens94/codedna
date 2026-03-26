# CodeDNA Plugin for Claude Code

Extends Claude Code with the [CodeDNA](https://github.com/Larens94/codedna) in-source AI communication protocol.

## What it does

- **/codedna:init** — annotate all unannotated files in the project ✅
- **/codedna:check** — coverage report: which files lack annotation, which `used_by:` references are stale ✅
- **/codedna:manifest** — full architectural map in one pass (replaces 10-20 file reads) 🔜 planned
- **/codedna:impact `<file>`** — cascade dependency chain before a refactor 🔜 planned
- **Automatic hook** — warns after every Write/Edit if the saved file lacks a CodeDNA annotation ✅
- **codedna-reviewer agent** — on-demand compliance reviewer, invokable via `/agents` ✅

## Install

```bash
claude plugin install codedna
```

Or test locally:

```bash
claude --plugin-dir ./codedna-plugin
```

## Usage

```
/codedna:init               # annotate all unannotated files
/codedna:check              # find unannotated files and stale used_by: refs
```

> `/codedna:manifest` and `/codedna:impact` are planned for a future release.

## What is CodeDNA?

CodeDNA is an inter-agent communication protocol embedded in source files. Every file carries a structured annotation (module docstring) that tells AI agents:

- **`exports:`** — what this file provides publicly
- **`used_by:`** — who depends on it (reverse dependency graph)
- **`rules:`** — hard constraints that must never be violated
- **`agent:`** — append-only session log from previous AI agents

This gives any AI agent instant architectural context without reading dozens of files.

See the [full spec](https://github.com/Larens94/codedna/blob/main/SPEC.md) for details.

## Requirements

- Claude Code 1.0.33+
- Python 3.8+ (for the annotation check hook)
