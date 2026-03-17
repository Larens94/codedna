#!/usr/bin/env python3
"""
tools/auto_annotate.py — Automatically annotate a Python codebase with CodeDNA v0.5 headers.

Uses AST to extract deps, exports, and compute used_by (inverse deps),
then injects CodeDNA module docstrings (Level 1) and function docstrings (Level 2a)
into every .py file.

Usage:
    python tools/auto_annotate.py /path/to/repo                    # L1 only (default)
    python tools/auto_annotate.py /path/to/repo --level2a          # L1 + L2a
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
        # Clean up common prefixes
        first_line = first_line.rstrip(".")
        if len(first_line) > 80:
            first_line = first_line[:77] + "..."
        return first_line
    
    # Generate from filename
    name = Path(rel_path).stem
    parent = Path(rel_path).parent.name
    if name == "__init__":
        return f"Package init for {parent}"
    return f"{name} module"


def format_deps(deps: dict, max_entries: int = 8) -> str:
    """Format deps dict into CodeDNA deps: line(s)."""
    if not deps:
        return "none"
    
    lines = []
    for dep_file, symbols in sorted(deps.items())[:max_entries]:
        if symbols:
            sym_str = ", ".join(symbols[:5])
            if len(symbols) > 5:
                sym_str += f" (+{len(symbols)-5} more)"
            lines.append(f"{dep_file} → {sym_str}")
        else:
            lines.append(dep_file)
    
    if len(deps) > max_entries:
        lines.append(f"(+{len(deps) - max_entries} more)")
    
    return lines[0] if len(lines) == 1 else "\n         ".join(lines)


def format_exports(exports: list, max_entries: int = 8) -> str:
    """Format exports list into CodeDNA exports: line."""
    if not exports:
        return "none"
    
    items = exports[:max_entries]
    result = " | ".join(items)
    if len(exports) > max_entries:
        result += f" (+{len(exports) - max_entries} more)"
    return result


def format_used_by(used_by_entries: dict, max_entries: int = 5) -> str:
    """Format used_by dict into CodeDNA used_by: line(s)."""
    if not used_by_entries:
        return "none"
    
    lines = []
    for importer, symbols in sorted(used_by_entries.items())[:max_entries]:
        if symbols:
            sym_str = ", ".join(symbols[:3])
            if len(symbols) > 3:
                sym_str += f" (+{len(symbols)-3})"
            lines.append(f"{importer} → {sym_str}")
        else:
            lines.append(importer)
    
    if len(used_by_entries) > max_entries:
        lines.append(f"(+{len(used_by_entries) - max_entries} more)")
    
    return lines[0] if len(lines) == 1 else "\n         ".join(lines)


def generate_header(rel_path: str, info: dict, used_by_entries: dict) -> str:
    """Generate a CodeDNA v0.5 module docstring."""
    purpose = generate_purpose(rel_path, info.get("docstring"))
    deps_str = format_deps(info["deps"])
    exports_str = format_exports(info["exports"])
    used_by_str = format_used_by(used_by_entries)

    header = f'"""{rel_path} — {purpose}.\n\n'
    header += f"deps:    {deps_str}\n"
    header += f"exports: {exports_str}\n"
    header += f"used_by: {used_by_str}\n"
    header += '"""\n'
    
    return header


# ── Level 2a: Function-level Depends: docstrings ──────────────────────────

def build_import_map(tree: ast.Module, top_package: str) -> dict:
    """Build a map of local names to their import sources.
    
    Returns: {local_name: (dotted_module, original_name)}
    """
    import_map = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if not node.module.startswith(top_package + "."):
                continue
            for alias in node.names:
                local = alias.asname or alias.name
                import_map[local] = (node.module, alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(top_package + "."):
                    local = alias.asname or alias.name
                    import_map[local] = (alias.name, None)
    return import_map


def extract_function_deps(func_node: ast.AST, import_map: dict) -> list:
    """Find cross-file dependencies used within a function body.
    
    Returns: list of "module.symbol" strings
    """
    deps = set()
    for child in ast.walk(func_node):
        # Direct name reference: e.g., FieldError
        if isinstance(child, ast.Name) and child.id in import_map:
            mod, name = import_map[child.id]
            dep_str = f"{mod}.{name}" if name else mod
            deps.add(dep_str)
        # Attribute access: e.g., tree.Node
        elif isinstance(child, ast.Attribute):
            if isinstance(child.value, ast.Name) and child.value.id in import_map:
                mod, name = import_map[child.value.id]
                dep_str = f"{mod}.{child.attr}"
                deps.add(dep_str)
    return sorted(deps)


def generate_func_docstring(func_name: str, deps: list) -> str:
    """Generate a Level 2a docstring with Depends: lines."""
    deps_str = ", ".join(deps[:5])
    if len(deps) > 5:
        deps_str += f" (+{len(deps)-5} more)"
    return f'"""Depends: {deps_str}"""'


def inject_level2a(py_file: Path, repo_root: Path, dry_run: bool = False) -> int:
    """Add Level 2a Depends: docstrings to functions with cross-file deps.
    
    Re-reads the file from disk (important: L1 headers may have shifted line
    numbers since the original AST parse), then re-parses to get correct
    line numbers for injection.
    
    Returns count of functions annotated.
    """
    try:
        # Re-read from disk — the file may have been modified by L1 injection
        source = py_file.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return 0

    rel = py_file.relative_to(repo_root)
    top_package = rel.parts[0] if len(rel.parts) > 0 else None
    if not top_package:
        return 0

    import_map = build_import_map(tree, top_package)
    if not import_map:
        return 0

    # Collect all functions/methods that need annotation
    # We work on source lines to inject docstrings
    lines = source.split("\n")
    insertions = []  # (line_index, content, mode)
    
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        
        # Skip if function already has a docstring
        existing_doc = ast.get_docstring(node)
        if existing_doc and "Depends:" in existing_doc:
            continue
        
        deps = extract_function_deps(node, import_map)
        if not deps:
            continue
        
        # Determine where to insert the docstring
        # The function body starts at node.body[0]
        if not node.body:
            continue
        
        first_stmt = node.body[0]
        func_line = node.lineno  # 1-indexed line of `def` statement
        
        # Find the end of the `def ...:` line (may span multiple lines)
        # The body starts right after the `:` in the def statement
        # Use the first body statement's line to determine where to insert
        body_line = first_stmt.lineno  # 1-indexed
        
        # If the first body statement has decorators (it's a decorated function),
        # its lineno is the `def` line, but its first decorator is on an earlier line.
        # We need to insert before the decorators, not between them and the `def`.
        if hasattr(first_stmt, 'decorator_list') and first_stmt.decorator_list:
            body_line = first_stmt.decorator_list[0].lineno
        
        # Calculate the indentation of the function body
        body_indent = ""
        if body_line - 1 < len(lines):
            body_text = lines[body_line - 1]
            body_indent = body_text[:len(body_text) - len(body_text.lstrip())]
        
        if not body_indent:
            # Fallback: use def indentation + 4 spaces
            def_text = lines[func_line - 1]
            def_indent = def_text[:len(def_text) - len(def_text.lstrip())]
            body_indent = def_indent + "    "
        
        deps_str = ", ".join(deps[:5])
        if len(deps) > 5:
            deps_str += f" (+{len(deps)-5} more)"

        # If there's an existing docstring, append Depends: to it
        if existing_doc:
            doc_node = first_stmt
            if isinstance(doc_node, ast.Expr) and isinstance(doc_node.value, ast.Constant):
                start_ln = doc_node.lineno       # 1-indexed
                end_ln = doc_node.end_lineno      # 1-indexed
                if end_ln and end_ln - 1 < len(lines):
                    closing_line = lines[end_ln - 1]
                    # One-liner docstring: """text""" — both quotes on same line
                    if start_ln == end_ln:
                        # Expand to multi-line and add Depends:
                        depends_line = f"\n{body_indent}Depends: {deps_str}\n{body_indent}"
                    else:
                        depends_line = f"\n{body_indent}Depends: {deps_str}\n"
                    # Determine which quote style is used
                    for quote in ['"""', "'''"]:
                        pos = closing_line.rfind(quote)
                        if pos >= 0:
                            lines[end_ln - 1] = closing_line[:pos] + depends_line + closing_line[pos:]
                            # Don't use insertions for this — edit in-place
                            break
            continue
        
        # No existing docstring — insert a new one right before the first body statement
        # (but before any decorators if the first body statement is a decorated func)
        new_doc = f'{body_indent}"""Depends: {deps_str}"""'
        insertions.append((body_line - 1, new_doc, "insert"))
    
    # Apply insertions (new docstrings) in reverse order so line numbers stay valid
    insertions.sort(key=lambda x: x[0], reverse=True)
    for line_idx, content, mode in insertions:
        if mode == "insert":
            lines.insert(line_idx, content)
    
    new_source = "\n".join(lines)
    
    # Check if anything actually changed
    if new_source == source:
        return 0
    
    if not dry_run:
        py_file.write_text(new_source, encoding="utf-8")
    
    # Count: number of Depends: lines we added
    original_count = source.count("Depends:")
    new_count = new_source.count("Depends:")
    return new_count - original_count


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
    parser = argparse.ArgumentParser(description="Auto-annotate Python codebase with CodeDNA v0.5")
    parser.add_argument("repo", type=Path, help="Root of the repository to annotate")
    parser.add_argument("--package", default=None, help="Only annotate this package (e.g. 'django')")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--level2a", action="store_true", help="Also add Level 2a function docstrings")
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
    print(f"🧬 CodeDNA Auto-Annotator v0.5")
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

    # Pass 3 + 4: Generate and inject headers
    print(f"Pass 3+4: {'Previewing' if args.dry_run else 'Writing'} headers...", flush=True)
    written = 0
    for rel, info in sorted(file_infos.items()):
        ub = used_by.get(rel, {})
        header = generate_header(rel, info, ub)
        py_file = repo_root / rel

        if args.verbose or args.dry_run:
            print(f"\n{'─'*60}")
            print(f"  {rel}")
            print(f"  deps={len(info['deps'])} exports={len(info['exports'])} "
                  f"used_by={len(ub)}")
            if args.verbose:
                for line in header.split("\n"):
                    print(f"  │ {line}")

        if inject_header(py_file, header, dry_run=args.dry_run):
            written += 1

    # Pass 5 (optional): Level 2a function docstrings
    l2a_count = 0
    if args.level2a:
        print(f"Pass 5: {'Previewing' if args.dry_run else 'Writing'} Level 2a function docstrings...", flush=True)
        for py_file in py_files:
            count = inject_level2a(py_file, repo_root, dry_run=args.dry_run)
            l2a_count += count
        print(f"  Functions annotated: {l2a_count}")

    print(f"\n{'='*60}")
    print(f"✅ {'Would annotate' if args.dry_run else 'Annotated'}: {written}/{total} files (Level 1)")
    if args.level2a:
        print(f"   Level 2a: {l2a_count} function docstrings")
    if args.dry_run:
        print(f"   Run without --dry-run to write changes.")
    
    # Stats
    total_deps = sum(len(i["deps"]) for i in file_infos.values())
    total_exports = sum(len(i["exports"]) for i in file_infos.values())
    avg_deps = total_deps / len(file_infos) if file_infos else 0
    avg_exports = total_exports / len(file_infos) if file_infos else 0
    print(f"\n   Stats:")
    print(f"   Avg deps/file:    {avg_deps:.1f}")
    print(f"   Avg exports/file: {avg_exports:.1f}")
    print(f"   Total graph edges: {edges}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
