# Changelog

All notable changes to CodeDNA will be documented in this file.

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
- Benchmark results updated: final multi-model results with Wilcoxon signed-rank tests. Gemini 2.5 Flash: +13pp F1, p=0.040 ✅. DeepSeek Chat: +9pp, p=0.11. Gemini 2.5 Pro: +9pp, p=0.11.
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
