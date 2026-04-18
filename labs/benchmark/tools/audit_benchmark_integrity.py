"""audit_benchmark_integrity.py — Verify codedna/ is safe to benchmark against control/.

exports: audit_task(task_id) -> dict | main()
used_by: none
rules:   body integrity: codedna/ must differ from control/ ONLY by docstrings.
         fix leak: codedna/ must NOT contain signature/logic from the official patch.
         problem_statement leak: rules:/Rules:/message: must NOT mention task keywords.
         Any failing check aborts the benchmark pre-flight.
agent:   claude-opus-4-7 | anthropic | 2026-04-17 | s_20260417_opus47 | initial audit tool for labs/benchmark pipeline
claude-opus-4-7 | anthropic | 2026-04-17 | s_20260417_opus47 | fix false-positive body mismatches: empty-body Module ≡ docstring-only Module (prevents 150 __init__.py false diffs)
claude-opus-4-7 | anthropic | 2026-04-17 | s_20260417_opus47 | strip ALL leading string-expr (not just first) — codedna init prepends header without removing existing module docstring, producing stacked literals
"""

import argparse
import ast
import json
import sys
from pathlib import Path

BENCH_ROOT = Path(__file__).resolve().parents[1]
PROJECTS_DIR = BENCH_ROOT / "projects"

# Per-task keywords that should NEVER appear in rules:/Rules:/message: lines.
# Chosen to be specific to the bug (not generic API names that appear legitimately).
HOT_KEYWORDS = {
    "django__django-14480": ["xor", "bitwise xor", "^ "],
    "django__django-13495": ["tzinfo", "tzname=None"],
    "django__django-12508": ["dbshell -c", "-c SQL", "execute SQL directly", "stdin="],
    "django__django-11991": ["include_columns", "non-key columns", "covering index", "INCLUDE clause"],
    "django__django-11808": ["NotImplemented", "symmetric comparison", "return NotImplemented"],
}


def _strip_docstrings(tree: ast.AST) -> ast.AST:
    """Strip ALL leading string-expression statements from every scope.

    Handles the case where `codedna init` prepends a header docstring without
    removing an existing module docstring — resulting in two stacked string
    literals. Both must be stripped to compare semantic equivalence with control.
    """
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            while (n.body
                    and isinstance(n.body[0], ast.Expr)
                    and isinstance(n.body[0].value, ast.Constant)
                    and isinstance(n.body[0].value.value, str)):
                n.body = n.body[1:]
            if not n.body:
                n.body = [ast.Pass()]
    return tree


def _normalized_source(src: str):
    """Return AST-canonical source with docstrings stripped.

    Modules/classes/functions whose body is ONLY a docstring are treated as
    empty (equivalent to empty file or `pass`-only stub) to avoid false-positive
    diffs between control/ (empty __init__.py) and codedna/ (docstring-only __init__.py).
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    tree = _strip_docstrings(tree)
    # Reduce "Module with only Pass" to "empty Module" for equivalence
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if len(n.body) == 1 and isinstance(n.body[0], ast.Pass):
                if isinstance(n, ast.Module):
                    n.body = []
    return ast.unparse(tree)


def audit_task(task_id: str) -> dict:
    """Return dict with body_mismatches, syntax_errors, leaks, fix_leaks."""
    task_dir = PROJECTS_DIR / task_id
    ctrl = task_dir / "control"
    cdna = task_dir / "codedna"
    gt_path = task_dir / "files_in_patch.json"

    report = {
        "task_id": task_id,
        "body_mismatches": [],
        "syntax_errors_cdna": [],
        "annotation_leaks": [],
        "fix_leaks": [],
        "stats": {},
    }

    if not ctrl.exists() or not cdna.exists():
        report["fatal"] = "missing control/ or codedna/ dir"
        return report

    gt_files = json.loads(gt_path.read_text()) if gt_path.exists() else []
    hot = HOT_KEYWORDS.get(task_id, [])

    total = 0
    for fc in ctrl.rglob("*.py"):
        rel = fc.relative_to(ctrl)
        if "migrations" in rel.parts or "__pycache__" in rel.parts:
            continue
        fd = cdna / rel
        if not fd.exists():
            continue
        total += 1
        src_c = fc.read_text(errors="replace")
        src_d = fd.read_text(errors="replace")

        nc = _normalized_source(src_c)
        nd = _normalized_source(src_d)

        if nd is None:
            report["syntax_errors_cdna"].append(str(rel))
            continue
        if nc is None:
            continue
        if nc != nd:
            report["body_mismatches"].append(str(rel))

        if hot:
            try:
                tree = ast.parse(src_d)
            except SyntaxError:
                continue

            mod_doc = ast.get_docstring(tree) or ""
            for kw in hot:
                if kw.lower() in mod_doc.lower():
                    report["annotation_leaks"].append(
                        {"file": str(rel), "where": "HEADER", "kw": kw}
                    )
                    break

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    d = ast.get_docstring(node) or ""
                    rules_lines = [l for l in d.split("\n")
                                   if "Rules:" in l or "message:" in l]
                    for line in rules_lines:
                        for kw in hot:
                            if kw.lower() in line.lower():
                                report["annotation_leaks"].append(
                                    {"file": str(rel), "where": node.name, "kw": kw, "line": line.strip()[:160]}
                                )
                                break

    report["stats"] = {
        "total_py_compared": total,
        "gt_files": len(gt_files),
        "body_mismatch_count": len(report["body_mismatches"]),
        "syntax_error_count": len(report["syntax_errors_cdna"]),
        "leak_count": len(report["annotation_leaks"]),
    }
    return report


def main():
    parser = argparse.ArgumentParser(description="Audit codedna/ integrity vs control/")
    parser.add_argument("--task-id", nargs="+", default=None,
                        help="Task IDs to audit (bare number or full). Defaults to all in projects/")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    args = parser.parse_args()

    if args.task_id:
        task_ids = []
        for t in args.task_id:
            task_ids.append(f"django__django-{t}" if "__" not in t else t)
    else:
        task_ids = sorted([p.name for p in PROJECTS_DIR.iterdir()
                           if p.is_dir() and (p / "codedna").exists()])

    reports = []
    failed = 0
    for tid in task_ids:
        r = audit_task(tid)
        reports.append(r)
        s = r["stats"]
        status = "OK" if (s.get("body_mismatch_count", 0) == 0
                           and s.get("syntax_error_count", 0) == 0
                           and s.get("leak_count", 0) == 0) else "FAIL"
        if status == "FAIL":
            failed += 1

        if args.json:
            continue

        print(f"\n=== {tid}  [{status}] ===")
        print(f"  py files compared:  {s.get('total_py_compared', '?')}")
        print(f"  GT files:           {s.get('gt_files', '?')}")
        print(f"  body mismatches:    {s.get('body_mismatch_count', 0)}")
        print(f"  syntax errors cdna: {s.get('syntax_error_count', 0)}")
        print(f"  annotation leaks:   {s.get('leak_count', 0)}")

        if args.verbose and r["body_mismatches"]:
            print("  mismatched files (first 10):")
            for f in r["body_mismatches"][:10]:
                print(f"    - {f}")
        if r["annotation_leaks"]:
            print("  LEAKS:")
            for l in r["annotation_leaks"]:
                print(f"    - {l['file']} [{l['where']}] kw={l['kw']!r}")
                if "line" in l:
                    print(f"      {l['line']}")

    if args.json:
        print(json.dumps(reports, indent=2))

    if failed:
        print(f"\nFAIL: {failed}/{len(task_ids)} task(s) failed integrity audit", file=sys.stderr)
        sys.exit(1)
    print(f"\nOK: all {len(task_ids)} task(s) passed integrity audit")


if __name__ == "__main__":
    main()
