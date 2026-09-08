# Agent prompt — CodeDNA Challenge (€200)

> Paste this whole message into your AI coding agent (Cursor, Claude Code, OpenCode, Codex, …).  
> Ranking page: https://larens94.github.io/codedna/challenge.html  
> Rules: https://github.com/Larens94/codedna/blob/main/docs/challenge.md  
> Italiano: [challenge-agent-prompt.it.md](challenge-agent-prompt.it.md)

---

## Role

Help me run the **CodeDNA Challenge** on **my real project** honestly and reproducibly. Do not invent metrics. If something is not measurable, mark it `inconclusive`.

## Methodology (same for everyone)

We compare the **same ≥10 tasks** under two conditions:

| Condition | What |
|---|---|
| **A — Control** | Normal AI workflow **without** CodeDNA (no headers / do not rely on CodeDNA) |
| **B — CodeDNA** | Same agent/model **with** CodeDNA installed and annotated |

### Allowed setup (pick one and declare it)

1. **Two branches** in the same repo — e.g. `challenge/control` and `challenge/codedna`  
2. **Two checkouts / two folders** of the same project  
3. **Two twin projects** (same starting code)

Rules:

- The **same tasks** in A and B (same list, same order if possible).
- Same agent, same model, same L1/L2 layers (wiki/skills/Graphify) unless `codedna_only` mode is declared.
- **Real working project** (≥25 source files). No toy landing page / hello-world.

## Stack to declare

Capture, then put in `metrics.json`:

- languages, frameworks (not language alone), approx files, size band S/M/L/XL
- agent + model
- how CodeDNA was installed (`install.steps`)
- layout used: `two_branches` | `two_checkouts` | `two_projects`

## Install CodeDNA (condition B)

```bash
pipx install git+https://github.com/Larens94/codedna.git
codedna install --path . --tools <my-agent>
codedna init . --no-llm
```

If it fails: reproduce, open an issue or fix PR on Larens94/codedna, list it in `bugs_reported`. Experimental — agent×language gaps are expected.

## Activity list (adapt to my repo, then freeze)

Create **≥10 tasks** on my code. Required mix: easy ≥3, medium ≥3, hard ≥2.

Use this checklist as a skeleton (replace titles with **real** tasks from my project):

### Easy (≥3)

- [ ] **E1** — Rename a symbol and update all callers
- [ ] **E2** — Add a field/DTO/prop with validation
- [ ] **E3** — Fix a clear bug with a known file
- [ ] **E4** (opt.) — Update an existing test after a rename

### Medium (≥3)

- [ ] **M1** — Small cross-file feature (API + service + test)
- [ ] **M2** — Refactor with an invariant that must not break
- [ ] **M3** — Signature / contract change and update callers
- [ ] **M4** (opt.) — Add logging/metrics on an existing path

### Hard (≥2)

- [ ] **H1** — Multi-module bug (“where do I change this safely?”)
- [ ] **H2** — Architectural / auth / multi-tenant / package-boundary constraint
- [ ] **H3** (opt.) — Migration or schema change across layers

For **each** task record Control and CodeDNA: `passed`, `minutes`/`turns`/`tool_calls` when available, `wrong_file_or_module`, `human_interventions`, notes.

**Optional (not required):**

- `files_expected` only if known; otherwise omit (do not invent precision/recall)
- `files_opened` / `files_edited` if you can track them
- After both sessions: run a **judge agent** with [`challenge-judge-prompt.md`](challenge-judge-prompt.md) and save `tasks[].judge` + optional top-level `judge`

## Deliverable

1. Freeze the task list **before** timed runs.
2. Run every task in **A**, then the **same** ones in **B** (or interleaved, but same IDs).
3. (Recommended) Have a separate agent judge both sessions with the judge prompt.
4. Fill `challenge/<my-github-handle>/metrics.json` from  
   https://github.com/Larens94/codedna/blob/main/challenge/metrics.example.json  
   (schema: `metrics.schema.json`).
5. Open a PR on `Larens94/codedna` titled:  
   `challenge: <handle> — CodeDNA Challenge submission`  
   Checklist: `challenge/SUBMISSION_TEMPLATE.md`
6. Honesty: no invented results. A Meet verification may be requested.

## What to do now

1. Inspect my repo and propose an adapted ≥10 task list (easy/medium/hard).
2. Ask which setup I will use: **two branches** / **two checkouts** / **two projects**.
3. Prepare install commands for condition B.
4. Only after I confirm: run the tasks and fill the metrics.
5. After the runs: offer the judge pass (prompt ready) if I want a structured comparison.
