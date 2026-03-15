#!/usr/bin/env python3
"""
# === CODEDNA:0.3 ==============================================
# FILE: validate_manifests.py
# PURPOSE: Validate CodeDNA manifest headers across a codebase
# CONTEXT_BUDGET: minimal
# DEPENDS_ON: none
# EXPORTS: validate_file(path) → ValidationResult
#          validate_directory(root, extensions) → list[ValidationResult]
# STYLE: none (CLI tool, stdlib only)
# DB_TABLES: none
# LAST_MODIFIED: initial implementation v0.3
# ==============================================================

CodeDNA Manifest Validator
==========================
Checks that every source file in a directory has a valid CodeDNA manifest
header with all required fields present and correctly formatted.

Usage:
    python validate_manifests.py [directory] [--extensions py js ts go rs]
    python validate_manifests.py .                    # validate current dir
    python validate_manifests.py src --extensions py  # only Python files

Exit codes:
    0 — all files valid
    1 — one or more validation errors
"""

import os
import re
import sys
import argparse
from dataclasses import dataclass, field
from typing import Optional

# Required fields in every manifest (order-insensitive)
REQUIRED_FIELDS = {"FILE", "PURPOSE", "CONTEXT_BUDGET", "DEPENDS_ON", "EXPORTS", "LAST_MODIFIED"}

# Valid CONTEXT_BUDGET values
VALID_BUDGETS = {"always", "normal", "minimal"}

# Comment prefixes by file extension
COMMENT_PREFIXES = {
    ".py": "#", ".rb": "#", ".sh": "#", ".bash": "#", ".zsh": "#",
    ".js": "//", ".ts": "//", ".jsx": "//", ".tsx": "//",
    ".go": "//", ".rs": "//", ".c": "//", ".cpp": "//", ".java": "//",
    ".sql": "--", ".lua": "--",
}

@dataclass
class ValidationResult:
    path: str
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    fields_found: dict = field(default_factory=dict)


def detect_prefix(filepath: str) -> Optional[str]:
    ext = os.path.splitext(filepath)[1].lower()
    return COMMENT_PREFIXES.get(ext)


def extract_manifest(lines: list[str], prefix: str) -> dict:
    """Extract key-value pairs from the CodeDNA manifest header."""
    in_manifest = False
    fields = {}
    # Match: "# ====" OR "# === CODEDNA:0.3 ===" OR "# === CODEDNA:0.3 ="
    delimiter_re = re.compile(
        rf"^{re.escape(prefix)}\s*(={{4,}}|===\s*CODEDNA:[^\s]+\s*=+)"
    )

    for line in lines[:30]:  # manifest must start within first 30 lines
        stripped = line.strip()
        if delimiter_re.match(stripped):
            if not in_manifest:
                in_manifest = True
                continue
            else:
                break  # closing delimiter

        if in_manifest:
            # Match "# KEY: value" or "// KEY: value" or "-- KEY: value"
            m = re.match(rf"^{re.escape(prefix)}\s+([A-Z_]+):\s*(.+)$", stripped)
            if m:
                fields[m.group(1)] = m.group(2).strip()

    return fields


def validate_file(filepath: str) -> ValidationResult:
    result = ValidationResult(path=filepath, valid=True)

    prefix = detect_prefix(filepath)
    if not prefix:
        result.warnings.append(f"Unknown extension — skipping")
        return result

    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError as e:
        result.valid = False
        result.errors.append(f"Cannot read file: {e}")
        return result

    if not lines:
        result.warnings.append("Empty file")
        return result

    # Check if manifest is present at all (first 20 lines)
    delimiter_re = re.compile(
        rf"^{re.escape(prefix)}\s*(={{4,}}|===\s*CODEDNA:[^\s]+\s*=+)"
    )
    has_manifest = any(delimiter_re.match(l.strip()) for l in lines[:20])

    if not has_manifest:
        result.valid = False
        result.errors.append("No CodeDNA manifest header found (missing delimiter ====)")
        return result

    fields = extract_manifest(lines, prefix)
    result.fields_found = fields

    # Check required fields
    for req in REQUIRED_FIELDS:
        if req not in fields:
            result.valid = False
            result.errors.append(f"Missing required field: {req}")
        elif not fields[req] or fields[req].lower() in ("", "none") and req in ("PURPOSE", "LAST_MODIFIED"):
            result.valid = False
            result.errors.append(f"Field {req} is empty or placeholder")

    # Check FILE matches actual filename
    if "FILE" in fields:
        actual = os.path.basename(filepath)
        declared = fields["FILE"]
        if declared != actual:
            result.valid = False
            result.errors.append(f"FILE mismatch: declared '{declared}', actual '{actual}'")

    # Check CONTEXT_BUDGET value
    if "CONTEXT_BUDGET" in fields:
        budget = fields["CONTEXT_BUDGET"].lower()
        if budget not in VALID_BUDGETS:
            result.valid = False
            result.errors.append(f"CONTEXT_BUDGET must be one of {VALID_BUDGETS}, got: '{budget}'")

    # Check PURPOSE length (soft warning)
    if "PURPOSE" in fields:
        words = len(fields["PURPOSE"].split())
        if words > 15:
            result.warnings.append(f"PURPOSE is {words} words (max 15 recommended)")

    # Check LAST_MODIFIED length
    if "LAST_MODIFIED" in fields:
        words = len(fields["LAST_MODIFIED"].split())
        if words > 8:
            result.warnings.append(f"LAST_MODIFIED is {words} words (max 8 recommended)")

    return result


def validate_directory(
    root: str,
    extensions: Optional[list[str]] = None,
    exclude_dirs: Optional[set[str]] = None,
) -> list[ValidationResult]:
    if extensions is None:
        extensions = list(COMMENT_PREFIXES.keys())
    if exclude_dirs is None:
        exclude_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build"}

    results = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune excluded dirs in-place
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        for fname in filenames:
            ext = os.path.splitext(fname)[1].lower()
            if ext in extensions:
                results.append(validate_file(os.path.join(dirpath, fname)))
    return results


def print_results(results: list[ValidationResult], verbose: bool = False) -> int:
    errors_total = 0
    warnings_total = 0

    valid_files = [r for r in results if r.valid and not r.errors]
    invalid_files = [r for r in results if r.errors]
    warned_files = [r for r in results if r.warnings]

    for r in invalid_files:
        print(f"\n❌  {r.path}")
        for e in r.errors:
            print(f"    ERROR: {e}")
        errors_total += len(r.errors)

    for r in warned_files:
        if verbose:
            print(f"\n⚠️   {r.path}")
            for w in r.warnings:
                print(f"    WARN: {w}")
        warnings_total += len(r.warnings)

    if verbose:
        for r in valid_files:
            print(f"✅  {r.path}")

    print(f"\n{'=' * 50}")
    print(f"Files checked:  {len(results)}")
    print(f"Valid:          {len(valid_files)}")
    print(f"With errors:    {len(invalid_files)}")
    print(f"With warnings:  {len(warned_files)}")
    print(f"{'=' * 50}")

    if errors_total == 0:
        print("✅ All CodeDNA manifests valid.")
    else:
        print(f"❌ {errors_total} error(s) found. Fix manifest headers before committing.")

    return 1 if errors_total > 0 else 0


def main():
    parser = argparse.ArgumentParser(
        description="CodeDNA Manifest Validator v0.3"
    )
    parser.add_argument("directory", nargs="?", default=".", help="Root directory to validate (default: .)")
    parser.add_argument("--extensions", nargs="+", metavar="EXT",
                        help="File extensions to check (e.g. .py .js .ts)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show valid files too")
    args = parser.parse_args()

    exts = [e if e.startswith(".") else f".{e}" for e in args.extensions] if args.extensions else None
    results = validate_directory(args.directory, extensions=exts)

    if not results:
        print("No matching files found.")
        sys.exit(0)

    sys.exit(print_results(results, verbose=args.verbose))


if __name__ == "__main__":
    main()
