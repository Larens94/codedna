# Multi-Agent Team Experiments

The SWE-bench benchmark tests single-agent file navigation. Here we test a different question: can CodeDNA help **teams of agents divide work without collisions** and produce integrated software?

Two experiments, both using 5-agent teams orchestrated with [Agno](https://github.com/agno-agi/agno) (`TeamMode.coordinate`). Same task, same model, same tools — only the instructions differ.

| Metric | Exp 1 — RPG (DeepSeek Chat) | Exp 2 — SaaS (DeepSeek R1) |
|---|---|---|
| **Duration (A / B)** | 1h 59m / 3h 11m (**1.6x faster**) | 82.6m / 99m (**17% faster**) |
| **Output quality** | Playable game / static scene | Lower complexity (2.1 vs 3.1) |
| **Annotation adoption** | 94% | **98.2%** (spontaneous, no reminders) |
| **`message:` adoption** | 0 (not in prompt) | **54 files** (100%, organic) |
| **Judge fixes needed** | 8 / 12 | — |

Full reports: [Exp 1 report](../experiments/runs/run_20260329_234232/REPORT.md) · [Exp 2 data](../experiments/runs/run_20260331_002754/)

---

## Experiment 1 — 2D RPG Game (run_20260329_234232)

**Setup:** identical 5-agent team (`GameDirector → GameEngineer → GraphicsSpecialist → GameplayDesigner → DataArchitect`), same task, same model (DeepSeek `deepseek-chat`), same tool budget. Only the instructions differed.

| Metric | Condition A — CodeDNA | Condition B — Standard |
|---|---|---|
| Total duration | **1h 59m** | **3h 11m** |
| Python files | **50** | 45 |
| Total LOC | 10,194 | **14,096** |
| Avg LOC/file | **203** | 313 |
| Annotation coverage | **94%** | 0% |
| Judge fixes to boot | **8** | **12** |
| Player controllable after fixes | **Yes (WASD)** | **No** |

**CodeDNA was 1.60× faster.** More importantly: after judge intervention to fix both outputs, condition A produced a **playable game** (ECS running, 5 entities, WASD input). Condition B produced a **visible but static scene** — `engine/ecs.py` and `gameplay/systems/player_system.py` were both correct, but the integration layer connecting them was never written.

### The director centralization cascade

Without `used_by:` contracts, the director spent 25 minutes occupying all four module namespaces before delegating (vs 12 minutes with CodeDNA). Every downstream specialist inherited structure they didn't design:

```
B Director builds full scaffold (25m — 2.0× A)
  → GameEngineer reverse-engineers structure (36m — 3.9× A)
    → GraphicsSpecialist works around pre-built renderer (41m — 1.4× A)
      → GameplayDesigner inherits 545-line monolith (35m — 2.6× A)
        → DataArchitect — independent domain, cleanest run (35m — 0.75× A ← only exception)
```

### Condition B's bugs were structurally different

All 8 fixes in condition A were corrections to existing code. Condition B had 12 fixes — 4 on existing code and **8 missing modules**: `entity_system.py`, `physics_engine.py`, `ai_system.py`, `player_controller.py`, and the entire `integration/` directory. These modules were declared by the director in `game_state.py` but never written by anyone.

> **More LOC does not mean more coverage.** B produced 38% more lines (14,096 vs 10,194) but 10% fewer files. Average file size: 313 lines vs 203. More code, less functionality.

Full report: [`experiments/runs/run_20260329_234232/REPORT.md`](../experiments/runs/run_20260329_234232/REPORT.md)

---

## Experiment 2 — AgentHub SaaS webapp A/B test (run_20260331_002754)

**Setup:** same 5-agent team, same task (build AgentHub — a multi-tenant SaaS platform to rent, configure and deploy AI agents), upgraded model: **DeepSeek R1** (`deepseek-reasoner`). Two conditions run sequentially on the same machine.

| Metric | Condition A — CodeDNA | Condition B — Standard |
|---|---|---|
| Duration | **82.6 min** | 99.0 min |
| Python files | 55 | 50 |
| Total LOC | **14,156** | 11,872 |
| Avg function length | **14.3 lines** | 26.2 lines |
| Avg cyclomatic complexity | **2.11** | 3.07 |
| Max function complexity | **10** | 16 |
| Classes | **90** | 50 |
| Annotation coverage | **98.2%** | 0% |
| Syntax errors | 1 | **0** |
| Validation score | 0.73 | **0.87** |

> The single syntax error in condition A was an em-dash character (`—` U+2014) introduced inside a `rules:` annotation field. Without it, validation scores would be near-equal.

### 98.2% adoption — spontaneous and sustained

DeepSeek R1 annotated 54 of 55 files with all 5 CodeDNA fields (`exports`, `used_by`, `rules`, `agent`, `message`) across a full 83-minute multi-agent session — without any prompting mid-run to "remember annotations."

Example — `app/agents/agent_wrapper.py` (written by the AgentIntegrator specialist):

```python
"""app/agents/agent_wrapper.py — Wraps agno.Agent, counts tokens, enforces credit cap.

exports: AgentWrapper, CreditExhaustedError
used_by: app/agents/agent_runner.py → run_agent_stream,
         app/services/agno_integration.py → agent execution
rules:   Never call agno.Agent directly from API layer — always go through AgentWrapper
         Token count must be extracted from agno response metadata and stored in agent run tokens_used
         AgentWrapper must raise CreditExhaustedError (HTTP 402) before starting if balance < min_credits
         All agent instructions must be sanitised (strip HTML, limit to 10k chars)
agent:   AgentIntegrator | 2024-12-05 | implemented AgentWrapper with token counting and credit cap
         message: "implement tool usage tracking and cost estimation"
"""
```

### `message:` as inter-agent forward planning

The field was used consistently across all 54 annotated files to encode work that the agent knew was needed but was out of scope for its current task:

```python
# app/agents/agent_runner.py
agent:   AgentIntegrator | 2024-12-05 | implemented agent runner with streaming and credit management
         message: "implement concurrent execution with asyncio semaphore"

# app/agents/memory_manager.py
agent:   AgentIntegrator | 2024-12-05 | implemented persistent memory with similarity search
         message: "implement memory summarization for long conversations"
```

These are not instructions the agent received — they are observations it left for itself (and for future agents), co-located with the code where the work would eventually happen.

### Annotations as inter-agent contracts (emergent behaviour)

Agents used `used_by:` not just to document existing imports, but as **architectural contracts for files that didn't exist yet**. The ProductArchitect wrote `used_by: all API routers` on `models.py` before any router existed — declaring who should consume it. When the BackendEngineer ran, it read that contract and built the routers accordingly.

The same pattern appeared with `rules:`: the DataEngineer wrote `rules: all operations must be atomic; use SELECT FOR UPDATE` on `credits.py`, and every downstream agent that touched billing respected that constraint without being told.

This transforms CodeDNA from documentation into a **coordination protocol** — each agent writes what it built and what it expects, the next agent reads and fulfills. No orchestrator needed.

### What the unconstrained condition built

Condition B (no CodeDNA) produced working code but with a notable structural anomaly: the agent **started Flask, then pivoted to FastAPI mid-session**, leaving both stacks in the codebase simultaneously. CodeDNA's `rules:` and `used_by:` fields force the agent to declare architectural boundaries upfront, which appears to reduce mid-session pivots.

### Summary

| Question | Answer |
|---|---|
| Does a reasoning model adopt CodeDNA spontaneously? | **Yes — 98.2% across 54 files, sustained over 83 min** |
| Does CodeDNA change code structure? | **Yes — lower complexity (2.11 vs 3.07), shorter functions (14 vs 26 lines), more classes (90 vs 50)** |
| Does it prevent bugs? | **No — the one syntax error was inside an annotation field** |
| Does `message:` get used as designed? | **Yes — 54 files, organically, without explicit instruction** |
| Does it prevent mid-session architectural pivots? | **Likely yes — B changed stack mid-session; A did not** |

> N=1 per condition. Results are directional, not statistically powered.

Full run data: [`experiments/runs/run_20260331_002754/`](../experiments/runs/run_20260331_002754/)

### Limitations

Both multi-agent experiments are N=1 per condition — results are directional, not statistically powered. Experiment 2 used sequential runs on shared hardware. Independent replication across different models, team sizes, and project types is needed.

---

## Fix Quality — Claude Code Manual Session

The SWE-bench benchmark measures **file navigation** (did the agent open the right files?). This second benchmark measures **fix completeness** (did the agent produce the correct patch?).

**Setup**: two Claude Code sessions on `django__django-13495`, same model (claude-sonnet-4-6), same prompt, same bug. Ground truth: the official Django patch (7 files).

| Metric | Control | CodeDNA |
|---|---|---|
| Session time | ~10–11 min | ~8 min |
| Total interactions (estimated) | ~33 | ~30 |
| Failed edits | 5 | 0 |
| Files matching official patch | **6 / 7** | **7 / 7** |
| `date_trunc_sql` fixed (DateField) | ✅ all backends | ✅ all backends |
| `time_trunc_sql` fixed (TimeField) | ❌ not touched | ✅ all backends |
| `sqlite3/base.py` updated | ❌ | ✅ |
| SQLite approach matches official patch | ❌ | ✅ |
| Knowledge left for next agent | ❌ | ✅ `rules:` + `agent:` updated |

**What made the difference:** a single `rules:` annotation on `TimezoneMixin.get_tzname()`:

```python
def get_tzname(self):
    """
    Rules: Timezone conversion must occur BEFORE applying datetime functions;
           database stores UTC but results must reflect input datetime's timezone.
    """
```

This described an architectural principle, not the bug. The control saw the same `time_trunc_sql` call on the line immediately below the reported bug — and didn't touch it. CodeDNA read the constraint and applied the fix to the full pattern.

Full report: [`benchmark_agent/claude_code_challenge/django__django-13495/BENCHMARK_RESULTS.md`](../benchmark_agent/claude_code_challenge/django__django-13495/BENCHMARK_RESULTS.md)
Session logs: [control](../benchmark_agent/claude_code_challenge/django__django-13495/session_log_control.md) · [codedna](../benchmark_agent/claude_code_challenge/django__django-13495/session_log_codedna.md)

**Run it yourself:**
1. Clone the control repository: `git clone https://github.com/Larens94/codedna-challenge-control`
2. Clone the CodeDNA-annotated version: `git clone https://github.com/Larens94/codedna-challenge-codedna`
3. Open either repository in your AI coding agent and paste the same prompt.
