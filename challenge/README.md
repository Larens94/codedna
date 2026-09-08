# CodeDNA Challenge submissions

**Enrollment = open a PR** with:

```text
challenge/<github-handle>/
  metrics.json    # REQUIRED (stack + install + setup.layout + same-task control/codedna results)
  README.md       # optional
  notes.md        # optional
```

No official signup. Public ranking (updated as valid PRs arrive): [`docs/challenge.html`](../docs/challenge.html) · data [`docs/challenge-board.json`](../docs/challenge-board.json)

**Copy for your agent**

- Italiano: [`docs/challenge-agent-prompt.it.md`](../docs/challenge-agent-prompt.it.md)
- English: [`docs/challenge-agent-prompt.md`](../docs/challenge-agent-prompt.md)
- Judge (optional, after both sessions): [`docs/challenge-judge-prompt.it.md`](../docs/challenge-judge-prompt.it.md) · [EN](../docs/challenge-judge-prompt.md)
- Task lists: [`TASKS_TEMPLATE.it.md`](./TASKS_TEMPLATE.it.md) · [`TASKS_TEMPLATE.md`](./TASKS_TEMPLATE.md)
- Pointer: [`AGENT_PROMPT.md`](./AGENT_PROMPT.md)

Methodology (same for everyone): same ≥10 tasks with vs without CodeDNA via `two_branches` / `two_checkouts` / `two_projects`.  
File-localization fields (`files_expected`, F1, …) are **optional** — use when known; otherwise a judge agent can still compare sessions.

**Metrics format**

- Example: [`metrics.example.json`](./metrics.example.json)
- Schema: [`metrics.schema.json`](./metrics.schema.json)

Required: `languages`, `frameworks`, `approx_source_files` (≥25), `size_band`, `install`, `setup.layout`, `bugs_reported`.

**Rules**

- English: [`docs/challenge.md`](../docs/challenge.md)
- Italiano: [`docs/challenge.it.md`](../docs/challenge.it.md)

**PR checklist**

- English: [`SUBMISSION_TEMPLATE.md`](./SUBMISSION_TEMPLATE.md)
- Italiano: [`SUBMISSION_TEMPLATE.it.md`](./SUBMISSION_TEMPLATE.it.md)
