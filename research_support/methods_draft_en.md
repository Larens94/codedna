# Methods (Draft)

## Study design

We evaluate CodeDNA as an in-source context protocol for code navigation and fix completeness.
The core comparison is:
- Control: original repositories without CodeDNA annotations
- CodeDNA: same repositories with CodeDNA annotations

All other factors are held constant: task set, prompts, tools, model family, run budget, and temperature.

## Benchmark

- Dataset: SWE-bench Verified
- Initial scope: Django subset (50 tasks, multi-file-first)
- Expansion target: 12 repositories, up to 500 tasks

Each task includes:
- base commit checkout
- issue/problem statement
- ground-truth changed files

## Procedure

1. Prepare control repositories at the benchmark base commits.
2. Generate CodeDNA variants from control repositories.
3. Run both conditions with identical agent/tool configuration.
4. Repeat runs per task (default 3; target 5+ for stronger power).
5. Store raw traces and per-run JSON outputs.

## Primary metric

- File Localization F1 (files read/proposed vs ground-truth patch files)

## Secondary metrics

- Precision and recall per task
- Navigation efficiency
- Redundant reads
- Token usage per correctly localized file
- First-hit rate on relevant files

## Statistical analysis

- Paired analysis by task and model
- Wilcoxon signed-rank test (one-tailed hypothesis: CodeDNA > Control)
- Effect size and confidence intervals reported when possible

## Controls for validity

- Same prompt and tool set across conditions
- Same randomization settings (temperature and run count)
- No task-specific answer hints in annotations
- Audit of annotation integrity before final analysis

## Limitations (planned to report explicitly)

- Small-N settings in pilot phases
- Model-specific variance on some tasks
- Potential OS/path differences in tooling and parsers
- Sequential hardware effects for long multi-agent runs

## Reproducibility package

For each experiment release:
- scripts used to generate/annotate/run
- task manifest and run config
- raw JSON run outputs
- analysis scripts and summary tables
- environment notes (OS, Python, dependency versions)

