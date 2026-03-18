"""patch_annotations_13495.py — Manual CodeDNA annotations for all 7 GT files of django__django-13495.

exports: none (script)
used_by: none
rules:   Run ONCE to fix broken annotations from truncated LLM output.
"""
from pathlib import Path

BASE = Path(__file__).parent / "projects_swebench" / "django__django-13495" / "codedna"

ANNOTATIONS = {
    "django/db/backends/base/operations.py": (
        '"""operations.py — BaseDatabaseOperations: abstract SQL generation hooks subclassed by all backends.\n\n'
        'exports: BaseDatabaseOperations\n'
        'used_by: django/db/backends/mysql/operations.py → DatabaseOperations\n'
        '         django/db/backends/oracle/operations.py → DatabaseOperations\n'
        '         django/db/backends/postgresql/operations.py → DatabaseOperations\n'
        '         django/db/backends/sqlite3/operations.py → DatabaseOperations\n'
        'rules:   Changes here affect ALL backends; each backend overrides specific methods — '
        'verify mysql, oracle, postgresql, sqlite3 all work after edits.\n'
        '"""'
    ),
    "django/db/backends/mysql/operations.py": (
        '"""operations.py — MySQL-specific SQL operations overriding BaseDatabaseOperations.\n\n'
        'exports: DatabaseOperations\n'
        'used_by: django/db/backends/mysql/base.py → DatabaseWrapper.ops\n'
        'rules:   MySQL lacks native boolean and uses CONVERT_TZ for timezone; '
        'always check supports_timezones before generating timezone SQL.\n'
        '"""'
    ),
    "django/db/backends/oracle/operations.py": (
        '"""operations.py — Oracle-specific SQL operations overriding BaseDatabaseOperations.\n\n'
        'exports: DatabaseOperations\n'
        'used_by: django/db/backends/oracle/base.py → DatabaseWrapper.ops\n'
        'rules:   Oracle uses custom date/time handling; timezone SQL must use Oracle-compatible functions.\n'
        '"""'
    ),
    "django/db/backends/postgresql/operations.py": (
        '"""operations.py — PostgreSQL-specific SQL operations overriding BaseDatabaseOperations.\n\n'
        'exports: DatabaseOperations\n'
        'used_by: django/db/backends/postgresql/base.py → DatabaseWrapper.ops\n'
        'rules:   PostgreSQL supports AT TIME ZONE natively; USE_TZ must be checked before timezone SQL.\n'
        '"""'
    ),
    "django/db/backends/sqlite3/base.py": (
        '"""base.py — SQLite3 DatabaseWrapper: configures connection, type conversions, version checks.\n\n'
        'exports: DatabaseWrapper\n'
        'used_by: django/db/backends/sqlite3/operations.py → DatabaseWrapper\n'
        'rules:   SQLite3 has limited type system; maintain strict compatibility with Django ORM expectations.\n'
        '"""'
    ),
    "django/db/backends/sqlite3/operations.py": (
        '"""operations.py — SQLite-specific SQL operations; emulates unsupported SQL features.\n\n'
        'exports: DatabaseOperations\n'
        'used_by: django/db/backends/sqlite3/base.py → DatabaseWrapper.ops\n'
        'rules:   SQLite has no native timezone support; timezone handling must be emulated at the Python level.\n'
        '"""'
    ),
    "django/db/models/functions/datetime.py": (
        '"""datetime.py — Datetime database functions (Trunc, Extract) for SQL date/time operations.\n\n'
        'exports: Extract, Trunc, TruncDate, TruncTime, TruncYear, TruncMonth, TruncDay\n'
        'used_by: django/db/models/functions/__init__.py → Extract, Trunc\n'
        'rules:   Trunc and Extract delegate timezone handling to the backend operations layer; '
        'verify all backend operations files when changing timezone-related logic.\n'
        '"""'
    ),
}


def strip_leading_docstrings_and_garbage(content: str) -> str:
    """Remove all leading docstrings and non-code lines."""
    lines = content.splitlines(keepends=True)
    in_doc = False
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not in_doc and (line.startswith('"""') or line.startswith("'''")):
            q = '"""' if line.startswith('"""') else "'''"
            rest = line[3:]
            in_doc = q not in rest
            i += 1
            continue
        if in_doc:
            if '"""' in lines[i] or "'''" in lines[i]:
                in_doc = False
            i += 1
            continue
        if line == "" or line.startswith("#"):
            i += 1
            continue
        if any(line.startswith(x) for x in ("import ", "from ", "class ", "def ", "@")):
            break
        i += 1
    return "".join(lines[i:])


for rel, annotation in ANNOTATIONS.items():
    fp = BASE / rel
    if not fp.exists():
        print(f"  ⚠️  not found: {fp}")
        continue
    old = fp.read_text(encoding="utf-8", errors="replace")
    clean = strip_leading_docstrings_and_garbage(old)
    fp.write_text(annotation + "\n\n" + clean, encoding="utf-8")

    check = fp.read_text(encoding="utf-8", errors="replace")[:600]
    ok = ("exports:" in check and "rules:" in check and check.count('"""') >= 2)
    print(f"  {'✅' if ok else '❌'} {rel}")

print("\nDone.")
