#!/usr/bin/env python3
"""validate_manifests.py — Validate CodeDNA v0.8 annotations across a codebase.

exports: validate_file(path) -> ValidationResult
         validate_directory(root, extensions) -> list[ValidationResult]
used_by: none — standalone CLI tool
rules:   validates v0.8 format only (exports:/used_by:/rules:/agent: in module docstring).
         Python uses AST; other languages use regex on first 40 lines.
         read-only — never modifies files.
agent:   claude-haiku-4-5-20251001 | anthropic | 2026-03-27 | s_20260327_001 | rewritten from v0.3 to v0.8
         claude-opus-4-6 | anthropic | 2026-04-01 | s_20260401_001 | added template engine extensions to COMMENT_PREFIX, added _get_ext for .blade.php, fixed validate_directory to use _get_ext, added _INNER_PREFIXES for block-comment parsing
         claude-sonnet-4-6 | anthropic | 2026-04-02 | s_20260402_001 | fixed _extract_python: return (None, {}) instead of (None, None) for valid Python without docstring, so validate_file shows "No module docstring found" instead of "Cannot parse file"
         claude-sonnet-4-6 | anthropic | 2026-04-02 | s_20260402_001 | added .volt to COMMENT_PREFIX for Phalcon Volt template validation

Usage:
    python tools/validate_manifests.py [path] [-v] [--extensions py ts go]
    python tools/validate_manifests.py .             # validate current dir (Python only)
    python tools/validate_manifests.py src/myapp -v  # verbose: show valid files too
    python tools/validate_manifests.py myfile.py     # single file

Exit codes:
    0 — all files valid
    1 — one or more validation errors
"""

import argparse
import ast
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

REQUIRED_FIELDS = {"exports", "used_by", "rules", "agent"}

SKIP_DIRS = {"__pycache__", ".git", "venv", ".venv", "node_modules", "dist", "build", "migrations"}

# Comment style by extension (for non-Python languages)
COMMENT_PREFIX = {
    ".js": "//", ".ts": "//", ".jsx": "//", ".tsx": "//",
    ".go": "//", ".rs": "//", ".java": "//", ".kt": "//", ".swift": "//",
    ".rb": "#", ".sh": "#",
    # Template engines — use block comment openers as prefix for field detection
    ".blade.php": "{{--", ".j2": "{#", ".jinja2": "{#", ".twig": "{#", ".volt": "{#",
    ".erb": "<%#", ".ejs": "<%#",
    ".hbs": "{{!--", ".mustache": "{{!--",
    ".cshtml": "@*", ".razor": "@*",
    ".vue": "<!--", ".svelte": "<!--",
}

# agent: line format: "model | provider | YYYY-MM-DD | ..."  or  "model | YYYY-MM-DD | ..."
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_PURPOSE_MAX_WORDS = 15
_AGENT_MAX_ENTRIES = 5


@dataclass
class ValidationResult:
    path: str
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    fields_found: set[str] = field(default_factory=set)

    def err(self, msg: str) -> None:
        self.valid = False
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


# ── Field extraction ──────────────────────────────────────────────────────────


def _parse_fields(text: str) -> dict[str, str]:
    """Parse CodeDNA fields from a docstring or comment block."""
    result: dict[str, str] = {}
    current: Optional[str] = None
    for line in text.split("\n"):
        s = line.strip()
        matched = False
        for key in REQUIRED_FIELDS:
            if s.startswith(f"{key}:"):
                current = key
                result[key] = s[len(key) + 1:].strip()
                matched = True
                break
        if not matched and current and s and not any(s.startswith(k + ":") for k in REQUIRED_FIELDS):
            result[current] = result[current] + " " + s
    return result


def _extract_python(path: Path) -> tuple[Optional[str], Optional[dict[str, str]]]:
    """Return (first_line_of_docstring, fields) using AST. Returns (None, None) on failure."""
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return None, None

    docstring = ast.get_docstring(tree)
    if not docstring:
        return None, {}  # valid Python, but no module docstring

    first_line = docstring.strip().split("\n")[0].strip()
    fields = _parse_fields(docstring)
    return first_line, fields


def _extract_other(path: Path, prefix: str) -> tuple[Optional[str], Optional[dict[str, str]]]:
    """Extract CodeDNA fields from a non-Python file using comment block regex."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[:40]
    except OSError:
        return None, None

    # For block-comment languages, inner lines may use a shorter prefix
    # e.g. {{-- ... --}} block uses "-- " for inner lines, {# #} uses "#", <!-- uses "  "
    _INNER_PREFIXES = {
        "{{--": ("{{--", "--"),
        "{#": ("{#", "#"),
        "<%#": ("<%#", "#"),
        "{{!--": ("{{!--",),
        "@*": ("@*", "*"),
        "<!--": ("<!--", "--"),
    }
    prefixes_to_check = _INNER_PREFIXES.get(prefix, (prefix,))

    # Look for a block like:  // exports: ...
    block_lines = []
    in_block = False
    for line in lines:
        s = line.strip()
        # Try to strip any known prefix from the line
        content = None
        for p in prefixes_to_check:
            if s.startswith(p):
                content = s[len(p):].strip()
                break
        if content is None:
            # Also try bare field lines (indented inside block comments)
            if any(s.startswith(k + ":") for k in REQUIRED_FIELDS):
                content = s
            elif in_block and s and not any(s.startswith(end) for end in ("-->", "--}}", "#}", "%>", "*@")):
                content = s
        if content is not None and any(content.startswith(k + ":") for k in REQUIRED_FIELDS):
            in_block = True
        if in_block:
            if content is not None:
                block_lines.append(content)
            elif block_lines:
                break

    if not block_lines:
        return None, None

    text = "\n".join(block_lines)
    fields = _parse_fields(text)
    return None, fields  # no purpose line for non-Python


# ── Validation rules ──────────────────────────────────────────────────────────


def _validate_purpose(result: ValidationResult, first_line: str, filename: str) -> None:
    """Rules: first line must be 'filename.py — <purpose ≤15 words>'."""
    if " — " not in first_line:
        result.err(f"First docstring line missing ' — ' separator: {first_line!r}")
        return

    declared_name, purpose = first_line.split(" — ", 1)
    # CLI writes the repo-relative path (e.g. "orders/models.py"); accept both forms
    if Path(declared_name.strip()).name != filename:
        result.warn(f"Filename mismatch in docstring: declared '{declared_name.strip()}', actual '{filename}'")

    word_count = len(purpose.strip().split())
    if word_count > _PURPOSE_MAX_WORDS:
        result.warn(f"Purpose is {word_count} words (max {_PURPOSE_MAX_WORDS} recommended)")


def _validate_agent(result: ValidationResult, agent_text: str) -> None:
    """Rules: each agent: line must have model | date | description (≥3 pipe parts, date in YYYY-MM-DD)."""
    entries = [l.strip() for l in agent_text.split("\n") if l.strip() and not l.strip().startswith("message:")]
    if not entries:
        result.err("agent: field is empty — must have at least one entry")
        return

    if len(entries) > _AGENT_MAX_ENTRIES:
        result.warn(f"agent: has {len(entries)} entries (rolling window is {_AGENT_MAX_ENTRIES} — oldest should be dropped)")

    for entry in entries:
        parts = [p.strip() for p in entry.split("|")]
        if len(parts) < 3:
            result.err(f"agent: entry has fewer than 3 pipe-separated parts: {entry!r}")
            continue
        # Date is either parts[1] (model|date|desc) or parts[2] (model|provider|date|desc)
        date_candidate = parts[2] if len(parts) >= 4 and _DATE_RE.match(parts[2].strip()) else parts[1]
        if not _DATE_RE.match(date_candidate.strip()):
            result.err(f"agent: entry missing YYYY-MM-DD date: {entry!r}")


def _validate_fields(result: ValidationResult, fields: dict[str, str]) -> None:
    """Check all required fields are present and non-empty."""
    for key in REQUIRED_FIELDS:
        if key not in fields:
            result.err(f"Missing required field: {key}:")
        else:
            val = fields[key].strip()
            if not val:
                result.err(f"Field '{key}:' is present but empty")

    if "exports" in fields and fields["exports"].strip() == "none":
        result.warn("exports: is 'none' — expected if file has no public API, but verify")

    if "used_by" in fields and fields["used_by"].strip() == "none":
        result.warn("used_by: is 'none' — verify no other file imports from this one")

    if "rules" in fields and fields["rules"].strip() == "none":
        result.warn("rules: is 'none' — consider adding architectural constraints")

    if "agent" in fields:
        _validate_agent(result, fields["agent"])


# ── Public API ────────────────────────────────────────────────────────────────


def _get_ext(path: Path) -> str:
    """Return file extension, handling compound extensions like .blade.php."""
    name = path.name.lower()
    if name.endswith(".blade.php"):
        return ".blade.php"
    return path.suffix.lower()


def validate_file(path: Path) -> ValidationResult:
    result = ValidationResult(path=str(path))
    ext = _get_ext(path)

    if ext == ".py":
        first_line, fields = _extract_python(path)
        if fields is None:
            result.err("Cannot parse file (SyntaxError or unreadable)")
            return result
        if not fields and first_line is None:
            result.err("No module docstring found — add a CodeDNA v0.8 header")
            return result
        if first_line:
            _validate_purpose(result, first_line, path.name)
        else:
            result.err("Module docstring is empty")
            return result

    elif ext in COMMENT_PREFIX:
        _, fields = _extract_other(path, COMMENT_PREFIX[ext])
        if fields is None:
            result.warn(f"No CodeDNA comment block found in {ext} file — skipping")
            return result
    else:
        result.warn(f"Extension {ext!r} not supported — skipping")
        return result

    result.fields_found = set(fields.keys())
    _validate_fields(result, fields)
    return result


def validate_directory(
    root: Path,
    extensions: Optional[list[str]] = None,
) -> list[ValidationResult]:
    if extensions is None:
        extensions = [".py"]

    results = []
    for f in sorted(root.rglob("*")):
        if not f.is_file():
            continue
        if any(part in SKIP_DIRS for part in f.parts):
            continue
        if _get_ext(f) in extensions:
            results.append(validate_file(f))
    return results


# ── Output ────────────────────────────────────────────────────────────────────


def print_results(results: list[ValidationResult], verbose: bool) -> int:
    invalid = [r for r in results if r.errors]
    warned  = [r for r in results if r.warnings and not r.errors]
    valid   = [r for r in results if not r.errors and not r.warnings]

    for r in invalid:
        print(f"\nFAIL  {r.path}")
        for e in r.errors:
            print(f"      error:   {e}")
        for w in r.warnings:
            print(f"      warning: {w}")

    for r in warned:
        if verbose:
            print(f"\nWARN  {r.path}")
            for w in r.warnings:
                print(f"      warning: {w}")

    if verbose:
        for r in valid:
            print(f"OK    {r.path}")

    print()
    print("=" * 50)
    print(f"Files checked : {len(results)}")
    print(f"Valid         : {len(valid)}")
    print(f"Warnings only : {len(warned)}")
    print(f"Errors        : {len(invalid)}")
    print("=" * 50)

    if not invalid:
        print("All CodeDNA v0.8 annotations valid.")
    else:
        print(f"{len(invalid)} file(s) failed. Run `codedna init` to annotate missing files.")

    return 1 if invalid else 0


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> int:
    p = argparse.ArgumentParser(
        prog="validate_manifests",
        description="Validate CodeDNA v0.8 annotations",
    )
    p.add_argument("path", nargs="?", default=".", type=Path, help="File or directory to validate (default: .)")
    p.add_argument("--extensions", nargs="+", metavar="EXT",
                   help="Extensions to check, e.g. .py .ts .go (default: .py)")
    p.add_argument("-v", "--verbose", action="store_true", help="Show valid and warned files")
    args = p.parse_args()

    target = args.path.resolve()
    if not target.exists():
        print(f"Error: {target} does not exist", file=sys.stderr)
        return 1

    exts = None
    if args.extensions:
        exts = [e if e.startswith(".") else f".{e}" for e in args.extensions]

    if target.is_file():
        results = [validate_file(target)]
    else:
        results = validate_directory(target, extensions=exts)

    if not results:
        print("No matching files found.")
        return 0

    return print_results(results, verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
