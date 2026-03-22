# Prompt — django__django-13495 / control

**Bug: Trunc() ignores tzinfo param when output_field=DateField()**

I'm trying to use TruncDay() function like this:
  TruncDay('created_at', output_field=DateField(), tzinfo=tz_kyiv)

but for PostgreSQL the SQL generated is:
  (DATE_TRUNC('day', "storage_transaction"."created_at"))

So timezone conversion like AT TIME ZONE 'Europe/Kiev' was totally ignored.

Find the root cause and fix it.

---

**Session logging (mandatory):**
As you work, continuously append every step to `session_log.md` in the project root using this format:

## [EXPLORE] <what you opened/searched and why>
## [FOUND] <what you discovered>
## [DECISION] <what you decided to do and why>
## [ACTION] <what you changed and where>
## [VERIFY] <how you checked the fix is correct>

Write each entry immediately when it happens. Do not batch at the end.
