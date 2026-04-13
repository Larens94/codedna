# 🧬 CodeDNA: An In-Source Communication Protocol for AI Coding Agents

> *An in-source communication protocol where the writing agent encodes architectural context and the reading agent decodes it. The file is the channel. Every fragment carries the whole.*

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/CodeDNA-v0.8-6366f1)](./SPEC.md)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.19158336-blue)](https://doi.org/10.5281/zenodo.19158336)
[![Website](https://img.shields.io/badge/website-codedna.silicoreautomation.space-6366f1)](https://codedna.silicoreautomation.space)
[![CI](https://github.com/Larens94/codedna/actions/workflows/ci.yml/badge.svg)](https://github.com/Larens94/codedna/actions/workflows/ci.yml)
[![CodeQL](https://github.com/Larens94/codedna/actions/workflows/codeql.yml/badge.svg)](https://github.com/Larens94/codedna/actions/workflows/codeql.yml)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-support-FF5E5B?logo=ko-fi&logoColor=white)](https://ko-fi.com/codedna)

[![Discord](https://img.shields.io/badge/Discord-Join_Community-5865F2?logo=discord&logoColor=white)](https://discord.gg/7Fs5J2ua)
[![Claude Code Plugin](https://img.shields.io/badge/Claude_Code-Plugin_Under_Review-orange?logo=anthropic&logoColor=white)](https://claude.com/plugins)
[![Languages](https://img.shields.io/badge/Languages-11_languages-6366f1)](#language-support)
[![Docs](https://img.shields.io/badge/Docs-Install_Guide-6366f1)](https://larens94.github.io/codedna/install.html)

**Compatible with:**
[![Claude Code](https://img.shields.io/badge/Claude_Code-D97757?logo=anthropic&logoColor=white)](./integrations/CLAUDE.md)
[![Cursor](https://img.shields.io/badge/Cursor-000000?logo=cursor&logoColor=white)](./integrations/.cursorrules)
[![GitHub Copilot](https://img.shields.io/badge/GitHub_Copilot-000000?logo=github&logoColor=white)](./integrations/copilot-instructions.md)
[![Windsurf](https://img.shields.io/badge/Windsurf-0891b2?logoColor=white)](./integrations/.windsurfrules)
[![OpenCode](https://img.shields.io/badge/OpenCode-6366f1?logoColor=white)](./integrations/AGENTS.md)
[![Gemini](https://img.shields.io/badge/Gemini-4285F4?logo=google&logoColor=white)](./QUICKSTART.md)
[![ChatGPT](https://img.shields.io/badge/ChatGPT-74aa9c?logo=openai&logoColor=white)](./QUICKSTART.md)


**CodeDNA** is an **inter-agent communication protocol** implemented as in-source annotations. The writing agent embeds architectural context directly into source files; the reading agent decodes it at any point in the file. Like biological DNA — cut a hologram in half and you get two smaller complete images.

**No RAG. No vector DB. No external rules files. Minimal drift (context co-located with code). [11 languages supported](#language-support).**

> **🎯 Less Prompt Engineering Needed:** CodeDNA annotations help AI agents navigate the codebase with less manual guidance. Even less-technical users can get better multi-file fixes by describing the problem — the architectural context is already in the code.

![CodeDNA Logo](./docs/logo.png)

---

## The Problem

AI coding agents waste a significant fraction of their context window exploring irrelevant files, re-reading code, and missing cross-file constraints or reverse dependencies. The result: incomplete patches, higher token costs, and models that repeat the same mistakes across sessions.

The root cause is structural. Information like reverse dependencies and domain constraints cannot be inferred from a single file — they require reading the whole codebase. Without a way to persist that knowledge, every agent starts from scratch.

CodeDNA embeds this context directly in source files: `used_by:` maps reverse dependencies, `rules:` encodes domain constraints, and `agent:` / `message:` accumulate knowledge across sessions. It is not intended to replace retrieval systems, vector databases, or external memory — it provides a persistent architectural context layer inside the repository that any of those systems can build on.

This also enables **agent-to-agent communication**: a constraint discovered by Agent A is available to Agent B in a different session or a different model. Knowledge compounds in a versioned, inspectable form.

**Preliminary results are encouraging:**
- **SWE-bench (single-agent navigation):** +13pp F1 on Gemini 2.5 Flash (p=0.040), +9pp on DeepSeek Chat — zero-shot, no fine-tuning, just annotations.
- **Multi-agent team experiments:** 5-agent teams build complete applications 1.6x faster with CodeDNA; `used_by:` contracts prevent integration gaps; the `message:` field (agent-to-agent chat) was adopted spontaneously in 98.2% of files.
- **Fix quality (Claude Code):** CodeDNA session matched 7/7 files of the official Django patch vs 6/7 for control, with zero failed edits.

Results are preliminary and require larger-scale validation.

---

## Where CodeDNA sits in the AI memory stack

Every AI coding agent relies on multiple memory layers to navigate a codebase. Most of them are external to the code — chat history, vector databases, markdown rules files. CodeDNA is different: it is the only layer that lives *inside* the source files themselves.

![CodeDNA Memory Layer Stack](./docs/stack-codedna-0.gif)

| Layer | Examples | Where it lives | Shared across tools? |
|---|---|---|---|
| LLM / Agent | Claude, GPT-4, Cursor, Copilot | Cloud | — |
| External memory | Chat history, Projects, Memory API | Cloud / external DB | ✗ tool-specific |
| Native agent memory | Claude auto-memory, Cursor memory, Windsurf memories, Devin session memory, … | Local machine / tool cloud | ✗ tool-specific |
| RAG / Vector DB | Embeddings, Pinecone, pgvector | External infrastructure | depends |
| Markdown / Config | README, CLAUDE.md, `.cursorrules`, AGENTS.md | Repo (outside source files) | partial (tool-specific files) |
| **CodeDNA** | `exports`, `rules`, `agent`, `message`, `.codedna` | **Inside every source file + repo root** | ✅ always |

Every other layer is either external to the code or tool-specific. CodeDNA is the only memory that:
1. **Travels with the source file** — through clones, forks, and CI pipelines, with no infrastructure dependency
2. **Is readable by any agent on any tool** — Claude, Cursor, Windsurf, Copilot, OpenCode, or a custom script all see the same annotations

**CodeDNA does not replace native agent memories** — it is additive. Every agentic tool (Claude Code, Cursor, Windsurf, Devin, and any future agent) has its own native memory for user preferences, feedback, and tool-specific context. That context belongs outside the repo. CodeDNA handles the architectural context that belongs *inside* it. Use both.

> **This is what makes CodeDNA composable.** RAG systems, vector databases, native tool memories, and external memory layers can all be built *on top of* or *alongside* CodeDNA annotations. The in-source layer is the shared foundation any of those systems can read from — and the only one that survives a `git clone`.

---

### Semantic vs structural reasoning

AI coding agents usually begin from a semantic prompt and must infer structure by exploring the repository.  
Without persistent architectural context, each session starts from scratch.

CodeDNA turns semantic reasoning into structured reasoning.

Annotations allow the agent to follow explicit dependency and constraint signals instead of relying only on token similarity or retrieval.

This suggests that source code alone may not be the optimal reasoning layer for AI agents.
While binary is the lowest layer for execution, structured source + annotations may be closer to the lowest layer for understanding.

## How it works — live benchmark data

![CodeDNA Navigation Demo](./docs/codedna_viz.gif)

> Three visual metaphors, same real data (django__django-11808 · DeepSeek-Chat · 5 runs).
> **Without CodeDNA**: agent opens 2 random files and stops — 8/10 critical files missed.
> **With CodeDNA**: follows the `used_by:` chain — finds 6/10 critical files. Retry risk −52%.
> [▶ Interactive version — 3 metaphors](./docs/codedna_viz_3metaphors.html)

> **🔄 The Network Effect:** When an AI agent writes CodeDNA annotations, it leaves a navigable trail for every other agent that reads the code after it — regardless of vendor or model. The more agents that participate, the more useful the protocol becomes.

---

## 🤔 Who is CodeDNA for?

| You are… | Without CodeDNA | With CodeDNA |
|---|---|---|
| **Non-technical user** | Must learn prompt engineering to guide the AI agent through the codebase | Just describe the problem — annotations give the agent structural context to follow |
| **Junior developer** | AI finds the obvious file, misses the 5 related ones | `used_by:` graph helps surface related files that may need changes |
| **Senior developer** | Spends time writing detailed prompts every session | Writes annotations once — that context persists across sessions |
| **Team lead** | Each developer's AI makes different mistakes | Annotations encode team knowledge — potentially more consistent results |

**The core idea:** today, the quality of AI-assisted coding often depends on the *user's* ability to prompt. CodeDNA moves some of that knowledge from ephemeral prompts into persistent, version-controlled source code.

---

## ⚡ Quick Start

Setting up CodeDNA is two steps:

1. **Install the integration for your AI tool** — tells the agent how to follow the protocol (Option 1 below)
2. **Annotate your existing codebase** — adds CodeDNA headers to files already in your repo (Option 2 below)

For a **new project**, step 1 is enough — the agent annotates files as it creates and edits them.
For an **existing codebase**, run both: step 1 first, then step 2 to bulk-annotate what's already there.

> **Want to try CodeDNA on a sample project or contribute to the codebase?** See [CONTRIBUTING.md](./CONTRIBUTING.md) for the dev setup.

---

### Option 1 — AI Tool Integration (Claude Code, Cursor, Copilot, Windsurf, OpenCode)

Run one command for your tool:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh) <tool>
```

| Tool | Option | Enforcement |
|---|---|---|
| **Claude Code** | **`claude-hooks`** | ✅ Active — 4 hooks + `.claude/settings.local.json` |
| **Cursor** | **`cursor-hooks`** | ✅ Active — hook scripts in `.cursor/hooks/` (v1.7+) |
| **GitHub Copilot** | **`copilot-hooks`** | ✅ Active — `.github/hooks/hooks.json` + scripts |
| **Cline** | **`cline-hooks`** | ✅ Active — hook scripts in `.clinerules/hooks/` (v3.36+) |
| **OpenCode** | **`opencode`** | ✅ Active — JS plugin in `.opencode/plugins/` |
| Windsurf | `windsurf` | ⚠️ Instructions only |
| Antigravity / custom agents | `agents` | ⚠️ Instructions only |
| Aider | `claude` | ⚠️ Instructions only |

> **Active enforcement** = hooks validate annotations on every file write/edit automatically, regardless of session length or task complexity. Full reference: [`integrations/README.md`](./integrations/README.md#install-for-your-tool).

> **`all`** installs everything at once — only useful for teams where each developer uses a different tool.

**Done. Your AI tool now follows the CodeDNA protocol.** If you have existing files to annotate, continue with Option 2.

---

### Option 2 — CLI: annotate an existing codebase

Annotate an entire project from the terminal. Supports local models via Ollama at zero cost:

```bash
pip install git+https://github.com/Larens94/codedna.git

# Free — structural only, no AI
codedna init /path/to/project --no-llm

# Free — local model via Ollama
codedna init /path/to/project --model ollama/llama3

# Paid — Anthropic Haiku (~$1-3 for a Django project)
ANTHROPIC_API_KEY=sk-... codedna init /path/to/project --model claude-haiku-4-5-20251001
```

| Command | What it does |
|---|---|
| `codedna init PATH` | First-time annotation — L1 module headers + L2 function `Rules:` |
| `codedna update PATH` | Incremental — only unannotated files (safe to re-run) |
| `codedna check PATH` | Coverage report without modifying files |
| `codedna init PATH --extensions ts go` | Annotate TypeScript + Go files too (L1 only) |

Supported models via `--model`:

| Provider | Example | Cost |
|---|---|---|
| Ollama (local) | `ollama/llama3`, `ollama/mistral` | Free |
| Anthropic | `claude-haiku-4-5-20251001` | ~$1–3 / project |
| OpenAI | `openai/gpt-4o-mini` | Low |
| Google | `gemini/gemini-2.0-flash` | Low |
| None | `--no-llm` | Free |

---

### Option 3 — Claude Code Plugin

Install via the independent marketplace (available now):

```bash
claude plugin marketplace add Larens94/codedna
claude plugin install codedna@codedna
```

No API key. No extra cost. Uses your existing Claude subscription. Adds `/codedna:init`, `/codedna:check`, `/codedna:manifest`, `/codedna:impact` skills + automatic annotation validation on every file write.

> **Official Anthropic directory:** the plugin has been submitted and is currently **under review**. Once approved, installation will simplify to `claude plugin install codedna`.

---

## 📊 Benchmark — SWE-bench Multi-Model Results

5 real Django issues from [SWE-bench](https://github.com/princeton-nlp/SWE-bench), tested across multiple LLMs. Same prompt, same tools, same tasks. **Only difference: CodeDNA annotations.**

> **Metric: File Localization F1** — harmonic mean of recall and precision on files read vs ground truth. Isolates the navigation bottleneck that precedes code generation.

> **Statistical test:** Wilcoxon signed-rank test (one-tailed, H1: CodeDNA > Control) over F1 pairs across 5 tasks. N=5 with ≥5 runs per task at T=0.1.

| Model | Ctrl F1 | DNA F1 | **Δ F1** | p-value | Tasks Won |
|---|---|---|---|---|---|
| **Gemini 2.5 Flash** | 60% | **72%** | **+13%** | 0.040* | 4/5 |
| **DeepSeek Chat** | 50% | **60%** | **+9%** | 0.11 | 4/5 |
| **Gemini 2.5 Pro** | 60% | **69%** | **+9%** | 0.11 | 3/5 |

> 3 of 3 models complete. Full data: [`benchmark_agent/runs/`](./benchmark_agent/runs/)
>
> Gemini 2.5 Flash: W+=14, N=5, p=0.040 ✅ significant. DeepSeek Chat: W+=12, N=5, p=0.11. Gemini 2.5 Pro: W+=12, N=5, p=0.11. All runs: 5 tasks × 3–5 runs at T=0.1.

### When CodeDNA Helps Most

Empirical analysis across 5 tasks (Gemini 2.5 Flash, ≥5 runs each) suggests a pattern:

| Task type | Example | Δ F1 |
|---|---|---|
| **Clear dependency chain** — A calls B which delegates to C | `dbshell → client → subprocess` (12508) | **+9%** |
| **Delegation with backend fan-out** — one interface, N backends | `Trunc → ops.date_trunc_sql` (13495) | **+21%** |
| **Feature addition with flag gating** — new capability across feature/schema layers | `INCLUDE clause in Index` (11991) | **+17%** |
| **XOR feature with multi-layer propagation** | `Q() XOR support` (14480) | **+18%** |
| **Cross-cutting fix** — same pattern in N unrelated files, no shared ancestor | `__eq__ NotImplemented` (11808) | **~0%** |

#### Per-task breakdown

| Task | What it is | Why hard without CodeDNA | Δ F1 (Flash / DeepSeek) |
|---|---|---|---|
| **12508** dbshell | Add `-c SQL` flag to `dbshell` management command | Entry point is obvious by name; 4 backend `runshell_db()` clients are hidden | +9% / +1% |
| **11991** INCLUDE | Add `INCLUDE` clause support to `Index` | `schema.py` is findable; 4 backend schema editors are not | +17% / +6% |
| **14480** Q() XOR | Add XOR operator to `Q()` and `QuerySet()` | ORM→SQL→backends cascade requires touching 7 files | +18% / +14% |
| **13495** Trunc tzinfo | Fix timezone handling in `TruncDay()` for non-DateTimeField | Per-backend `date_trunc_sql()` override not reachable by grep alone | **+22%** / −8% ⚠ |
| **11808** `__eq__` | Fix `__eq__` to return `NotImplemented` for unknown types | Entry is `models/base.py` (847 lines, generic name); 5 subclasses are unconnected | ≈0% / **+34%** |

> ⚠ Task 13495 shows a model-dependent anomaly: Flash benefits strongly (+22pp) while DeepSeek and Pro regress (−8/−9pp). Under investigation.

> **Transparency note on 11808:** the cross-cutting task was included deliberately to test the limits of the protocol. The benchmark annotations do **not** pre-populate a list of affected files — the agent must discover them independently. CodeDNA v0.7 shows Δ ≈ 0% on this task type. This is reported as a known limitation, not hidden. See [SPEC.md §2.4](./SPEC.md) for the proposed v0.8 extension (`cross_cutting_patterns:`) and why it would not constitute cheating.

**CodeDNA is most effective when there is a navigable call chain.** The `used_by:` graph guides the agent from entry point to all affected files. For cross-cutting concerns (same fix in many independent files with no shared ancestor), the benefit is smaller because there is no natural navigation path to follow.

### Annotation Integrity

A full audit confirmed no task-specific hints are embedded in the `codedna/` files. Where GT files appear in `used_by:` targets, it is because those files are genuine callers or subclasses — not cherry-picked. The cross-cutting task (11808, Δ≈0%) confirms this: annotations described the architecture accurately but gave no navigation advantage because there is no call chain to follow.

One correction was made during the audit: `base/schema.py` in task 11991 initially listed only `postgresql/schema.py` in `used_by:` — updated to include all 4 backend schema editors that genuinely inherit from it.

Full audit: [`benchmark_agent/claude_code_challenge/django__django-13495/BENCHMARK_RESULTS.md`](./benchmark_agent/claude_code_challenge/django__django-13495/BENCHMARK_RESULTS.md)

**Pattern:** cheaper models appear to benefit most. Flash (cheapest of the three) shows the strongest gain (p=0.040). This suggests annotating once may allow cheaper models to perform closer to more expensive ones — though the sample is small.

Full data: [`benchmark_agent/runs/`](./benchmark_agent/runs/) · Script: [`benchmark_agent/swebench/run_agent_multi.py`](./benchmark_agent/swebench/run_agent_multi.py)

---

## 🤝 Multi-Agent Team Experiments

The SWE-bench benchmark above tests single-agent file navigation. Here we test a different question: can CodeDNA help **teams of agents divide work without collisions** and produce integrated software?

Two experiments, both using 5-agent teams orchestrated with [Agno](https://github.com/agno-agi/agno) (`TeamMode.coordinate`). Same task, same model, same tools — only the instructions differ.

| Metric | Exp 1 — RPG (DeepSeek Chat) | Exp 2 — SaaS (DeepSeek R1) |
|---|---|---|
| **Duration (A / B)** | 1h 59m / 3h 11m (**1.6x faster**) | 82.6m / 99m (**17% faster**) |
| **Output quality** | Playable game / static scene | Lower complexity (2.1 vs 3.1) |
| **Annotation adoption** | 94% | **98.2%** (spontaneous, no reminders) |
| **`message:` adoption** | 0 (not in prompt) | **54 files** (100%, organic) |
| **Judge fixes needed** | 8 / 12 | — |

Full reports: [Exp 1 report](./experiments/runs/run_20260329_234232/REPORT.md) · [Exp 2 data](./experiments/runs/run_20260331_002754/)

### Experiment 1 — 2D RPG Game (run_20260329_234232)

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

#### The director centralization cascade

Without `used_by:` contracts, the director spent 25 minutes occupying all four module namespaces before delegating (vs 12 minutes with CodeDNA). Every downstream specialist inherited structure they didn't design:

```
B Director builds full scaffold (25m — 2.0× A)
  → GameEngineer reverse-engineers structure (36m — 3.9× A)
    → GraphicsSpecialist works around pre-built renderer (41m — 1.4× A)
      → GameplayDesigner inherits 545-line monolith (35m — 2.6× A)
        → DataArchitect — independent domain, cleanest run (35m — 0.75× A ← only exception)
```

The cascade peaks at the agent nearest to the director's territorial decisions and diminishes toward the most independent domain. `used_by:` forces ownership upfront — the director cannot occupy a module it declared as belonging to another agent.

#### Condition B's bugs were structurally different

All 8 fixes in condition A were corrections to existing code. Condition B had 12 fixes — 4 on existing code and **8 missing modules**: `entity_system.py`, `physics_engine.py`, `ai_system.py`, `player_controller.py`, and the entire `integration/` directory. These modules were declared by the director in `game_state.py` but never written by anyone. Writing them from scratch would be outside the scope of judge intervention.

> **More LOC does not mean more coverage.** B produced 38% more lines (14,096 vs 10,194) but 10% fewer files. Average file size: 313 lines vs 203. More code, less functionality.

Full report: [`experiments/runs/run_20260329_234232/REPORT.md`](./experiments/runs/run_20260329_234232/REPORT.md) · Run data: [`experiments/runs/run_20260329_234232/`](./experiments/runs/run_20260329_234232/)

### Experiment 2 — AgentHub SaaS webapp A/B test (run_20260331_002754)

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

> The single syntax error in condition A was an em-dash character (`—` U+2014) introduced inside a `rules:` annotation field. Without it, validation scores would be near-equal. The gap does not reflect a systematic correctness difference.

#### 98.2% adoption — spontaneous and sustained

DeepSeek R1 annotated 54 of 55 files with all 5 CodeDNA fields (`exports`, `used_by`, `rules`, `agent`, `message`) across a full 83-minute multi-agent session — without any prompting mid-run to "remember annotations." This is the highest adoption rate observed across all experiments.

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

The `rules:` field encodes four constraints (API layer isolation, token tracking, credit pre-check, input sanitization) that cannot be inferred by reading the file alone — they require knowing the full call chain. The `message:` field leaves a forward-planning note for the next agent in the session.

#### Level 2 annotations — function-level Rules

The same file shows L2 adoption inside the class body:

```python
class AgentWrapper:
    """Wraps an agno.Agent instance with token counting and credit enforcement.

    Rules:
        1. Token counting is extracted from agno response metadata
        2. Credit cap is enforced before execution
        3. Instructions are sanitized (HTML stripped, length limited)
        4. All agent interactions go through this wrapper
    """
```

#### `message:` as inter-agent forward planning

The field was used consistently across all 54 annotated files to encode work that the agent knew was needed but was out of scope for its current task:

```python
# app/agents/agent_runner.py
agent:   AgentIntegrator | 2024-12-05 | implemented agent runner with streaming and credit management
         message: "implement concurrent execution with asyncio semaphore"

# app/agents/memory_manager.py
agent:   AgentIntegrator | 2024-12-05 | implemented persistent memory with similarity search
         message: "implement memory summarization for long conversations"

# app/services/scheduler_service.py
agent:   Product Architect | 2024-03-30 | created scheduler service skeleton
         message: "implement job persistence for fault tolerance across restarts"

# app/services/agent_service.py
agent:   Product Architect | 2024-03-30 | created agent service skeleton
         message: "implement agent configuration validation against Agno framework schema"
```

These are not instructions the agent received — they are observations it left for itself (and for future agents), co-located with the code where the work would eventually happen. No agent was told to use `message:` this way.

#### What the unconstrained condition built

Condition B (no CodeDNA) produced working code but with a notable structural anomaly: the agent **started Flask, then pivoted to FastAPI mid-session**, leaving both stacks in the codebase simultaneously.

- `app/__init__.py` imports `Flask`, `SQLAlchemy`, `JWTManager`, `Bcrypt`, `Celery` — initializes `db = SQLAlchemy()`
- `app/main.py` creates a FastAPI application via `create_fastapi_app()`
- `run.py` calls `create_app()` with a Flask-style `app.run()`
- Jinja2 templates (`base.html`, `home.html`, `marketplace.html`) and static JS files are residue from the Flask phase

The pivot is not a bug in the usual sense — condition B's individual files are syntactically correct (0 errors). But the integration layer is inconsistent. CodeDNA's `rules:` and `used_by:` fields force the agent to declare architectural boundaries upfront, which appears to reduce mid-session pivots.

#### B went deeper on domain logic

Despite the architectural inconsistency, condition B fully implemented modules that A left as stubs:

- `app/billing/credit_engine.py` (413 LOC) — complete `CreditEngine` with `debit()`, `credit()`, `reserve()`, `release()`, transaction logging, `InsufficientCreditsError`
- `app/memory/manager.py` (638 LOC) — `MemoryManager` with vector similarity search, importance scoring, TTL expiry
- `demo_seed.py` — realistic seed data (A had none)
- `test_app.py` — basic test file (A had none)

A built stronger architecture (ServiceContainer DI, 9 exception types, async SQLAlchemy); B built more domain implementation. Neither was production-ready without further work.

#### Summary

| Question | Answer |
|---|---|
| Does a reasoning model adopt CodeDNA spontaneously? | **Yes — 98.2% across 54 files, sustained over 83 min** |
| Does CodeDNA change code structure? | **Yes — lower complexity (2.11 vs 3.07), shorter functions (14 vs 26 lines), more classes (90 vs 50)** |
| Does it prevent bugs? | **No — the one syntax error was inside an annotation field** |
| Does `message:` get used as designed? | **Yes — 54 files, organically, without explicit instruction** |
| Does it prevent mid-session architectural pivots? | **Likely yes — B changed stack mid-session; A did not** |

> N=1 per condition. Results are directional, not statistically powered. The experiment is presented as a qualitative case study to complement the SWE-bench navigation benchmark.

Full run data: [`experiments/runs/run_20260331_002754/`](./experiments/runs/run_20260331_002754/) · Script: [`experiments/run_experiment_webapp2.py`](./experiments/run_experiment_webapp2.py)

#### Limitations

Both multi-agent experiments are N=1 per condition — results are directional, not statistically powered. Experiment 2 used sequential runs on shared hardware (machine state may differ between conditions). Task 13495 shows an unexplained model-dependent anomaly (Flash +22pp, DeepSeek -8pp). Independent replication across different models, team sizes, and project types is needed.

---

### Fix Quality — Claude Code Manual Session

The SWE-bench benchmark measures **file navigation** (did the agent open the right files?). This second benchmark measures **fix completeness** (did the agent produce the correct patch?).

**Setup**: two Claude Code sessions on `django__django-13495`, same model (claude-sonnet-4-6), same prompt, same bug. Ground truth: the official Django patch (7 files).

```
Bug: TruncDay('created_at', output_field=DateField(), tzinfo=tz_kyiv)
     generates SQL without AT TIME ZONE — timezone param silently ignored.
```

**Results:**

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

> **Validity note**: this is a single run, not a statistically powered study. The result is presented as an illustrative case, not a population estimate. The causal mechanism is traceable: one annotation changed the frame from "fix DateField" to "fix the timezone pattern across all output fields."

Full report: [`benchmark_agent/claude_code_challenge/django__django-13495/BENCHMARK_RESULTS.md`](./benchmark_agent/claude_code_challenge/django__django-13495/BENCHMARK_RESULTS.md)
Session logs: [control](./benchmark_agent/claude_code_challenge/django__django-13495/session_log_control.md) · [codedna](./benchmark_agent/claude_code_challenge/django__django-13495/session_log_codedna.md)
Reproduce: [`HOW_TO_RERUN.md`](./benchmark_agent/claude_code_challenge/django__django-13495/HOW_TO_RERUN.md)

**Run it yourself:**
1. Clone the control repository:
   ```bash
   git clone https://github.com/Larens94/codedna-challenge-control
   ```
2. Clone the CodeDNA-annotated version:
   ```bash
   git clone https://github.com/Larens94/codedna-challenge-codedna
   ```
3. Open either repository in your AI coding agent (Claude Code, Cursor, etc.)
4. Paste the same prompt into your agent and score how many of the 7 patch files it touches.

**Quick test with the CLI:**
```bash
# Check annotation coverage
codedna check ./codedna-challenge-codedna

# Run a dry-run annotation (no LLM)
codedna init ./codedna-challenge-codedna --no-llm --dry-run
```

---

## 🗺️ Roadmap

CodeDNA v0.8 is the current release. The planned development path:

| Milestone | Goal | Status |
|---|---|---|
| **M1 — Protocol & CLI** | v0.8 spec · `codedna init/update/check` · AST-based auto-extraction · `message:` agent chat layer | ✅ Done |
| **M2 — Benchmark Expansion** | 20+ SWE-bench tasks · 5+ LLMs · Zenodo dataset · public dashboard | 🔜 |
| **M3 — Multi-Tool Hooks** | Active enforcement hooks for Claude Code · Cursor · Copilot · Cline · OpenCode — validates on every write | ✅ Done |
| **M4 — Language Extension** | 11 languages: Python · TS/JS · Go · PHP (Laravel) · Rust · Java · Kotlin · Ruby · C# · Swift · Blade/Jinja2/Vue | ✅ Done |
| **M5 — Editor & Workflow** | VS Code extension (used_by graph · agent timeline · model heatmap) · GitHub Action CI | 🔜 |
| **M6 — Research & Dissemination** | arXiv preprint · ICSE NIER/workshop submission · annotate Flask, FastAPI | 🔜 |

> This roadmap is part of a funding application to [NLnet NGI0 Commons Fund](https://nlnet.nl/commonsfund/) (deadline April 1st 2026). If you find CodeDNA useful and want to support its development, ⭐ the repo and share it.

---

## 🔬 v0.8 Features

### `message:` — Persistent Agent Chat in Code

The `agent:` field records what an agent did. The `message:` sub-field (new in v0.8) adds a **conversational layer** — soft observations, open questions, and forward-looking notes left directly for the next agent.

```python
"""analytics/revenue.py — Monthly/annual revenue aggregation.

...
agent:   claude-sonnet-4-6 | anthropic | 2026-03-10 | Implemented monthly_revenue.
         message: "rounding edge case in multi-currency — investigate before next release"
agent:   gemini-2.5-pro    | google    | 2026-03-18 | Added annual_summary.
         message: "@prev: confirmed, promoted to rules:. New: timezone rollover in January"
"""
```

`message:` works at **both levels**:
- **Level 1 (module docstring)** — for agents that read the full file
- **Level 2 (function docstring)** — for agents using a sliding window that never sees the top of the file

The lifecycle: an observation left in `message:` either gets promoted to `rules:` (architectural truth confirmed) or dismissed with a reply. Append-only, never deleted.

### Agent Telemetry via Git Trailers

Git is already immutable, append-only, and diff-complete. v0.8 uses **git trailers** — the same standard as `Co-Authored-By:`, natively recognised by GitHub — to embed AI session metadata directly in commit messages:

```
implement monthly revenue aggregation

AI-Agent:    claude-sonnet-4-6
AI-Provider: anthropic
AI-Session:  s_a1b2c3
AI-Visited:  analytics/revenue.py, payments/models.py, api/reports.py
AI-Message:  found rounding edge case in multi-currency — investigate before next release
```

Git already records the diff, date, and changed files. `AI-Visited:` is the only addition — files **read** during the session, which git does not track natively.

This gives you audit queries immediately:

```bash
git log --grep="AI-Agent:"                          # all AI commits
git log --grep="AI-Agent: claude" -p -- revenue.py  # claude's changes to a file
git log --format="%b" | grep "AI-Agent:" | sort | uniq -c  # model distribution
```

Three-tier architecture: **git** (authoritative audit, full diff) ↔ **`.codedna`** (lean session summary for agent navigation) ↔ **file `agent:` field** (one-liner, sliding-window safe). A `session_id` links all three.

### VSCode Extension (planned, M3)

Built on top of `git log` with AI trailers:
- **CodeLens** — last AI agent + commit count inline on every file and function
- **File heatmap** — how many AI sessions touched each file, by provider
- **Agent Timeline** — chronological session log with git diff per session
- **Stats panel** — model distribution chart, navigation efficiency per model

> Full spec: [SPEC.md §4.7–4.8](./SPEC.md) · VSCode extension is planned for M3.

---

## 🧬 The Four Levels

### Level 0 — Project Manifest `.codedna` *(The view from far away)*

A single YAML file at the repo root. The agent reads this first — before opening any source file — to understand packages, their purposes, and inter-package dependencies.

```yaml
# .codedna — auto-generated by codedna init
project: myapp
packages:
  payments/:
    purpose: "Invoice generation, payment processing"
  analytics/:
    purpose: "Revenue reports, KPI dashboards"
    depends_on: [payments/, tenants/]
  tenants/:
    purpose: "Multi-tenant management, suspension"
```

### Level 1 — Module Header *(The view from close up: ~50 tokens)*

A docstring at the top of every file. Five fields: `exports:` (public API), `used_by:` (reverse dependencies), `rules:` (hard constraints), `agent:` (session log), and `message:` (agent-to-agent chat). Only includes information that **cannot be inferred from the code**.

```python
"""orders/orders.py — Order lifecycle management.

exports: get_active_orders() -> list[dict] | create_order(user_id, items) -> None
used_by: analytics/revenue.py → get_revenue_rows
rules:   User system uses soft delete — NEVER return orders for users
         where users.deleted_at IS NOT NULL. Always JOIN on users.
agent:   claude-sonnet-4-6 | 2026-03-10 | Implemented order lifecycle.
         message: "bulk delete not tested with >1000 orders — verify before release"
"""
```

### Level 2 — Function-Level Rules *(The view from very close)*

`Rules:` and `message:` docstrings on critical functions, written **organically** by agents as they discover constraints. Each agent that fixes a bug or learns something important leaves a `Rules:` for the next agent — knowledge accumulates over time. `message:` carries open observations not yet confirmed as rules.

```python
def get_active_orders() -> list[dict]:
    """Return all non-cancelled orders for active (non-deleted) users.

    Rules:   MUST JOIN users and filter deleted_at before returning results.
             Failure to filter inflates revenue reports with deleted-user orders.
    message: claude-sonnet-4-6 | 2026-03-10 | pagination not implemented —
             will OOM on tenants with >50k orders
    """
```

### Level 3 — Semantic Naming *(Cognitive compression)*

**This is an agent-first convention, not a human style guide.** Traditional naming optimises for human readability in an IDE with type hints, hover tooltips, and "Go to Definition". LLM agents have none of these — they see raw text in a fixed-size context window. A variable named `data` forces the agent to trace backwards; `list_dict_users_from_db` is self-documenting in any 10-line window.

As AI agents write more of the code, the primary reader of source files shifts from human to machine. Semantic naming is designed for that present — and accelerating — reality.

```python
# ❌ Standard — agent must trace the entire call chain
data  = get_users()
price = request.json["price"]

# ✅ CodeDNA — readable in any context window
list_dict_users_from_db  = get_users()
int_cents_price_from_req = request.json["price"]
```

### Planner Read Protocol

To plan edits across 10+ files: read `.codedna` first, then read only the module docstring of each file (first 8–12 lines), build an `exports:` → `used_by:` graph, then open only the relevant files in full.

---

## 🎯 Annotation Design Principle — Architecture, Not Answers

The key rule for `rules:` annotations: **describe the mechanism, not the solution**.

```python
# ❌ Wrong — gives away the answer
rules:   Fix mysql/operations.py, oracle/operations.py, postgresql/operations.py

# ✅ Correct — describes the delegation chain
rules:   Trunc.as_sql() delegates to connection.ops.date_trunc_sql() and
         time_trunc_sql(). Each backend implements these independently.
```

`used_by:` is a **navigation map**, not a to-do list. The agent reasons about which targets are relevant to the current task and opens only those. In the benchmark, CodeDNA runs showed P=100% (zero wasted reads) on the tasks measured, while control runs scattered across irrelevant files.

---

## 🔄 Inter-Agent Knowledge Accumulation

CodeDNA is designed for multi-agent environments — different models, different tools, different sessions. Each agent leaves knowledge for the next:

```
Agent A fixes a bug → adds Rules: "MUST filter soft-deleted users"
Agent B reads Rules: → avoids the same bug without re-discovering it
Agent C discovers an edge case → extends the Rules:
```

Unlike external docs (which go stale), `Rules:` annotations are co-located with the code — read every time the function is edited. The maintenance cost is real but proportional: in a traditional codebase, a human developer maintains this knowledge manually across sessions. With CodeDNA, agents maintain annotations as a side effect of normal work — the same budget that would pay a developer to document constraints now pays for agent sessions that both fix bugs *and* leave annotations for the next agent. Verification agents (see [SPEC.md §8.6](./SPEC.md)) can audit annotation accuracy automatically, which is not possible with free-form comments.

Current benchmark results are **zero-shot** — no fine-tuning on the protocol. Models follow `used_by:` and `rules:` by general language understanding alone. A fine-tuned model could potentially treat these as native structured signals, which might reduce variance further — this remains to be tested.

> **See [SPEC.md](./SPEC.md) for the full inter-agent model, verification protocol, fine-tuning potential, and training corpus design.**

---

## 🌐 Language Support

CodeDNA v0.8 supports **11 languages**. Python is the reference implementation with full AST-based extraction (L1 module headers + L2 function `Rules:`). All other languages get L1-only annotation via regex adapters — no external toolchain required.

| Language | Extensions | L1 | L2 | Framework awareness |
|---|---|---|---|---|
| Python | `.py` | ✅ AST | ✅ AST | — |
| TypeScript / JavaScript | `.ts .tsx .js .jsx .mjs` | ✅ | — | — |
| Go | `.go` | ✅ | — | — |
| PHP | `.php` | ✅ | — | **Laravel** (Route facades, Eloquent) · **Phalcon** (Controller/Model, DI, Router) |
| Rust | `.rs` | ✅ | — | — |
| Java | `.java` | ✅ | — | — |
| Kotlin | `.kt .kts` | ✅ | — | — |
| C# | `.cs` | ✅ | — | — |
| Swift | `.swift` | ✅ | — | — |
| Ruby | `.rb` | ✅ | — | — |

**Template engines** (L1 via block-comment extraction):

| Template | Extensions | Comment syntax |
|---|---|---|
| Blade (Laravel) | `.blade.php` | `{{-- --}}` |
| Jinja2 / Twig | `.j2 .jinja2 .twig` | `{# #}` |
| Volt (Phalcon) | `.volt` | `{# #}` |
| ERB / EJS | `.erb .ejs` | `<%# %>` |
| Handlebars / Mustache | `.hbs .mustache` | `{{!-- --}}` |
| Razor / Cshtml | `.cshtml .razor` | `@* *@` |
| Vue SFC / Svelte | `.vue .svelte` | `<!-- -->` |

Pass `--extensions` to annotate non-Python files:

```bash
codedna init ./src --extensions ts go              # TypeScript + Go
codedna init ./app --extensions php                # PHP/Laravel or PHP/Phalcon
codedna init ./templates --extensions volt blade   # Phalcon Volt + Laravel Blade
codedna init . --extensions ts go php rs java      # mixed project
codedna check . --extensions ts go -v              # coverage report
```

### PHP + Laravel example

```php
<?php
// app/Http/Controllers/UserController.php — Handles user CRUD endpoints.
//
// exports: UserController::index() -> Response
//          UserController::store(Request) -> JsonResponse
// used_by: routes/web.php -> Route::resource('users', UserController::class)
// rules:   must extend App\Http\Controllers\Controller.
//          all public methods are auto-detected as exports.
// agent:   claude-sonnet-4-6 | anthropic | 2026-04-02 | s_20260402_001 | initial controller scaffold
```

### PHP + Phalcon example

```php
<?php
// app/controllers/UserController.php — Handles user CRUD in Phalcon MVC.
//
// exports: UserController::indexAction() -> Response
//          UserController::createAction() -> Response
//          route:/users
//          service:userService
// used_by: app/config/router.php -> $router->addGet('/users', ...)
// rules:   extends Phalcon\Mvc\Controller — do not add constructor, use DI.
//          $di->set('userService', ...) registers this service globally.
// agent:   claude-sonnet-4-6 | anthropic | 2026-04-02 | s_20260402_001 | initial Phalcon controller

namespace App\Controllers;

use Phalcon\Mvc\Controller;

class UserController extends Controller
{
    public function indexAction() { ... }
    public function createAction() { ... }
}
```

The PHP adapter auto-detects:
- `extends Controller` / `extends Model` / `extends Phalcon\Mvc\Controller` → marks as Phalcon component
- `$router->addGet('/uri', ...)` → exports as `route:/uri`
- `$di->set('serviceName', ...)` / `$di->setShared(...)` → exports as `service:serviceName`
- Public methods → annotated as `ClassName::method`

---

## 📁 Repository Structure

```
codedna/
├── README.md               ← you are here
├── QUICKSTART.md           ← 2-minute setup for every AI tool
├── SPEC.md                 ← full technical specification v0.8
├── integrations/
│   ├── CLAUDE.md               ← Claude Code system prompt
│   ├── .cursorrules             ← Cursor / Windsurf rules file
│   ├── .windsurfrules           ← Windsurf rules file
│   ├── .clinerules              ← Cline rules file
│   ├── copilot-instructions.md ← GitHub Copilot instructions
│   └── install.sh              ← one-line installer for all tools
├── codedna_tool/           ← installable CLI package (codedna init/update/check)
│   ├── cli.py
│   ├── __init__.py
│   └── languages/          ← per-language annotation adapters
├── codedna-plugin/         ← Claude Code plugin (pending review)
├── benchmark_agent/
│   ├── swebench/
│   │   ├── run_agent_multi.py          ← multi-model benchmark (5 providers)
│   │   └── analyze_multi.py            ← multi-model comparison
│   ├── claude_code_challenge/          ← fix-quality benchmark (control vs CodeDNA)
│   │   └── django__django-13495/
│   └── runs/                           ← results by model
├── examples/
│   ├── python/             ← annotated Python example
│   ├── python-api/         ← annotated Flask/FastAPI example
│   ├── typescript-api/     ← annotated TypeScript example
│   ├── go-api/             ← annotated Go example
│   ├── java-service/       ← annotated Java example
│   ├── rust-cli/           ← annotated Rust example
│   ├── php-laravel/        ← annotated Laravel example
│   └── ruby-sinatra/       ← annotated Ruby/Sinatra example
├── paper/                  ← scientific paper (arXiv preprint)
│   ├── codedna_paper.pdf
│   ├── codedna_paper.html
│   ├── codedna_whitepaper_EN.html
│   └── codedna_paper_IT.html
└── tools/
    ├── pre-commit              ← CodeDNA v0.8 pre-commit hook (validates staged files)
    ├── install-hooks.sh        ← installer: copies pre-commit into .git/hooks/
    ├── validate_manifests.py   ← deep annotation validator (format, agent dates, purpose length)
    ├── agent_history.py        ← session history viewer (reads AI git trailers)
    ├── traces_to_training.py   ← SFT/DPO/PRM dataset converter from benchmark runs
    └── extract_city_data.py    ← extract annotations to JSON for city visualization
```

---

## 💬 A note from the author

This is my first paper. I'm not a researcher — I'm a developer who is genuinely passionate about AI and how it interacts with code.

I built CodeDNA because I kept running into the same problem: AI agents making mistakes not because they were wrong, but because they had no context. I wondered: what if the context was already *in the file*? What if every snippet the agent read was self-sufficient?

I'm sharing this with complete humility. The benchmark is real, the data is reproducible, and the spec is open. Maybe it's useful to you. Maybe it sparks a better idea. Either way, I hope it contributes something.

If you find it helpful, try it, break it, improve it — or just tell me what you think. Feedback from people who actually use it is the only way this gets better.

If CodeDNA saved you some context tokens, a coffee is always welcome: [ko-fi.com/codedna](https://ko-fi.com/codedna)

— Fabrizio

---

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md). Examples in any language are welcome.

## License

[MIT](./LICENSE)
