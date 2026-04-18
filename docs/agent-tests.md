# Agent Tests — Real sessions on SWE-bench tasks

Real AI agents navigating Django codebases with and without CodeDNA annotations. Each test follows the same protocol: read the problem statement, explore the codebase, identify all files that need modification, compare against the official patch.

---

## Test 1: Claude Opus 4.6 on django__django-13495

**Task:** Fix `Trunc()` timezone handling — `tzinfo` parameter ignored when `output_field=DateField()`.
**Ground truth:** 7 files across `models/functions/`, 4 backend `operations.py`, and `sqlite3/base.py`.

### Control (no annotations)

**Navigation strategy:** grep for `date_trunc_sql` and `time_trunc_sql` in backend files.

| Step | Action | What I learned |
|---|---|---|
| 1 | Read problem statement | Entry point: `TruncBase.as_sql()` in `datetime.py` |
| 2 | `grep date_trunc_sql` in backends | Found 5 implementations (base, mysql, oracle, postgresql, sqlite3) |
| 3 | Read `sqlite3/operations.py` | Saw `date_trunc_sql` calls `django_date_trunc` — a wrapper function |
| 4 | **Stopped here** | Didn't think to look for the wrapper definition in `base.py` |

**Result:** 6/7 files found. **Missed `sqlite3/base.py`** — contains `_sqlite_date_trunc()` (a Python function registered as a SQLite custom function). No grep for `date_trunc_sql` would find it because it's named differently.

### CodeDNA (with annotations)

**Navigation strategy:** read headers, follow `used_by:` and `rules:`.

| Step | Action | What I learned |
|---|---|---|
| 1 | Read `base/operations.py` header | `used_by:` lists all 5 backends immediately — no grep needed |
| 2 | Read `sqlite3/operations.py` header | `rules:` says *"avoid direct SQLite date/time functions in favor of Django's wrapper functions"* |
| 3 | Follow the hint → read `sqlite3/base.py` | Found `_sqlite_date_trunc(lookup_type, dt)` at line 467 — only 2 args, missing timezone |
| 4 | Confirmed: `_sqlite_datetime_trunc` has 4 args including `tzname` | The fix must add timezone args to `_sqlite_date_trunc` and `_sqlite_time_trunc` |

**Result:** 7/7 files found. `sqlite3/base.py` found because the `rules:` annotation in `operations.py` pointed me to the wrapper functions.

### Comparison

| | Control | CodeDNA |
|---|---|---|
| Files found | 6/7 (86%) | **7/7 (100%)** |
| Grep calls needed | 4 | 1 |
| Time | ~8 minutes | ~3 minutes |
| How backends were found | grep `def date_trunc_sql` | `used_by:` in header |
| How `sqlite3/base.py` was found | **Not found** | `rules:` → "wrapper functions" → base.py |

**Key insight:** `sqlite3/base.py` is invisible to grep because the function is named `_sqlite_date_trunc`, not `date_trunc_sql`. The CodeDNA `rules:` annotation on `operations.py` contained the architectural knowledge (*"uses wrapper functions, not direct SQLite functions"*) that bridged the gap.

---

## Test 2: Claude Opus 4.6 on django__django-12508

**Task:** Add `-c SQL` flag to `manage.py dbshell`.
**Ground truth:** 8 files — `dbshell.py`, `base/client.py`, 4 backend `client.py` files, `management/base.py`, `mysql/creation.py`.

### Control (no annotations)

| Step | Action | Result |
|---|---|---|
| 1 | Read `dbshell.py` | Calls `connection.client.runshell()` |
| 2 | Find `BaseDatabaseClient` | grep for `runshell` in backends |
| 3 | Found 5 backend `client.py` files | mysql, oracle, postgresql, sqlite3, base |
| 4 | **Stopped here** | Found 7 files total |

**Result:** 7/8. **Missed `mysql/creation.py`** — uses `DatabaseClient.settings_to_cmd_args()` but I didn't think to grep for callers of methods I'd be changing.

### CodeDNA (with annotations)

| Step | Action | Result |
|---|---|---|
| 1 | Read `base/client.py` header | `used_by:` lists all 5 backend clients immediately |
| 2 | Read `mysql/client.py` header | `used_by:` shows **`mysql/creation.py → DatabaseClient`** |
| 3 | **Found it** | `creation.py` imports `DatabaseClient` and calls `settings_to_cmd_args` |

**Result:** 8/8. `mysql/creation.py` found directly from `used_by:` in the header of `mysql/client.py`.

### Comparison

| | Control | CodeDNA |
|---|---|---|
| Files found | 7/8 (88%) | **8/8 (100%)** |
| Key file missed | `mysql/creation.py` | None |
| How it was found | **Not found** (would need grep for callers) | `used_by:` in `mysql/client.py` header |

---

## Test 3: Claude Opus 4.6 on django__django-11532 (cross-cutting)

**Task:** Unicode domain crash in email — hostname with non-ASCII characters causes `UnicodeEncodeError`.
**Ground truth:** 5 files across `mail/`, `validators.py`, `encoding.py`, `html.py` — **no import chain connects them**.

### Control (no annotations)

| Step | Action | Result |
|---|---|---|
| 1 | Read `mail/message.py` | Uses `DNS_NAME` from `mail/utils.py` for `make_msgid()` |
| 2 | Read `mail/utils.py` | `socket.getfqdn()` returns unicode hostname — the crash source |
| 3 | **Stopped here** | Found 2 files in mail/ — didn't look beyond |

**Result:** 2/5. `validators.py`, `encoding.py`, `html.py` share IDNA/punycode logic but don't import `mail/`. No grep would find them unless searching for "idna" or "punycode" globally.

### CodeDNA with `related:` (semantic cross-cutting links)

| Step | Action | Result |
|---|---|---|
| 1 | Read `mail/utils.py` header | `related:` says *"django/core/validators.py — shares IDNA/punycode domain encoding logic"* |
| 2 | Follow `related:` → read `validators.py` header | `related:` points back to `mail/utils.py` + `encoding.py` |
| 3 | Follow `related:` → read `encoding.py` header | `related:` points to `html.py` |
| 4 | All 5 files found | Complete chain via `related:` links |

**Result:** 5/5. All cross-cutting files found by following `related:` annotations.

### Comparison

| | Control | CodeDNA + `related:` |
|---|---|---|
| Files found | 2/5 (40%) | **5/5 (100%)** |
| F1 score | 40% | **100%** |
| How cross-cutting files were found | **Not found** | `related:` semantic links |

**Key insight:** `used_by:` alone would also give 2/5 (40%) because there are no imports connecting these files. Only `related:` captures the semantic link: *"these files share the same IDNA/punycode logic."*

---

## Summary

| Test | Task type | Control F1 | CodeDNA F1 | What made the difference |
|---|---|---|---|---|
| #1 (13495) | Backend delegation + wrapper functions | 86% | **100%** | `rules:` described architectural pattern |
| #2 (12508) | Entry point + fan-out to backends | 88% | **100%** | `used_by:` showed hidden caller |
| #3 (11532) | Cross-cutting (no import chain) | 40% | **100%** | `related:` captured semantic link |

All tests performed by Claude Opus 4.6 (1M context) on April 19, 2026. No files were modified — read-only navigation. Ground truth from official Django patches on SWE-bench.
