# Prompt — django__django-13495 / codedna

**Bug: Trunc() ignores tzinfo param when output_field=DateField()**

I'm trying to use TruncDay() function like this:
  TruncDay('created_at', output_field=DateField(), tzinfo=tz_kyiv)

but for PostgreSQL the SQL generated is:
  (DATE_TRUNC('day', "storage_transaction"."created_at"))

So timezone conversion like AT TIME ZONE 'Europe/Kiev' was totally ignored.

Find the root cause and fix it.

**Before writing any code, follow the CodeDNA reading protocol:**
1. Read the `.codedna` manifest file first to understand recent project history (last 3-5 `agent_sessions:` entries).
2. Read the module docstring of every file you open before reading the code.
3. Parse `exports:`, `used_by:`, `rules:`, `agent:` fields.
4. For any function you edit, read its `Rules:` docstring first.
5. After editing, append an `agent:` line to the module docstring.
6. Update `rules:` if you discover a new constraint.
7. When checking `used_by:` dependencies, only follow the ones directly relevant to this task — do not explore the full dependency graph.

---

**Session logging (mandatory):**
As you work, continuously append every step to `session_log.md` in the project root using this format:

## [EXPLORE] <what you opened/searched and why>
## [FOUND] <what you discovered>
## [DECISION] <what you decided to do and why>
## [ACTION] <what you changed and where>
## [VERIFY] <how you checked the fix is correct>

Write each entry immediately when it happens. Do not batch at the end.
