"""Manually patch 5 difficult GT files with correct CodeDNA annotations."""
from pathlib import Path

BASE = Path(__file__).parent / "projects_swebench"

ANNOTATIONS = {
    "django__django-13495/codedna/django/db/backends/mysql/operations.py": (
        '"""operations.py — MySQL-specific SQL operations overriding base DatabaseOperations.\n\n'
        'exports: DatabaseOperations\n'
        'used_by: django/db/backends/mysql/base.py → DatabaseOperations\n'
        'rules:   MySQL lacks native boolean and requires CONVERT_TZ for timezone; '
        'always check supports_timezones before generating timezone SQL.\n'
        '"""'
    ),
    "django__django-13495/codedna/django/db/backends/sqlite3/operations.py": (
        '"""operations.py — SQLite-specific SQL operations; emulates unsupported SQL features.\n\n'
        'exports: DatabaseOperations\n'
        'used_by: django/db/backends/sqlite3/base.py → DatabaseOperations\n'
        'rules:   SQLite has no native timezone support; Trunc/Extract timezone must be emulated in Python.\n'
        '"""'
    ),
    "django__django-11991/codedna/django/db/backends/base/schema.py": (
        '"""schema.py — Base schema editor for DDL generation; all backends subclass this.\n\n'
        'exports: BaseDatabaseSchemaEditor\n'
        'used_by: django/db/backends/postgresql/schema.py → BaseDatabaseSchemaEditor\n'
        'rules:   New DDL features (e.g. INCLUDE) must be gated by a supports_* flag in features.py.\n'
        '"""'
    ),
    "django__django-11808/codedna/django/db/models/base.py": (
        '"""base.py — Core Model class; all Django ORM models inherit from this.\n\n'
        'exports: Model, ModelBase\n'
        'used_by: django/db/models/__init__.py → Model\n'
        'rules:   Model.__eq__ must return NotImplemented for unknown types, never False; pk-based identity.\n'
        '"""'
    ),
    "django__django-11808/codedna/django/db/models/constraints.py": (
        '"""constraints.py — Database constraint definitions (CheckConstraint, UniqueConstraint).\n\n'
        'exports: CheckConstraint, UniqueConstraint\n'
        'used_by: django/db/models/base.py → CheckConstraint, UniqueConstraint\n'
        'rules:   __eq__ must return NotImplemented for non-Constraint types, not False.\n'
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
            in_doc = q not in rest  # still open if closing not on same line
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
        i += 1  # skip orphan garbage lines
    return "".join(lines[i:])


for rel, annotation in ANNOTATIONS.items():
    fp = BASE / rel
    if not fp.exists():
        print(f"  ⚠️  not found: {fp}")
        continue
    old = fp.read_text(encoding="utf-8", errors="replace")
    clean = strip_leading_docstrings_and_garbage(old)
    fp.write_text(annotation + "\n\n" + clean, encoding="utf-8")

    check = fp.read_text(encoding="utf-8", errors="replace")[:400]
    ok = ("exports:" in check and "rules:" in check and check.count('"""') >= 2)
    print(f"  {'✅' if ok else '❌'} {rel}")

print("\nDone.")
