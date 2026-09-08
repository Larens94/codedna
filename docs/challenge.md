# CodeDNA Challenge — €200

> **Language:** English · [Italiano](challenge.it.md)  
> **Status:** draft / open  
> **Prize:** €200  
> **Duration:** 1 month from the official start date  
> **Enrollment:** opening a metrics PR = you are enrolled (no separate signup)  
> **Not a SWE-bench rerun.** You test CodeDNA on **your own project**.  
> **Public board:** [challenge.html](challenge.html) on the docs site

This challenge asks one question:

> Does CodeDNA help (or not) when you do real AI-assisted development work — and can we measure it honestly?

**Experimental.** CodeDNA quality still depends on the **AI coding agent** and the **language / framework** you use. Some combinations work better than others. If install, annotation, hooks, or refresh misbehave on your stack, **open a GitHub issue or a fix PR** — that is part of the challenge, and we will harden upstream from your reports.

---

## TL;DR

1. Work on **your real, working project** (not our old benchmarks — not a toy site).
2. Declare your full **tech stack** (languages, frameworks, agent, install path).
3. Run **at least 10 tasks** (easy / medium / hard mix) — the **same tasks twice**: once **without** CodeDNA, once **with** CodeDNA.
4. Keep your AI stack **fair** (see Levels below).
5. Document **how you installed CodeDNA**; report bugs / open fix PRs when something breaks (expected — still experimental).
6. Open a **Pull Request** with `metrics.json` — even if CodeDNA looks worse. **That PR is your enrollment.**
7. The **public board / ranking updates as valid PRs arrive** and stays visible on the docs site.
8. Your project may be called to a **live review / presentation** (conference call) so we can verify the tests are real.
9. Prize unlocks only if the **minimum participant count** is met.

---

## Prize & minimum participants

| Item | Rule |
|---|---|
| Prize pool | **€200** (paid to the winning submission after review) |
| Minimum valid submissions | **5** to unlock the prize (stretch goal: 10) |
| If fewer than 5 valid PRs | Challenge still publishes results; prize is **not** awarded (or rolled to the next edition) |
| Winner | Selected by Fabrizio Corpora + review team (not community vote) |
| Honesty | Claims must be true and evidence-backed — fabricated metrics, fake projects, or invented narratives = disqualification |
| Verification | Fabrizio or the review team may require a **conference call + presentation** (Google Meet / similar): show the real project, explain how you ran the tests, walk through install + `metrics.json` |
| Public board | Ranking on [challenge.html](challenge.html) is updated **as soon as valid PRs arrive** (maintainer review → board row) and remains publicly visible |
| Lives | When possible we will host public live sessions discussing submitted tests (with entrant consent where needed) |

### What we score (in order)

1. **Protocol honesty** — real project, fair stack, declared mode, reproducible notes; **no invented results**  
2. **Task quality** — real easy/medium/hard mix on a real working codebase  
3. **Evidence** — metrics + install path + short narrative; pro **or** against CodeDNA is fine  
4. **Bug reports / fix PRs** — required when CodeDNA breaks on your agent or language; actionable upstream issues count positively  
5. **Clarity** — another engineer can re-run your comparison  

### Honesty, review calls, and lives

- You **must not invent** pass/fail outcomes, timings, stack details, or narrative claims. If you cannot reproduce a number, mark the task inconclusive and say so.
- **Fake or throwaway projects are not allowed.** We may require a **live conference + short presentation** where you:
  - show that the project is real and working;
  - explain your tech stack;
  - walk through how you installed CodeDNA;
  - show how you ran the **same tasks** with and without CodeDNA;
  - answer questions on `metrics.json` / notes.
- Refusing a reasonable verification request without a good reason can void prize eligibility for that entry.
- When feasible we will also run **public live sessions** covering interesting challenge runs (methodology, surprises, agent × language gaps). Participation in a live is optional unless you are asked for verification.

---

## Timeline (fill before publish)

| Phase | When |
|---|---|
| Announcement + video | **TBD** |
| Submissions open (PR = enroll) | **TBD** |
| Challenge window | **1 month** from start date |
| Submission deadline | end of challenge window (PRs must be open) |
| Board / ranking | updated continuously as valid PRs arrive |
| Review | ~1–2 weeks after deadline (plus any Meet presentations) |
| Winner announced | **TBD** |

---

## Who can enter

- Any developer using an AI coding agent (Cursor, Claude Code, Codex, Copilot, Cline, Roo, Windsurf, OpenCode, …)
- Solo or small team (one PR per entrant / team)
- Your project can be private during the run; the **metrics PR** to this repo must be public

---

## Core protocol (mandatory)

### 1. Your project (must be real)

Use a repo **you** maintain (work or personal). It must be a **real, working project** — small is fine; a tiny marketing page, hello-world, or throwaway demo is **not**.

**Rejected examples:** one-page “sito vetrina”, empty CRUD scaffold with no domain logic, synthetic repos built only for the challenge.

**Accepted examples:** a service you actually use or ship, an internal tool, a library with real callers, a small but complete product (≥ **25** source files as a hard floor).

In `metrics.json` you **must** declare your **tech stack**:

| Field | Example |
|---|---|
| `languages` | `["TypeScript", "Python"]` |
| `frameworks` | `["NestJS", "FastAPI"]` — language alone is **not** enough |
| `approx_source_files` | `120` (minimum **25**) |
| `size_band` | `S` (<50) · `M` (50–199) · `L` (200–999) · `XL` (1000+) |
| `tech_stack_notes` | optional — DB, monorepo layout, infra, major libs |
| `install.agent` + `install.steps` | which AI agent + exact CodeDNA install/init commands |

### 2. Ten tasks minimum — same tasks both ways

Define **≥10** tasks **before** you start the timed runs (or freeze the list in the PR).

Suggested mix:

| Difficulty | Count (min) | Examples |
|---|---|---|
| Easy | ≥3 | rename + update callers, add a field, fix a clear bug with known file |
| Medium | ≥3 | cross-file feature, refactor with invariants, API change |
| Hard | ≥2 | multi-module bug, architecture constraint, “where do I change this safely?” |

Record for each task: goal, difficulty, agent/tool, success/fail, notes.

**Critical:** every task runs in **both** conditions. Do not invent a different task list for Control vs CodeDNA.

### 3. Two conditions: without vs with CodeDNA

For **each of the same tasks**, run:

| Condition | Setup |
|---|---|
| **A — Control** | Your normal AI workflow **without** CodeDNA annotations / without relying on CodeDNA headers |
| **B — CodeDNA** | Same workflow **with** CodeDNA installed + annotated (`codedna init` / maintained headers) |

Keep the **agent, model, and higher stack layers identical** between A and B except for CodeDNA itself (unless you declare an explicit mode — see below).

### 4. Fair stack — Levels (critical)

If you already use extra AI-dev layers, CodeDNA must be tested **on top of the same stack**, not instead of it by accident.

| Level | Examples | Rule |
|---|---|---|
| **L0** | CodeDNA in-source headers | The layer under test |
| **L1** | LLM wiki, curated markdown memory, skill packs, agent instruction files | If Control has it, CodeDNA run has it too |
| **L2** | Graphify / graph memory / similar structural layers | If Control has it, CodeDNA run has it too |

**Parity rule:**  
`stack(Control) == stack(CodeDNA)` except for L0 CodeDNA being present in B.

**Declared solo-L0 mode (optional):**  
If you deliberately test whether **CodeDNA alone** can replace L1/L2, you **must** say so in the PR (`mode: codedna-only-vs-higher-stack` or similar) and describe what you removed. Curiosity-only or undeclared unequal stacks are **invalid**.

### 5. Metrics (minimum set) — **JSON required**

The mergeable source of truth is a single file:

```text
challenge/<your-github-handle>/metrics.json
```

Copy [`challenge/metrics.example.json`](../challenge/metrics.example.json) and fill it.  
Schema: [`challenge/metrics.schema.json`](../challenge/metrics.schema.json) (`schema_version: "1.0"`).

Required per task (Control + CodeDNA):

| Field | Notes |
|---|---|
| `passed` | Your success definition must be stated in `success_definition` |
| `minutes` / `turns` / `tool_calls` | Use what you can measure; `null` if unknown |
| `wrong_file_or_module` | When applicable |
| `human_interventions` | How often you had to steer |
| `confidence_1_to_5` | Optional but useful |

Also fill:

- `summary.favors`: `codedna` | `control` | `tie` | `inconclusive`
- `install` — **required**: agent + exact install/init steps (and whether it worked)
- `bugs_reported` — **required** array (empty if none); if something broke, file an issue or fix PR and list it here

Raw numbers can favor CodeDNA **or not**. Honesty beats cheerleading.  
Markdown notes (`notes.md`) are optional narrative — **do not replace** `metrics.json`.

### 6. Install path + bug reports (mandatory when relevant)

Publish **how you installed CodeDNA** in `metrics.json` → `install` (commands, `--tools` flag, agent).  
CodeDNA is still **experimental**: it may fail or behave poorly with some agentic tools (Claude Code, OpenCode, Cursor, Codex, …) or languages.

If install, annotation, hooks, or refresh misbehaves:

1. Reproduce once (agent + language/framework + command).
2. Open a **GitHub issue** or a **fix PR**.
3. List it in `bugs_reported` and mention it in `notes.md`.

Broken tooling on a given stack does **not** disqualify you — **hiding** it does.

### 7. Submission = Pull Request

Open a PR against `Larens94/codedna`. Copy the checklist into the PR body:

- English: [`challenge/SUBMISSION_TEMPLATE.md`](../challenge/SUBMISSION_TEMPLATE.md)
- Italiano: [`challenge/SUBMISSION_TEMPLATE.it.md`](../challenge/SUBMISSION_TEMPLATE.it.md)

Add this folder:

```text
challenge/<your-github-handle>/
  metrics.json       # REQUIRED — machine-readable results (merged + aggregated later)
  README.md          # summary + mode declaration + stack levels used
  notes.md           # optional narrative, surprises, bugs
  (optional) logs/   # redacted session excerpts
```

Use the PR title:

```text
challenge: <handle> — CodeDNA Challenge submission
```

**Why JSON:** each entrant lands in their own folder, PRs merge cleanly, and we can aggregate all `metrics.json` files after the window closes.

### 8. Public board / ranking

The live ranking is [challenge.html](challenge.html) (data: [`challenge-board.json`](challenge-board.json)).

- As soon as a valid metrics PR is reviewed, we add/update a row — the board stays **publicly visible**.
- Opening a PR enrolls you; appearing on the board means maintainers accepted the submission format and stack declaration.

---

## How to enter (no official signup)

There is **no separate registration**. When you open a valid challenge PR with `metrics.json`, you are enrolled.

1. Install CodeDNA and annotate your project (record the exact steps in `install`):

```bash
pipx install git+https://github.com/Larens94/codedna.git
codedna install --path . --tools <your-agent>
codedna init . --no-llm   # or with an LLM for rules:
```

2. Run your ≥10 **same** tasks twice (Control vs CodeDNA, fair stack).
3. Open a PR adding `challenge/<handle>/metrics.json` (include `install` + `bugs_reported`).
4. We review, update the [public board](challenge.html), and may invite you to a Meet presentation.

Questions only (optional): GitHub Discussions / Discord — the old “entry issue” template is not required.

### If something breaks on your agent or language

CodeDNA is still experimental across agents and languages (Claude Code, OpenCode, Cursor, Codex, …). Prefer this path:

1. Reproduce once (agent + language/framework + command).
2. Open an **issue** (bug) or a **PR** with a minimal fix / regression test.
3. Continue the challenge if you can; note the incident in `metrics.json` → `bugs_reported` and in `notes.md`.

Broken tooling on a given stack does **not** disqualify you — **hiding** it does.

---

## What this challenge is not

- Not a rerun of SWE-bench / our historical F1 tables  
- Not “annotate our fixture repos only”  
- Not a tiny throwaway site or hello-world built only for the prize  
- Not unpaid consulting for us — you keep your project IP; we only review the metrics PR (+ optional Meet presentation)  

---

## Communication

- Issues / bugs: GitHub Issues  
- Challenge Q&A: GitHub Discussions (Announcements / Q&A)  
- Community: Discord (see README badge)  
- Verification / presentation calls: Google Meet (or similar) when requested by maintainers  
- Public lives: announced on Discussions / Discord when scheduled  
- Maintainer: Fabrizio Corpora  

---

## License of submissions

By opening a challenge PR you grant permission to quote **metrics and anonymized summaries** in CodeDNA docs / blog / video. Do not upload secrets, proprietary source, or credentials. Redact logs.
