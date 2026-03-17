# NLnet NGI0 Commons Fund — Bozza di candidatura per CodeDNA (CORRETTA)

> **Scadenza: 1 aprile 2026, 12:00 CEST**
> **NON INVIARE** — revisionare e personalizzare prima

---

## Selezione del bando
**Bando tematico**: `NGI Zero Commons Fund`

## Informazioni di contatto
- **Nome**: `[IL TUO NOME]`
- **Email**: `[LA TUA EMAIL]`
- **Telefono**: `[IL TUO TELEFONO]`
- **Organizzazione**: `[LA TUA ORG o lascia vuoto]`
- **Paese**: `Italia`

---

## Informazioni generali sul progetto

### Nome della proposta
```text
CodeDNA — An inter-agent communication protocol for AI-navigable source code
```

### Sito web / wiki
```text
https://github.com/Larens94/codedna
```

### Riassunto (max 1200 caratteri)
```text
CodeDNA is an inter-agent communication protocol implemented as in-source annotations. The writing agent encodes architectural context directly into source files; the reading agent decodes it. The file is the channel — no RAG, no vector DB, no external rules files.

The problem: AI coding agents waste 40-60% of their context window exploring irrelevant files. They grep blindly, re-read files, and miss critical dependencies.

CodeDNA solves this with 4 layers: a project manifest (.codedna), module headers (exports, used_by, rules), function-level rules, and semantic naming. The key insight: used_by (reverse dependencies) and rules (domain constraints) cannot be inferred from reading the code alone — they require reading many files. CodeDNA embeds this knowledge once.

Crucially, this is agent-to-agent communication, not human-to-agent. When Agent A discovers a constraint, it writes a rules: annotation. Agent B — different model, different session — reads it and avoids the same mistake. Knowledge accumulates organically.

Benchmarks on SWE-bench (5 Django tasks, 5 LLMs) show +20% F1 improvement in file localization, with fewer tokens consumed.

Fully open source (MIT), vendor-neutral, zero dependencies.
```

### Esperienza (max 2500 caratteri)
```text
I am a software engineer with experience in full-stack development, automation, and AI-assisted tooling. I have been working on the intersection of AI agents and software engineering since 2023.

CodeDNA originated from practical frustration: while using AI coding assistants (Claude, Copilot, Gemini) on large codebases, I observed that agents consistently failed to navigate complex dependency graphs. They would read the wrong files, miss critical consumers, and waste tokens on irrelevant code. More importantly, each agent session started from scratch — no knowledge was preserved between sessions or across different AI tools.

I developed the CodeDNA protocol iteratively through real-world usage:
- v0.1-v0.5: experimented with various annotation formats (YAML frontmatter, inline comments, separate manifests)
- v0.6: consolidated to the current 3-field module header (exports, used_by, rules)
- v0.7: current version, validated on Python, with CLI tooling, benchmark infrastructure, and integration templates for 6 AI coding tools

I built a benchmark suite based on SWE-bench (real GitHub issues from Django) that measures how annotations affect AI agent file localization accuracy. The benchmark compares control (vanilla code) vs CodeDNA (annotated code) using the same LLM, tools, and constraints. Results across 5 models show consistent improvement on 4 out of 5 LLMs.

I have also created a one-line installer for integration with Claude Code, Cursor, Copilot, Windsurf, and other tools, plus a documentation website.

The project is open source on GitHub and has been developed entirely in public.
```

---

## Supporto richiesto

### Importo richiesto
```text
50000
```

### Utilizzo del budget (max 2500 caratteri)
```text
Rate: €60/hour. Total: €50,000 (~833 hours over 12 months).

Milestone 1 — Protocol Specification & CLI (€12,000, ~200h)
- Finalize CodeDNA v1.0 specification document
- Build robust CLI: codedna init, codedna verify, codedna update
- Python AST-based analysis for accurate exports/used_by extraction
- Automated verification agent: detect stale annotations, missing headers, incorrect rules
- Package for PyPI distribution

Milestone 2 — Benchmark Suite (€10,000, ~167h)
- Expand from 5 to 20+ SWE-bench tasks across multiple projects
- Test with 5+ LLMs (Gemini, GPT, Claude, DeepSeek, Codex)
- Statistical analysis with confidence intervals
- Reproducible benchmark runner (single command)
- Public results dashboard

Milestone 3 — AI Tool Integrations (€10,000, ~167h)
- Native integration templates for Claude Code, GitHub Copilot, Cursor, Antigravity
- MCP server for CodeDNA (Model Context Protocol)
- VS Code extension for visualizing the used_by graph
- Auto-update hooks (pre-commit, CI/CD)

Milestone 4 — Language Extension & Documentation (€8,000, ~133h)
- Extend CodeDNA to JavaScript/TypeScript
- Extension points for Go, Rust (community-driven)
- Comprehensive documentation site
- Tutorial videos and quickstart guides

Milestone 5 — Research Paper & Community (€10,000, ~167h)
- Peer-reviewed paper with full benchmark results
- Conference submissions (ICSE, ASE, or similar)
- Community engagement: Discord, GitHub Discussions
- Outreach to open source projects for adoption

No other funding sources currently. This would be the first external funding for CodeDNA.
```

### Confronto con le iniziative esistenti (max 4000 caratteri)
```text
Several approaches exist for helping AI agents work with codebases. CodeDNA differs from all of them in one fundamental way: it is an inter-agent communication protocol, not a human-to-agent instruction format.

1. REPOSITORY-LEVEL CONTEXT FILES (CLAUDE.md, .cursor/rules/, copilot-instructions.md)
These are human→agent communication: a developer writes instructions for the AI. They describe the project at a high level but don't provide file-level navigation. CodeDNA is agent→agent communication: when Agent A discovers a constraint, it writes a rules: annotation that Agent B (different model, different session) reads and acts on. The file is the channel. This distinction matters because human-written rules don't scale — agents discover constraints faster than humans can document them.

2. LANGUAGE SERVERS (LSP)
Language servers provide precise "go-to-definition" capabilities but require a running process and answer "where is this symbol defined?". They don't answer "who depends on this file?" (the reverse dependency) or "what domain constraints apply here?". CodeDNA provides reverse dependencies (used_by) and domain rules — information that requires cross-file knowledge. It is static, zero-dependency, and works with any tool.

3. DOCUMENTATION GENERATORS (Sphinx, JSDoc, TypeDoc)
These describe WHAT code does, not HOW it connects to other code. They don't provide a navigation graph or accumulate domain constraints. CodeDNA complements documentation by adding the inter-file metadata that agents need for multi-file tasks.

4. DEPENDENCY GRAPHS (import analyzers, call graphs)
Static analysis can generate dependency graphs, but as external artifacts (JSON, diagrams). When an agent reads a file, it doesn't see the graph. CodeDNA embeds the graph in the file header — visible in the first 10 lines of every read.

5. RAG / VECTOR DATABASES
RAG systems require infrastructure (embedding pipeline, vector store, retrieval logic). They add latency, cost, and a new failure mode (retrieval quality). CodeDNA has zero retrieval latency — context is co-located with the code. No infrastructure needed.

6. AI-SPECIFIC ANNOTATION STANDARDS
To our knowledge, no open standard exists for agent-to-agent communication via source code. CLAUDE.md, .cursorrules, and AGENTS.md are all human→agent formats, vendor-specific, and project-level (not file-level). CodeDNA fills this gap with a vendor-neutral, file-level protocol.

KEY DIFFERENTIATORS:
- Inter-agent: agent→agent communication, not human→agent
- Inline: metadata IN the file, not in separate artifacts
- Navigable: used_by graph — reverse dependencies in every header
- Cumulative: rules accumulate across agent sessions (knowledge doesn't evaporate)
- Zero dependencies: plain text, no build step, no runtime, no infrastructure
- Vendor-neutral: works with any AI tool, any language, any editor
- Measurable: +20% F1 on SWE-bench (5 tasks, 5 models)
```

### Sfide tecniche (max 5000 caratteri)
```text
1. ACCURATE STATIC ANALYSIS FOR used_by EXTRACTION
The used_by field requires knowing which files import symbols from the current module. For Python, this means resolving import statements across the entire project, handling relative imports, re-exports, and dynamic imports. The current implementation uses AST-based analysis but edge cases (star imports, conditional imports, monkey-patching) require heuristics. We plan to use a hybrid approach: AST analysis for direct imports + heuristic matching for indirect dependencies.

2. KEEPING ANNOTATIONS IN SYNC
As code evolves, annotations can become stale. A renamed function might not be updated in exports; a deleted file might still appear in used_by. The codedna verify command must detect these inconsistencies efficiently without requiring a full project re-analysis on every change. We plan to use file-level hashing for change detection and incremental re-analysis.

3. VERIFICATION AGENTS — MANAGING HALLUCINATION RISK
Because agents write rules: annotations, they may contain incorrect information. A wrong annotation (e.g., "MUST filter by tenant_id" when no such filter exists) could propagate into every future agent's output. This is the cost of agent→agent communication — the channel can carry noise. The solution is verification agents that periodically cross-check annotations against actual code. Building reliable, efficient verification is a key technical challenge.

4. SCALING TO LARGE CODEBASES
Django has ~2,000 Python files. Enterprise codebases can have 50,000+. The CLI must handle annotation generation and verification at this scale in reasonable time (<60 seconds for verify, <5 minutes for full init). This requires efficient file scanning, parallel processing, and caching.

5. LANGUAGE EXTENSION BEYOND PYTHON
Each language has different module systems, import mechanisms, and docstring conventions. Python uses docstrings in triple quotes; JavaScript uses JSDoc comments; Rust uses /// doc comments. The CodeDNA format must adapt to each language's conventions while maintaining a consistent protocol structure. The v1.0 spec must define clear extension points.

6. BENCHMARK VALIDITY AND REPRODUCIBILITY
Ensuring scientifically valid results requires careful methodology: sufficient sample size, temperature control, statistical testing, and transparent reporting. We must also account for model versioning — results may change when LLM providers update their models. The benchmark must be both rigorous enough for academic publication and practical enough for community adoption.

7. THE NETWORK EFFECT BOOTSTRAPPING PROBLEM
CodeDNA's value increases with adoption (each annotated project benefits all agents that read it). But initial adoption requires value before the network effect kicks in. We need to solve this chicken-and-egg problem through CLI automation (codedna init generates useful annotations immediately) and by annotating popular open source projects ourselves.
```

### Ecosistema (max 2500 caratteri)
```text
CodeDNA sits at the intersection of three ecosystems:

1. AI CODING TOOLS
We will engage with the teams behind major AI coding assistants:
- Anthropic (Claude Code) — CodeDNA integrates via CLAUDE.md
- GitHub (Copilot) — integration via copilot-instructions.md
- Cursor, Windsurf, Cline — integration via .cursorrules
- Google (Gemini/Antigravity) — integration via .gemini/ configuration

CodeDNA is vendor-neutral by design. The one-line installer already supports 6 tools. The protocol works with ANY agent that can read source files.

2. OPEN SOURCE PROJECTS
We will target adoption in well-known open source projects:
- Django (already used in benchmarks — 51 files annotated)
- Flask, FastAPI (Python web frameworks)
- Community outreach via GitHub Issues, PRs, and annotating codebases as contributions

3. THE NETWORK EFFECT
CodeDNA has a natural network effect: when Agent A writes annotations in Project X, every Agent B that later reads Project X benefits — regardless of vendor. The more projects that adopt CodeDNA, the more useful it becomes for all agents. This makes it a true digital commons.

4. STANDARDS AND RESEARCH
- Publish benchmark methodology and results as a peer-reviewed paper
- Engage with the SE research community (ICSE, ASE, FSE)
- Propose CodeDNA as a discussion point in emerging AI coding standards
- Collaborate with NLnet's network of NGI projects

5. GREEN IT IMPACT
CodeDNA reduces token consumption by 33% in our benchmarks. At scale across millions of daily AI coding sessions, this translates to measurable energy savings in GPU inference. We will quantify this environmental benefit as part of outreach.

All code, data, benchmarks, and results are open source under MIT license.
```

---

## Intelligenza Artificiale Generativa

### Utilizzo dell'IA
```text
I have used generative AI in writing this proposal
```

### Dettagli
```text
Model: Google Gemini 2.5 (via Antigravity IDE)
Date: March 18, 2026
Usage: The AI assistant helped draft and refine the proposal text based on my project description, benchmark results, and technical specifications. All claims, data, and technical details originate from my own work and were verified by me. The AI assisted with English language formulation and structuring the responses to match NLnet's format requirements.
```