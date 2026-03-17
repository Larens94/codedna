# 🧬 CodeDNA — Inter-Agent Communication Protocol v0.7

> *An in-source annotation standard where the writing agent encodes architectural context and the reading agent decodes it. The file is the channel. Every fragment carries the whole.*

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/CodeDNA-v0.7-6366f1)](./SPEC.md)
[![arXiv](https://img.shields.io/badge/paper-arXiv-b31b1b)](./paper/codedna_paper.pdf)
[![CI](https://github.com/Larens94/codedna/actions/workflows/ci.yml/badge.svg)](https://github.com/Larens94/codedna/actions/workflows/ci.yml)
[![CodeQL](https://github.com/Larens94/codedna/actions/workflows/codeql.yml/badge.svg)](https://github.com/Larens94/codedna/actions/workflows/codeql.yml)

**Compatible with:**
[![Cursor](https://img.shields.io/badge/Cursor-000000?logo=cursor&logoColor=white)](./integrations/.cursorrules)
[![Claude Code](https://img.shields.io/badge/Claude_Code-D97757?logo=anthropic&logoColor=white)](./integrations/CLAUDE.md)
[![GitHub Copilot](https://img.shields.io/badge/GitHub_Copilot-000000?logo=github&logoColor=white)](./integrations/copilot-instructions.md)
[![Windsurf](https://img.shields.io/badge/Windsurf-0891b2?logoColor=white)](./integrations/.cursorrules)
[![ChatGPT](https://img.shields.io/badge/ChatGPT-74aa9c?logo=openai&logoColor=white)](./QUICKSTART.md)
[![Gemini](https://img.shields.io/badge/Gemini-4285F4?logo=google&logoColor=white)](./QUICKSTART.md)

**CodeDNA** is an **inter-agent communication protocol** implemented as in-source annotations. The writing agent embeds architectural context directly into source files; the reading agent decodes it at any point in the file. Like biological DNA — cut a hologram in half and you get two smaller complete images.

**No RAG. No vector DB. No external rules files. Minimal drift (context co-located with code).**

> **🎯 Less Prompt Engineering Needed:** CodeDNA annotations help AI agents navigate the codebase with less manual guidance. Even less-technical users can get better multi-file fixes by describing the problem — the architectural context is already in the code.

![CodeDNA Site — Animated DNA Hero](./docs/hero.png)

> **🔄 The Network Effect:** When an AI agent writes CodeDNA annotations, it leaves a navigable trail for every other agent that reads the code after it — regardless of vendor or model. The more agents that participate, the more useful the protocol becomes.

---

## 🤔 Who is CodeDNA for?

| You are… | Without CodeDNA | With CodeDNA |
|---|---|---|
| **Non-technical user** | Must learn prompt engineering to guide the AI agent through the codebase | Just describe the problem — annotations guide the agent automatically |
| **Junior developer** | AI finds the obvious file, misses the 5 related ones | `used_by:` graph helps find related files that may need changes |
| **Senior developer** | Spends time writing detailed prompts every session | Writes annotations once, benefits persist across sessions |
| **Team lead** | Each developer's AI makes different mistakes | Annotations encode team knowledge — more consistent results |

**The core idea:** today, the quality of AI-assisted coding often depends on the *user's* ability to prompt. CodeDNA moves some of that knowledge from ephemeral prompts into persistent, version-controlled source code.

---

## ⚡ 2-Minute Setup

### One-Line Install (CLI)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh)
```

Install for a **single tool** only:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh) cursor
# Options: claude | cursor | copilot | cline | windsurf | agents | all
```

### Manual Setup

**Pick your AI tool and paste:**

| Tool | File to create | Source |
|---|---|---|
| Cursor | `.cursorrules` | [`integrations/.cursorrules`](./integrations/.cursorrules) |
| Claude Code | `CLAUDE.md` | [`integrations/CLAUDE.md`](./integrations/CLAUDE.md) |
| GitHub Copilot | `.github/copilot-instructions.md` | [`integrations/copilot-instructions.md`](./integrations/copilot-instructions.md) |
| Antigravity / Custom | System prompt | See [QUICKSTART.md](./QUICKSTART.md) |
| Any other LLM | Any of the above | See [QUICKSTART.md](./QUICKSTART.md) |

Then annotate your first file → see [QUICKSTART.md](./QUICKSTART.md)

---

## 📊 Benchmark — SWE-bench Multi-Model Results

5 real Django issues from [SWE-bench](https://github.com/princeton-nlp/SWE-bench), tested across 5 state-of-the-art LLMs. Same prompt, same tools, same tasks. **Only difference: CodeDNA annotations.**

> **Metric: File Localization F1** — measures how accurately models identify the files that need modification. While standard SWE-bench evaluates end-to-end resolution, this benchmark isolates the preceding bottleneck: navigation.

| Model | Ctrl F1 | DNA F1 | **Δ F1** | Tasks Won |
|---|---|---|---|---|
| **Gemini 2.5 Flash** | 57% | **77%** | **+20%** | 4/5 |
| **GPT-5.3 Codex** | 39% | **51%** | **+12%** | 3/5 |
| **Gemini 2.5 Pro** | 57% | **65%** | **+8%** | 3/5 |
| **GPT-4o** | 49% | **51%** | **+2%** | 1/5 |
| **DeepSeek Chat** | 42% | 40% | −1% | 1/5 |

> **CodeDNA improves file localization F1 on 4 out of 5 models.** The largest gain (+20pp) is on Gemini 2.5 Flash, winning 4/5 tasks. The benefit is most pronounced on tasks requiring cross-module navigation.

Full data: [`benchmark_agent/runs/`](./benchmark_agent/runs/) · Script: [`benchmark_agent/swebench/run_agent_multi.py`](./benchmark_agent/swebench/run_agent_multi.py)

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

A docstring at the top of every file. Only includes information that **cannot be inferred from the code**: the public API (`exports:`), who depends on this file (`used_by:`), and domain constraints (`rules:`). Import statements already declare dependencies — no need to duplicate them.

```python
"""orders/orders.py — Order lifecycle management.

exports: get_active_orders() -> list[dict] | create_order(user_id, items) -> None
used_by: analytics/revenue.py → get_revenue_rows
rules:   User system uses soft delete — NEVER return orders for users
         where users.deleted_at IS NOT NULL. Always JOIN on users.
"""
```

### Level 2 — Function-Level Rules *(The view from very close)*

`Rules:` docstrings on critical functions, written **organically** by agents as they discover constraints. Each agent that fixes a bug or learns something important leaves a `Rules:` for the next agent — knowledge accumulates over time.

```python
def get_active_orders() -> list[dict]:
    """Return all non-cancelled orders for active (non-deleted) users.

    Rules:   MUST JOIN users and filter deleted_at before returning results.
             Failure to filter inflates revenue reports with deleted-user orders.
    """
```

### Level 3 — Semantic Naming *(Cognitive compression)*

Variable names encode type, shape, domain, and origin. Any 10-line extract is self-documenting.

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

## 🔄 Inter-Agent Knowledge Accumulation

CodeDNA is built for environments where **multiple AI agents work on the same codebase over time** — different models, different tools, different sessions. Each agent leaves knowledge for the next:

```
Agent A fixes a bug → adds Rules: "MUST filter soft-deleted users"
         ↓
Agent B reads Rules: → avoids the same bug without re-discovering it
         ↓
Agent C discovers a related edge case → extends the Rules:
         ↓
Knowledge accumulates organically in the codebase
```

Unlike documentation (which goes stale), `Rules:` annotations are **co-located with the code** — they are read every time the function is edited.

### Verification Agents

Because agents can hallucinate, `Rules:` annotations may contain incorrect information. A wrong annotation — e.g., "MUST filter by tenant_id" when no such filter exists — could propagate into every future agent's output.

**Solution: verification agents** that periodically cross-check annotations against the actual code. This is the cost of the savings — annotation maintenance. But because annotations are structured and machine-readable, this maintenance is also automatable.

| Without CodeDNA | With CodeDNA |
|---|---|
| N agents rediscover the same constraint | One writes `Rules:`, N benefit |
| Bugs re-introduced across sessions | Constraints preserved across sessions |
| Human writes prompts every session | Knowledge accumulates automatically |

> **See [SPEC.md §8.5–8.7](./SPEC.md) for the full inter-agent model, verification protocol, and cost analysis.**

---

## 🌐 Language Support

CodeDNA v0.7 is validated on **Python** using the native module docstring format. Support for other languages is planned for future versions.

---

## 📁 Repository Structure

```
codedna/
├── README.md               ← you are here
├── QUICKSTART.md           ← 2-minute setup for every AI tool
├── SPEC.md                 ← full technical specification v0.7
├── integrations/
│   ├── CLAUDE.md               ← Claude Code system prompt
│   ├── .cursorrules             ← Cursor rules file
│   ├── copilot-instructions.md ← GitHub Copilot instructions
│   └── install.sh              ← one-line installer for all tools
├── benchmark_agent/
│   ├── swebench/
│   │   ├── run_agent_multi.py      ← multi-model benchmark (5 providers)
│   │   └── analyze_multi.py        ← multi-model comparison
│   └── runs/                       ← results by model
├── examples/
│   └── python/
├── paper/                  ← scientific paper (arXiv preprint)
│   └── codedna_paper.pdf
└── tools/
    └── auto_annotate.py    ← auto-generate exports/used_by for existing codebases
```

---

## 💬 A note from the author

This is my first paper. I'm not a researcher — I'm a developer who is genuinely passionate about AI and how it interacts with code.

I built CodeDNA because I kept running into the same problem: AI agents making mistakes not because they were wrong, but because they had no context. I wondered: what if the context was already *in the file*? What if every snippet the agent read was self-sufficient?

I'm sharing this with complete humility. The benchmark is real, the data is reproducible, and the spec is open. Maybe it's useful to you. Maybe it sparks a better idea. Either way, I hope it contributes something.

If you find it helpful, try it, break it, improve it — or just tell me what you think. Feedback from people who actually use it is the only way this gets better.

— Fabrizio

---

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md). Examples in any language are welcome.

## License

[MIT](./LICENSE)
