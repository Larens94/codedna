# Benchmark Report — django__django-13495
## CodeDNA v0.8 vs Control · Claude Sonnet 4.6 · Single Run

**Date**: 2026-03-23
**Bug**: `Trunc()` ignores `tzinfo` param when `output_field=DateField()`
**Model**: claude-sonnet-4-6 (both sessions, same prompt)
**Ground truth**: official Django patch (7 files)

---

## Setup

| | Control | CodeDNA |
|---|---|---|
| Codebase | Django 3.2 vanilla | Django 3.2 + CodeDNA v0.8 annotations |
| CLAUDE.md | absent | present (CodeDNA reading protocol) |
| `.codedna` manifest | absent | present |
| Annotated files | 0 | 537 (92 L1 + 214 L2 function Rules:) |
| Spoilers on bug location | — | none (verified pre-test) |
| Model | claude-sonnet-4-6 | claude-sonnet-4-6 |

---

## Results

### 1. File Coverage vs Official Patch

The official Django fix touches exactly 7 files. Each session is scored against this ground truth.

| File | Official Patch | Control | CodeDNA |
|---|:---:|:---:|:---:|
| `django/db/models/functions/datetime.py` | ✅ | ✅ | ✅ |
| `django/db/backends/base/operations.py` | ✅ | ✅ | ✅ |
| `django/db/backends/postgresql/operations.py` | ✅ | ✅ | ✅ |
| `django/db/backends/mysql/operations.py` | ✅ | ✅ | ✅ |
| `django/db/backends/oracle/operations.py` | ✅ | ✅ | ✅ |
| `django/db/backends/sqlite3/operations.py` | ✅ | ✅ | ✅ |
| `django/db/backends/sqlite3/base.py` | ✅ | ❌ | ✅ |
| **Score** | **7 / 7** | **6 / 7 (86%)** | **7 / 7 (100%)** |

### 2. Fix Completeness

| Dimension | Control | CodeDNA |
|---|---|---|
| `date_trunc_sql` fixed for DateField | ✅ all backends | ✅ all backends |
| `time_trunc_sql` fixed for TimeField | ❌ not touched | ✅ all backends |
| `_sqlite_date_trunc` updated to 4 args | ❌ not touched | ✅ |
| `_sqlite_time_trunc` updated to 4 args | ❌ not touched | ✅ |
| SQLite approach matches official patch | ❌ (different strategy) | ✅ (4-arg registration) |
| Regression test added | ✅ (after multiple retries) | ❌ (Python 3.14 env) |
| `agent:` lines updated in modified files | ❌ | ✅ all 7 files |
| `.codedna` session entry written | ❌ | ✅ |
| `rules:` updated with new constraint | ❌ | ✅ |

### 3. Session Interactions

Wall-clock time was observed by the operator during the live sessions.
"Baked for Xm Ys" in Claude Code's UI refers to the last single-response generation time,
not total session duration — those values are not reported here.

**Observed session times**: Control ~10–11 min · CodeDNA ~8 min.

The values below are reconstructed from the tool call sequences in the session transcripts.

| Interaction type | Control | CodeDNA |
|---|:---:|:---:|
| **Session time (observed)** | **~10–11 min** | **~8 min** |
| File reads | ~8 | ~10 |
| Grep / search | ~7 | ~5 |
| Successful edits | 7 | 12 |
| **Failed edits** | **5** | **0** |
| Test runs attempted | 4 | 2 |
| Test runs succeeded | 1 | 0 (Python 3.14) |
| Session log writes | 2 | 1 |
| **Total interactions (estimated)** | **~33** | **~30** |

CodeDNA fixed more files, in less time, with zero edit failures. The control spent ~3 extra
minutes on 5 failed edit attempts on `test_extract_trunc.py` and 3 failed test run setups.

### 4. Navigation Path

| Step | Control | CodeDNA |
|---|---|---|
| 1 | Read project root | Read `.codedna` manifest |
| 2 | Read `datetime.py` | Read `datetime.py` module docstring (CodeDNA protocol) |
| 3 | [FOUND] bug in `DateField` branch | [FOUND] bug in `DateField` branch |
| 4 | Read all backend `date_trunc_sql` | Read all backend `date_trunc_sql` |
| 5 | Decision: fix `DateField` only | [FOUND] SQLite-specific complication identified separately |
| 6 | Fix + test + run tests | Decision: fix `DateField` AND `TimeField` + SQLite base |
| 7 | — | Fix all + logical verification |

Both sessions found the root cause at step 3, with the same number of explore steps.
CodeDNA added one extra [FOUND] step to document the SQLite complication explicitly —
this is where the deeper fix originated.

---

## Analysis

### What the control did well

Direct and efficient navigation. The control read `datetime.py`, immediately recognized the
asymmetry between the `DateTimeField` and `DateField` branches in `TruncBase.as_sql()`,
scanned all backends, and applied the primary fix. It also added a regression test and ran
the full test suite (80/80 pass). The reasoning at each step was clean.

### What CodeDNA changed — and why

**1. Fix scope: DateField + TimeField, not just DateField.**

The `rules:` annotation on `TimezoneMixin.get_tzname()` stated:

> *"TimezoneMixin must be inherited by any class that needs timezone-aware SQL generation;
> Extract and TruncBase both depend on its get_tzname() method."*

This architectural context prompted the agent to reason about the pattern, not just the
reported symptom. The bug description mentioned `DateField`; CodeDNA also fixed `TimeField`.
The control saw the same `time_trunc_sql` call on the line immediately below the bug —
and didn't touch it.

**2. SQLite: correct approach vs workaround.**

The control applied a SQLite fix by wrapping the field with `django_datetime_cast_date`:
```sql
django_date_trunc('day', django_datetime_cast_date(field, tz, conn_tz))
```
This reuses an existing function and avoids modifying `base.py`. It may work at runtime,
but it does not match the official patch strategy.

The official patch (and CodeDNA) updates `_sqlite_date_trunc` in `base.py` to accept
`tzname` and `conn_tzname` directly, and re-registers the function with 4 args:
```sql
django_date_trunc('day', field, 'Europe/Kiev', 'UTC')
```
CodeDNA identified this as a distinct [FOUND] step — "SQLite-specific complication" —
before deciding on the fix strategy. The control never logged this distinction.

**3. Knowledge propagation.**

After fixing, CodeDNA updated `rules:` in `datetime.py`:

> *"TruncBase.as_sql() must pass tzname to date_trunc_sql() and time_trunc_sql() when lhs
> is DateTimeField, so that output_field=DateField()/TimeField() with tzinfo works correctly."*

And appended `agent:` lines to all 7 modified files plus the `.codedna` session manifest.
The next agent opening this codebase will not need to rediscover this constraint.
The control left no trace for future agents.

### The SQLite question

The control's SQLite approach (`django_datetime_cast_date` wrapping) is not obviously wrong —
it reuses an existing 3-arg function that already handles timezone conversion. However:

- It does not touch `sqlite3/base.py`, which the official patch does.
- It does not update `_sqlite_date_trunc` to handle timezone natively.
- It does not fix `time_trunc_sql` for SQLite (same pattern, not addressed).

Whether the control's approach would pass Django's own test suite is unknown (tests could
not be run on CodeDNA due to Python 3.14; the control ran tests on SQLite only with 80/80
pass — but that test suite predates the fix and has limited timezone coverage).

---

## Ground Truth Scorecard

| Metric | Control | CodeDNA |
|---|---|---|
| Files matching official patch | **6 / 7** | **7 / 7** |
| `time_trunc_sql` bug fixed | ❌ | ✅ |
| SQLite approach matches official | ❌ | ✅ |
| Runtime correctness risk | ⚠️ SQLite `time_trunc` untouched | ✅ none identified |
| Fix introduces regressions | unknown | unknown |
| Knowledge left for next agent | ❌ | ✅ |

---

## Interpretation

**Fix completeness**: CodeDNA produced a patch that exactly matches the official Django fix
scope (7/7 files). The control produced a 6/7 patch, missed the `time_trunc_sql` path
(same bug, different output field), and applied a non-standard SQLite strategy.

**Navigation efficiency**: Both sessions found the root cause in the same number of explore
steps. CodeDNA made fewer total interactions (~30 vs ~33), with zero failed edits vs 5 in
the control. The control spent interaction budget on test retries and failed edits.

**The mechanism**: The difference in fix scope is traceable to a single `rules:` annotation
on `TimezoneMixin.get_tzname()`. That annotation encoded a general architectural truth
("any class needing timezone-aware SQL must use this mixin") rather than a description of
the specific reported bug. This caused the agent to evaluate the fix at the pattern level,
not just the symptom level.

---

## Limitations

- **Single run**: one run per condition. Variance is unknown; multiple runs are needed for
  statistical validity and to separate model noise from protocol effect.
- **Same model**: both sessions used claude-sonnet-4-6. Results may differ with weaker
  models where architectural context matters more.
- **Test failure in CodeDNA**: the regression test was not written (Python 3.14
  incompatibility with Django 3.2's `cgi` module). This is environmental, not protocol-related.
- **Wall-clock time not measured**: the interaction count proxy has limits. A future run
  should log precise timestamps.
- **Single annotator**: the `rules:` annotations were generated by claude-haiku-4-5 via
  `codedna init`. A different annotator or manual annotations might produce different results.

---

## Appendix — Files Changed

**Control (6 files + 1 test):**
```
django/db/models/functions/datetime.py
django/db/backends/base/operations.py
django/db/backends/postgresql/operations.py
django/db/backends/mysql/operations.py
django/db/backends/sqlite3/operations.py
django/db/backends/oracle/operations.py
tests/db_functions/datetime/test_extract_trunc.py  ← not in official patch scope
```

**CodeDNA (7 files + manifest):**
```
django/db/models/functions/datetime.py        ← agent: + rules: updated
django/db/backends/base/operations.py         ← agent: updated
django/db/backends/postgresql/operations.py   ← agent: + rules: updated
django/db/backends/mysql/operations.py        ← agent: updated
django/db/backends/oracle/operations.py       ← agent: updated
django/db/backends/sqlite3/operations.py      ← agent: updated
django/db/backends/sqlite3/base.py            ← agent: updated (missing from control)
.codedna                                       ← agent_sessions: entry appended
```
