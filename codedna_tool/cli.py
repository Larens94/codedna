#!/usr/bin/env python3
"""cli.py — CodeDNA v0.8 annotation tool: init, update, check.

AST for structure (exports, used_by, candidates).
LLM only for semantic content (rules:, function Rules:).

Commands:
  init   PATH   First-time annotation of every .py file under PATH
  update PATH   Annotate only files missing CodeDNA headers (incremental)
  check  PATH   Report annotation coverage without modifying files

LLM calls: max 2 per file (1 module skeleton rules + 1 function batch).
           0 calls if file already annotated (skipped by init/update).

Requires: ANTHROPIC_API_KEY env var (or --api-key) for Anthropic models.
          No API key needed for local models via Ollama (pip install 'codedna[litellm]').

Provider priority: litellm (all providers) > anthropic (fallback, Claude only).
"""

import argparse
import ast
import json
import os
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

try:
    import litellm as _litellm

    HAS_LITELLM = True
except ImportError:
    HAS_LITELLM = False

try:
    import anthropic as _anthropic

    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


# ── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class FuncInfo:
    name: str
    lineno: int  # 1-based, line of "def"
    body_lineno: int  # 1-based, first line of body
    ds_end_lineno: int  # 1-based, last line of docstring (0 = no docstring)
    col_offset: int  # columns of "def" keyword
    has_rules: bool  # already has Rules: annotation
    source: str  # truncated source for LLM prompt
    is_public: bool
    is_dunder: bool


@dataclass
class FileInfo:
    path: Path
    rel: str
    exports: list[str]
    deps: dict  # {dep_rel_path: [symbols]}
    docstring: Optional[str]
    has_codedna: bool  # already has exports:/used_by:/rules: fields
    funcs: list[FuncInfo]
    parseable: bool


# ── AST analysis ─────────────────────────────────────────────────────────────


def _resolve_dep(module: str, repo_root: Path, top_pkg: str) -> Optional[str]:
    """Resolve a dotted module name to a repo-relative path string."""
    if not module.startswith(top_pkg + ".") and module != top_pkg:
        return None
    parts = module.replace(".", "/")
    for suffix in [".py", "/__init__.py"]:
        p = repo_root / f"{parts}{suffix}"
        if p.exists():
            return str(p.relative_to(repo_root))
    return None


def _extract_funcs(tree: ast.AST, source_lines: list[str]) -> list[FuncInfo]:
    funcs = []

    def _walk(node, in_class=False):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                _walk(child, in_class=True)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Body start
                body_ln = child.body[0].lineno if child.body else child.lineno + 1

                # Docstring span
                ds_end = 0
                has_rules = False
                if child.body:
                    first = child.body[0]
                    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                        ds_val = first.value.value
                        if isinstance(ds_val, str):
                            ds_end = first.end_lineno
                            has_rules = "Rules:" in ds_val

                # Truncated source for LLM
                lines = source_lines[child.lineno - 1 : child.end_lineno]
                src = "\n".join(lines)[:600]

                name = child.name
                funcs.append(
                    FuncInfo(
                        name=name,
                        lineno=child.lineno,
                        body_lineno=body_ln,
                        ds_end_lineno=ds_end,
                        col_offset=child.col_offset,
                        has_rules=has_rules,
                        source=src,
                        is_public=not name.startswith("_"),
                        is_dunder=name.startswith("__") and name.endswith("__"),
                    )
                )

    _walk(tree)
    return funcs


def scan_file(path: Path, repo_root: Path) -> FileInfo:
    rel = str(path.relative_to(repo_root))
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return FileInfo(
            path=path, rel=rel, exports=[], deps={}, docstring=None, has_codedna=False, funcs=[], parseable=False
        )

    source_lines = source.splitlines()
    top_pkg = Path(rel).parts[0] if Path(rel).parts else ""

    # Exports: public top-level symbols
    exports = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            exports.append(f"class {node.name}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                args = [a.arg for a in node.args.args if a.arg not in ("self", "cls")]
                exports.append(f"{node.name}({', '.join(args)})")
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id.isupper():
                    exports.append(t.id)

    # Deps: internal imports only
    deps: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            key = _resolve_dep(node.module, repo_root, top_pkg)
            if key:
                syms = [a.name for a in node.names if a.name != "*"]
                deps.setdefault(key, []).extend(syms)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                key = _resolve_dep(alias.name, repo_root, top_pkg)
                if key:
                    deps.setdefault(key, [])
    for k in deps:
        deps[k] = sorted(set(deps[k]))

    docstring = ast.get_docstring(tree)
    has_codedna = bool(docstring and any(f in docstring for f in ("exports:", "used_by:", "rules:")))

    funcs = _extract_funcs(tree, source_lines)

    return FileInfo(
        path=path,
        rel=rel,
        exports=exports,
        deps=deps,
        docstring=docstring,
        has_codedna=has_codedna,
        funcs=funcs,
        parseable=True,
    )


def build_used_by(infos: dict[str, FileInfo]) -> dict[str, dict[str, list[str]]]:
    """Invert deps graph → {file: {importer: [symbols]}}"""
    used_by: dict[str, dict] = {}
    for rel, info in infos.items():
        for dep, syms in info.deps.items():
            used_by.setdefault(dep, {})[rel] = syms
    return used_by


# ── AST skeleton builder ─────────────────────────────────────────────────────


def build_ast_skeleton(source: str, rel: str) -> str:
    """
    Build a compact structural summary of a Python file for LLM consumption.

    Includes every class, every method signature, and the first meaningful
    body line of each method — so the LLM sees the full file architecture
    regardless of file length, at a fraction of the token cost.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source[:3000]

    lines = source.splitlines()
    parts = [f"# {rel}  ({len(source)} bytes, {len(lines)} lines)\n"]

    def _first_body_line(node) -> str:
        """Return first non-docstring body line, stripped, max 80 chars."""
        for stmt in node.body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                continue  # skip docstring
            ln = stmt.lineno - 1
            text = lines[ln].strip()[:80] if ln < len(lines) else ""
            return text
        return ""

    def _fmt_args(node) -> str:
        args = [a.arg for a in node.args.args if a.arg not in ("self", "cls")]
        if node.args.vararg:
            args.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg:
            args.append(f"**{node.args.kwarg.arg}")
        return ", ".join(args)

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            bases = ", ".join(ast.unparse(b) for b in node.bases) if node.bases else ""
            header = f"class {node.name}({bases}):" if bases else f"class {node.name}:"
            cls_doc = ast.get_docstring(node)
            if cls_doc:
                header += f"  # {cls_doc.split(chr(10))[0].strip()[:70]}"
            parts.append(header)

            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    sig = f"    def {child.name}({_fmt_args(child)})"
                    preview = _first_body_line(child)
                    if preview:
                        sig += f"  →  {preview}"
                    parts.append(sig)
            parts.append("")

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            sig = f"def {node.name}({_fmt_args(node)})"
            preview = _first_body_line(node)
            if preview:
                sig += f"  →  {preview}"
            parts.append(sig)

    return "\n".join(parts)


# ── LLM calls ────────────────────────────────────────────────────────────────


class LLM:
    """Unified LLM client.

    Provider resolution order:
    1. litellm  — supports any model string: ollama/llama3, gpt-4o-mini,
                  gemini/gemini-2.0-flash, claude-haiku-4-5-20251001, etc.
    2. anthropic — fallback if litellm is not installed and model is a Claude model.

    Install options:
      pip install 'codedna[litellm]'    # all providers + local models via Ollama
      pip install 'codedna[anthropic]'  # Anthropic only (legacy)
      pip install 'codedna[all]'        # both
    """

    def __init__(self, model: str, api_key: Optional[str] = None):
        self.model = model
        self._use_litellm = HAS_LITELLM
        self._client = None

        if HAS_LITELLM:
            # litellm reads API keys from env vars automatically.
            # If the caller passes --api-key, inject it into the right env var.
            if api_key:
                provider = self._detect_provider(model)
                env_map = {
                    "anthropic": "ANTHROPIC_API_KEY",
                    "openai":    "OPENAI_API_KEY",
                    "gemini":    "GEMINI_API_KEY",
                    "mistral":   "MISTRAL_API_KEY",
                    "cohere":    "COHERE_API_KEY",
                }
                env_key = env_map.get(provider)
                if env_key:
                    os.environ[env_key] = api_key
        elif HAS_ANTHROPIC:
            # Legacy fallback — only works for Claude models.
            self._client = _anthropic.Anthropic(
                api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
            )
        else:
            raise ImportError(
                "No LLM backend found.\n"
                "  All providers (including local Ollama): pip install 'codedna[litellm]'\n"
                "  Anthropic only:                        pip install 'codedna[anthropic]'\n"
                "  Skip AI entirely:                      codedna init ./ --no-llm"
            )

    @staticmethod
    def _detect_provider(model: str) -> str:
        """Detect provider from model string prefix or well-known name."""
        m = model.lower()
        if m.startswith("ollama/") or m.startswith("ollama_chat/"):
            return "ollama"
        if m.startswith("openai/") or m.startswith("gpt"):
            return "openai"
        if m.startswith("gemini/") or m.startswith("google/"):
            return "gemini"
        if m.startswith("mistral/"):
            return "mistral"
        if m.startswith("cohere/"):
            return "cohere"
        if m.startswith("anthropic/") or "claude" in m:
            return "anthropic"
        return "unknown"

    def _call(self, prompt: str, max_tokens: int = 200) -> str:
        if self._use_litellm:
            r = _litellm.completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            return r.choices[0].message.content.strip()
        # Anthropic fallback
        r = self._client.messages.create(
            model=self.model, max_tokens=max_tokens, messages=[{"role": "user", "content": prompt}]
        )
        return r.content[0].text.strip()

    def module_rules(self, rel: str, source: str) -> str:
        """1 call → rules: content for the module."""
        skeleton = build_ast_skeleton(source, rel)
        resp = self._call(
            "You are generating the `rules:` field for a CodeDNA v0.8 module docstring.\n\n"
            "Below is a structural skeleton of the file (every class and method signature "
            "with its first body line). Use this to understand the full architecture.\n\n"
            f"File: {rel}\n```\n{skeleton}\n```\n\n"
            "Write 1-3 lines of hard architectural constraints a future agent MUST know before editing.\n"
            "Focus on constraints that apply to the whole module, not individual functions.\n"
            "Do NOT hint at specific bugs. Return only the constraint text.\n"
            "If no meaningful constraints exist, return exactly: none",
            max_tokens=150,
        )
        return resp if resp else "none"

    def function_rules_batch(self, rel: str, funcs: list[FuncInfo]) -> dict[str, str]:
        """1 call per file → {func_name: 'constraint' or 'SKIP'}"""
        if not funcs:
            return {}
        blocks = "\n\n".join(f"### {f.name}\n```python\n{f.source}\n```" for f in funcs)
        resp = self._call(
            f"File: {rel}\n\n"
            "For each function, does it have NON-OBVIOUS domain constraints a future developer MUST know?\n"
            "YES → brief constraint (1-2 lines). NO → SKIP.\n\n"
            f"{blocks}\n\n"
            f'Return ONLY valid JSON: {{"func_name": "constraint or SKIP", ...}}',
            max_tokens=500,
        )
        try:
            # Strip markdown code fences if present
            clean = resp.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            return json.loads(clean.strip())
        except (json.JSONDecodeError, Exception):
            return {}


# ── Docstring builders ────────────────────────────────────────────────────────


def _fmt_exports(exports: list[str]) -> str:
    return " | ".join(exports) if exports else "none"


def _fmt_used_by(ub: dict[str, list[str]]) -> str:
    if not ub:
        return "none"
    lines = []
    for importer, syms in sorted(ub.items()):
        lines.append(f"{importer} → {', '.join(syms)}" if syms else importer)
    return lines[0] if len(lines) == 1 else "\n         ".join(lines)


def _purpose(rel: str, existing: Optional[str]) -> str:
    if existing:
        first = existing.strip().split("\n")[0].strip()
        while " — " in first:
            after = first.split(" — ", 1)[1].strip()
            if after and not after.startswith(("exports:", "used_by:", "rules:")):
                first = after
            else:
                break
        first = first.rstrip(".")
        if first and not first.startswith(("exports:", "used_by:", "rules:")) and len(first) <= 80:
            return first
    stem = Path(rel).stem
    parent = Path(rel).parent.name
    return f"Package init for {parent}" if stem == "__init__" else f"{stem} module"


def build_module_docstring(info: FileInfo, ub: dict, rules: str, model_id: str) -> str:
    today = date.today().isoformat()
    lines = [
        f'"""{info.rel} — {_purpose(info.rel, info.docstring)}.',
        "",
        f"exports: {_fmt_exports(info.exports)}",
        f"used_by: {_fmt_used_by(ub)}",
        f"rules:   {rules}",
        f"agent:   {model_id} | {today} | initial CodeDNA annotation pass",
        '"""',
    ]
    return "\n".join(lines) + "\n"


# ── Source injection ──────────────────────────────────────────────────────────


def inject_module_docstring(source: str, docstring: str) -> str:
    """Replace or prepend module docstring."""
    lines = source.split("\n")
    start = 0
    if lines and lines[0].startswith("#!"):
        start = 1
    if start < len(lines) and lines[start].startswith("# -*-"):
        start += 1
    while start < len(lines) and not lines[start].strip():
        start += 1

    end = None
    if start < len(lines):
        stripped = lines[start].strip()
        if stripped.startswith(('"""', "'''")):
            q = stripped[:3]
            if stripped.count(q) >= 2 and len(stripped) > 6:
                end = start
            else:
                for i in range(start + 1, len(lines)):
                    if q in lines[i]:
                        end = i
                        break

    before = "\n".join(lines[:start])
    after = "\n".join(lines[end + 1 :] if end is not None else lines[start:])
    parts = [p for p in [before, docstring.rstrip(), after] if p]
    return "\n".join(parts)


def inject_function_rules(source: str, func: FuncInfo, rules_text: str) -> str:
    """
    Inject Rules: into a function docstring (or create one).
    Caller must apply from BOTTOM to TOP to preserve line numbers.
    """
    lines = source.split("\n")
    indent = " " * (func.col_offset + 4)

    if func.ds_end_lineno > 0:
        # Has existing docstring
        body_ln = func.body_lineno  # 1-based
        ds_end = func.ds_end_lineno  # 1-based

        if body_ln == ds_end:
            # Single-line docstring → expand
            idx = body_ln - 1  # 0-based
            raw = lines[idx].strip()
            q = '"""' if raw.startswith('"""') else "'''"
            inner = raw[3:-3].strip()
            new = [
                f"{indent}{q}{inner}",
                "",
                f"{indent}Rules:   {rules_text}",
                f"{indent}{q}",
            ]
            lines = lines[:idx] + new + lines[idx + 1 :]
        else:
            # Multi-line: insert before closing quotes
            end_idx = ds_end - 1  # 0-based
            lines = lines[:end_idx] + ["", f"{indent}Rules:   {rules_text}"] + lines[end_idx:]
    else:
        # No docstring → insert one before first body statement
        idx = func.body_lineno - 1  # 0-based
        new = [
            f'{indent}"""',
            f"{indent}Rules:   {rules_text}",
            f'{indent}"""',
        ]
        lines = lines[:idx] + new + lines[idx:]

    return "\n".join(lines)


# ── Pipeline ──────────────────────────────────────────────────────────────────


def collect_files(target: Path, exclude: list[str]) -> list[Path]:
    if target.is_file():
        return [target]
    skip = {"__pycache__", ".git", "venv", ".venv", "node_modules", "migrations"}
    files = []
    for f in sorted(target.rglob("*.py")):
        if any(p in f.parts for p in skip):
            continue
        if any(f.match(p) for p in exclude):
            continue
        files.append(f)
    return files


def run(
    target: Path,
    levels: list[int],
    model: str,
    dry_run: bool,
    exclude: list[str],
    force: bool,
    no_llm: bool,
    only_public: bool,
    verbose: bool,
    api_key: Optional[str],
    repo_root: Optional[Path] = None,
):
    effective_root = target if target.is_dir() else target.parent
    if repo_root is None:
        repo_root = effective_root
    py_files = collect_files(target, exclude)

    print("CodeDNA Annotator v0.8")
    print(f"Target  {target}")
    print(f"Levels  {levels}")
    print(f"Mode    {'DRY RUN' if dry_run else 'WRITE'}")
    print(f"LLM     {'disabled (--no-llm)' if no_llm else model}")
    print(f"Files   {len(py_files)}")
    print()

    # Pass 1 — scan target files (these are the ones we will annotate)
    print("Pass 1/3  Scanning...", flush=True)
    infos: dict[str, FileInfo] = {}
    for f in py_files:
        info = scan_file(f, repo_root)
        if info.parseable:
            infos[info.rel] = info
    print(f"          {len(infos)} parsed  ({len(py_files) - len(infos)} skipped)")

    # Pass 2 — used_by graph
    # If repo_root differs from the effective target root, scan the full repo so
    # we can find callers that live outside the target subdirectory.
    print("Pass 2/3  Building dependency graph...", flush=True)
    graph_infos: dict[str, FileInfo] = dict(infos)
    if repo_root != effective_root:
        repo_files = collect_files(repo_root, exclude)
        target_paths = {info.path for info in infos.values()}
        for f in repo_files:
            if f not in target_paths:
                extra = scan_file(f, repo_root)
                if extra.parseable:
                    graph_infos[extra.rel] = extra
        print(
            f"          graph built from {len(graph_infos)} files "
            f"({len(infos)} target + {len(graph_infos) - len(infos)} repo)"
        )
    ub_graph = build_used_by(graph_infos)
    edges = sum(len(v) for v in ub_graph.values())
    print(f"          {edges} edges across {len(ub_graph)} files")

    # Pass 3 — annotate
    print("Pass 3/3  Annotating...", flush=True)

    llm: Optional[LLM] = None
    if not no_llm:
        if not HAS_ANTHROPIC:
            print("  Warning: anthropic not installed. Run: pip install anthropic")
            print("           Falling back to --no-llm (rules: none)")
        else:
            try:
                llm = LLM(model=model, api_key=api_key)
            except Exception as e:
                print(f"  Warning: LLM unavailable ({e}). rules: will be 'none'")

    l1_count = l2_count = llm_calls = 0

    for rel, info in sorted(infos.items()):
        source = info.path.read_text(encoding="utf-8", errors="replace")
        modified = source
        file_changed = False

        if verbose:
            print(f"\n  {rel}")

        # ── Level 2: function Rules: (applied FIRST against original source) ──
        # CRITICAL: L2 uses AST line numbers from the original scan. L1 adds
        # lines at the top of the file, shifting all subsequent positions.
        # By applying L2 first (bottom-to-top on original source), then L1
        # (which only touches the module docstring at the very top), we ensure
        # L2 injections always land at the correct positions.
        if 2 in levels:
            candidates = [
                f
                for f in info.funcs
                if not f.has_rules
                and not f.is_dunder
                and (not only_public or f.is_public)
                and len(f.source.strip()) > 60  # skip trivial one-liners
            ]

            if candidates:
                rules_map: dict[str, str] = {}
                if llm:
                    rules_map = llm.function_rules_batch(rel, candidates)
                    llm_calls += 1

                # Apply bottom-to-top to keep earlier line numbers valid
                to_inject = [
                    (f, rules_map.get(f.name, "SKIP"))
                    for f in candidates
                    if rules_map.get(f.name, "SKIP") not in ("SKIP", "", None)
                ]
                for func, rules_text in sorted(to_inject, key=lambda x: x[0].lineno, reverse=True):
                    modified = inject_function_rules(modified, func, rules_text)
                    l2_count += 1
                    file_changed = True
                    if verbose:
                        print(f"    L2  {func.name}(): {rules_text[:60]}")

        # ── Level 1: module docstring (applied AFTER L2) ───────────────────
        # L1 replaces/prepends the module docstring at the top of the file.
        # Since L2 has already been applied, any line-number shifts from L1
        # don't affect L2 (which is already done).
        if 1 in levels:
            if info.has_codedna and not force:
                if verbose:
                    print("    L1  skip (already annotated)")
            else:
                rules = "none"
                if llm:
                    rules = llm.module_rules(rel, source)
                    llm_calls += 1

                ub = ub_graph.get(rel, {})
                docstring = build_module_docstring(info, ub, rules, model)
                modified = inject_module_docstring(modified, docstring)
                l1_count += 1
                file_changed = True

                if verbose:
                    print(f"    L1  rules: {rules[:70]}")

        # Write
        if file_changed and modified != source:
            if not dry_run:
                info.path.write_text(modified, encoding="utf-8")

    # Summary
    print()
    print("=" * 50)
    if 1 in levels:
        verb = "Would annotate" if dry_run else "Annotated"
        print(f"L1 modules   {verb} {l1_count} files")
    if 2 in levels:
        verb = "Would add" if dry_run else "Added"
        print(f"L2 functions {verb} Rules: to {l2_count} functions")
    print(f"LLM calls    {llm_calls}")
    if dry_run:
        print()
        print("Dry run — no files written.")


# ── Check command ─────────────────────────────────────────────────────────────


def cmd_check(target: Path, repo_root: Optional[Path], exclude: list[str], verbose: bool):
    """Report annotation coverage without modifying any files."""
    effective_root = target if target.is_dir() else target.parent
    if repo_root is None:
        repo_root = effective_root

    py_files = collect_files(target, exclude)
    print("CodeDNA Check")
    print(f"Target  {target}")
    print(f"Files   {len(py_files)}")
    print()

    total = annotated_l1 = annotated_l2 = unparseable = 0
    missing_l1 = []
    missing_l2 = []

    for f in py_files:
        info = scan_file(f, repo_root)
        total += 1
        if not info.parseable:
            unparseable += 1
            continue

        if info.has_codedna:
            annotated_l1 += 1
        else:
            missing_l1.append(info.rel)

        funcs_need_l2 = [
            fn
            for fn in info.funcs
            if fn.is_public and not fn.is_dunder and not fn.has_rules and len(fn.source.strip()) > 60
        ]
        if not funcs_need_l2:
            annotated_l2 += 1
        else:
            missing_l2.append((info.rel, [fn.name for fn in funcs_need_l2]))

    pct_l1 = 100 * annotated_l1 // total if total else 0
    pct_l2 = 100 * annotated_l2 // total if total else 0

    print(f"L1 (module headers)    {annotated_l1}/{total}  ({pct_l1}%)")
    print(f"L2 (function Rules:)   {annotated_l2}/{total}  ({pct_l2}%)")
    if unparseable:
        print(f"Unparseable            {unparseable}")
    print()

    if verbose and missing_l1:
        print("Missing L1:")
        for rel in missing_l1:
            print(f"  {rel}")
        print()

    if verbose and missing_l2:
        print("Missing L2 Rules::")
        for rel, fns in missing_l2:
            print(f"  {rel}: {', '.join(fns)}")
        print()

    ok = (annotated_l1 == total - unparseable) and (annotated_l2 == total - unparseable)
    print("OK — fully annotated" if ok else "INCOMPLETE — run `codedna init` to annotate missing files")
    return 0 if ok else 1


# ── CLI ───────────────────────────────────────────────────────────────────────


def _add_common_args(sub):
    """Shared arguments for init and update."""
    sub.add_argument("path", type=Path, help="File or directory to annotate")
    sub.add_argument(
        "--model",
        default="claude-haiku-4-5-20251001",
        help=(
            "Model to use for generating rules: annotations. "
            "Requires litellm (pip install 'codedna[litellm]') for non-Anthropic models. "
            "Examples: "
            "claude-haiku-4-5-20251001 (default, Anthropic), "
            "ollama/llama3 (local, free), "
            "ollama/mistral (local, free), "
            "openai/gpt-4o-mini (OpenAI), "
            "gemini/gemini-2.0-flash (Google). "
            "Use --no-llm to skip AI entirely (rules: none)."
        ),
    )
    sub.add_argument("--dry-run", action="store_true", help="Preview changes without writing files")
    sub.add_argument("--no-llm", action="store_true", help="Structural annotations only — skip LLM (rules: none)")
    sub.add_argument(
        "--all-functions", action="store_true", help="Level 2: include private functions (default: public only)"
    )
    sub.add_argument("--exclude", nargs="*", default=[], help="Glob patterns to exclude")
    sub.add_argument("--api-key", default=None, help="Anthropic API key (default: ANTHROPIC_API_KEY env var)")
    sub.add_argument("--repo-root", type=Path, default=None, help="Project root for used_by graph (default: path)")
    sub.add_argument("-v", "--verbose", action="store_true", help="Per-file progress")


def main():
    p = argparse.ArgumentParser(
        prog="codedna",
        description="CodeDNA v0.8 — in-source annotation protocol",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subs = p.add_subparsers(dest="command", metavar="COMMAND")
    subs.required = True

    # ── init ──────────────────────────────────────────────────────────────────
    init_p = subs.add_parser(
        "init",
        help="First-time annotation of a project (L1 module headers + L2 function Rules:)",
        description=(
            "Scan every Python file under PATH and add CodeDNA annotations:\n"
            "  L1  Module docstring with exports:, used_by:, rules:, agent:\n"
            "  L2  Rules: docstrings on non-trivial public functions\n\n"
            "Already-annotated files are skipped unless --force is given.\n"
            "Run once when onboarding a project, then use `codedna update` for changes."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_common_args(init_p)
    init_p.add_argument("--force", action="store_true", help="Re-annotate files that already have CodeDNA headers")

    # ── update ────────────────────────────────────────────────────────────────
    update_p = subs.add_parser(
        "update",
        help="Annotate files that are missing CodeDNA headers (incremental)",
        description=(
            "Like `init` but only processes files that are not yet annotated.\n"
            "Use after adding new files or after `git checkout` on unannotated branches."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_common_args(update_p)

    # ── check ─────────────────────────────────────────────────────────────────
    check_p = subs.add_parser(
        "check",
        help="Report annotation coverage without modifying files",
        description="Prints coverage stats. Exits 0 if fully annotated, 1 otherwise.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    check_p.add_argument("path", type=Path, help="File or directory to check")
    check_p.add_argument("--repo-root", type=Path, default=None)
    check_p.add_argument("--exclude", nargs="*", default=[])
    check_p.add_argument("-v", "--verbose", action="store_true", help="List specific files missing annotations")

    args = p.parse_args()

    # ── dispatch ──────────────────────────────────────────────────────────────
    if args.command == "check":
        target = args.path.resolve()
        if not target.exists():
            print(f"Error: {target} does not exist", file=sys.stderr)
            return 1
        repo_root = args.repo_root.resolve() if args.repo_root else None
        return cmd_check(target, repo_root, list(args.exclude), args.verbose)

    # init / update share the same run() — only difference is force flag
    target = args.path.resolve()
    if not target.exists():
        print(f"Error: {target} does not exist", file=sys.stderr)
        return 1

    force = getattr(args, "force", False)  # update never forces
    repo_root = args.repo_root.resolve() if args.repo_root else None

    run(
        target=target,
        levels=[1, 2],
        model=args.model,
        dry_run=args.dry_run,
        exclude=list(args.exclude),
        force=force,
        no_llm=args.no_llm,
        only_public=not args.all_functions,
        verbose=args.verbose,
        api_key=args.api_key,
        repo_root=repo_root,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
