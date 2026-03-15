# Beacon Framework

> *The context doesn't need to be retrieved. It's already in the file.*

**Beacon** is a source-file annotation standard that lets AI models understand any file instantly — by reading it top to bottom, without external memory, vector databases, or context injection.

Every file starts with a **Beacon Header**: a compact, machine-readable block that describes what the file does, what it depends on, what it exports, and what changed last. The AI reads the header first. By the time it reaches line 1 of actual code, it already knows everything it needs.

---

## The Problem

Modern AI coding assistants manage context through external systems:

| Approach | Problem |
|---|---|
| `CLAUDE.md` / `Cursor Rules` | Static, grows stale, floods the prompt with irrelevant tokens |
| RAG / Vector DBs | Retrieval latency, depends on embedding quality |
| MemGPT-style paging | Complex infrastructure, can evict relevant context |

All of these treat context as something to be *fetched*. Beacon treats context as something to be *embedded*.

---

## How It Works

Every source file begins with a Beacon Header:

```python
# ==============================================================
# FILE: dashboard.py
# PURPOSE: Monthly revenue KPI dashboard with chart and table
# DEPENDS_ON: utils.py → calculate_kpi(), format_currency()
# EXPORTS: render(execute_query_func) → HTML string
# STYLE: tailwind, chart.js
# DB_TABLES: orders (month, revenue, cost)
# LAST_MODIFIED: added margin column to table
# ==============================================================

from .utils import calculate_kpi, format_currency

def render(execute_query_func):
    ...
```

When an AI model opens this file, it reads the header in the first pass. It immediately knows:
- **What** the file does (`PURPOSE`)  
- **What it must not break** (`DEPENDS_ON`)  
- **What others rely on** (`EXPORTS`)  
- **What was last changed** (`LAST_MODIFIED`)

No external lookup. No prompt stuffing. Zero overhead.

---

## Language Support

Beacon works with any language that supports single-line comments:

| Language | Header style |
|---|---|
| Python | `# KEY: value` |
| JavaScript / TypeScript | `// KEY: value` |
| Go, Rust, C, C++ | `// KEY: value` |
| Ruby | `# KEY: value` |
| SQL | `-- KEY: value` |
| Shell | `# KEY: value` |

See [`examples/`](./examples/) for reference implementations.

---

## Benchmark Results

Compared to context-injection (CLAUDE.md style), Beacon shows:

| Metric | Control | Beacon | Delta |
|---|---|---|---|
| Prompt tokens (avg) | 540 | 388 | **−28%** |
| Edit quality score (AI Judge, 0–10) | 7.8 | 8.8 | **+13%** |
| Response speed | baseline | ≈ same | — |

Benchmarks run with Gemini across 3 edit scenarios × 3 runs each.  
Reproduce: see [`benchmark/`](./benchmark/).

---

## The Beacon Header Spec

| Field | Rule |
|---|---|
| `FILE` | Exact filename |
| `PURPOSE` | 1 line, max 12 words, describes *what*, not *how* |
| `DEPENDS_ON` | `file → func1, func2` or `none` |
| `EXPORTS` | Public API with signature, e.g. `render(fn) → str` |
| `STYLE` | CSS framework, chart library, UI conventions |
| `DB_TABLES` | Tables and relevant columns |
| `LAST_MODIFIED` | Last change in ≤8 words, updated on every edit |

Full spec: [`SPEC.md`](./SPEC.md)

---

## Why Beacon Wins

```
Token overhead:    Zero   (context is in the file, not the prompt)
Context drift:     Zero   (header is co-located with the code it describes)
Retrieval latency: Zero   (no lookup required)
Maintenance:       Auto   (LAST_MODIFIED updated on every edit)
```

---

## Quick Start

1. Add a Beacon Header to every file you want AI-aware
2. Configure your AI coding assistant to read the header before editing
3. Instruct the assistant to update `LAST_MODIFIED` as its first change on every edit

No libraries to install. No infrastructure to run. It's just comments.

---

## Repository Structure

```
beacon-framework/
├── README.md           ← you are here
├── SPEC.md             ← full technical specification
├── CONTRIBUTING.md     ← how to contribute
├── LICENSE             ← MIT
├── examples/
│   ├── python/         ← Python example
│   ├── javascript/     ← JavaScript example
│   └── typescript/     ← TypeScript example
└── benchmark/
    ├── beacon_benchmark.py   ← reproducible benchmark script
    ├── index.html            ← framework landing page
    └── README.md             ← how to run benchmarks
```

---

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md). All languages and use cases welcome.

---

## License

[MIT](./LICENSE) — use it, fork it, embed it.
