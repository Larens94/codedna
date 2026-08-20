"""audit.py — Verify CodeDNA drift, impact, and installation health without writes.

exports: class AuditIssue | verify_repository(root, extensions, exclude) | impact_report(root, query, extensions, exclude) | doctor_report(root)
used_by: codedna_tool/cli.py → doctor_report, impact_report, verify_repository
         tests/test_audit.py → doctor_report, impact_report, verify_repository
related: codedna_tool/cli.py — owns structural scanners and adapter registry
rules:   Audit commands are strictly read-only and return structured data before rendering.
Error severities determine exit codes; warnings never silently become errors.
agent:   gpt-5 | openai | 2026-08-20 | s_20260820_audit | implement structural verification, impact traversal, and installation diagnostics
message: "Semantic rule truth is intentionally out of scope until evidence/schema exists."
"""

from __future__ import annotations

import ast
import importlib.util
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class AuditIssue:
    """One evidence-backed audit finding.

    Rules:   code is stable for automation; evidence explains observed versus expected state.
    """

    severity: str
    code: str
    path: str
    evidence: str

    def to_dict(self) -> dict[str, str]:
        """Return a JSON-serializable issue.

        Rules:   Field names are a public CLI contract and must remain stable.
        """
        return asdict(self)


def _project_root(target: Path) -> Path:
    """Find the repository boundary used to resolve cross-directory callers."""
    start = target if target.is_dir() else target.parent
    for candidate in (start, *start.parents):
        if (candidate / ".codedna").exists() or (candidate / ".git").exists():
            return candidate
    return start


def _scan_repository(root: Path, extensions: Optional[list[str]], exclude: list[str]):
    from codedna_tool.cli import (
        _auto_detect_extensions,
        _normalize_extensions,
        build_used_by,
        collect_files,
        _read_codedna_excludes,
        scan_file,
        scan_file_lang,
    )
    from codedna_tool.languages import get_adapter

    project_root = _project_root(root)
    # Rules: repository exclusions apply even when an agent verifies a subdirectory.
    effective_exclude = list(dict.fromkeys([*exclude, *_read_codedna_excludes(project_root)]))
    normalized = _normalize_extensions(extensions) if extensions else _auto_detect_extensions(project_root)
    infos = {}
    for extension in normalized:
        for path in collect_files(project_root, effective_exclude, extensions=[extension]):
            if extension == ".py":
                info = scan_file(path, project_root)
            else:
                adapter = get_adapter(extension)
                if adapter is None:
                    continue
                info = scan_file_lang(path, project_root, adapter)
            if info.parseable:
                infos[info.rel] = info
    used_by = build_used_by(infos)
    # Rules: packages may use their own source root (for example `from models import`).
    # Resolve those graph keys only when the repo-relative suffix match is unambiguous.
    for dependency in list(used_by):
        if dependency in infos:
            continue
        matches = [rel for rel in infos if rel.endswith("/" + dependency)]
        if len(matches) == 1:
            target = matches[0]
            for caller, symbols in used_by.pop(dependency).items():
                used_by.setdefault(target, {})[caller] = symbols
    selected = {
        rel for rel, info in infos.items()
        if info.path == root or (root.is_dir() and root in info.path.parents)
    }
    return infos, used_by, normalized, selected


def _declared_fields(info, extension: str) -> dict[str, str]:
    from codedna_tool.cli import _parse_existing_docstring, _parse_lang_header
    from codedna_tool.languages import get_adapter

    if extension == ".py":
        return _parse_existing_docstring(info.docstring or "")
    adapter = get_adapter(extension)
    if adapter is None:
        return {}
    source = info.path.read_text(encoding="utf-8", errors="replace")
    return _parse_lang_header(source, adapter.comment_prefix) or {}


def _value(fields: dict[str, str], name: str) -> str:
    raw = fields.get(name, "")
    prefix = name + ":"
    return raw[len(prefix):].strip() if raw.startswith(prefix) else raw.strip()


def _declared_export_names(value: str) -> set[str]:
    names = set()
    for item in value.split("|"):
        token = item.strip()
        if not token or token == "none" or token.startswith("(+"):
            continue
        token = re.sub(r"^class\s+", "", token)
        token = token.split("(", 1)[0].split(":", 1)[0].strip()
        names.add(token.replace("::", "."))
    return names


def _python_symbols(path: Path) -> tuple[set[str], set[str]]:
    """Return every resolvable symbol and required public module exports."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    all_names: set[str] = set()
    public_names: set[str] = set()
    def visit_statements(nodes: list[ast.stmt]) -> None:
        """Inspect module control flow without treating nested locals as exports."""
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                all_names.add(node.name)
                if not node.name.startswith("_"):
                    public_names.add(node.name)
                if isinstance(node, ast.ClassDef):
                    for child in node.body:
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            all_names.add(f"{node.name}.{child.name}")
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name):
                        all_names.add(target.id)
                        if target.id.isupper() and not target.id.startswith("_"):
                            public_names.add(target.id)
            elif isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With,
                                   ast.AsyncWith, ast.Try)):
                visit_statements(node.body)
                visit_statements(node.orelse)
                if isinstance(node, ast.Try):
                    for handler in node.handlers:
                        visit_statements(handler.body)
                    visit_statements(node.finalbody)

    visit_statements(tree.body)
    return all_names, public_names


def _declared_caller_paths(value: str) -> set[str]:
    paths = set()
    for line in value.splitlines():
        caller = line.split("→", 1)[0].replace("[cascade]", "").strip()
        if caller and not caller.startswith("none"):
            paths.add(caller)
    return paths


def _resolve_declared_callers(declared: set[str], actual: set[str]) -> set[str]:
    """Resolve headers generated from a package subroot against repo-relative paths."""
    resolved = set()
    for caller in declared:
        suffix_matches = [path for path in actual if path == caller or path.endswith("/" + caller)]
        resolved.add(suffix_matches[0] if len(suffix_matches) == 1 else caller)
    return resolved


def _python_caller_imports(caller: Path, target_rel: str) -> bool:
    """Confirm a package-root-relative import when the global scanner cannot resolve it."""
    target_module = target_rel.removesuffix("/__init__.py").removesuffix(".py")
    tree = ast.parse(caller.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported = node.module.replace(".", "/")
            if target_module == imported or target_module.endswith("/" + imported):
                return True
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported = alias.name.replace(".", "/")
                if target_module == imported or target_module.endswith("/" + imported):
                    return True
    return False


def verify_repository(root: Path, extensions: Optional[list[str]] = None,
                      exclude: Optional[list[str]] = None) -> dict[str, Any]:
    """Compare declared structural fields with current source structure.

    Rules:   Verify exports and used_by only; never claim semantic rules are true.
             Every failure includes current and expected evidence and performs no writes.
    """
    from codedna_tool.cli import _get_extension

    infos, used_by, normalized, selected = _scan_repository(root, extensions, exclude or [])
    issues: list[AuditIssue] = []
    files_checked = 0
    for rel in sorted(selected):
        info = infos[rel]
        extension = _get_extension(info.path)
        # Rules: coverage belongs to `codedna check`; verify only audits existing CodeDNA headers.
        if not info.has_codedna:
            continue
        files_checked += 1
        fields = _declared_fields(info, extension)
        if not fields:
            issues.append(AuditIssue("error", "missing_header", rel, "No CodeDNA L1 header found"))
            continue
        declared_exports = _value(fields, "exports")
        declared_used_by = _value(fields, "used_by")
        declared_names = _declared_export_names(declared_exports)
        capped = "(+" in declared_exports
        if extension == ".py":
            actual_names, required_names = _python_symbols(info.path)
            stale = declared_names - actual_names
            missing = set() if capped else required_names - declared_names
        else:
            actual_names = _declared_export_names(" | ".join(info.exports))
            stale = declared_names - actual_names
            missing = actual_names - declared_names
        if stale or missing:
            issues.append(AuditIssue(
                "error", "export_drift", rel,
                f"stale={sorted(stale)!r}; missing={sorted(missing)!r}",
            ))
        actual_callers = set(used_by.get(rel, {}))
        raw_declared_callers = _declared_caller_paths(declared_used_by)
        for caller in raw_declared_callers - actual_callers:
            matches = [candidate for candidate in infos
                       if candidate == caller or candidate.endswith("/" + caller)]
            if len(matches) == 1 and _get_extension(infos[matches[0]].path) == ".py":
                if _python_caller_imports(infos[matches[0]].path, rel):
                    actual_callers.add(matches[0])
        declared_callers = _resolve_declared_callers(
            raw_declared_callers, actual_callers,
        )
        stale_callers = declared_callers - actual_callers
        missing_callers = actual_callers - declared_callers
        if stale_callers or missing_callers:
            issues.append(AuditIssue(
                "error", "used_by_drift", rel,
                f"stale={sorted(stale_callers)!r}; missing={sorted(missing_callers)!r}",
            ))
    return {
        "command": "verify",
        "root": str(root),
        "extensions": normalized,
        "files_checked": files_checked,
        "issues": [issue.to_dict() for issue in issues],
        "ok": not issues,
    }


def impact_report(root: Path, query: str, extensions: Optional[list[str]] = None,
                  exclude: Optional[list[str]] = None) -> dict[str, Any]:
    """Return transitive dependants and rules for a file or exported symbol.

    Rules:   Query matches an exact repo-relative path first, then exported symbol text.
             Traverse used_by breadth-first and never report the same file twice.
    """
    from codedna_tool.cli import _get_extension

    infos, used_by, normalized, _selected = _scan_repository(root, extensions, exclude or [])
    roots = [query] if query in infos else [
        rel for rel, info in infos.items()
        if any(query == export or query in export for export in info.exports)
    ]
    roots = sorted(set(roots))
    queue = list(roots)
    seen = set(roots)
    dependants: list[dict[str, Any]] = []
    while queue:
        current = queue.pop(0)
        for caller, symbols in sorted(used_by.get(current, {}).items()):
            if caller in seen:
                continue
            seen.add(caller)
            queue.append(caller)
            dependants.append({"path": caller, "via": current, "symbols": symbols})
    rules = {}
    for rel in roots:
        fields = _declared_fields(infos[rel], _get_extension(infos[rel].path))
        rules[rel] = _value(fields, "rules") or "none"
    return {
        "command": "impact",
        "root": str(root),
        "query": query,
        "extensions": normalized,
        "matches": roots,
        "rules": rules,
        "dependants": dependants,
        "ok": bool(roots),
    }


def doctor_report(root: Path) -> dict[str, Any]:
    """Inspect local CodeDNA installation and advertised runtime capabilities.

    Rules:   Missing manifest or core adapter dependency is an error; optional hooks and
             CI integration are warnings because CodeDNA can operate without them.
    """
    from codedna_tool.languages import SUPPORTED_EXTENSIONS

    checks: list[dict[str, str]] = []

    def add(status: str, code: str, evidence: str) -> None:
        checks.append({"status": status, "code": code, "evidence": evidence})

    manifest = root / ".codedna"
    add("ok" if manifest.exists() else "error", "manifest",
        str(manifest) if manifest.exists() else ".codedna is missing")
    required_modules = (
        "tree_sitter", "tree_sitter_typescript", "tree_sitter_go", "tree_sitter_php",
        "tree_sitter_java", "tree_sitter_rust", "tree_sitter_c_sharp",
        "tree_sitter_ruby", "tree_sitter_kotlin",
    )
    missing = [name for name in required_modules if importlib.util.find_spec(name) is None]
    add("error" if missing else "ok", "adapter_dependencies",
        "missing: " + ", ".join(missing) if missing else f"{len(SUPPORTED_EXTENSIONS)} extensions registered")
    hook = root / ".git" / "hooks" / "pre-commit"
    add("ok" if hook.exists() else "warning", "pre_commit_hook",
        str(hook) if hook.exists() else "optional pre-commit hook is not installed")
    workflow = root / ".github" / "workflows" / "ci.yml"
    add("ok" if workflow.exists() else "warning", "ci",
        str(workflow) if workflow.exists() else "no .github/workflows/ci.yml found")
    gitignore = root / ".gitignore"
    ignored = gitignore.exists() and ".codedna.lock" in gitignore.read_text(encoding="utf-8", errors="replace")
    add("ok" if ignored else "warning", "lock_ignore",
        ".codedna.lock ignored" if ignored else "add .codedna.lock to .gitignore")
    return {
        "command": "doctor",
        "root": str(root),
        "checks": checks,
        "ok": not any(check["status"] == "error" for check in checks),
    }
