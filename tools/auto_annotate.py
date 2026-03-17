#!/usr/bin/env python3
"""
tools/auto_annotate.py — Automatically annotate a Python codebase with CodeDNA v0.7 headers.

Uses AST to extract exports and compute used_by (inverse dependency graph),
then injects CodeDNA module docstrings into every .py file.

Usage:
    python tools/auto_annotate.py /path/to/repo                    # annotate all files
    python tools/auto_annotate.py /path/to/repo --init             # also generate .codedna manifest
    python tools/auto_annotate.py /path/to/repo --dry-run          # preview only
    python tools/auto_annotate.py /path/to/repo --dry-run --limit 5  # preview 5 files
    python tools/auto_annotate.py /path/to/repo --package django   # only annotate django/
"""

import argparse
import ast
import sys
from pathlib import Path


# ── Pass 1: Scan all files ──────────────────────────────────────────────────

def module_path_to_file(module_path: str, repo_root: Path) -> Path | None:
    """Convert a dotted module path to a file path.
    
    Tries module/path.py first, then module/path/__init__.py.
    """
    parts = module_path.replace(".", "/")
    candidate = repo_root / f"{parts}.py"
    if candidate.exists():
        return candidate
    candidate = repo_root / parts / "__init__.py"
    if candidate.exists():
        return candidate
    return None


def extract_file_info(py_file: Path, repo_root: Path) -> dict:
    """Extract deps, exports, and existing docstring from a Python file."""
    try:
        source = py_file.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return {"deps": {}, "exports": [], "docstring": None, "parseable": False}

    # Extract imports (deps) — only internal to repo
    deps = {}  # {relative_file_path: [imported_symbols]}
    top_package = None  # detect the top-level package from file path
    rel = py_file.relative_to(repo_root)
    if len(rel.parts) > 0:
        top_package = rel.parts[0]

    def _add_dep(module, names):
        """Register a dependency on module with imported names."""
        if not (module and top_package and module.startswith(top_package + ".")):
            return
        dep_file = module_path_to_file(module, repo_root)
        if dep_file:
            dep_rel = str(dep_file.relative_to(repo_root))
            if dep_rel not in deps:
                deps[dep_rel] = []
            if names:
                deps[dep_rel].extend(names)
        else:
            mod_as_path = module.replace(".", "/") + ".py"
            if mod_as_path not in deps:
                deps[mod_as_path] = []
            if names:
                deps[mod_as_path].extend(names)

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            names = [a.name for a in node.names if a.name != "*"]
            if not names and node.names:
                names = ["*"]
            _add_dep(node.module, names)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                _add_dep(alias.name, [])

    # Deduplicate symbol lists
    for k in deps:
        deps[k] = sorted(set(deps[k]))

    # Extract exports (public top-level classes and functions)
    exports = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            exports.append(f"class {node.name}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                args = []
                for a in node.args.args:
                    if a.arg != "self" and a.arg != "cls":
                        args.append(a.arg)
                sig = f"{node.name}({', '.join(args)})"
                exports.append(sig)
        elif isinstance(node, ast.Assign):
            # Top-level constants like AND = "AND"
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    exports.append(target.id)

    # Existing docstring
    docstring = ast.get_docstring(tree)

    return {
        "deps": deps,
        "exports": exports,
        "docstring": docstring,
        "parseable": True,
    }


# ── Pass 2: Compute used_by ────────────────────────────────────────────────

def compute_used_by(file_infos: dict) -> dict:
    """Invert the deps graph: for each file, find who imports it.
    
    Returns: {file_path: {importer_path: [symbols_imported]}}
    """
    used_by = {}
    for file_path, info in file_infos.items():
        for dep, symbols in info["deps"].items():
            if dep not in used_by:
                used_by[dep] = {}
            used_by[dep][file_path] = symbols
    return used_by


# ── Pass 3: Generate CodeDNA headers ───────────────────────────────────────

def generate_purpose(rel_path: str, existing_docstring: str | None) -> str:
    """Generate a one-line purpose description."""
    if existing_docstring:
        # Use first line of existing docstring
        first_line = existing_docstring.strip().split("\n")[0].strip()
        # Strip all existing CodeDNA path prefixes: "a/b.py — c/d.py — purpose" → "purpose"
        while " — " in first_line:
            after = first_line.split(" — ", 1)[1].strip()
            if after:
                first_line = after
            else:
                break
        # Skip if it looks like a file path (e.g. leftover "django/apps/registry.py")
        if "/" in first_line and first_line.endswith(".py"):
            first_line = ""
        # Skip if it's a CodeDNA field line (exports:, used_by:, etc.)
        if first_line.startswith(("exports:", "used_by:", "deps:", "rules:")):
            first_line = ""
        # Clean up
        first_line = first_line.rstrip(".")
        if first_line and len(first_line) > 80:
            first_line = first_line[:77] + "..."
        if first_line:
            return first_line
    
    # Generate from filename
    name = Path(rel_path).stem
    parent = Path(rel_path).parent.name
    if name == "__init__":
        return f"Package init for {parent}"
    return f"{name} module"


def format_exports(exports: list) -> str:
    """Format exports list into CodeDNA exports: line."""
    if not exports:
        return "none"
    return " | ".join(exports)


def format_used_by(used_by_entries: dict) -> str:
    """Format used_by dict into CodeDNA used_by: line(s)."""
    if not used_by_entries:
        return "none"
    
    lines = []
    for importer, symbols in sorted(used_by_entries.items()):
        if symbols:
            sym_str = ", ".join(symbols)
            lines.append(f"{importer} → {sym_str}")
        else:
            lines.append(importer)
    
    return lines[0] if len(lines) == 1 else "\n         ".join(lines)


def generate_header(rel_path: str, info: dict, used_by_entries: dict) -> str:
    """Generate a CodeDNA v0.7 module docstring (exports + used_by + rules)."""
    purpose = generate_purpose(rel_path, info.get("docstring"))
    exports_str = format_exports(info["exports"])
    used_by_str = format_used_by(used_by_entries)

    header = f'"""{rel_path} — {purpose}.\n\n'
    header += f"exports: {exports_str}\n"
    header += f"used_by: {used_by_str}\n"
    header += f"rules:   none\n"
    header += '"""\n'
    
    return header


# ── .codedna manifest generation ──────────────────────────────────────────

def generate_codedna_manifest(repo_root: Path, file_infos: dict, package: str | None = None) -> str:
    """Generate a .codedna YAML manifest describing the project structure."""
    lines = ["# .codedna — Project structure manifest (auto-generated by codedna init)"]
    
    # Detect project name from directory
    project_name = package or repo_root.name
    lines.append(f"project: {project_name}")
    lines.append("")
    lines.append("packages:")
    
    # Group files by package directory (parent dir of the file)
    packages = {}  # {package_path: {purpose, files, deps_on}}
    
    for rel_path, info in sorted(file_infos.items()):
        parts = Path(rel_path).parts
        if len(parts) < 2:
            continue
        
        # Get package path: use directory containing the file (2 levels deep for subpackages)
        parent = str(Path(rel_path).parent)
        if package:
            # Within the --package scope, group at 2nd level (e.g. django/apps, django/contrib/admin)
            if len(parts) >= 4:
                pkg_path = "/".join(parts[:3])  # e.g. django/contrib/admin
            elif len(parts) >= 3:
                pkg_path = "/".join(parts[:2])   # e.g. django/apps
            else:
                pkg_path = parts[0]              # e.g. django (root-level files)
        else:
            pkg_path = parts[0]
        
        if pkg_path not in packages:
            packages[pkg_path] = {"purpose": None, "files": [], "deps_on": set()}
        
        packages[pkg_path]["files"].append(rel_path)
        
        # Extract purpose from __init__.py docstring
        if parts[-1] == "__init__.py" and info.get("docstring"):
            existing = packages[pkg_path]["purpose"]
            if not existing or len(info["docstring"]) > len(existing):
                purpose = generate_purpose(rel_path, info["docstring"])
                packages[pkg_path]["purpose"] = purpose
        
        # Track inter-package dependencies
        for dep_file in info.get("deps", {}):
            dep_parts = Path(dep_file).parts
            if package:
                if len(dep_parts) >= 4:
                    dep_pkg = "/".join(dep_parts[:3])
                elif len(dep_parts) >= 3:
                    dep_pkg = "/".join(dep_parts[:2])
                else:
                    dep_pkg = dep_parts[0] if dep_parts else ""
            else:
                dep_pkg = dep_parts[0] if dep_parts else ""
            if dep_pkg and dep_pkg != pkg_path:
                packages[pkg_path]["deps_on"].add(dep_pkg)
    
    for pkg_path in sorted(packages):
        pkg = packages[pkg_path]
        lines.append(f"  {pkg_path}/:")
        if pkg["purpose"]:
            lines.append(f'    purpose: "{pkg["purpose"]}"')
        else:
            lines.append(f'    purpose: "{Path(pkg_path).name} package"')
        
        if pkg["deps_on"]:
            deps_list = ", ".join(sorted(pkg["deps_on"])[:10])
            lines.append(f"    depends_on: [{deps_list}]")
        
        lines.append("")
    
    return "\n".join(lines) + "\n"


# ── Pass 4: Inject headers ─────────────────────────────────────────────────

def inject_header(py_file: Path, header: str, dry_run: bool = False) -> bool:
    """Replace or insert the module docstring with the CodeDNA header.
    
    Returns True if the file was modified.
    """
    try:
        source = py_file.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False

    lines = source.split("\n")

    # Find where the existing docstring is (if any)
    start_line = 0
    
    # Skip shebang
    if lines and lines[0].startswith("#!"):
        start_line = 1
    # Skip encoding declaration  
    if start_line < len(lines) and lines[start_line].startswith("# -*-"):
        start_line += 1

    # Skip blank lines after shebang/encoding
    while start_line < len(lines) and lines[start_line].strip() == "":
        start_line += 1

    # Check if there's an existing docstring at start_line
    end_line = None
    if start_line < len(lines):
        line = lines[start_line].strip()
        if line.startswith('"""') or line.startswith("'''"):
            quote = line[:3]
            if line.count(quote) >= 2 and len(line) > 6:
                # Single-line docstring: """..."""
                end_line = start_line
            else:
                # Multi-line docstring: find closing quotes
                for i in range(start_line + 1, len(lines)):
                    if quote in lines[i]:
                        end_line = i
                        break

    if end_line is not None:
        # Replace existing docstring
        before = "\n".join(lines[:start_line])
        after = "\n".join(lines[end_line + 1:])
        new_source = before
        if before and not before.endswith("\n"):
            new_source += "\n"
        new_source += header
        new_source += after
    else:
        # No existing docstring — insert before first import/code
        before = "\n".join(lines[:start_line])
        after = "\n".join(lines[start_line:])
        new_source = before
        if before and not before.endswith("\n"):
            new_source += "\n"
        new_source += header + "\n"
        new_source += after

    if not dry_run:
        py_file.write_text(new_source, encoding="utf-8")
    
    return True


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Auto-annotate Python codebase with CodeDNA v0.7")
    parser.add_argument("repo", type=Path, help="Root of the repository to annotate")
    parser.add_argument("--package", default=None, help="Only annotate this package (e.g. 'django')")
    parser.add_argument("--init", action="store_true", help="Also generate .codedna manifest")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of files (for testing)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show generated headers")
    args = parser.parse_args()

    repo_root = args.repo.resolve()
    if not repo_root.exists():
        print(f"Error: {repo_root} does not exist")
        return 1

    scan_dir = repo_root / args.package if args.package else repo_root
    if not scan_dir.exists():
        print(f"Error: {scan_dir} does not exist")
        return 1

    # Collect all .py files
    py_files = sorted(f for f in scan_dir.rglob("*.py")
                       if "__pycache__" not in str(f)
                       and ".git" not in str(f)
                       and "venv" not in str(f)
                       and "node_modules" not in str(f))
    
    if args.limit:
        py_files = py_files[:args.limit]

    total = len(py_files)
    print(f"🧬 CodeDNA Auto-Annotator v0.7")
    print(f"   Repo: {repo_root}")
    print(f"   Scan: {scan_dir.relative_to(repo_root)}")
    print(f"   Files: {total}")
    print(f"   Mode: {'DRY RUN' if args.dry_run else 'WRITE'}")
    print()

    # Pass 1: Scan all files
    print("Pass 1: Scanning files...", flush=True)
    file_infos = {}
    skipped = 0
    for py_file in py_files:
        rel = str(py_file.relative_to(repo_root))
        info = extract_file_info(py_file, repo_root)
        if info["parseable"]:
            file_infos[rel] = info
        else:
            skipped += 1

    print(f"  Scanned: {len(file_infos)} files ({skipped} skipped)")

    # Pass 2: Compute used_by
    print("Pass 2: Computing used_by graph...", flush=True)
    used_by = compute_used_by(file_infos)
    edges = sum(len(v) for v in used_by.values())
    print(f"  Graph: {edges} edges across {len(used_by)} target files")

    # Pass 3: Generate .codedna manifest (if --init)
    if args.init:
        print("Pass 3: Generating .codedna manifest...", flush=True)
        manifest = generate_codedna_manifest(repo_root, file_infos, args.package)
        codedna_path = repo_root / ".codedna"
        if args.dry_run:
            print("  .codedna preview:")
            for line in manifest.split("\n")[:20]:
                print(f"  │ {line}")
        else:
            codedna_path.write_text(manifest, encoding="utf-8")
            print(f"  Written: {codedna_path}")

    # Pass 4: Generate and inject headers
    print(f"Pass 4: {'Previewing' if args.dry_run else 'Writing'} headers...", flush=True)
    written = 0
    for rel, info in sorted(file_infos.items()):
        ub = used_by.get(rel, {})
        header = generate_header(rel, info, ub)
        py_file = repo_root / rel

        if args.verbose or args.dry_run:
            print(f"\n{'─'*60}")
            print(f"  {rel}")
            print(f"  exports={len(info['exports'])} used_by={len(ub)}")
            if args.verbose:
                for line in header.split("\n"):
                    print(f"  │ {line}")

        if inject_header(py_file, header, dry_run=args.dry_run):
            written += 1

    print(f"\n{'='*60}")
    print(f"✅ {'Would annotate' if args.dry_run else 'Annotated'}: {written}/{total} files")
    if args.init:
        print(f"   .codedna manifest: {'previewed' if args.dry_run else 'written'}")
    if args.dry_run:
        print(f"   Run without --dry-run to write changes.")
    
    # Stats
    total_exports = sum(len(i["exports"]) for i in file_infos.values())
    avg_exports = total_exports / len(file_infos) if file_infos else 0
    print(f"\n   Stats:")
    print(f"   Avg exports/file: {avg_exports:.1f}")
    print(f"   Total graph edges: {edges}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
