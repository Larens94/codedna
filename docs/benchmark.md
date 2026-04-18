# Benchmark Results — SWE-bench Multi-Model

5 real Django issues from [SWE-bench](https://github.com/princeton-nlp/SWE-bench), tested across multiple LLMs. Same prompt, same tools, same tasks. **Only difference: CodeDNA annotations.**

> **Metric: File Localization F1** — harmonic mean of recall and precision on files read vs ground truth. Isolates the navigation bottleneck that precedes code generation.

> **Statistical test:** Wilcoxon signed-rank test (one-tailed, H1: CodeDNA > Control) over F1 pairs across 5 tasks. N=5 with ≥5 runs per task at T=0.1.

| Model | Ctrl F1 | DNA F1 | **Δ F1** | p-value | Tasks Won |
|---|---|---|---|---|---|
| **Gemini 2.5 Flash** | 60% | **72%** | **+13%** | 0.040* | 4/5 |
| **DeepSeek Chat** | 50% | **60%** | **+9%** | 0.11 | 4/5 |
| **Gemini 2.5 Pro** | 60% | **69%** | **+9%** | 0.11 | 3/5 |

> Gemini 2.5 Flash: W+=14, N=5, p=0.040 ✅ significant. DeepSeek Chat: W+=12, N=5, p=0.11. Gemini 2.5 Pro: W+=12, N=5, p=0.11. All runs: 5 tasks × 3–5 runs at T=0.1.

---

## When CodeDNA Helps Most

Empirical analysis across 5 tasks (Gemini 2.5 Flash, ≥5 runs each) suggests a pattern:

| Task type | Example | Δ F1 |
|---|---|---|
| **Clear dependency chain** — A calls B which delegates to C | `dbshell → client → subprocess` (12508) | **+9%** |
| **Delegation with backend fan-out** — one interface, N backends | `Trunc → ops.date_trunc_sql` (13495) | **+21%** |
| **Feature addition with flag gating** — new capability across feature/schema layers | `INCLUDE clause in Index` (11991) | **+17%** |
| **XOR feature with multi-layer propagation** | `Q() XOR support` (14480) | **+18%** |
| **Cross-cutting fix** — same pattern in N unrelated files, no shared ancestor | `__eq__ NotImplemented` (11808) | **~0%** |

### Per-task breakdown

| Task | What it is | Why hard without CodeDNA | Δ F1 (Flash / DeepSeek) |
|---|---|---|---|
| **12508** dbshell | Add `-c SQL` flag to `dbshell` management command | Entry point is obvious by name; 4 backend `runshell_db()` clients are hidden | +9% / +1% |
| **11991** INCLUDE | Add `INCLUDE` clause support to `Index` | `schema.py` is findable; 4 backend schema editors are not | +17% / +6% |
| **14480** Q() XOR | Add XOR operator to `Q()` and `QuerySet()` | ORM→SQL→backends cascade requires touching 7 files | +18% / +14% |
| **13495** Trunc tzinfo | Fix timezone handling in `TruncDay()` for non-DateTimeField | Per-backend `date_trunc_sql()` override not reachable by grep alone | **+22%** / −8% ⚠ |
| **11808** `__eq__` | Fix `__eq__` to return `NotImplemented` for unknown types | Entry is `models/base.py` (847 lines, generic name); 5 subclasses are unconnected | ≈0% / **+34%** |

> ⚠ Task 13495 shows a model-dependent anomaly: Flash benefits strongly (+22pp) while DeepSeek and Pro regress (−8/−9pp). Under investigation.

> **Transparency note on 11808:** the cross-cutting task was included deliberately to test the limits of the protocol. The benchmark annotations do **not** pre-populate a list of affected files — the agent must discover them independently. CodeDNA v0.7 shows Δ ≈ 0% on this task type. This is reported as a known limitation, not hidden. See [SPEC.md §2.4](../SPEC.md) for the proposed v0.8 extension (`cross_cutting_patterns:`) and why it would not constitute cheating.

**CodeDNA is most effective when there is a navigable call chain.** The `used_by:` graph guides the agent from entry point to all affected files. For cross-cutting concerns (same fix in many independent files with no shared ancestor), the benefit is smaller because there is no natural navigation path to follow.

### `related:` field — closing the cross-cutting gap (v0.8)

The `related:` field was introduced to address the cross-cutting limitation. While `used_by:` captures structural links (imports), `related:` captures **semantic links** — files that share the same logic without importing each other.

**Manual test: task 11532 (unicode domain crash in email)**

Ground truth: 5 files across `mail/`, `validators.py`, `encoding.py`, `html.py` — no import chain connects them. They share IDNA/punycode domain encoding logic independently.

| Condition | Files found | F1 |
|---|---|---|
| Control (no annotations) | 2/5 (only mail/) | **40%** |
| CodeDNA with `used_by:` only | 2/5 (only mail/) | **40%** |
| CodeDNA with `used_by:` + `related:` | 5/5 | **100%** |

The `related:` annotations were: `"shares IDNA/punycode domain encoding logic"` — a factual statement about the code, not a hint at the solution. Any developer documenting the project would write the same.

`related:` is populated by the LLM during annotation (pass 2 — cross-file pattern detection) or by agents during their work when they discover semantic connections.

---

## Annotation Integrity

A full audit confirmed no task-specific hints are embedded in the `codedna/` files. Where GT files appear in `used_by:` targets, it is because those files are genuine callers or subclasses — not cherry-picked. The cross-cutting task (11808, Δ≈0%) confirms this: annotations described the architecture accurately but gave no navigation advantage because there is no call chain to follow.

One correction was made during the audit: `base/schema.py` in task 11991 initially listed only `postgresql/schema.py` in `used_by:` — updated to include all 4 backend schema editors that genuinely inherit from it.

Full audit: [`benchmark_agent/claude_code_challenge/django__django-13495/BENCHMARK_RESULTS.md`](../benchmark_agent/claude_code_challenge/django__django-13495/BENCHMARK_RESULTS.md)

**Pattern:** cheaper models appear to benefit most. Flash (cheapest of the three) shows the strongest gain (p=0.040). This suggests annotating once may allow cheaper models to perform closer to more expensive ones — though the sample is small.

Full data: [`benchmark_agent/runs/`](../benchmark_agent/runs/) · Script: [`benchmark_agent/swebench/run_agent_multi.py`](../benchmark_agent/swebench/run_agent_multi.py)

---

## Annotation Design Principle — Architecture, Not Answers

The key rule for `rules:` annotations: **describe the mechanism, not the solution**.

```python
# ❌ Wrong — gives away the answer
rules:   Fix mysql/operations.py, oracle/operations.py, postgresql/operations.py

# ✅ Correct — describes the delegation chain
rules:   Trunc.as_sql() delegates to connection.ops.date_trunc_sql() and
         time_trunc_sql(). Each backend implements these independently.
```

`used_by:` is a **navigation map**, not a to-do list. The agent reasons about which targets are relevant to the current task and opens only those.

---

## Inter-Agent Knowledge Accumulation

CodeDNA is designed for multi-agent environments — different models, different tools, different sessions. Each agent leaves knowledge for the next:

```
Agent A fixes a bug → adds Rules: "MUST filter soft-deleted users"
Agent B reads Rules: → avoids the same bug without re-discovering it
Agent C discovers an edge case → extends the Rules:
```

Unlike external docs (which go stale), `Rules:` annotations are co-located with the code — read every time the function is edited. The maintenance cost is real but proportional: in a traditional codebase, a human developer maintains this knowledge manually across sessions. With CodeDNA, agents maintain annotations as a side effect of normal work. Verification agents (see [SPEC.md §8.6](../SPEC.md)) can audit annotation accuracy automatically, which is not possible with free-form comments.

Current benchmark results are **zero-shot** — no fine-tuning on the protocol. Models follow `used_by:` and `rules:` by general language understanding alone.

> **See [SPEC.md](../SPEC.md) for the full inter-agent model, verification protocol, fine-tuning potential, and training corpus design.**
