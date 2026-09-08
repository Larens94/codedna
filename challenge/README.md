# CodeDNA Challenge submissions

**Enrollment = open a PR** with:

```text
challenge/<github-handle>/
  metrics.json    # REQUIRED (stack + install + same-task control/codedna results)
  README.md       # optional
  notes.md        # optional
```

No official signup. Public board / ranking (updated as valid PRs arrive): [`docs/challenge.html`](../docs/challenge.html) · data [`docs/challenge-board.json`](../docs/challenge-board.json)

**Metrics format**

- Example: [`metrics.example.json`](./metrics.example.json)
- Schema: [`metrics.schema.json`](./metrics.schema.json)

Required: `languages`, `frameworks`, `approx_source_files` (≥25), `size_band` (`S`/`M`/`L`/`XL`), `install` (agent + steps), `bugs_reported` (array; empty OK).

Real working projects only — toy sites / hello-world demos are rejected. Same tasks must be run with and without CodeDNA. Meet presentation may be required.

**Rules**

- English: [`docs/challenge.md`](../docs/challenge.md)
- Italiano: [`docs/challenge.it.md`](../docs/challenge.it.md)

**PR checklist**

- English: [`SUBMISSION_TEMPLATE.md`](./SUBMISSION_TEMPLATE.md)
- Italiano: [`SUBMISSION_TEMPLATE.it.md`](./SUBMISSION_TEMPLATE.it.md)
