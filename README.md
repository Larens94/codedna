# CodeDNA

> *Every file contains the entire project's genome. The AI reads one cell and understands the whole organism.*

**CodeDNA** is an **LLM Navigation Protocol** that embeds context directly into source code — at every level. Like biological DNA, a single fragment contains enough information to understand the whole.

No external memory. No vector databases. No context files that drift out of sync.

---

## The Biological Analogy

| Biology | CodeDNA |
|---|---|
| **Genome** | The complete set of project rules and conventions |
| **Chromosome** | A source file with its Manifest Header |
| **Gene** | A fully annotated function |
| **Genetic Marker** | An inline hyperlink (`@REQUIRES-READ`, `@SEE`) |

Just as cutting a hologram in half gives you two complete (if smaller) images, extracting 10 lines from a CodeDNA file gives you 10 lines that still carry enough context to act safely.

---

## The Two-Level Architecture

### Level 1 — The Genome (Manifest Header)

Every file starts with a **Manifest Header**: a compact, machine-readable block read by the AI *before* any code. In ~60 tokens, it answers:

- **What does this file do?** (`PURPOSE`)
- **What must I never break?** (`DEPENDS_ON`)
- **What do others rely on from me?** (`EXPORTS`)
- **What style must I maintain?** (`STYLE`)
- **Which database tables do I touch?** (`DB_TABLES`)
- **What was the last change?** (`LAST_MODIFIED`)

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
```

### Level 2 — The Genetic Markers (Inline Hyperlinks)

Modern AI agents often extract code in **sliding windows** — reading only lines 50–80 to edit a function, skipping the file header entirely. CodeDNA solves this with **inline hyperlinks** embedded at the function level:

```python
def apply_discount(base_price: int, user_tier: str) -> float:
    # @REQUIRES-READ: config.py → MAX_DISCOUNT_ALLOWED (must not exceed this limit)
    # @REQUIRES-READ: db.py → UserSchema (valid values for user_tier)
    # @MODIFIES-ALSO: invoice.py → calculate_total() (recalculates if discount changes)

    if user_tier == "premium":
        return base_price * 0.8  # cast to int done in main.py
    return base_price
```

When an agent reads this fragment, it knows exactly what to look up before making any change. It's **Hyperlinking for LLMs** — the agent follows the links, gathers context, then acts.

#### Hyperlink Annotations

| Tag | Semantics |
|---|---|
| `@SEE: file → symbol` | Recommended context — helpful but not blocking |
| `@REQUIRES-READ: file → symbol` | Mandatory — agent MUST read this before editing |
| `@MODIFIES-ALSO: file → symbol` | If you change this, go change that too |

---

## Why It Works

**Standard approach**: context lives outside the code (CLAUDE.md, RAG, MemGPT).  
Every prompt must fetch, inject, and pay the token cost for it.

**CodeDNA approach**: context lives *inside* the code, at every level.  
The AI reads it for free as part of reading the file.

```
Token overhead:    Zero   — context is in the file, not the prompt
Context drift:     Zero   — the header is co-located with the code it describes
Retrieval latency: Zero   — no lookup, no embedding, no network call
Sliding window:    Solved — inline hyperlinks guide the agent even on partial reads
```

---

## Benchmark (Real Results — gemini-2.5-flash)

3 edit scenarios × 3 runs each. Judge: independent Gemini instance.

| Metric | Control | CodeDNA |
|---|---|---|
| Edit quality (AI Judge) | **10 / 10** | **10 / 10** |
| Cross-file errors | baseline | **0** |
| External context system required | Yes | **No** |

CodeDNA matches quality without any external context infrastructure.  
Full results: [`benchmark/results.json`](./benchmark/results.json)

---

## Language Support

CodeDNA works with any language that supports single-line comments:

| Language | Comment style |
|---|---|
| Python, Ruby, Shell | `# KEY: value` |
| JavaScript, TypeScript, Go, Rust, C | `// KEY: value` |
| SQL | `-- KEY: value` |

---

## Repository Structure

```
codedna/
├── README.md               ← you are here
├── SPEC.md                 ← full technical specification
├── CONTRIBUTING.md         ← how to add language examples
├── LICENSE                 ← MIT
├── examples/
│   ├── python/             ← Python with Manifest + Hyperlinks
│   ├── javascript/         ← JavaScript example
│   └── typescript/         ← TypeScript example
└── benchmark/
    ├── codedna_benchmark.py    ← reproducible benchmark
    ├── results.json            ← real Gemini results
    └── index.html              ← protocol landing page
```

---

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md). Examples in any language are welcome.

---

## License

[MIT](./LICENSE)
