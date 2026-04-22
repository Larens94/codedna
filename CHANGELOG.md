# Changelog

All notable changes to CodeDNA will be documented in this file.

## [0.9.1] — 2026-04-22

### Added

- **DeepSeek benchmark expanded to 10 tasks** — 6 new Django tasks (13121, 15629, 16263, 11400, 11883, 11808) independently replicated by [@fabioscialanga](https://github.com/fabioscialanga), integrated in [a9ddde6](https://github.com/Larens94/codedna/commit/a9ddde6) with co-authorship. Combined result: **+17.1pp F1 mean** (was +11pp on 6 tasks), Wilcoxon exact **p=0.0009765625**, wins/losses/ties = **10/0/0**. Two tasks (11808, 13121) show CodeDNA std=0.00 across 3 runs vs 0.20–0.25 for control — stability, not just mean.

### Fixed

- **`codedna refresh` no longer degrades real annotations to `"none"`** — when tree-sitter/AST returns no exports or no importers (e.g. PHP config files, TSX with unresolved `@/` aliases), the existing LLM-annotated value is preserved instead of being overwritten. Regression bug reported against a Laravel+Inertia project where 107 files had their `exports:`/`used_by:` zeroed out. Fix applies to both Python (AST) and non-Python (tree-sitter) paths.
- **`tools/validate_manifests.py` now recognises optional fields** — parser was iterating over `REQUIRED_FIELDS` only, silently folding `wiki:`/`related:`/`message:` values into the previous field. The `wiki:` path-existence check was therefore never executed in practice.

### Tests

- 173 total tests passing (was 170); 17 new regression tests in `TestRefreshPreserveMatrix` and `TestRefreshPreservesLLMAnnotations` — exhaustive preserve-vs-update matrix across Python+PHP paths, all combinations of old/new exports/used_by values.

## [0.9.0] — 2026-04-21

### Added

- **`wiki:` optional docstring field (v0.9 experimental)** — opt-in pointer from a source file's docstring to a curated markdown under `docs/wiki/`. When present, an agent editing the file must read the pointed markdown first; absence means the docstring is sufficient. *Sparsity is the signal.* Validated by `tools/validate_manifests.py` (path must exist). Parser/rebuilder in `codedna_tool/cli.py` preserve the field across `codedna refresh`.
- **`codedna wiki bootstrap <path>`** — generate an [Obsidian](https://obsidian.md)-ready per-file vault under `docs/wiki/` (nested layout mirroring the source tree) with `[[wikilinks]]` derived from `used_by:` and `related:` graphs. Preserves AGENT NOTES sections across regeneration.
- **`codedna wiki sync <path>`** — regenerate a single narrative project wiki at `docs/codedna-wiki.md` following the Karpathy LLM-wiki 7-section template (identity / L0 relationship / semantic topology / workflows / testing / hotspots / refresh protocol). Designed to be wired into a post-commit hook for hard enforcement (avoiding the "agent forgets to update markdown" failure mode).
- **`AGENTS.md`** — Codex/OpenCode/Aider-compatible mirror of `CLAUDE.md`. Ships full v0.9 protocol including `related:`, `wiki:`, and the inline `# Rules:` / `# message:` annotation patterns. Keep in sync with `CLAUDE.md`.

### Credits

- `codedna-wiki.md` 7-section narrative template and `AGENTS.md` scaffold originally contributed by [@workingfm](https://github.com/workingfm) in [PR #2](https://github.com/Larens94/codedna/pull/2), adapted here to use post-commit hooks instead of the skill/sub-agent scaffolding (agents empirically forget markdown instructions).
- Pattern inspired by Andrej Karpathy's [LLM-wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — though we interpret *"compile once, maintain forever"* as *"compile deliberately, not everything"*.

### Tests

- 170 total tests passing (was 139); 25 new tests in `tests/test_wiki.py` cover slug generation, wikilink escaping, vault generation, AGENT NOTES preservation, project wiki rendering, and the `wiki:` field opt-in flow.

## [0.8.2] — 2026-03-30

### Experimental Results

- **Multi-agent team experiment 1 (RPG game):** CodeDNA team completed task in 1h 59m vs 3h 11m for standard Python team (**1.60× faster**). CodeDNA produced a playable game (WASD, ECS, 5 entities); standard produced a visible but static scene. Core finding: without `used_by:` contracts, the director occupies all module namespaces before delegating, creating a cascade of reverse-engineering overhead in every downstream specialist. The director centralization cascade peaks at the agent nearest to the director's decisions.
- **Multi-agent team experiment 2 (AgentHub SaaS):** `message:` field first non-zero result — **100% adoption** (44/44 annotated files) when included in prompt. Three usage patterns observed: (1) module-level handoff notes, (2) per-function gap annotations, (3) cross-file constraint propagation via dual-channel (`rules:` in owner, `message:` in consumers). Pattern 3 emerged without explicit instruction.
- **Director centralization finding:** `used_by:` is a delegation forcing function. Without it, director spent 2× longer in round 1 and occupied all module namespaces. Per-agent B/A ratios: GameDirector R1 2.0×, GameEngineer 3.9×, GraphicsSpecialist 1.4×, GameplayDesigner 2.6×, DataArchitect 0.75× (most independent domain). Cascade diminishes toward independent modules.
- **LOC vs completeness:** condition B produced 38% more lines (14,096 vs 10,194) and 10% fewer files. More code, less functionality — the integration layer was never written.

### Known Issues / Fixes Queued

- **Date hallucination:** all agents wrote `2024-01-15` in `agent:` entries regardless of actual date. Fix: inject `{current_date}` into prompt template.
- **`message:` lifecycle not yet activated:** no agent responded with `@prev: promoted to rules:` or `@prev: dismissed`. Director R2 needs explicit instruction to process open messages. Fix: add lifecycle instruction to Director round-2 prompt.
- **Duplicate `message:` content:** AgentIntegrator copy-pasted same module-level message to 6 related files instead of writing per-file observations. Acceptable for now; per-function level (Level 2) showed better specificity.

---

## [0.8.1] — 2026-03-27

### Added
- **Multi-language adapters** — 10 new language adapters in `codedna_tool/languages/`: TypeScript/JavaScript, Go, PHP (Laravel-aware), Rust, Java, Kotlin, C#, Swift, Ruby. Python remains the reference implementation with full L1+L2 AST extraction; all other languages get L1-only annotation via regex (no external toolchain required).
- **`--extensions` CLI flag** — `codedna init`, `codedna update`, `codedna check` now accept `--extensions ts go php` etc. to annotate non-Python files.
- **`tools/pre-commit`** — rewritten from v0.3 `CODEDNA:0.3` block format to v0.8. Validates staged source files using `validate_manifests.py`; blocks commit on annotation errors. Install with `bash tools/install-hooks.sh`.
- **Examples** — `examples/php-laravel/` (OrderController, Order model, routes) and `examples/ruby-sinatra/` (order.rb, Sinatra app) added and annotated.

### Fixed
- `codedna_tool/cli.py` `_resolve_dep()` no longer filters by `top_pkg` — cross-package `used_by` graph now works correctly across package boundaries.
- `tools/validate_manifests.py` filename mismatch false positive — now accepts repo-relative paths in the docstring first line (e.g. `analytics/revenue.py — ...`).

---

## [0.8.0] — 2026-03-20

### Added
- **`message:` — Agent Chat Layer**: new optional sub-field under `agent:` for open hypotheses and inter-agent observations not yet certain enough to become `rules:`. Works at Level 1 (module docstring) and Level 2 (function docstring). Lifecycle: promote to `rules:` or dismiss with `@prev:` reply. Append-only — never delete.
- **Git Trailers for AI audit**: every AI session commit must include `AI-Agent:`, `AI-Provider:`, `AI-Session:`, `AI-Visited:`, `AI-Message:` trailers. Git is the authoritative audit log; `.codedna` and file `agent:` fields are lightweight navigation caches.
- **`session_id`** field added to `agent:` entries and `.codedna` `agent_sessions:` — links git trailers, `.codedna` entries, and file-level annotations to the same session.
- **`visited:` field** in `.codedna` `agent_sessions:` — lists files read (not just changed) during a session.
- **`provider:` field** in `agent:` and `.codedna` `agent_sessions:`.
- **Session trace logging** (`session_traces/<session_id>.json`) — ordered tool call sequence with relative timestamps per benchmark run.
- `tools/traces_to_training.py` — converts benchmark results to SFT/DPO/PRM JSONL training datasets. Produces 3 formats: SFT (F1 ≥ 0.6), DPO (codedna vs control + cross-model pairs), PRM (per-step reward).
- `tools/agent_history.py` — reads AI git trailers and renders a session timeline. Supports filtering by model, file, or message presence.
- Claude Code plugin (`codedna-plugin/`) — adds `/codedna:init` and `/codedna:check` slash commands plus a PostToolUse hook for annotation enforcement. `/codedna:manifest` and `/codedna:impact` are planned.
- Multi-language annotation adapters (`codedna_tool/languages/`) — planned; TypeScript and Go adapters included as preview. Full 11-language coverage delivered in v0.8.1.
- SVG diagrams in `docs/diagrams/`: architecture (4 levels), agent workflow, three-tier audit, `message:` lifecycle state machine.
- Fix-quality benchmark: Claude Code manual session on `django__django-13495` — CodeDNA achieves 7/7 files vs 6/7 control, 0 failed edits vs 5.
- Protocol renamed from "CodeDNA Annotation Standard" to "CodeDNA: An In-Source Communication Protocol for AI Coding Agents".
- Zenodo dataset published (DOI: 10.5281/zenodo.19158336).

### Changed
- `agent:` format extended: `model | provider | YYYY-MM-DD | session_id | description`
- `.codedna` `agent_sessions:` format extended with `provider`, `session_id`, `visited` fields
- Benchmark results updated: final multi-model results with Wilcoxon signed-rank tests. Gemini 2.5 Flash: +13pp F1, p=0.040 ✅. DeepSeek Chat: +9pp, p=0.11 *(later expanded to 10 tasks in 0.9.1: +17pp, p=0.001)*. Gemini 2.5 Pro: +9pp, p=0.11.
- B1/B2 custom benchmarks removed from all papers — only SWE-bench results remain.
- All integration files (`.cursorrules`, `.windsurfrules`, `.clinerules`, `copilot-instructions.md`, `.agents/workflows/codedna.md`) aligned to v0.8.

---

## [0.7.0] — 2026-03-19

### Added
- **Formal session management**: `agent:` field becomes append-only rolling log (last 5 entries). Full history in git.
- **`.codedna` project manifest**: YAML file at repo root with `packages:`, `agent_sessions:`, `cross_cutting_patterns:` fields. Read first at session start.
- `tools/agent_history.py` initial version — reads and displays agent session data.
- `tools/traces_to_training.py` initial version — SFT/DPO/PRM converter.
- New integration file for Antigravity/Agents (`integrations/.agents/workflows/codedna.md`).

### Changed
- **Protocol simplified**: removed `tables:`, `cascade:`, `tested_by:`, `raises:`, `deps:`, `Modifies:` fields. Only `exports:`, `used_by:`, `rules:`, `agent:` remain.
- `rules:` promoted as the primary architectural constraint channel — replaces all removed fields.
- `codedna_tool/cli.py` rewritten: AST-based extraction + LLM only for semantic `rules:` content. Max 2 LLM calls per file.
- All docs and integration files aligned to new title "In-Source Communication Protocol".

---

## [0.6.0] — 2026-03-18

### Changed
- **Removed `deps:` and `Depends:` fields** — dependency information now encoded in `used_by:` (reverse deps) and import statements (forward deps). No duplication.
- **Removed Level 2a Google-style docstrings** and Level 2b inline call-site comments — simplified to `Rules:` docstrings on critical functions only.
- `auto_annotate.py` updated to v0.6 format: no longer extracts `deps:`, generates only `exports:` and `used_by:`.

---

## [0.5.1] — 2026-03-17

### Added
- **Multi-Model SWE-bench Benchmark**: 5 real Django issues tested across Gemini 2.5 Flash (+20pp F1), GPT-5.3 Codex (+12pp), Gemini 2.5 Pro (+8pp), GPT-4o (+2pp), DeepSeek-V3 (−1pp). CodeDNA improves 4/5 models.
- `benchmark_agent/swebench/run_agent_multi.py` — multi-provider benchmark runner (Gemini, Anthropic, OpenAI Chat, OpenAI Codex/Responses API, DeepSeek)
- `benchmark_agent/swebench/analyze_multi.py` — cross-model comparison analysis
- `benchmark_agent/runs/` — structured results directory per model
- Multi-model benchmark section in paper, README, and docs website
- Chart.js grouped bar chart on docs website showing F1 by model
- CHANGELOG.md (this file)

### Fixed
- `install.sh` version updated from v0.3 to v0.5
- README: fixed broken links to non-existent result files
- README: updated repository structure to reflect current layout
- Paper: replaced "Single model" limitation with multi-model evaluation note

### Changed
- Paper abstract updated to mention multi-model evaluation across 5 LLMs
- Paper contributions list now includes multi-model benchmark (contribution #4)
- Paper conclusion updated with multi-model results
- Docs roadmap: "White Paper" and "Multi-Model Benchmark" moved from Next → Done
- Docs roadmap: added "Full SWE-bench Evaluation — 50+ tasks" as Next

## [0.5.0] — 2026-03-15

### Added
- CodeDNA Annotation Standard v0.5 (LLM-Optimised Format)
- Python-native module docstring (Level 1) replaces custom comment blocks
- Google-style function docstring (Level 2a) for sliding-window safety
- Inline call-site comments (Level 2b) as last line of defence
- Enterprise benchmark (105 files, 3 bugs, 48 distractors)
- Integration files for Claude Code, Cursor, GitHub Copilot, Windsurf, Cline, Antigravity
- `install.sh` one-line installer for all AI tool integrations
- Scientific paper (arXiv preprint format)
- Docs website with 3D DNA helix, Chart.js benchmarks, i18n (EN/IT)
