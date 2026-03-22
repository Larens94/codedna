# Session Log — TruncDay tzinfo Bug Fix

## [EXPLORE] Read .codedna manifest
No prior agent_sessions entries. Fresh project.

## [EXPLORE] Read django/db/models/functions/datetime.py
Read module docstring first (CodeDNA protocol). File exports TruncBase, Trunc, TruncDay etc.
rules: TimezoneMixin must be inherited by any class needing timezone-aware SQL generation.

## [FOUND] Root cause in TruncBase.as_sql() — line 207-208
```python
elif isinstance(self.output_field, DateField):
    sql = connection.ops.date_trunc_sql(self.kind, inner_sql)  # BUG: tzname NOT passed
```
When output_field=DateField, the code skips calling get_tzname() entirely and passes no
tzname to date_trunc_sql(). The DateTimeField branch (line 204-206) correctly calls
get_tzname() and passes it to datetime_trunc_sql(), but DateField branch does not.

## [EXPLORE] Read all backend date_trunc_sql() implementations
- postgresql/operations.py: date_trunc_sql(lookup_type, field_name) — no tzname param
  Has _convert_field_to_tz() that applies "AT TIME ZONE" when USE_TZ is set.
- mysql/operations.py: date_trunc_sql(lookup_type, field_name) — no tzname param
  Has _convert_field_to_tz() that applies CONVERT_TZ() when USE_TZ is set.
- sqlite3/operations.py: date_trunc_sql(lookup_type, field_name) — no tzname param
  Delegates to django_date_trunc custom function (registered with 2 args).
- oracle/operations.py: date_trunc_sql(lookup_type, field_name) — no tzname param
  Has _convert_field_to_tz() for timezone conversion.
- base/operations.py: date_trunc_sql(lookup_type, field_name) — base class signature.

## [FOUND] SQLite-specific complication
SQLite's django_date_trunc is registered with 2 args (lookup_type, dt).
_sqlite_date_trunc(lookup_type, dt) passes dt to _sqlite_datetime_parse(dt) without tzname.
_sqlite_datetime_parse(dt, tzname=None, conn_tzname=None) already supports timezone params.
Fix requires: update _sqlite_date_trunc to accept tzname/conn_tzname, update registration to 4 args,
and update date_trunc_sql to pass _convert_tznames_to_sql() results.

## [DECISION] Fix strategy — check lhs type in TruncBase.as_sql() and pass tzname to all backends
- In TruncBase.as_sql(): pass tzname when lhs is DateTimeField (not DateField)
  Rationale: DateField inputs don't have a time component, so TZ conversion makes no sense.
  DateTimeField inputs are stored in UTC and need TZ conversion before truncating to date.
- In all backends: add tzname=None to date_trunc_sql(), apply conversion when tzname is not None.
- For SQLite: update _sqlite_date_trunc to accept optional tzname/conn_tzname,
  re-register with 4 args, update date_trunc_sql in operations.py.

## [ACTION] Editing TruncBase.as_sql() in datetime.py
Changed DateField branch to get tzname from lhs field type and pass it to date_trunc_sql.

## [ACTION] Editing postgresql/operations.py date_trunc_sql()
Added tzname=None param, apply _convert_field_to_tz when tzname provided.

## [ACTION] Editing mysql/operations.py date_trunc_sql()
Added tzname=None param, apply _convert_field_to_tz when tzname provided.

## [ACTION] Editing oracle/operations.py date_trunc_sql()
Added tzname=None param, apply _convert_field_to_tz when tzname provided.

## [ACTION] Editing sqlite3/base.py _sqlite_date_trunc()
Updated to accept tzname=None and conn_tzname=None, passes them to _sqlite_datetime_parse.
Updated registration from 2 to 4 args.

## [ACTION] Editing sqlite3/operations.py date_trunc_sql()
Updated to accept tzname=None and pass _convert_tznames_to_sql results when tzname provided.

## [ACTION] Editing base/operations.py date_trunc_sql()
Updated docstring/signature to document new optional tzname parameter.

## [VERIFY] Logic check for fix correctness
- TruncDay('created_at', output_field=DateField(), tzinfo=tz_kyiv):
  - lhs.output_field = DateTimeField → tzname = get_tzname() returns 'Europe/Kiev'
  - Calls date_trunc_sql('day', inner_sql, 'Europe/Kiev')
  - PostgreSQL: applies _convert_field_to_tz → "created_at AT TIME ZONE 'Europe/Kiev'"
  - Final SQL: DATE_TRUNC('day', "storage_transaction"."created_at" AT TIME ZONE 'Europe/Kiev')
  - Correct! ✓
- TruncDay('date_field', output_field=DateField()):
  - lhs.output_field = DateField (not DateTimeField) → tzname = None
  - Calls date_trunc_sql('day', inner_sql, None) → no conversion applied
  - Correct! ✓
- TruncDay('created_at', output_field=DateTimeField(), tzinfo=tz_kyiv):
  - output_field is DateTimeField → existing branch applies → Correct! ✓

## [VERIFY] Tests could not be executed
- Python 3.14 environment; Django codebase uses removed `cgi` module.
- Logical correctness verified by tracing the call stack for each scenario.
- All 5 backends consistently updated to accept optional tzname.
- SQLite custom functions re-registered with 4 args (was 2) to support tzname/conn_tzname.
- _convert_tznames_to_sql(None) is guarded — only called when tzname is provided.
