# CodeDNA Benchmark — Methodology & Test Preparation

## Overview

This benchmark measures how CodeDNA annotations affect an AI agent's ability to **locate the correct files** for a code modification task. It compares three conditions:

- **Control**: agent navigates a vanilla Django codebase (no annotations)
- **CodeDNA**: agent navigates the same codebase with curated CodeDNA v0.7 annotations
- **Agent-Annotated**: agent navigates a codebase where another LLM agent auto-generated the CodeDNA annotations (no human curation — tests the protocol end-to-end)

All three conditions use the same LLM, tools, file size limits, and temperature.

---

## Test Preparation

### 1. Task Selection

Tasks are selected from [SWE-bench](https://www.swebench.com/), a public benchmark of real GitHub issues. We selected 5 multi-file Django tasks where the ground truth requires modifying 7–10 files across multiple packages.

| Instance ID | Files | Description |
|---|---|---|
| django__django-14480 | 7 | Add XOR support to Q() and QuerySet() |
| django__django-13495 | 7 | Fix Trunc() tzinfo param for non-DateTimeField |
| django__django-12508 | 8 | Add `dbshell -c SQL` argument support |
| django__django-11991 | 9 | Add INCLUDE clause support to Index |
| django__django-11808 | 10 | Fix `__eq__` to return NotImplemented |

### 2. CodeDNA Annotation (codedna variant)

The codedna variant has two layers of annotation:

#### a) Module headers (every Python file)
Each file gets a docstring header with:
- `exports:` — public API symbols
- `used_by:` — files that import from this module (the navigation graph)
- `rules:` — architectural constraints written by developers with knowledge of the codebase

#### b) `rules:` field
Written by developers with knowledge of Django's architecture, simulating the knowledge accumulation that occurs through repeated use of the codebase. **Rules are not task-specific** — they describe real architectural constraints (e.g., "SQLite has no ALTER COLUMN; schema changes recreate the table") that would be true regardless of which task is being evaluated.

> **Transparency note**: The `rules:` field was populated for the `django/db/` subtree. Rules describe general Django patterns and do not reference specific bugs or the names of evaluation tasks.

### 3. Agent-Annotated Variant (agent_annotated variant)

The `agent_annotated` variant demonstrates the protocol working end-to-end with zero human knowledge injection:

1. Start from a clean copy of the `control` codebase
2. Run `setup_agent_annotated.py` — an LLM agent auto-generates CodeDNA headers for each file
3. Benchmark agent navigates using only these auto-generated annotations

Annotation cost (chars generated, time, files annotated) is stored in `agent_annotated/.annotation_cost.json` per task and reported by `analyze_multi.py --annotation-cost`.

### 4. Control Variant

The control variant uses the exact same Django codebase but **without any CodeDNA annotations** — no module headers, no rules. Files are plain Django source code.

### 5. Agent Configuration

| Parameter | Value |
|-----------|-------|
| READ_FILE_LIMIT | 12,000 characters |
| GREP_LIMIT | 4,000 characters |
| Max turns | 30 |
| Temperature | 0.0 (single run) or 0.1 (multi-run) |
| Tools | `list_files`, `read_file`, `grep` |

For statistical significance, each condition is run **3 times per task** with `temperature=0.1`. Mean and standard deviation of F1 are reported.

---

## Metrics

- **F1 (read)**: harmonic mean of recall and precision, computed on **files actually read** by the agent vs ground truth files
- **F1 (proposed)**: same metric but on files the agent **proposes to modify** in its final response
- **Token consumption**: total characters read across all `read_file` calls
- **Annotation cost**: total characters generated to produce auto-annotations (agent_annotated only)

Primary metric: **F1 (read)** — it measures pure navigation efficiency without penalising the agent for mentioning files it didn't read.

### Statistical Test

We use the **Wilcoxon signed-rank test** (one-tailed, H1: annotated condition > control) over F1 pairs across the 5 tasks. The normal approximation is used for p-values; for N<5 we report W+ directly and note that exact p requires a lookup table.

---

## Running the Benchmark

```bash
# 1. Set up agent-annotated variants (one-time)
GEMINI_API_KEY=... python swebench/setup_agent_annotated.py

# 2. Run benchmark (3 runs per task, temperature=0.1)
GEMINI_API_KEY=... python swebench/run_agent_multi.py \
  --model gemini-2.5-flash --runs 3 --temperature 0.1

# 3. Analyse results
python swebench/analyze_multi.py
python swebench/analyze_multi.py --qualitative       # which rules guided the agent
python swebench/analyze_multi.py --annotation-cost   # auto-annotation overhead
```

---

## Preliminary Results (1 task, N=1 run)

| Model | Control F1 | CodeDNA F1 | Δ F1 | Token Savings |
|-------|-----------|------------|------|---------------|
| Gemini 2.5 Flash | 43% | 67% | **+24%** | -33% |
| GPT-5.3 Codex | 40% | 55% | **+15%** | +32% |

> **Note**: These are preliminary results on a single task (django__django-14480), single run.
> Statistical significance requires completing all 5 tasks with ≥3 runs.

---

## Limitations & Disclaimers

1. **Sample size**: N=5 tasks is the minimum for meaningful Wilcoxon statistics. Results across all 5 tasks are required before claiming significance.
2. **Rules authorship (codedna)**: `rules:` were written by developers with Django architecture knowledge. They were not written to favour specific tasks, but describe real architectural constraints.
3. **Rules authorship (agent_annotated)**: fully automatic — no human involvement after setup. Represents the realistic adoption path for new codebases.
4. **Annotation effort**: Annotation cost (chars generated, time) is measured and reported for the `agent_annotated` condition. Curated `codedna` annotation cost is not measured but is a real consideration for adoption.
5. **Single domain**: All tasks are from Django (Python web framework). Generalisation to other languages/frameworks is not tested in this benchmark.

---

## File Structure

```
benchmark_agent/
├── BENCHMARK_NOTES.md                  ← this file
├── benchmark_server.py                 ← HTTP server + dashboard
├── benchmark_ui.html                   ← web dashboard
├── projects_swebench/                  ← Django repos (3 variants per task)
│   └── django__django-XXXXX/
│       ├── control/                    ← vanilla codebase
│       ├── codedna/                    ← curated CodeDNA annotations
│       └── agent_annotated/            ← auto-generated annotations
│           └── .annotation_cost.json  ← cost metadata
├── runs/                               ← results per model
│   └── <model>/results.json
└── swebench/
    ├── run_agent_multi.py              ← agent runner (3 conditions)
    ├── analyze_multi.py                ← results + Wilcoxon + qualitative
    ├── setup_agent_annotated.py        ← creates agent_annotated/ variants
    ├── tasks.json                      ← task definitions
    └── annotator.py                    ← CodeDNA annotation generator (manual)
```
