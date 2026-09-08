## CodeDNA Challenge submission

> **Language:** English · [Italiano](SUBMISSION_TEMPLATE.it.md)  
> Use this template for challenge PRs.  
> Title: `challenge: <handle> — CodeDNA Challenge submission`

### Entrant

- Handle:
- Challenge mode:
  - [ ] Parity (same L1/L2 on Control and CodeDNA)
  - [ ] Declared `codedna-only` vs higher stack

### Tech stack (required)

- Language(s):
- Framework(s) (required — not language alone):
- Agent / model:
- Approx. source files (≥ **25**):
- Size band (`S`/`M`/`L`/`XL`):
- Tech stack notes (DB, monorepo, infra — optional):
- Public URL (optional) / “private — metrics only”:
- [ ] This is a **real working project** (not a toy site / hello-world / throwaway demo)

### CodeDNA install (required)

- Agent used with CodeDNA:
- Exact install / init steps (paste commands):
- `codedna install --tools` value (if any):
- Did install + annotation work? yes / no — notes:

### Control vs CodeDNA setup (required)

- [ ] `two_branches` (e.g. `challenge/control` + `challenge/codedna`)
- [ ] `two_checkouts` (two folders)
- [ ] `two_projects` (twin projects)
- Control / CodeDNA refs:
- [ ] Agent prompt used: [`docs/challenge-agent-prompt.md`](../docs/challenge-agent-prompt.md)
- [ ] Frozen task list: [`TASKS_TEMPLATE.md`](./TASKS_TEMPLATE.md)

### Stack under test (L0/L1/L2)

| Level | Tools / files | Present in Control? | Present in CodeDNA? |
|---|---|---|---|
| L0 CodeDNA | in-source headers | no | yes |
| L1 | | | |
| L2 | | | |

### Metrics JSON (required)

- [ ] `challenge/<handle>/metrics.json` present
- [ ] Copied from [`metrics.example.json`](./metrics.example.json) / matches [`metrics.schema.json`](./metrics.schema.json)
- [ ] `schema_version` = `"1.0"`
- [ ] `project.languages` + `project.frameworks` + `approx_source_files` (≥25) + `size_band` filled
- [ ] `install.agent` + `install.steps` filled
- [ ] `setup.layout` filled (`two_branches` | `two_checkouts` | `two_projects`)
- [ ] `bugs_reported` present (empty array OK if none)
- [ ] ≥10 tasks with `difficulty` mix (easy ≥3, medium ≥3, hard ≥2)
- [ ] **Same tasks** each have both `control` and `codedna` results
- [ ] `summary.favors` set (`codedna` | `control` | `tie` | `inconclusive`)
- [ ] Results may favor **or** disfavor CodeDNA (honesty OK)

### Optional

- [ ] `README.md` / `notes.md` narrative
- [ ] Redacted `logs/`

### Bugs found in CodeDNA

- Links (or “none”) — also list them in `metrics.json` → `bugs_reported`:
- [ ] If something broke on my agent/language, I filed an issue or fix PR

### Checklist

- [ ] No secrets / proprietary source in this PR
- [ ] Redacted logs only
- [ ] Mode + stack parity declared in JSON (`mode`, `stack`)
- [ ] Metrics and narrative are truthful (not invented)
- [ ] I can present the project and test process on a review call (Meet / similar) if asked
- [ ] I understand fabricated claims or fake projects = disqualification
