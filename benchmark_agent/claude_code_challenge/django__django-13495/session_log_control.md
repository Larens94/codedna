# Session Log — django__django-13495 Trunc() tzinfo bug fix

## [EXPLORE] Opening project root to understand structure
Starting investigation of Trunc() ignoring tzinfo when output_field=DateField().

## [EXPLORE] Reading django/db/models/functions/datetime.py
Looking for TruncBase.as_sql() implementation at lines 192-203.

## [FOUND] Root cause in TruncBase.as_sql() — datetime.py lines 197-198
```python
elif isinstance(self.output_field, DateField):
    sql = connection.ops.date_trunc_sql(self.kind, inner_sql)  # BUG: no tzname passed!
```
When output_field=DateField, `date_trunc_sql` is called WITHOUT tzname.
Contrast with DateTimeField branch (line 195-196) which correctly calls:
`datetime_trunc_sql(self.kind, inner_sql, tzname)`
The tzinfo parameter stored in self.tzinfo is fully ignored for this path.

## [EXPLORE] Reading all backend date_trunc_sql implementations
PostgreSQL, MySQL, SQLite3, Oracle — none accept a tzname parameter.
Their `datetime_trunc_sql` counterparts DO handle tzname (all use _convert_field_to_tz).

## [DECISION] Fix approach: add optional tzname to date_trunc_sql in all backends
When the lhs is a DateTimeField (not DateField), pass tzname to date_trunc_sql.
Each backend applies timezone conversion before truncating when tzname is provided.
This mirrors exactly how datetime_trunc_sql already works across all backends.

## [ACTION] Modified datetime.py — TruncBase.as_sql()
```python
elif isinstance(self.output_field, DateField):
    tzname = self.get_tzname() if isinstance(self.lhs.output_field, DateTimeField) else None
    sql = connection.ops.date_trunc_sql(self.kind, inner_sql, tzname)
```

## [ACTION] Modified base/operations.py
Added `tzname=None` to `date_trunc_sql` signature + updated docstring.

## [ACTION] Modified postgresql/operations.py
```python
def date_trunc_sql(self, lookup_type, field_name, tzname=None):
    field_name = self._convert_field_to_tz(field_name, tzname) if tzname else field_name
    return "DATE_TRUNC('%s', %s)" % (lookup_type, field_name)
```
Produces: `DATE_TRUNC('day', "created_at" AT TIME ZONE 'Europe/Kiev')` — exactly what was missing.

## [ACTION] Modified mysql/operations.py
Added tzname=None parameter; calls `_convert_field_to_tz` first when tzname provided.

## [ACTION] Modified sqlite3/operations.py
Uses `django_datetime_cast_date` (existing 3-arg function) to pre-convert timezone,
then applies `django_date_trunc` on the result:
`django_date_trunc('day', django_datetime_cast_date(field, tzname, conn_tzname))`

## [ACTION] Modified oracle/operations.py
Added tzname=None parameter; calls `_convert_field_to_tz` first when tzname provided.

## [ACTION] Added test in test_extract_trunc.py — test_trunc_func_with_timezone
Added `test_datetime_to_date_kind()` inner function that exercises:
`Trunc('start_datetime', kind, output_field=DateField(), tzinfo=melb)`
for kinds: year, quarter, month, week, day.
This is the exact scenario that was broken and is now fixed.

## [VERIFY] Ran full db_functions.datetime test suite
All 80 tests pass (2 skipped for unrelated has_native_duration_field).
test_trunc_func_with_timezone (including new assertions) passes on SQLite.
