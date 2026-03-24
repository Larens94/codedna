# CodeDNA Plugin for Claude Code

Extends Claude Code with the [CodeDNA](https://github.com/Larens94/codedna) in-source AI communication protocol.

## What it does

- **/codedna:check** — coverage report: which files lack annotation, which `used_by:` references are stale
- **/codedna:manifest** — full architectural map of the project in one pass (replaces 10-20 file reads)
- **/codedna:impact `<file>`** — cascade dependency chain before a refactor
- **Automatic hook** — warns after every Write/Edit if the saved file lacks a CodeDNA annotation
- **codedna-reviewer agent** — on-demand compliance reviewer, invokable via `/agents`

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
/codedna:check              # find unannotated files
/codedna:manifest           # architectural map — run at session start
/codedna:impact src/api.py  # who depends on this file?
```

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
