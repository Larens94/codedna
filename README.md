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

**No RAG. No vector DB. No external rules files. Zero drift.**

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

A real **Gemini 2.5 Flash agent** with function-calling tools (`read_file`, `list_files`, `grep`) navigated two versions of the same codebase to find bugs. **Identical task. Identical model. Only difference: CodeDNA annotations.**

### Agent Navigation Benchmark — Simple Codebase (11 files)

| Metric | Control | CodeDNA | Improvement |
|---|---|---|---|
| Total tool calls | 4 | 3 | **−25%** |
| Files read | 3 | 2 | **−33%** |
| Conversation turns | 5 | 4 | **−20%** |
| Bug found | ✅ Yes | ✅ Yes | Equal accuracy |

### Enterprise Benchmark — Large Multi-Domain Codebase

3 real-world bug scenarios. Control = no annotations. CodeDNA = standard v0.5 headers.

| Bug Scenario | Control Tools | CodeDNA Tools | Control Found? | CodeDNA Found? |
|---|---|---|---|---|
| **B1** Suspended tenants in revenue | 4 | 3 | ❌ **No** | ✅ **Yes** |
| **B3** Admin permission bypass | 3 | 3 | ✅ Yes | ✅ Yes |
| **B4** Fulfillment inventory race | 6 | 4 | ✅ Yes | ✅ Yes |
| **Average** | **4.3** | **3.3** | **67%** | **100%** |

> **B1 is the decisive scenario**: the Control agent used more tool calls and still failed to identify the root cause. CodeDNA used fewer calls and succeeded.

Full data: [`benchmark_agent/results_agent.json`](./benchmark_agent/results_agent.json) · [`benchmark_agent/results_enterprise.json`](./benchmark_agent/results_enterprise.json)

---

## 🧬 The Three Levels

### Level 1 — Manifest Header *(Macro-context: ~70 tokens)*

The first 14 lines of every file. The AI reads this before any code and already knows the file's purpose, dependencies, public API, and constraints it must respect.

```python
# === CODEDNA:0.4 =============================================
# FILE:           orders/orders.py
# PURPOSE:        Order lifecycle management
# CONTEXT_BUDGET: always
# DEPENDS_ON:     db/queries.py :: execute()
#                 users/users.py :: get_user()
# EXPORTS:        get_active_orders() → list[dict]
#                 create_order(user_id, items) → None
# REQUIRED_BY:    analytics/revenue.py :: get_revenue_rows()
# AGENT_RULES:    User system uses soft delete.
#                 Never join orders without filtering deleted_at.
# LAST_MODIFIED:  added soft-delete filter
# =============================================================
```

### Level 2 — Inline Hyperlinks *(Micro-context: per-function)*

AI agents often read files in **sliding windows** — lines 200–250, skipping the header. Inline hyperlinks solve this by embedding navigation cues at each function.

```python
def get_active_orders():
    # @REQUIRES-READ: users/users.py :: delete_user() — soft delete semantics
    # @MODIFIES-ALSO: analytics/revenue.py :: get_revenue_rows()
    return execute("SELECT * FROM orders WHERE status != 'cancelled'")
```

| Tag | Meaning | Agent must... |
|---|---|---|
| `@SEE` | Recommended context | Read when uncertain |
| `@REQUIRES-READ` | Mandatory prerequisite | Read before writing any logic |
| `@MODIFIES-ALSO` | Cascade required | Update target in same changeset |
| `@BREAKS-IF-RENAMED` | Identity is load-bearing | Never rename without updating all callers |

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

To plan edits across 10+ files, read only the first 14 lines of each (≈70 tokens × N files), filter by `CONTEXT_BUDGET`, build a `DEPENDS_ON` graph, then open only the relevant files in full.

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
│   └── copilot-instructions.md ← GitHub Copilot instructions
├── benchmark_agent/
│   ├── agent.py                ← live Gemini agent with function calling
│   ├── generate_codebase.py    ← generates control + codedna codebases
│   ├── run_benchmark.py        ← runs the benchmark
│   ├── results_agent.json      ← simple benchmark results
│   └── results_enterprise.json ← enterprise benchmark results
├── examples/
│   ├── python/
│   ├── javascript/
│   └── typescript/
├── benchmark/              ← older LLM-judge benchmark (v1)
├── paper/                  ← scientific paper (arXiv preprint)
│   └── codedna_paper.pdf
└── tools/
    └── validate_manifests.py
```

---

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md). Examples in any language are welcome.

## License

[MIT](./LICENSE)
