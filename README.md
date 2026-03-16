# 🧬 CodeDNA — Annotation Standard v0.5

> *Every file contains the entire project's genome. The AI reads one fragment and understands the whole.*

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/CodeDNA-v0.5-6366f1)](./SPEC.md)
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

**CodeDNA** embeds architectural context **directly into source files**. Like biological DNA — cut a hologram in half and you get two smaller complete images. Extract 10 lines from a CodeDNA file and those 10 lines still carry enough context for an AI agent to act correctly.

**No RAG. No vector DB. No external rules files. Minimal drift (context co-located with code).**

![CodeDNA Site — Animated DNA Hero](./docs/hero.png)

---

## ⚡ 2-Minute Setup

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

## 📊 Benchmark — Real Agent Results

### 🆕 Multi-Model SWE-bench Benchmark (5 models × 5 tasks)

5 real Django issues from [SWE-bench](https://github.com/princeton-nlp/SWE-bench), tested across 5 state-of-the-art LLMs. Same prompt, same tools, same tasks. **Only difference: CodeDNA annotations.**

| Model | Ctrl F1 | DNA F1 | **Δ F1** | Tasks Won |
|---|---|---|---|---|
| **Gemini 2.5 Flash** | 57% | **77%** | **+20%** | 4/5 |
| **GPT-5.3 Codex** | 39% | **51%** | **+12%** | 3/5 |
| **Gemini 2.5 Pro** | 57% | **65%** | **+8%** | 3/5 |
| **GPT-4o** | 49% | **51%** | **+2%** | 1/5 |
| **DeepSeek Chat** | 42% | 40% | −1% | 1/5 |

> **CodeDNA improves file localization F1 on 4 out of 5 models.** The largest gain (+20pp) is on Gemini 2.5 Flash, winning 4/5 tasks. The benefit is most pronounced on tasks requiring cross-module navigation.

Full data: [`benchmark_agent/runs/`](./benchmark_agent/runs/) · Script: [`benchmark_agent/swebench/run_agent_multi.py`](./benchmark_agent/swebench/run_agent_multi.py)

### Agent Navigation Benchmark — Simple Codebase (11 files)

| Metric | Control | CodeDNA | Improvement |
|---|---|---|---|
| Total tool calls | 4 | 3 | **−25%** |
| Files read | 3 | 2 | **−33%** |
| Conversation turns | 5 | 4 | **−20%** |
| Bug found | ✅ Yes | ✅ Yes | Equal accuracy |

### Enterprise Benchmark — 105-file Codebase (3 bugs, 48 distractors)

| Bug Scenario | Control Tools | CodeDNA Tools | Control Found? | CodeDNA Found? |
|---|---|---|---|---|
| **B1** Suspended tenants in revenue | 4 | 3 | ❌ **No** | ✅ **Yes** |
| **B3** Admin permission bypass | 3 | 3 | ✅ Yes | ✅ Yes |
| **B4** Fulfillment inventory race | 6 | 4 | ✅ Yes | ✅ Yes |
| **Average** | **4.3** | **3.3** | **67%** | **100%** |

> **B1 is the decisive scenario**: the Control agent used more tool calls and still failed to identify the root cause. CodeDNA used fewer calls and succeeded.

---

## 🧬 The Three Levels

### Level 1 — Module Header *(Macro-context: ~70 tokens)*

A Python-native module docstring at the top of every file. The AI reads this before any code and immediately knows the file's purpose, dependencies, public API, and the rules it must respect. Using Python's standard docstring format maximises LLM comprehension — models trained on billions of Python files apply existing pattern-matching to the structured fields.

```python
"""orders/orders.py — Order lifecycle management.

deps:    db/queries.py → execute | users/users.py → get_user
exports: get_active_orders() -> list[dict] | create_order(user_id, items) -> None
used_by: analytics/revenue.py → get_revenue_rows
tables:  orders(user_id, status, created_at) | users(deleted_at)
rules:   User system uses soft delete — NEVER return orders for users
         where users.deleted_at IS NOT NULL. Always JOIN on users.
"""
```

### Level 2 — Sliding-Window Annotations *(Micro-context: per-function)*

AI agents often read files in **sliding windows** — lines 200–250, skipping the header. Level 2 solves this with two sub-layers:

**2a — Function docstring** (Google style) — embeds deps and rules at function scope:

```python
def get_active_orders() -> list[dict]:
    """Return all non-cancelled orders for active (non-deleted) users.

    Depends: users.get_user — soft-delete contract: filter deleted_at IS NOT NULL.
    Rules:   MUST JOIN users and filter deleted_at before returning results.
             Failure to filter inflates revenue reports with deleted-user orders.
    """
```

**2b — Call-site inline comment** — last line of defence, present at the exact danger point:

```python
    orders = execute("SELECT * FROM orders WHERE status != 'cancelled'")
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

### Bonus — Planner Manifest-Only Read Protocol

To plan edits across 10+ files, read only the module docstring of each (≈70 tokens × N files), build a `deps` → `exports` graph, then open only the relevant files in full.

---

## 🌐 Language Support

CodeDNA works in every language that supports single-line comments:

| Language | Comment style |
|---|---|
| Python, Ruby, Shell | `# KEY: value` |
| JavaScript, TypeScript, Go, Rust, C | `// KEY: value` |
| SQL | `-- KEY: value` |
| HTML | `<!-- KEY: value -->` |

---

## 📁 Repository Structure

```
codedna/
├── README.md               ← you are here
├── QUICKSTART.md           ← 2-minute setup for every AI tool
├── SPEC.md                 ← full technical specification v0.5
├── integrations/
│   ├── CLAUDE.md               ← Claude Code system prompt
│   ├── .cursorrules             ← Cursor rules file
│   ├── copilot-instructions.md ← GitHub Copilot instructions
│   └── install.sh              ← one-line installer for all tools
├── benchmark_agent/
│   ├── swebench/
│   │   ├── run_agent.py            ← single-model Gemini benchmark
│   │   ├── run_agent_multi.py      ← multi-model benchmark (5 providers)
│   │   ├── analyze.py              ← single-model analysis
│   │   └── analyze_multi.py        ← multi-model comparison
│   └── runs/                       ← results by model (gemini-2.5-flash, gpt-4o, etc.)
├── examples/
│   ├── python/
│   ├── javascript/
│   └── typescript/
├── paper/                  ← scientific paper (arXiv preprint)
│   └── codedna_paper.pdf
└── tools/
    └── validate_manifests.py
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
