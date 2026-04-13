# NLnet NGI0 Commons Fund — Application for CodeDNA

> **Deadline: April 1st 2026, 12:00 CEST**

---

## Call Selection
**Thematic call**: `NGI Zero Commons Fund`

## Contact Information
- **Name**: `Fabrizio Corpora`
- **Email**: `fabrizio.corpora@gmail.com`
- **Phone**: `+39 328 186 7883 (WhatsApp)`
- **Organisation**: `Silicoreautomation`
- **Country**: `Italy`

---

## General Project Information

### Name of the proposal
```
CodeDNA — An inter-agent communication protocol for AI-navigable source code
```

### Website / wiki
```
https://codedna.silicoreautomation.space
```

### Source code repository
```
https://github.com/Larens94/codedna
```

### Research paper (Zenodo preprint)
```
https://doi.org/10.5281/zenodo.19158336
```

### Abstract (max 1200 chars)
```
CodeDNA is an inter-agent communication protocol implemented as in-source annotations. The writing agent encodes architectural context directly into source files; the reading agent decodes it. The file is the channel — no RAG, no vector DB, no external rules files.

The problem: AI coding agents waste context exploring irrelevant files, re-reading code, and missing cross-file constraints. Multi-agent teams duplicate work and leave integration gaps because agents lack explicit ownership contracts.

CodeDNA addresses this with 4 layers: a project manifest (.codedna), module headers (exports, used_by, rules, message), function-level rules, and semantic naming. used_by maps reverse dependencies; rules encodes domain constraints; message is a conversational channel for open hypotheses between agents across sessions.

Validated across two experiment types:

Single-agent navigation (SWE-bench, 5 Django tasks): Gemini 2.5 Flash +13pp F1 (p=0.040), DeepSeek Chat +9pp, Gemini 2.5 Pro +9pp.

Multi-agent team coordination (2 experiments, DeepSeek, 5-agent teams): CodeDNA team was 1.60x faster (1h59m vs 3h11m), produced a playable game vs a static scene. Without used_by contracts, the director occupied all module namespaces before delegating — creating a cascade of reverse-engineering overhead in every downstream agent. The message field reached 100% adoption when included in the prompt; a cross-file constraint propagation pattern (rules in owner, message in consumers) emerged without explicit instruction.

Fully open source (MIT), vendor-neutral, zero dependencies.
```

### Experience (max 2500 chars)
```
I am a software engineer with experience in full-stack development, automation, and AI-assisted tooling. I have been working on the intersection of AI agents and software engineering since 2023.

CodeDNA originated from practical frustration: while using AI coding assistants (Claude, Copilot, Gemini) on large codebases, I observed that agents consistently failed to navigate complex dependency graphs. They would read the wrong files, miss critical consumers, and waste tokens on irrelevant code. More importantly, each agent session started from scratch — no knowledge was preserved between sessions or across different AI tools.

I developed the CodeDNA protocol iteratively through real-world usage:
- v0.1-v0.5: experimented with various annotation formats (YAML frontmatter, inline comments, separate manifests)
- v0.6: consolidated to the current 3-field module header (exports, used_by, rules)
- v0.7: validated on Python, with CLI tooling, benchmark infrastructure, and integration templates for 6 AI coding tools
- v0.8: added the message: field (inter-agent chat layer), Git audit trailers, multi-language adapters (11 languages), and a Claude Code plugin

I built two complementary benchmark suites:

1. Single-agent navigation (SWE-bench): 5 real Django issues, 3 models (Gemini 2.5 Flash p=0.040 ✅, DeepSeek Chat p=0.11, Gemini 2.5 Pro p=0.11). Measures file localization F1 — did the agent open the right files?

2. Multi-agent team coordination: controlled A/B experiments where 5-agent teams (DeepSeek deepseek-chat) build complete software projects from scratch. Condition A uses CodeDNA; condition B uses standard Python conventions. Identical task, model, team structure, tool budget.

Results from 2 completed multi-agent experiments: CodeDNA team 1.60× faster on a game project; produced a playable game vs a static scene. The used_by field prevents director centralization — without it, the director builds all scaffolding before delegating, creating a cascade of reverse-engineering overhead that peaks at 3.9× slower for the nearest downstream agent. The message field reached 100% adoption in experiment 2, with a correct dual-channel usage pattern emerging without explicit instruction.

I have also built a one-line installer for Claude Code, Cursor, Copilot, Windsurf, and other tools, plus a documentation website, a pre-commit hook, and CI integration. The project is open source on GitHub and has been developed entirely in public.
```

---

## Requested Support

### Requested Amount
```
50000
```

### Budget usage (max 2500 chars)
```
Rate: €60/hour. Total: €50,000 (~833 hours over 12 months).

Milestone 1 — Protocol Specification & CLI (€14,000, ~233h)
- Finalize and publish CodeDNA v1.0 specification document
- Python AST-based automatic extraction of exports: and used_by: fields (currently written manually or by LLM)
- codedna verify: detect stale annotations, renamed symbols, deleted files still referenced in used_by
- codedna update: re-sync annotations incrementally after code changes, using file-level hashing
- Package and publish on PyPI

Milestone 2 — Benchmark Expansion (€10,000, ~167h)
- Expand from 5 to 20+ SWE-bench tasks across multiple open source projects (not only Django)
- Run benchmark with 5+ LLMs and publish full results with confidence intervals
- Publish benchmark dataset and runner on Zenodo for reproducibility
- Extend public results dashboard with per-task and per-model breakdowns

Milestone 3 — Editor & Workflow Integrations (€10,000, ~167h)
- VS Code extension: visualize the used_by graph, highlight files with missing or stale annotations
- Pre-commit hook: run codedna verify before each commit, blocking on stale annotations
- GitHub Action: CI/CD annotation verification on pull requests
- Tested setup guides for Claude Code, Cursor, Copilot, Windsurf

Milestone 4 — Language Extension (€9,000, ~150h)
- Adapt CodeDNA format to JavaScript/TypeScript (JSDoc-compatible)
- Adapter for Go (godoc comments) and Rust (/// doc comments)
- Formal extension points in v1.0 spec for community-driven language support
- Rewrite documentation site with full spec, language guides, and quickstart examples

Milestone 5 — Research Paper & Dissemination (€7,000, ~117h)
- Finalize paper with complete benchmark results and publish preprint on arXiv
- Submit to ICSE NIER track (New Ideas and Emerging Results) or a relevant workshop (LLM4Code, NLP4SE)
- Contribute CodeDNA annotations to 3+ popular open source projects (Flask, FastAPI, and one non-Python project)

No other funding sources currently. This would be the first external funding for CodeDNA.
```

### Comparison with existing efforts (max 4000 chars)
```
Several approaches exist for helping AI agents work with codebases. CodeDNA differs from all of them in one fundamental way: it is an inter-agent communication protocol, not a human-to-agent instruction format.

1. REPOSITORY-LEVEL CONTEXT FILES (CLAUDE.md, .cursor/rules/, copilot-instructions.md)
These are human→agent communication: a developer writes instructions for the AI. They describe the project at a high level but don't provide file-level navigation. CodeDNA is agent→agent communication: when Agent A discovers a constraint, it writes a rules: annotation that Agent B (different model, different session) reads and acts on. The file is the channel. This distinction matters because human-written rules don't scale as codebases and agent sessions multiply.

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
- Coordination forcing: used_by prevents director centralization in multi-agent teams — agents cannot occupy a module they declared as owned by another agent
- Cumulative: rules and message accumulate across agent sessions — knowledge written by one agent is available to all future agents on any tool
- Zero dependencies: plain text, no build step, no runtime, no infrastructure
- Vendor-neutral: works with any AI tool and editor; 11 languages supported
- Measurable (two dimensions):
  - Single-agent navigation: +13pp F1 on SWE-bench (Gemini 2.5 Flash, p=0.040); +9pp on DeepSeek Chat and Gemini 2.5 Pro
  - Multi-agent coordination: 1.60× faster team execution; playable vs static game output; message: adoption 0% → 100% when included in prompt
```

### Technical challenges (max 5000 chars)
```
1. ACCURATE STATIC ANALYSIS FOR used_by EXTRACTION
The used_by field requires knowing which files import symbols from the current module. For Python, this means resolving import statements across the entire project, handling relative imports, re-exports, and dynamic imports. Currently, annotations are written manually or generated by an LLM agent. We plan to build AST-based automatic extraction, using a hybrid approach: AST analysis for direct imports + heuristic matching for indirect dependencies. Edge cases (star imports, conditional imports, monkey-patching) will require carefully designed heuristics.

2. KEEPING ANNOTATIONS IN SYNC
As code evolves, annotations can become stale. A renamed function might not be updated in exports; a deleted file might still appear in used_by. The codedna verify command must detect these inconsistencies efficiently without requiring a full project re-analysis on every change. We plan to use file-level hashing for change detection and incremental re-analysis.

3. VERIFICATION AGENTS — MANAGING HALLUCINATION RISK
Because agents write rules: annotations, they may contain incorrect information. A wrong annotation (e.g., "MUST filter by tenant_id" when no such filter exists) could propagate into every future agent's output. This is the cost of agent→agent communication — the channel can carry noise.

The mitigation strategy is a layered verification pipeline:
- IDE integration: a VS Code extension highlights annotations that are inconsistent with the current code (e.g., an exports: field referencing a renamed function)
- Pre-commit hook: codedna verify runs before every commit and blocks on stale or suspicious annotations
- CI/CD: a GitHub Action re-runs verification on every pull request, so annotations are checked before code reaches the main branch
- Periodic verification agent: an LLM agent periodically cross-checks rules: annotations against the actual code logic, flagging annotations that contradict the implementation

This pipeline ensures that annotation quality degrades visibly rather than silently, and that human reviewers are alerted before incorrect annotations propagate.

4. SCALING TO LARGE CODEBASES
Django has ~2,000 Python files. Enterprise codebases can have 50,000+. The CLI must handle annotation generation and verification at this scale in reasonable time (<60 seconds for verify, <5 minutes for full init). This requires efficient file scanning, parallel processing, and caching.

5. LANGUAGE EXTENSION BEYOND PYTHON
Each language has different module systems, import mechanisms, and docstring conventions. Python uses docstrings in triple quotes; JavaScript uses JSDoc comments; Rust uses /// doc comments. The CodeDNA format must adapt to each language's conventions while maintaining a consistent protocol structure. The v1.0 spec must define clear extension points.

6. BENCHMARK VALIDITY AND REPRODUCIBILITY
Ensuring scientifically valid results requires careful methodology: sufficient sample size, temperature control, statistical testing, and transparent reporting. We must also account for model versioning — results may change when LLM providers update their models. The benchmark must be both rigorous enough for academic publication and practical enough for community adoption.

7. THE NETWORK EFFECT BOOTSTRAPPING PROBLEM
CodeDNA's value increases with adoption (each annotated project benefits all agents that read it). But initial adoption requires value before the network effect kicks in. We need to solve this chicken-and-egg problem through CLI automation (codedna init generates useful annotations immediately) and by annotating popular open source projects ourselves.
```

### Ecosystem (max 2500 chars)
```
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
- Publish preprint on arXiv and submit to ICSE NIER track or a relevant workshop (LLM4Code, NLP4SE)
- Engage with the SE research community as benchmark results mature
- Propose CodeDNA as a discussion point in emerging AI coding standards
- Collaborate with NLnet's network of NGI projects

5. ENVIRONMENTAL IMPACT
AI coding agents consume significant GPU resources. CodeDNA reduces unnecessary file reads — each avoided read_file call saves tokens and inference compute. We will measure and report token consumption reduction as part of the benchmark results.

All code, data, benchmarks, and results are open source under MIT license.
```

---

## Generative AI

### AI usage
```
I have used generative AI in writing this proposal
```

### Details
```
Models: Claude Code (Anthropic) and Google Gemini 2.5
Date: March 19, 2026
Usage: AI assistants helped draft and refine the proposal text based on my project description, benchmark results, and technical specifications. All claims, data, and technical details originate from my own work and were verified by me. The AI assisted with English language formulation and structuring the responses to match NLnet's format requirements.
```
