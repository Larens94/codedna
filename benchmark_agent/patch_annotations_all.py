"""patch_annotations_all.py — Fix cheating and truncated CodeDNA annotations across tasks 12508, 11991, 11808.

exports: none (script)
used_by: none
rules:   Annotations must be ARCHITECTURAL ONLY — no hints about the specific bug or fix.
"""
from pathlib import Path

BASE = Path(__file__).parent / "projects_swebench"

ANNOTATIONS = {
    # ── Task 12508: dbshell -c ─────────────────────────────────────────────────
    "django__django-12508/codedna/django/core/management/commands/dbshell.py": (
        '"""dbshell.py — Management command that opens an interactive database shell.\n\n'
        'exports: Command\n'
        'used_by: none\n'
        'rules:   Command delegates execution to the backend DatabaseClient; '
        'any new CLI args must be forwarded through to BaseDatabaseClient.runshell().\n'
        '"""'
    ),
    "django__django-12508/codedna/django/db/backends/base/client.py": (
        '"""client.py — BaseDatabaseClient: abstract base for database shell clients.\n\n'
        'exports: BaseDatabaseClient\n'
        'used_by: django/db/backends/mysql/client.py → BaseDatabaseClient\n'
        '         django/db/backends/oracle/client.py → BaseDatabaseClient\n'
        '         django/db/backends/postgresql/client.py → BaseDatabaseClient\n'
        '         django/db/backends/sqlite3/client.py → BaseDatabaseClient\n'
        'rules:   Subclasses must override runshell() and executable_name; '
        'all backends must handle the same interface for subprocess invocation.\n'
        '"""'
    ),
    "django__django-12508/codedna/django/db/backends/postgresql/client.py": (
        '"""client.py — PostgreSQL database shell client; wraps psql subprocess.\n\n'
        'exports: DatabaseClient\n'
        'used_by: django/db/backends/postgresql/base.py → DatabaseWrapper.client_class\n'
        'rules:   Must correctly build psql command args from Django database settings '
        'and pass them to subprocess; handle env vars for credentials.\n'
        '"""'
    ),
    "django__django-12508/codedna/django/db/backends/sqlite3/client.py": (
        '"""client.py — SQLite3 database shell client; wraps sqlite3 subprocess.\n\n'
        'exports: DatabaseClient\n'
        'used_by: django/db/backends/sqlite3/base.py → DatabaseWrapper.client_class\n'
        'rules:   Must correctly invoke the sqlite3 executable with the database file path from settings.\n'
        '"""'
    ),

    # ── Task 11991: Index INCLUDE ──────────────────────────────────────────────
    "django__django-11991/codedna/django/contrib/gis/db/backends/postgis/schema.py": (
        '"""schema.py — PostGIS schema editor; overrides DDL for geometry and spatial indexes.\n\n'
        'exports: DatabaseSchemaEditor\n'
        'used_by: django/contrib/gis/db/backends/postgis/base.py → DatabaseWrapper\n'
        'rules:   PostGIS DDL overrides must not break standard PostgreSQL DDL; '
        'spatial index creation requires geometry-aware SQL.\n'
        '"""'
    ),
    "django__django-11991/codedna/django/db/backends/base/features.py": (
        '"""features.py — BaseDatabaseFeatures: boolean capability flags for all DB backends.\n\n'
        'exports: BaseDatabaseFeatures\n'
        'used_by: django/db/backends/mysql/features.py → BaseDatabaseFeatures\n'
        '         django/db/backends/oracle/features.py → BaseDatabaseFeatures\n'
        '         django/db/backends/postgresql/features.py → BaseDatabaseFeatures\n'
        '         django/db/backends/sqlite3/features.py → BaseDatabaseFeatures\n'
        'rules:   Boolean flags control SQL feature availability; '
        'each backend overrides flags to declare its capabilities — new DDL features need a flag here first.\n'
        '"""'
    ),
    "django__django-11991/codedna/django/db/backends/base/schema.py": (
        '"""schema.py — BaseDatabaseSchemaEditor: DDL generation for all database backends.\n\n'
        'exports: BaseDatabaseSchemaEditor\n'
        'used_by: django/db/backends/postgresql/schema.py → BaseDatabaseSchemaEditor\n'
        'rules:   New DDL features must be gated by a supports_* flag in features.py; '
        'subclasses override methods for backend-specific DDL.\n'
        '"""'
    ),
    "django__django-11991/codedna/django/db/backends/postgresql/schema.py": (
        '"""schema.py — PostgreSQL schema editor; overrides DDL for PostgreSQL-specific features.\n\n'
        'exports: PostgreSQLSchemaEditor\n'
        'used_by: django/db/backends/postgresql/base.py → DatabaseWrapper\n'
        'rules:   PostgreSQL-specific DDL must check the corresponding supports_* flag in features.py '
        'before generating backend-specific SQL.\n'
        '"""'
    ),
    "django__django-11991/codedna/django/db/models/base.py": (
        '"""base.py — Django Model base class and metaclass; foundation of the ORM.\n\n'
        'exports: Model, ModelBase\n'
        'used_by: django/db/models/__init__.py → Model\n'
        'rules:   Model metaclass handles field registration, validation, and Meta options; '
        'changes here affect every ORM model in every Django project.\n'
        '"""'
    ),

    # ── Task 11808: __eq__ NotImplemented ────────────────────────────────────
    "django__django-11808/codedna/django/db/models/base.py": (
        '"""base.py — Core Model class; all Django ORM models inherit from this.\n\n'
        'exports: Model, ModelBase\n'
        'used_by: django/db/models/__init__.py → Model\n'
        'rules:   Model equality is pk-based; comparison operators must follow Python data model conventions.\n'
        '"""'
    ),
    "django__django-11808/codedna/django/db/models/constraints.py": (
        '"""constraints.py — Database constraint definitions (CheckConstraint, UniqueConstraint).\n\n'
        'exports: CheckConstraint, UniqueConstraint\n'
        'used_by: django/db/models/base.py → CheckConstraint, UniqueConstraint\n'
        'rules:   Constraint classes must be deconstructible and comparable; '
        'follow Python data model conventions for equality operators.\n'
        '"""'
    ),
    "django__django-11808/codedna/django/core/validators.py": (
        '"""validators.py — Built-in Django validators for fields and forms.\n\n'
        'exports: RegexValidator, URLValidator, EmailValidator, BaseValidator\n'
        'used_by: django/db/models/fields/__init__.py → validators\n'
        'rules:   Validators raise ValidationError on failure; '
        'must never return a value — either raise or do nothing.\n'
        '"""'
    ),
    "django__django-11808/codedna/django/db/models/expressions.py": (
        '"""expressions.py — ORM expression classes for SQL generation.\n\n'
        'exports: Combinable, BaseExpression, Expression, F, Value, Func\n'
        'used_by: django/db/models/__init__.py → F, Value, Func\n'
        'rules:   Expression subclasses must implement resolve_expression() and as_sql(); '
        'Combinable mixin enables operator overloading for expressions.\n'
        '"""'
    ),
    "django__django-11808/codedna/django/db/models/query.py": (
        '"""query.py — QuerySet and related iterable classes for ORM query evaluation.\n\n'
        'exports: QuerySet, ModelIterable, ValuesIterable, ValuesListIterable\n'
        'used_by: django/db/models/__init__.py → QuerySet\n'
        'rules:   Iterable classes define how QuerySet results are materialized; '
        'lazy evaluation must be preserved — do not trigger queries prematurely.\n'
        '"""'
    ),
}


def strip_leading_docstrings_and_garbage(content: str) -> str:
    """Remove all leading docstrings and non-code lines before first import/class/def."""
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


ok_count, fail_count = 0, 0
for rel, annotation in ANNOTATIONS.items():
    fp = BASE / rel
    if not fp.exists():
        print(f"  ⚠️  not found: {rel}")
        continue
    old = fp.read_text(encoding="utf-8", errors="replace")
    clean = strip_leading_docstrings_and_garbage(old)
    fp.write_text(annotation + "\n\n" + clean, encoding="utf-8")

    check = fp.read_text(encoding="utf-8", errors="replace")[:600]
    ok = ("exports:" in check and "rules:" in check and check.count('"""') >= 2)
    icon = "✅" if ok else "❌"
    if ok:
        ok_count += 1
    else:
        fail_count += 1
    task = rel.split("/")[0]
    short = "/".join(rel.split("/")[3:])
    print(f"  {icon} [{task}] {short}")

print(f"\nDone. {ok_count} OK, {fail_count} failed.")
