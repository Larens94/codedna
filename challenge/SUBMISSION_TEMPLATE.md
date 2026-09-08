## CodeDNA Challenge submission

> **Language:** English · [Italiano](SUBMISSION_TEMPLATE.it.md)  
> Use this template for challenge PRs.  
> Title: `challenge: <handle> — CodeDNA Challenge submission`

### Entrant

- Handle:
- Linked entry issue:
- Challenge mode:
  - [ ] Parity (same L1/L2 on Control and CodeDNA)
  - [ ] Declared `codedna-only` vs higher stack

### Stack under test

| Level | Tools / files | Present in Control? | Present in CodeDNA? |
|---|---|---|---|
| L0 CodeDNA | in-source headers | no | yes |
| L1 | | | |
| L2 | | | |

### Project

- Language(s):
- Size (approx. source files):
- Public URL (optional) / “private — metrics only”:

### Metrics JSON (required)

- [ ] `challenge/<handle>/metrics.json` present
- [ ] Copied from [`metrics.example.json`](./metrics.example.json) / matches [`metrics.schema.json`](./metrics.schema.json)
- [ ] `schema_version` = `"1.0"`
- [ ] ≥10 tasks with `difficulty` mix (easy ≥3, medium ≥3, hard ≥2)
- [ ] Each task has both `control` and `codedna` results
- [ ] `summary.favors` set (`codedna` | `control` | `tie` | `inconclusive`)
- [ ] Results may favor **or** disfavor CodeDNA (honesty OK)

### Optional

- [ ] `README.md` / `notes.md` narrative
- [ ] Redacted `logs/`

### Bugs found in CodeDNA

- Links (or “none”) — also list them in `metrics.json` → `bugs_reported`:

### Checklist

- [ ] No secrets / proprietary source in this PR
- [ ] Redacted logs only
- [ ] Mode + stack parity declared in JSON (`mode`, `stack`)
