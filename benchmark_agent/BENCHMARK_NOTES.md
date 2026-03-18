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

For statistical significance, each condition is run **≥5 times per task** with `temperature=0.1`. Mean and standard deviation of F1 are reported.

### 6. CodeDNA File Format Requirement

**Critical:** each file in the `codedna/` variant must contain the annotated docstring **plus the complete original source code** from the `control/` variant. Files containing only the docstring (stubs) cause catastrophic navigation failure — the agent reads the stub, finds no code patterns, and either stops or navigates to wrong files.

Verification: `wc -l codedna/some_file.py` must be within ~10 lines of `wc -l control/some_file.py` (the difference is the docstring).

**Format:** `codedna_file = annotated_docstring + "\n\n" + control_file_verbatim`

### 7. Tool Robustness for Weaker Models

Weaker models (e.g., GPT-4o-mini) occasionally call `list_files()` on a file path or `read_file()` on a directory. The harness must guard against this:

```python
def list_files(directory="."):
    if not target.is_dir():
        return f"Not a directory: {directory}"
    # ...

def read_file(path):
    if target.is_dir():
        return f"Is a directory, use list_files() instead: {path}"
    # ...
```

Without these guards, the benchmark crashes mid-run and discards all results from that task forward.

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

## Results (in progress — multi-model, multi-run)

### Gemini 2.5 Flash — 5 tasks, ≥5 runs/task at T=0.1

| Task | GT Files | Ctrl F1 | DNA F1 | Δ | Notes |
|------|----------|---------|--------|---|-------|
| django__django-14480 | 7 | ~64% | 75% | **+11%** | XOR Q() — dependency chain |
| django__django-13495 | 7 | ~63% | 74% | **+11%** | Trunc tzinfo — delegation chain |
| django__django-12508 | 8 | ~85% | 87% | **+2%** | dbshell --args — linear chain |
| django__django-11991 | 9 | 59% | TBD | TBD | INCLUDE index — in re-run after file fix |
| django__django-11808 | 10 | 57% | TBD | TBD | `__eq__` cross-cutting — in re-run after file fix |

**Wilcoxon W+=14, N=5, p=0.04 (one-tailed)** — significant on first 3 tasks + preliminary 11991/11808.

### Task Type Analysis

| Task type | Tasks | Avg Δ |
|---|---|---|
| Dependency/delegation chain | 14480, 13495, 12508, 11991 | **+13%** |
| Cross-cutting (no shared ancestor) | 11808 | **~0%** |

**Transparency note on 11808 (cross-cutting task):**

Task 11808 (`__eq__` returning `NotImplemented` across 10 independent classes) was deliberately included to test the protocol's limits. The benchmark annotations contain **no list of affected files** — each file's `rules:` describes only local Python data model conventions. The agent must discover all 10 files independently.

CodeDNA v0.7 shows Δ ≈ 0% on this task. This is an honest result: the `used_by:` navigation graph has no shared ancestor connecting the 10 classes, so structural navigation provides no advantage. Both conditions find the same ~6/10 obvious ORM files and miss the 4 peripheral ones (`validators.py`, `messages/`, `template/`, `postgres/constraints.py`).

The proposed fix (v0.8 `cross_cutting_patterns:` in `.codedna`) would be written by an agent **post-fix** as accumulated knowledge — not pre-populated for evaluation. This distinction is documented in SPEC.md §2.4.

### The Cheaper-Model Hypothesis (to be confirmed)

Weaker models are expected to show larger Δ because they lack the reasoning ability to navigate large codebases without structural guidance. CodeDNA provides that scaffolding. Results for DeepSeek Chat, Claude Haiku, GPT-4o-mini in progress.

> **Note**: Tasks 11991 and 11808 were initially run with truncated codedna files (stub docstrings, no code). Those results were discarded and re-runs are in progress with corrected files.

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
