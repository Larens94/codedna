# Changelog

All notable changes to CodeDNA will be documented in this file.

## [Unreleased]

### Fixed

- **`codedna init` no longer annotates AI-agent worktrees and IDE state.** Three independent "skip lists" (one inline in `collect_files`, one in `_MANIFEST_SKIP`, one in `wiki.SKIP_DIRS`) had drifted: only `wiki` excluded `.claude/` and `worktrees/`. A real-world session burned ~25 minutes and ~$0.30 of LLM calls annotating files inside `.claude/worktrees/<wt-id>/` (ephemeral git worktrees created by the Claude Code agent itself), then crashed when the new model returned non-strict JSON for 46/47 batches. Fix introduces a canonical `_DEFAULT_SKIP_DIRS` frozenset (now includes `.claude`, `worktrees`, `_repo_cache`); `collect_files` uses it directly, `_MANIFEST_SKIP` is `_DEFAULT_SKIP_DIRS | {"coverage", "htmlcov"}`, and `wiki.SKIP_DIRS` is `_DEFAULT_SKIP_DIRS | {"runs", "docs", "paper", "thesis", "dev_notes", "examples", "projects_swebench", "projects"}`. A drift-guard test (`test_collect_files_skip_set_matches_wiki_skip_dirs`) prevents the divergence from sneaking back. Total: 4 new regression tests.

### Changed

- **Recommend `pipx install` over `pip install` everywhere in docs (#8).** Direct `pip install codedna[litellm]` into a polluted global Python environment was causing transitive-dependency conflicts (e.g. with `rembg` requiring `jsonschema>=4.25.1`, while litellm pinned an older version). Reported by @DATEx2. The fix is documentation-only: every `pip install` line for the codedna CLI now reads `pipx install`. pipx auto-isolates each tool in its own venv, so codedna's transitive deps cannot conflict with anything else on the user's machine. `uv tool install` works identically. Files updated: README.md, README-it.md, QUICKSTART.md, SPEC.md, integrations/CLAUDE.md (with explicit `[litellm]`/`[anthropic]` extras blocks), integrations/AGENTS.md, integrations/copilot-instructions.md, codedna-plugin/commands/init.md, labs/benchmark/README.md, docs/install.html (×2), docs/install/reports/php-laravel/codedna-install-report.html. The `[litellm]` extra itself is preserved — Ollama / OpenAI / Gemini / DeepSeek / Mistral / Cohere routing all flows through litellm.

### Fixed

- **`codedna manifest` two related bugs (#11, yuzi-co).**
  - **Bug A:** `--exclude '**/<dir>/**'` did not match a directory at the project root. `fnmatch` (and `pathlib.match` pre-3.13) does not treat `**` as a multi-segment glob — it collapses to a single `*`, which requires at least one parent segment. Pre-fix `**/infrastructure/**` therefore never excluded root-level `infrastructure/`. New helper `_expand_exclude()` conservatively also tries the form without the leading `**/`. Patterns are kept as-is — purely additive, no other globs change semantics.
  - **Bug B:** Go-only directories silently fell into `(root)` instead of becoming their own package. `_detect_packages` only recognised `__init__.py` as a package marker. New helper `_is_package_marker()` also accepts `.go` files (non-`*_test.go`) — Go has no marker file, the directory IS the package. Other languages currently fall through to the existing root-segment fallback; extend `_is_package_marker` when adding language-specific markers.
- **`codedna init` no longer destroys multi-line module docstrings (#10).** Reported by @yuzi-co — on a real 745-file repo `init` had silently erased migration documentation, architectural notes, test prerequisites and pipeline diagrams across hundreds of files. Pre-fix `build_module_docstring` only kept the first (summary) line of the existing docstring via `_purpose()`; everything else was dropped when `inject_module_docstring` replaced the original triple-quoted block. New helper `_extract_docstring_body()` now extracts the prose body and splices it between the summary line and the CodeDNA fields. Pre-existing CodeDNA fields in the body are stripped so `init --force` over an annotated file does not duplicate them.
- **`codedna wiki bootstrap` no longer OOMs on large non-source files (#9).** Pre-fix, `_extract_fields` did `path.read_text()` which loaded each file fully into memory before checking for a CodeDNA header. On repos containing GGUF model weights, datasets, or any multi-GB binary, this raised `MemoryError` (reported by @DATEx2 — confirmed via traceback). The function now reads only the first 16 KB of each file, runs a cheap `"exports:" in head` pre-check to skip files without an L1 annotation, and falls back to a regex extraction of the leading triple-quoted string if the truncated head breaks AST parsing. Wiki content is unchanged (still L1-only — used_by/related/rules/agent/wiki/message). Smoke-tested with a 50 MB binary in the repo root: peak memory ~180 MB, vault generates correctly.
- **Antigravity integration: directory renamed `.agents/` → `.agent/`** (singular per [official docs](https://antigravity.google/docs/rules-workflows)). The previous path was never read by the IDE, so `bash install.sh agents` was effectively a no-op for end users. Affects [integrations/install.sh](integrations/install.sh), [codedna_tool/cli.py](codedna_tool/cli.py) `_TOOL_FILES["agents"]`, and the source workflow file at [integrations/.agent/workflows/codedna.md](integrations/.agent/workflows/codedna.md).

### Added

- **Antigravity: `agents` install now writes `AGENTS.md` + `.agent/workflows/codedna.md`** (was workflow-only). `AGENTS.md` is read by Antigravity v1.20.3+ as an always-on rules file (cross-vendor standard, also read by OpenCode/Cursor/Claude Code), giving the agent the CodeDNA protocol every session — not only when the user types `/codedna`.
- **`_detect_ai_tools()` now detects Antigravity** — checks for `.agent/`, `GEMINI.md`, or `.gemini/` in the repo. Previously `codedna install` (no flags) never auto-installed Antigravity files.
- **`--tools agents` documented in `codedna install --help`** — was previously accepted but undocumented.

### Tests

- 204 total tests passing (was 185); the `LLM` routing layer is now under CI for the first time — 11 new tests in `TestLLM` (offline, monkey-patch `_litellm`/`_anthropic`) covering provider detection for all 6 prefixes, litellm routing with kwargs verification, anthropic fallback with timeout, ImportError when neither backend is installed, and api_key env-var injection (positive + negative). 2 new regression tests for #11 in new `TestManifest` class (`test_exclude_pattern_matches_root_level_dir`, `test_go_only_directory_becomes_its_own_package`); 4 new for #10 in `TestBuildDocstring` + `TestInit` (multi-line body preserved, CodeDNA fields not duplicated on `--force`, single-line behaviour unchanged, E2E reproduces the reporter's exact case); 2 new for #9 in `TestBuildVault` (5 MB binary in repo doesn't OOM, Python file with body > 16 KB still has its header extracted via regex fallback).

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
