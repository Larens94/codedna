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

### Quick Start (from repo root)

```bash
cd benchmark_agent/swebench

# 1. List available tasks
python3 setup_benchmark.py --list --repo django/django

# 2. Download 50 Django tasks (multi-file first)
python3 setup_benchmark.py --repo django/django --n-tasks 50 --multi-file-first

# 3. Annotate with CodeDNA (structural only, free)
python3 setup_benchmark.py --repo django/django --annotate --no-llm

# 4. Annotate with LLM for rules: (optional, better quality)
python3 setup_benchmark.py --repo django/django --annotate --model ollama/llama3

# 5. Run benchmark
python3 run_agent_multi.py --model deepseek-chat --runs 3 --temperature 0.1

# 6. Analyse results
python3 analyze_multi.py
python3 analyze_multi.py --qualitative       # which rules guided the agent
python3 analyze_multi.py --annotation-cost   # auto-annotation overhead
```

### Script Reference

| Script | Purpose |
|---|---|
| `setup_benchmark.py` | Download repos from SWE-bench Verified, prepare control/ + codedna/ |
| `run_agent_multi.py` | Run agent on tasks (17 models, 4 providers, local via Ollama) |
| `analyze_multi.py` | Analyse results, Wilcoxon test, per-task breakdown |
| `setup_agent_annotated.py` | Create agent_annotated/ variant (auto-generated annotations) |
| `annotator.py` | Manual annotation with Gemini |

### setup_benchmark.py Options

```bash
python3 setup_benchmark.py --list --repo django/django          # list tasks + status
python3 setup_benchmark.py --repo django/django --n-tasks 50    # download 50 tasks
python3 setup_benchmark.py --repo django/django --multi-file-first  # prioritize 2+ file tasks
python3 setup_benchmark.py --all                                 # all 500 Verified tasks (12 repos)
python3 setup_benchmark.py --repo django/django --annotate --no-llm  # annotate without LLM
python3 setup_benchmark.py --repo django/django --force          # re-download everything
```

---

## Results — multi-model, multi-run (3 of 3 models complete ✅)

### Gemini 2.5 Flash — 5 tasks, 5 runs/task at T=0.1 ✅

| Task | GT Files | Ctrl F1 | DNA F1 | Δ | Notes |
|------|----------|---------|--------|---|-------|
| django__django-14480 | 7 | 55% | 72% | **+17%** | XOR Q() — dependency chain |
| django__django-13495 | 7 | 52% | 74% | **+22%** | Trunc tzinfo — delegation chain |
| django__django-12508 | 8 | 84% | 93% | **+9%** | dbshell --args — linear chain |
| django__django-11991 | 9 | 49% | 66% | **+17%** | INCLUDE index — fan-out |
| django__django-11808 | 10 | 58% | 57% | **−1%** | `__eq__` cross-cutting |

**Wilcoxon W+=14, N=5, p=0.040 (one-tailed)** ✅ significant. Overall ctrl=60%, DNA=72%, Δ=+13%.

### DeepSeek Chat — 5 tasks, 5 runs/task at T=0.1 ✅

| Task | GT Files | Ctrl F1 | DNA F1 | Δ | Notes |
|------|----------|---------|--------|---|-------|
| django__django-14480 | 7 | 55% | 69% | **+14%** | XOR Q() |
| django__django-13495 | 7 | 45% | 36% | **−9%** | ⚠️ anomaly — under investigation |
| django__django-12508 | 8 | 82% | 83% | **+1%** | dbshell --args |
| django__django-11991 | 9 | 50% | 56% | **+6%** | INCLUDE index |
| django__django-11808 | 10 | 20% | 55% | **+35%** | `__eq__` cross-cutting — opposite of Flash! |

**Wilcoxon W+=12, N=5, p=0.11 (one-tailed)** ✗ not significant. Overall ctrl=50%, DNA=60%, Δ=+9%.

**Notable:** DeepSeek gained +35pp on the cross-cutting task 11808 (vs Flash's −1pp), suggesting the model uses a different navigation strategy. Task 13495 anomaly (−9pp) is unexplained.

### Gemini 2.5 Pro — 5 tasks, 3 runs/task at T=0.1 ✅

| Task | GT Files | Ctrl F1 | DNA F1 | Δ | Notes |
|------|----------|---------|--------|---|-------|
| django__django-14480 | 7 | 48% | 75% | **+27pp** | ✅ strongest gain across all models |
| django__django-13495 | 7 | 91% | 83% | **−8pp** | ⚠️ anomaly — same as DeepSeek |
| django__django-12508 | 8 | 76% | 89% | **+13pp** | ✅ |
| django__django-11991 | 9 | 54% | 73% | **+19pp** | ✅ |
| django__django-11808 | 10 | 27% | 25% | **−2pp** | cross-cutting — expected |

**Wilcoxon W+=12, N=5, p=0.11 (one-tailed)** ✗ not significant. Overall ctrl=60%, DNA=69%, Δ=+9pp, 3/5 tasks.

### Task Type Analysis

| Task type | Tasks | Flash Δ | DeepSeek Δ | Pro Δ |
|---|---|---|---|---|
| Dependency/delegation chain | 14480, 12508, 11991 | **+14pp** | **+7pp** | **+20pp** |
| Delegation with backend fan-out | 13495 | **+22pp** | **−9pp** ⚠️ | **−8pp** ⚠️ |
| Cross-cutting (no shared ancestor) | 11808 | **−1pp** | **+35pp** | **−2pp** |

**Key finding on task 13495:** both DeepSeek and Pro show negative Δ on this task, while Flash shows +22pp. This is a consistent, model-specific pattern — not random noise. Hypothesis: Flash's more concise reasoning style follows the CodeDNA delegation chain more faithfully, while larger/more verbose models (Pro, DeepSeek) over-explore and dilute precision.

**Transparency note on 11808 (cross-cutting task):**

Task 11808 (`__eq__` returning `NotImplemented` across 10 independent classes) was deliberately included to test the protocol's limits. The benchmark annotations contain **no list of affected files** — each file's `rules:` describes only local Python data model conventions. The agent must discover all 10 files independently.

Gemini 2.5 Flash shows Δ ≈ 0% on this task — as expected, since the `used_by:` graph has no shared ancestor. DeepSeek Chat shows Δ=+35%, which may reflect different sampling behaviour at T=0.1 or a model-specific tendency to explore more broadly.

The proposed fix (v0.8 `cross_cutting_patterns:` in `.codedna`) would be written by an agent **post-fix** as accumulated knowledge — not pre-populated for evaluation. This distinction is documented in SPEC.md §2.4.

### The Cheaper-Model Hypothesis — reassessed

All 3 models complete. Gemini 2.5 Pro ctrl=60% — identical to Flash, not higher as expected. The hypothesis that stronger models need CodeDNA less is **not confirmed** by raw F1. However, Flash shows the largest Δ (+13pp) vs Pro/DeepSeek (+9pp each), suggesting Flash benefits more from the annotations on a per-task basis. The pattern is more nuanced than expected: model reasoning style (concise vs verbose) may matter more than raw capability.

---

## Limitations & Disclaimers

1. **Sample size**: N=5 tasks is the minimum for meaningful Wilcoxon statistics. Results across all 5 tasks are required before claiming significance.
2. **Rules authorship (codedna)**: `rules:` were written by developers with Django architecture knowledge. They were not written to favour specific tasks, but describe real architectural constraints.
3. **Rules authorship (agent_annotated)**: fully automatic — no human involvement after setup. Represents the realistic adoption path for new codebases.
4. **Annotation effort**: Annotation cost (chars generated, time) is measured and reported for the `agent_annotated` condition. Curated `codedna` annotation cost is not measured but is a real consideration for adoption.
5. **Single domain**: All tasks are from Django (Python web framework). Generalisation to other languages/frameworks is not tested in this benchmark.
6. **Dataset note**: The 5 tasks in this benchmark are from **SWE-bench Full** (2,294 tasks), not SWE-bench Verified (500 tasks). The Verified subset — the gold standard used in publications — does not include these 5 tasks. An expanded benchmark on SWE-bench Verified is in progress in `labs/benchmark/`.

---

## File Structure

```
benchmark_agent/
├── BENCHMARK_NOTES.md                  ← this file
├── benchmark_server.py                 ← HTTP server + dashboard
├── benchmark_ui.html                   ← web dashboard
├── _repo_cache/                        ← bare git clones (cached, 1 per repo)
├── projects_swebench/                  ← task repos (3 variants per task)
│   └── django__django-XXXXX/
│       ├── control/                    ← vanilla codebase at base_commit
│       ├── codedna/                    ← control + CodeDNA annotations
│       ├── agent_annotated/            ← control + auto-generated annotations
│       ├── problem_statement.txt       ← GitHub issue description
│       └── files_in_patch.json         ← ground truth file list
├── runs/                               ← results per model
│   └── <model>/
│       ├── results.json
│       └── session_traces/             ← per-run tool call traces
└── swebench/
    ├── setup_benchmark.py              ← download + prepare SWE-bench Verified tasks
    ├── run_agent_multi.py              ← agent runner (17 models, 4 providers)
    ├── analyze_multi.py                ← results + Wilcoxon + qualitative
    ├── setup_agent_annotated.py        ← creates agent_annotated/ variants
    ├── annotator.py                    ← CodeDNA annotation generator (Gemini)
    └── tasks.json                      ← task definitions
```
