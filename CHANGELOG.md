# Changelog

All notable changes to CodeDNA will be documented in this file.

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
