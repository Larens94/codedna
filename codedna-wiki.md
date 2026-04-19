# CodeDNA Wiki

Last refreshed: 2026-04-17
Primary structural source: [.codedna](/Users/elettrofranky/python-projects/codedna/.codedna)
Semantic support artifacts: [.planning/codebase/](/Users/elettrofranky/python-projects/codedna/.planning/codebase)

## Identity

`codedna` is both:

- a shipping CLI/tooling package for in-source agent annotations
- a research repo that benchmarks and documents the protocol on real tasks

The product core is small and centered on `codedna_tool/`; the repo surface is much larger because it also contains experiments, benchmark harnesses, papers, and integration templates.

## How this wiki relates to L0

Use `.codedna` as Level 0 truth for:

- project identity
- package boundaries
- recent agent sessions

Use this wiki for:

- semantic topology
- mental model of the product and research layers
- hotspots, drift risks, and navigation advice

If this file and `.codedna` disagree on structure, trust `.codedna` and refresh this file.

## Semantic topology

### 1. Product engine

The operational heart of the repo is [codedna_tool/cli.py](/Users/elettrofranky/python-projects/codedna/codedna_tool/cli.py). It owns:

- command dispatch
- Python scanning and dependency graph building
- docstring injection
- non-Python annotation orchestration
- install-time integration setup
- manifest generation

This is the highest-leverage file for product changes and the riskiest place for regressions.

### 2. Language adapter layer

`codedna_tool/languages/` is the extension seam. The repo supports a hybrid parsing model:

- tree-sitter for strong structural extraction where bindings exist
- regex fallback adapters for resilience and portability

The stable contract is [codedna_tool/languages/base.py](/Users/elettrofranky/python-projects/codedna/codedna_tool/languages/base.py).

### 3. Protocol and documentation layer

The repo’s actual “product spec” is spread across:

- [README.md](/Users/elettrofranky/python-projects/codedna/README.md)
- [QUICKSTART.md](/Users/elettrofranky/python-projects/codedna/QUICKSTART.md)
- [SPEC.md](/Users/elettrofranky/python-projects/codedna/SPEC.md)
- [AGENTS.md](/Users/elettrofranky/python-projects/codedna/AGENTS.md)

This layer matters operationally because the tool exists to instantiate the protocol described there.

### 4. Validation layer

The repo protects itself mainly through:

- CLI subprocess tests in [tests/test_cli.py](/Users/elettrofranky/python-projects/codedna/tests/test_cli.py)
- refresh and validator tests in `tests/test_refresh.py` and `tests/test_validator.py`
- adapter regression suites in `tests/test_language_adapters.py` and `tests/test_integration_langs.py`
- standalone validation logic in [tools/validate_manifests.py](/Users/elettrofranky/python-projects/codedna/tools/validate_manifests.py)

### 5. Research and proof layer

The benchmark and experiment surfaces exist to demonstrate or stress the protocol:

- `benchmark_agent/` for benchmark harnesses and live benchmark UI/server
- `experiments/` for multi-agent product experiments
- `paper/`, `thesis/`, `docs/` for publication and visualization artifacts

These directories are important context, but they should not dominate everyday product edits.

## Operational workflows

### Install and setup

`codedna install` prepares a project with:

- prompt templates for agent runtimes
- optional hook setup
- a starter `.codedna`

This path depends on remote template fetches from GitHub raw URLs.

### Annotation flow

`codedna init` is the first-write path:

- scan files
- build reverse dependency graph
- write L1 / L2 annotations

In this fork, it also scaffolds the semantic wiki layer:

- `.agents/skills/create-wiki/SKILL.md`
- `codedna-wiki.md`

### Maintenance flow

- `codedna update` annotates only missing files
- `codedna refresh` repairs structural drift without touching semantic fields
- `codedna check` measures coverage
- `codedna manifest` regenerates `.codedna` package structure while preserving session history

## Testing and validation model

The repo optimizes for:

- idempotent annotation
- structural correctness of headers
- adapter coverage across many languages

It is less opinionated, today, about validating higher-level semantic synthesis. That is one of the gaps this wiki layer is meant to reduce.

## Hotspots and likely drift

### Monolithic CLI

`codedna_tool/cli.py` changes easily accumulate unrelated responsibilities. Any new feature should either stay very small or carve out a helper boundary.

### Remote integration templates

Install-time prompt files and hooks are fetched remotely. Template drift can desynchronize packaged behavior from repository expectations.

### Research noise

`experiments/` is much larger than the production package. Agents can burn context there if they do not anchor on `.codedna`, `.planning/codebase/`, and `codedna_tool/` first.

### Semantic gap

Before this fork, the repo had structural truth and local file truth but no durable semantic synthesis artifact. This file is intended to close that gap.

## Refresh protocol

Refresh this wiki when:

- `.planning/codebase/` is regenerated
- `codedna_tool/cli.py` changes meaningfully
- install/integration strategy changes
- language adapter architecture changes
- test strategy changes

When refreshing:

1. re-read `.codedna`
2. re-read `.planning/codebase/*.md`
3. inspect only the changed files needed to update the semantic model
4. keep this file compact and explanatory rather than exhaustive
