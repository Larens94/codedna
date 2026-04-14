# CodeDNA: An In-Source Communication Protocol for AI Coding Agents

> *The writing agent encodes architectural context. The reading agent decodes it. The file is the channel.*

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/CodeDNA-v0.8-6366f1)](./SPEC.md)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.19158336-blue)](https://doi.org/10.5281/zenodo.19158336)
[![Website](https://img.shields.io/badge/website-codedna.silicoreautomation.space-6366f1)](https://codedna.silicoreautomation.space)
[![CI](https://github.com/Larens94/codedna/actions/workflows/ci.yml/badge.svg)](https://github.com/Larens94/codedna/actions/workflows/ci.yml)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-support-FF5E5B?logo=ko-fi&logoColor=white)](https://ko-fi.com/codedna)
[![Discord](https://img.shields.io/badge/Discord-Join_Community-5865F2?logo=discord&logoColor=white)](https://discord.gg/7Fs5J2ua)
[![Languages](https://img.shields.io/badge/Languages-11_languages-6366f1)](docs/languages.md)

**Compatible with:**
[![Claude Code](https://img.shields.io/badge/Claude_Code-D97757?logo=anthropic&logoColor=white)](./integrations/CLAUDE.md)
[![Cursor](https://img.shields.io/badge/Cursor-000000?logo=cursor&logoColor=white)](./integrations/.cursorrules)
[![GitHub Copilot](https://img.shields.io/badge/GitHub_Copilot-000000?logo=github&logoColor=white)](./integrations/copilot-instructions.md)
[![Windsurf](https://img.shields.io/badge/Windsurf-0891b2?logoColor=white)](./integrations/.windsurfrules)
[![OpenCode](https://img.shields.io/badge/OpenCode-6366f1?logoColor=white)](./integrations/AGENTS.md)
[![Gemini](https://img.shields.io/badge/Gemini-4285F4?logo=google&logoColor=white)](./QUICKSTART.md)
[![ChatGPT](https://img.shields.io/badge/ChatGPT-74aa9c?logo=openai&logoColor=white)](./QUICKSTART.md)

---

**CodeDNA** embeds architectural context directly in source files as structured annotations. AI agents read `used_by:` (who depends on me), `rules:` (hard constraints), and `message:` (agent-to-agent chat) — no RAG, no vector DB, no external rules files. [11 languages supported](docs/languages.md).

**Preliminary results:**
- **SWE-bench:** +13pp F1 on Gemini 2.5 Flash (p=0.040), +9pp on DeepSeek Chat — zero-shot, no fine-tuning
- **Multi-agent teams:** 5-agent teams build applications 1.6x faster; `message:` field adopted spontaneously in 98.2% of files
- **Fix quality:** CodeDNA session matched 7/7 files of the official Django patch vs 6/7 for control

> [Full benchmark results](docs/benchmark.md) · [Multi-agent experiments](docs/experiments.md)

![CodeDNA Logo](./docs/logo.png)

---

## The Problem

AI coding agents waste context exploring irrelevant files, missing cross-file constraints and reverse dependencies. The result: incomplete patches, higher token costs, and models that repeat the same mistakes across sessions.

The root cause is structural. Information like reverse dependencies and domain constraints cannot be inferred from a single file — they require reading the whole codebase. Without a way to persist that knowledge, every agent starts from scratch.

CodeDNA embeds this context directly in source files: `used_by:` maps reverse dependencies, `rules:` encodes domain constraints, and `agent:` / `message:` accumulate knowledge across sessions.

---

## How it works

![CodeDNA Navigation Demo](./docs/codedna_viz.gif)

> Without CodeDNA: agent opens random files, misses 8/10 critical files. With CodeDNA: follows `used_by:` chain, finds 6/10. Retry risk -52%.
> [Interactive version](./docs/codedna_viz_3metaphors.html)

---

## Who is CodeDNA for?

| You are... | Without CodeDNA | With CodeDNA |
|---|---|---|
| **Non-technical user** | Must learn prompt engineering to guide the AI | Describe the problem — annotations provide structural context |
| **Junior developer** | AI finds the obvious file, misses the 5 related ones | `used_by:` graph surfaces related files |
| **Senior developer** | Writes detailed prompts every session | Writes annotations once — context persists |
| **Team lead** | Each developer's AI makes different mistakes | Annotations encode team knowledge |

---

## Quick Start

### Option 1 — Claude Code Plugin (recommended)

```bash
claude plugin marketplace add Larens94/codedna
claude plugin install codedna@codedna
```

Includes 4 hooks (SessionStart, PreToolUse, PostToolUse, Stop) + 4 skills (`/codedna:init`, `/codedna:check`, `/codedna:manifest`, `/codedna:impact`). Automatic enforcement on every file write across all 11 languages.

### Option 2 — Other AI Tools

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh) <tool>
```

| Tool | Command | Enforcement |
|---|---|---|
| **Cursor** | `cursor-hooks` | Active — hook scripts in `.cursor/hooks/` |
| **GitHub Copilot** | `copilot-hooks` | Active — `.github/hooks/hooks.json` |
| **Cline** | `cline-hooks` | Active — `.clinerules/hooks/` |
| **OpenCode** | `opencode` | Active — JS plugin in `.opencode/plugins/` |
| Windsurf | `windsurf` | Instructions only |
| Claude Code (manual) | `claude-hooks` | Active — alternative to Option 1 |

> Full setup guide: [QUICKSTART.md](./QUICKSTART.md) · [integrations/README.md](./integrations/README.md)

### Option 3 — Annotate existing files (CLI)

```bash
pip install git+https://github.com/Larens94/codedna.git

codedna init /path/to/project --no-llm     # Free — structural only (exports + used_by via AST)
codedna init /path/to/project --model ollama/llama3   # Free — local LLM adds rules:
codedna check /path/to/project              # Coverage report
```

---

## The Four Levels

**Level 0 — Project Manifest (`.codedna`)** — the view from far away. Package structure + session log.

**Level 1 — Module Header** — the view from close up (~50 tokens per file):

```python
"""orders/orders.py — Order lifecycle management.

exports: get_active_orders() -> list[dict] | create_order(user_id, items) -> None
used_by: analytics/revenue.py → get_revenue_rows
rules:   User system uses soft delete — NEVER return orders where users.deleted_at IS NOT NULL.
agent:   claude-sonnet-4-6 | anthropic | 2026-03-10 | s_001 | Implemented order lifecycle.
         message: "bulk delete not tested with >1000 orders — verify before release"
"""
```

**Level 2 — Function-Level Rules** — the view from very close (sliding-window safe):

```python
def get_active_orders() -> list[dict]:
    """Return all non-cancelled orders for active users.

    Rules:   MUST JOIN users and filter deleted_at before returning results.
    message: claude-sonnet-4-6 | 2026-03-10 | pagination not implemented — will OOM on >50k orders
    """
```

**Level 3 — Semantic Naming** — agent-first cognitive compression:

```python
list_dict_users_from_db  = get_users()          # not: data = get_users()
int_cents_price_from_req = request.json["price"] # not: price = request.json["price"]
```

> Full specification: [SPEC.md](./SPEC.md)

---

## Benchmark Results

| Model | Ctrl F1 | DNA F1 | **Δ F1** | p-value |
|---|---|---|---|---|
| **Gemini 2.5 Flash** | 60% | **72%** | **+13pp** | 0.040 |
| **DeepSeek Chat** | 50% | **60%** | **+9pp** | 0.11 |
| **Gemini 2.5 Pro** | 60% | **69%** | **+9pp** | 0.11 |

CodeDNA is most effective on **dependency chain tasks** (up to +22pp). On cross-cutting tasks (same fix in N unrelated files), the benefit is ~0% — a known limitation.

| Experiment | Key result |
|---|---|
| **Multi-agent RPG** (5 agents, DeepSeek Chat) | 1.6x faster, playable game vs static scene |
| **Multi-agent SaaS** (5 agents, DeepSeek R1) | 98.2% annotation adoption, lower complexity |
| **Fix quality** (Claude Sonnet, django-13495) | 7/7 patch files vs 6/7, zero failed edits |

> [Detailed benchmark](docs/benchmark.md) · [Experiment reports](docs/experiments.md) · [Raw data](benchmark_agent/runs/)

---

## Roadmap

| Milestone | Status |
|---|---|
| **M1** — Protocol v0.8, CLI, AST extraction, `message:` | Done |
| **M3** — Enforcement hooks (Claude, Cursor, Copilot, Cline, OpenCode) | Done |
| **M4** — 11 languages + template engines | Done |
| **M2** — SWE-bench Verified (500 tasks, 12 repos) | In progress |
| **M5** — VSCode extension (used_by graph, agent timeline) | Planned |
| **M6** — arXiv preprint, ICSE submission | Planned |

---

## Documentation

| Document | What it covers |
|---|---|
| [SPEC.md](./SPEC.md) | Full technical specification v0.8 |
| [QUICKSTART.md](./QUICKSTART.md) | Setup guide for every AI tool |
| [docs/benchmark.md](docs/benchmark.md) | SWE-bench results, per-task analysis, annotation integrity |
| [docs/experiments.md](docs/experiments.md) | Multi-agent team experiments (RPG, SaaS, fix quality) |
| [docs/languages.md](docs/languages.md) | 11 languages, PHP/Laravel/Phalcon, template engines |
| [integrations/README.md](integrations/README.md) | Tool-specific installation reference |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | Dev setup, contribution guidelines |

---

## A note from the author

I built CodeDNA because AI agents kept making mistakes not because they were wrong, but because they had no context. What if the context was already *in the file*?

The benchmark is real, the data is reproducible, and the spec is open. Try it, break it, improve it — or just tell me what you think.

If CodeDNA saved you some context tokens, a coffee is always welcome: [ko-fi.com/codedna](https://ko-fi.com/codedna)

— Fabrizio

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md). Examples in any language are welcome.

## License

[MIT](./LICENSE)
