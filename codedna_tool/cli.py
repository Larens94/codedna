#!/usr/bin/env python3
"""cli.py — CodeDNA v0.8 annotation tool: init, update, check, install.

exports: class FuncInfo | class FileInfo | scan_file(path, repo_root) | build_used_by(infos) | build_ast_skeleton(source, rel) | class LLM | _EXPORTS_CAP | build_module_docstring(info, ub, rules, model_id) | inject_module_docstring(source, docstring) | inject_function_rules(source, func, rules_text) | collect_files(target, exclude, extensions) | run_lang_files(target, extensions, repo_root, exclude, model, dry_run, force, no_llm, verbose, api_key) | run(target, levels, model, dry_run, exclude, force, no_llm, only_public, verbose, api_key, repo_root, extensions) | cmd_refresh(target, repo_root, exclude, dry_run, verbose) | cmd_check(target, repo_root, exclude, verbose, extensions) | _TOOL_FILES | _HOOK_TOOLS | _TOOL_HOOKS_MAP | _HOOKS_BASE_MAP | _PRE_COMMIT_HOOK | (+7 more)
used_by: tests/test_cli.py → FileInfo, build_module_docstring
rules:   L2 (function Rules:) applies Python AST only; language adapters are L1-only.
LLM calls are capped at 2 per Python file; --no-llm skips all LLM calls.
_resolve_dep must NOT filter by top_pkg — filesystem existence is the guard.
`init` must scaffold `codedna-wiki.md` and `.agents/skills/create-wiki/SKILL.md`
idempotently at repo root without overwriting existing wiki assets.
scan_file handles 3 import patterns: (1) from .mod import X, (2) from . import X
(submodule-first then __init__.py symbol), (3) from pkg import X (tries pkg/X.py
before falling back to pkg/__init__.py). All 3 were previously under-resolved.
agent:   claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_004 | fix L2 batch overflow: _L2_BATCH_SIZE=12, dynamic max_tokens, _parse_json_response with truncation recovery
claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_004 | skip *_test.go; cap exports@20; fix non-Python path (raw join→_fmt_exports, module_rules→module_rules_raw, provider detection)
claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_005 | run_lang_files returns (annotated, llm_calls) tuple; run() aggregates lang llm_calls into summary counter
claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_bench | fix 3 used_by bugs in scan_file; fix LLM gating: run() checked HAS_ANTHROPIC instead of HAS_LITELLM|HAS_ANTHROPIC — litellm (DeepSeek/GPT) was silently falling back to --no-llm
gpt-5.4 | openai | 2026-04-17 | s_20260417_001 | scaffold repo-local create-wiki skill and codedna-wiki.md after init via dedicated helper module
claude-opus-4-7 | anthropic | 2026-04-19 | s_20260419_001 | add explicit `codedna wiki` subcommand so semantic wiki is independent of init; idempotent scaffold with --dry-run
AST for structure (exports, used_by, candidates). Python only.
LLM only for semantic content (rules:, function Rules:).
Language adapters for non-Python files (TypeScript, Go, …) via languages/ package.
Commands:
install        Setup CodeDNA in a project (pre-commit hook + AI tool prompt + .codedna)
init   PATH    First-time annotation of every source file under PATH
update PATH    Annotate only files missing CodeDNA headers (incremental)
check  PATH    Report annotation coverage without modifying files
wiki   [PATH]  Scaffold codedna-wiki.md and repo-local create-wiki skill (idempotent)
LLM calls: max 2 per Python file (1 module skeleton rules + 1 function batch).
0 calls if file already annotated (skipped by init/update).
Non-Python files: 1 LLM call per file for rules: (or none with --no-llm).
Requires: ANTHROPIC_API_KEY env var (or --api-key) for Anthropic models.
No API key needed for local models via Ollama (pip install 'codedna[litellm]').
Provider priority: litellm (all providers) > anthropic (fallback, Claude only).
Multi-language: pass --extensions ts go php rs java kt rb cs swift (or with dots).
Supported: .ts .tsx .js .jsx .mjs | .go | .php | .rs | .java | .kt .kts | .rb | .cs | .swift
"""

import argparse
import ast
import fnmatch
import json
import os
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

from .languages import SUPPORTED_EXTENSIONS, get_adapter
from .wiki import ensure_wiki_scaffold

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
    """Resolve a dotted module name to a repo-relative path string.

    Rules:   Do NOT filter by top_pkg — cross-package imports (e.g. analytics → orders)
             must be resolved. Existence check on the filesystem is the correct guard
             against external libraries (os, requests, etc. won't exist under repo_root).
    """
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
    file_dir = path.parent
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level > 0:
                # Relative import: from .foo import bar  OR  from . import bar
                # node.module may be None for "from . import X"
                parent = file_dir
                for _ in range(node.level - 1):
                    parent = parent.parent

                if node.module:
                    # from .foo import bar  → resolve .foo to a file
                    rel_target = parent / node.module.replace(".", "/")
                    for suffix in [".py", "/__init__.py"]:
                        candidate = Path(str(rel_target) + suffix)
                        if candidate.exists():
                            try:
                                key = str(candidate.relative_to(repo_root))
                                syms = [a.name for a in node.names if a.name != "*"]
                                deps.setdefault(key, []).extend(syms)
                            except ValueError:
                                pass
                            break
                else:
                    # from . import X  → X may be a submodule (X.py) or a symbol
                    for alias in node.names:
                        if alias.name == "*":
                            continue
                        # Check if X is a submodule file first
                        candidates = [parent / f"{alias.name}.py", parent / alias.name / "__init__.py"]
                        for candidate in candidates:
                            if candidate.exists():
                                try:
                                    key = str(candidate.relative_to(repo_root))
                                    deps.setdefault(key, [])
                                except ValueError:
                                    pass
                                break
                        else:
                            # Symbol from the package __init__.py
                            init = parent / "__init__.py"
                            if init.exists():
                                try:
                                    key = str(init.relative_to(repo_root))
                                    deps.setdefault(key, []).append(alias.name)
                                except ValueError:
                                    pass
            elif node.module:
                # Absolute import: from pkg import X
                # X may be a submodule (pkg/X.py) or a symbol from pkg/__init__.py
                syms = [a.name for a in node.names if a.name != "*"]
                resolved_any = False
                for sym in syms:
                    # Try pkg/X.py or pkg/X/__init__.py first (submodule)
                    sub_key = _resolve_dep(f"{node.module}.{sym}", repo_root, top_pkg)
                    if sub_key:
                        deps.setdefault(sub_key, [])
                        resolved_any = True
                    # Also record dependency on the package itself for re-export tracing
                    pkg_key = _resolve_dep(node.module, repo_root, top_pkg)
                    if pkg_key and not sub_key:
                        deps.setdefault(pkg_key, []).append(sym)
                        resolved_any = True
                # If nothing resolved, try the module itself
                if not resolved_any:
                    key = _resolve_dep(node.module, repo_root, top_pkg)
                    if key:
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
                    "openai": "OPENAI_API_KEY",
                    "gemini": "GEMINI_API_KEY",
                    "deepseek": "DEEPSEEK_API_KEY",
                    "mistral": "MISTRAL_API_KEY",
                    "cohere": "COHERE_API_KEY",
                }
                env_key = env_map.get(provider)
                if env_key:
                    os.environ[env_key] = api_key
        elif HAS_ANTHROPIC:
            # Legacy fallback — only works for Claude models.
            self._client = _anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
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
        if m.startswith("deepseek/") or m.startswith("deepseek-"):
            return "deepseek"
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
        """1 call → rules: content for a Python module (uses AST skeleton)."""
        skeleton = build_ast_skeleton(source, rel)
        return self._module_rules_from_context(rel, f"```\n{skeleton}\n```")

    def module_rules_raw(self, rel: str, source_snippet: str) -> str:
        """1 call → rules: content for a non-Python module (uses raw source snippet).

        Rules:   Use this for PHP/Go/TS/Ruby/etc — build_ast_skeleton() is Python-only.
                 source_snippet should be the first 2000 chars of the file.
        """
        return self._module_rules_from_context(rel, f"```\n{source_snippet}\n```")

    def _module_rules_from_context(self, rel: str, context_block: str) -> str:
        """Shared prompt builder for module_rules and module_rules_raw."""
        resp = self._call(
            "You are generating the `rules:` field for a CodeDNA v0.8 module header.\n\n"
            "Below is the source context of the file.\n\n"
            f"File: {rel}\n{context_block}\n\n"
            "Write 1-3 lines of hard architectural constraints a future agent MUST know before editing.\n"
            "Focus on constraints that apply to the whole module, not individual functions.\n"
            "Do NOT hint at specific bugs. Return only the constraint text.\n"
            "If no meaningful constraints exist, return exactly: none",
            max_tokens=150,
        )
        if not resp or not resp.strip():
            print(f"    WARNING: LLM returned empty rules for {rel} — using 'none'")
            return "none"
        return resp

    def package_purpose(self, pkg_name: str, key_files: list[str], exports_sample: str) -> str:
        """1 call → purpose: description for a package (≤15 words)."""
        resp = self._call(
            "You are writing the `purpose:` field for a CodeDNA `.codedna` manifest entry.\n\n"
            f"Package: {pkg_name}/\n"
            f"Key files: {', '.join(key_files)}\n"
            f"Exports sample: {exports_sample[:400]}\n\n"
            "Write ONE sentence (≤15 words) describing what this package does.\n"
            "Be specific and concrete. Focus on domain responsibility, not implementation.\n"
            "Return only the sentence, no quotes, no punctuation at end.",
            max_tokens=60,
        )
        return resp.strip().rstrip(".") if resp else f"{pkg_name} package"

    # Rules: never send more than _L2_BATCH_SIZE functions per call —
    #        large files (e.g. 38-fn app.py) overflow max_tokens and produce truncated JSON.
    _L2_BATCH_SIZE = 12

    def function_rules_batch(self, rel: str, funcs: list[FuncInfo]) -> dict[str, str]:
        """N calls per file (batched) → {func_name: 'constraint' or 'SKIP'}.

        Rules:   Batches of _L2_BATCH_SIZE to keep prompt + response within token limits.
                 max_tokens scales with batch size (50 tokens per function).
                 _parse_json_response() attempts partial extraction before giving up.
        """
        if not funcs:
            return {}
        result: dict[str, str] = {}
        for i in range(0, len(funcs), self._L2_BATCH_SIZE):
            batch = funcs[i : i + self._L2_BATCH_SIZE]
            result.update(self._function_rules_single_batch(rel, batch))
        return result

    def _function_rules_single_batch(self, rel: str, funcs: list[FuncInfo]) -> dict[str, str]:
        """1 LLM call for a batch of ≤ _L2_BATCH_SIZE functions."""
        blocks = "\n\n".join(f"### {f.name}\n```python\n{f.source}\n```" for f in funcs)
        # Scale max_tokens with batch size — 50 tokens per function is a safe upper bound
        max_tok = max(400, len(funcs) * 50)
        resp = self._call(
            f"File: {rel}\n\n"
            "For each function, does it have NON-OBVIOUS domain constraints a future developer MUST know?\n"
            "YES → brief constraint (1-2 lines). NO → SKIP.\n\n"
            f"{blocks}\n\n"
            f'Return ONLY valid JSON: {{"func_name": "constraint or SKIP", ...}}',
            max_tokens=max_tok,
        )
        parsed = self._parse_json_response(resp)
        if parsed is None:
            print(f"    WARNING: LLM returned invalid JSON for function rules in {rel} — skipping batch")
            return {}
        return parsed

    @staticmethod
    def _parse_json_response(resp: str) -> Optional[dict]:
        """Extract a JSON object from an LLM response, tolerating markdown fences and truncation.

        Rules:   Tries three strategies in order:
                 1. Strip fences, parse directly.
                 2. Find the last complete key-value pair before a truncation point and close the object.
                 3. Return None — caller emits WARNING and skips the batch.
        """
        if not resp:
            return None
        clean = resp.strip()
        # Strip markdown code fences
        if clean.startswith("```"):
            parts = clean.split("```")
            clean = parts[1] if len(parts) > 1 else clean
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip()

        # Strategy 1: direct parse
        try:
            return json.loads(clean)
        except (json.JSONDecodeError, ValueError):
            pass

        # Strategy 2: truncated JSON — find last complete "key": "value" pair and close the object
        # Handles the case where max_tokens cut the response mid-object.
        try:
            # Find the rightmost complete "key": "value" entry
            last_comma = clean.rfind('",')
            if last_comma > 0:
                candidate = clean[: last_comma + 1].rstrip().rstrip(",") + "\n}"
                # Ensure it starts with {
                brace = candidate.find("{")
                if brace >= 0:
                    return json.loads(candidate[brace:])
        except (json.JSONDecodeError, ValueError):
            pass

        return None


# ── Docstring builders ────────────────────────────────────────────────────────


_EXPORTS_CAP = 20  # max entries before truncation — prevents unreadable walls of text in large files

def _fmt_exports(exports: list[str]) -> str:
    if not exports:
        return "none"
    if len(exports) <= _EXPORTS_CAP:
        return " | ".join(exports)
    return " | ".join(exports[:_EXPORTS_CAP]) + f" | (+{len(exports) - _EXPORTS_CAP} more)"


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
    provider = (
        "codedna-cli"
        if model_id == "codedna-cli (no-llm)"
        else LLM._detect_provider(model_id)
    )
    lines = [
        f'"""{info.rel} — {_purpose(info.rel, info.docstring)}.',
        "",
        f"exports: {_fmt_exports(info.exports)}",
        f"used_by: {_fmt_used_by(ub)}",
        f"rules:   {rules}",
        f"agent:   {model_id} | {provider} | {today} | codedna-cli | initial CodeDNA annotation pass",
        '"""',
    ]
    return "\n".join(lines) + "\n"


# ── Source injection ──────────────────────────────────────────────────────────


def inject_module_docstring(source: str, docstring: str) -> str:
    """Replace or prepend module docstring.

    Rules:   Normalize \r\n and bare \r to \n before splitting — .split('\n') on
             CRLF input leaves \r at line endings which corrupts the written file.
    """
    source = source.replace("\r\n", "\n").replace("\r", "\n")
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


def _get_extension(path: Path) -> str:
    """Return the file extension, handling compound extensions like .blade.php.

    Rules:   Compound extensions (.blade.php, etc.) take priority over simple suffix.
             Falls back to path.suffix for standard extensions.
    """
    name = path.name.lower()
    # Check for known compound extensions
    _COMPOUND_EXTS = [".blade.php"]
    for ext in _COMPOUND_EXTS:
        if name.endswith(ext):
            return ext
    return path.suffix.lower()


def collect_files(target: Path, exclude: list[str], extensions: Optional[list[str]] = None) -> list[Path]:
    """Collect source files under target matching the given extensions.

    Rules:   Default extensions = ['.py'] (Python only).
             extensions values must include leading dot (e.g. ['.ts', '.go']).
             Supports compound extensions (e.g. '.blade.php').
    """
    if extensions is None:
        extensions = [".py"]
    if target.is_file():
        return [target] if _get_extension(target) in extensions else []
    skip = {
        "__pycache__", ".git", ".hg", ".svn",
        "venv", ".venv", "env", ".env",
        "node_modules", "vendor", "bower_components",
        "dist", "build", ".tox", ".mypy_cache", ".ruff_cache",
        "migrations", "__pypackages__",
    }
    files = []
    for f in sorted(target.rglob("*")):
        if not f.is_file():
            continue
        if any(p in f.parts for p in skip):
            continue
        if _get_extension(f) not in extensions:
            continue
        # Skip Go test files (*_test.go) — test infrastructure, not project source
        if f.suffix == ".go" and f.stem.endswith("_test"):
            continue
        rel_str = str(f.relative_to(target))
        if any(fnmatch.fnmatch(rel_str, p) or f.match(p) for p in exclude):
            continue
        files.append(f)
    return files


def _normalize_extensions(raw: Optional[list[str]]) -> list[str]:
    """Normalize extension list: ensure leading dot, lowercase."""
    if not raw:
        return [".py"]
    return [e if e.startswith(".") else f".{e}" for e in raw]


def _auto_detect_extensions(target: Path) -> list[str]:
    """Scan target directory and return extensions that have matching language adapters.

    Rules:   Always includes .py. Only returns extensions for which an adapter exists.
             Skips __pycache__, .git, venv, node_modules, etc.
    """
    skip = {"__pycache__", ".git", "venv", ".venv", "node_modules",
            "migrations", "dist", "build", ".tox", ".mypy_cache"}
    set_str_found_exts: set[str] = {".py"}

    if not target.is_dir():
        ext = _get_extension(target)
        if get_adapter(ext):
            set_str_found_exts.add(ext)
        return sorted(set_str_found_exts)

    for f in target.rglob("*"):
        if not f.is_file():
            continue
        if any(p in f.parts for p in skip):
            continue
        ext = _get_extension(f)
        if ext not in set_str_found_exts and get_adapter(ext):
            set_str_found_exts.add(ext)

    return sorted(set_str_found_exts)


def run_lang_files(
    target: Path,
    extensions: list[str],
    repo_root: Path,
    exclude: list[str],
    model: str,
    dry_run: bool,
    force: bool,
    no_llm: bool,
    verbose: bool,
    api_key: Optional[str],
) -> tuple[int, int]:
    """Annotate non-Python source files using language adapters (L1 module header only).

    Rules:   Returns (annotated_count, llm_call_count) — caller adds llm_call_count to its own counter.
             Only runs for extensions that have a registered adapter.
             L2 (function Rules:) is Python-only; language adapters do L1 only.
             Only runs for extensions that have a registered adapter.
    """
    lang_exts = [e for e in extensions if e != ".py" and get_adapter(e) is not None]
    if not lang_exts:
        return 0, 0

    lang_files = collect_files(target, exclude, extensions=lang_exts)
    if not lang_files:
        return 0, 0

    print(f"\nMulti-language pass ({', '.join(lang_exts)})  {len(lang_files)} files")

    llm: Optional[LLM] = None
    if not no_llm:
        try:
            llm = LLM(model=model, api_key=api_key)
        except Exception as e:
            print(f"  Warning: LLM unavailable ({e}). rules: will be 'none'")

    today = date.today().isoformat()
    annotated = 0
    llm_calls = 0

    for path in lang_files:
        adapter = get_adapter(_get_extension(path))
        if adapter is None:
            continue

        info = adapter.extract_info(path, repo_root)
        if not info.parseable:
            if verbose:
                print(f"  SKIP (unreadable)  {info.rel}")
            continue

        if info.has_codedna and not force:
            if verbose:
                print(f"  skip (annotated)   {info.rel}")
            continue

        source = path.read_text(encoding="utf-8", errors="replace")
        exports_str = _fmt_exports(info.exports)
        used_by_str = "none"  # cross-file graph not available for non-Python files yet

        rules_str = "none"
        if llm and info.exports:
            try:
                snippet = source[:2000]
                # Rules: use module_rules_raw for non-Python — module_rules() uses Python AST skeleton
                rules_str = llm.module_rules_raw(info.rel, snippet)
                llm_calls += 1
            except Exception:
                rules_str = "none"

        agent_id = "codedna-cli (no-llm)" if no_llm else model
        new_source = adapter.inject_header(
            source, info.rel, exports_str, used_by_str, rules_str, agent_id, today
        )

        if new_source != source:
            if not dry_run:
                path.write_text(new_source, encoding="utf-8")
            annotated += 1
            if verbose:
                print(f"  L1  {info.rel}  exports: {exports_str[:60]}")

    print(f"  Annotated {annotated} non-Python files")
    return annotated, llm_calls


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
    extensions: Optional[list[str]] = None,
):
    effective_root = target if target.is_dir() else target.parent
    if repo_root is None:
        repo_root = effective_root
    all_exts = _normalize_extensions(extensions)
    py_files = collect_files(target, exclude, extensions=[".py"])

    print("CodeDNA Annotator v0.8")
    print(f"Target      {target}")
    print(f"Extensions  {', '.join(all_exts)}")
    print(f"Levels      {levels}")
    print(f"Mode        {'DRY RUN' if dry_run else 'WRITE'}")
    print(f"LLM         {'disabled (--no-llm)' if no_llm else model}")
    print(f"Python      {len(py_files)} files")
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
        if not HAS_LITELLM and not HAS_ANTHROPIC:
            print("  Warning: no LLM backend found.")
            print("           Run: pip install 'codedna[litellm]'  (all providers)")
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
                agent_id = "codedna-cli (no-llm)" if no_llm else model
                docstring = build_module_docstring(info, ub, rules, agent_id)
                modified = inject_module_docstring(modified, docstring)
                l1_count += 1
                file_changed = True

                if verbose:
                    print(f"    L1  rules: {rules[:70]}")

        # Write
        if file_changed and modified != source:
            if not dry_run:
                info.path.write_text(modified, encoding="utf-8")

    # Non-Python languages
    if any(e != ".py" for e in all_exts):
        _, lang_llm_calls = run_lang_files(
            target=target,
            extensions=all_exts,
            repo_root=repo_root,
            exclude=exclude,
            model=model,
            dry_run=dry_run,
            force=force,
            no_llm=no_llm,
            verbose=verbose,
            api_key=api_key,
        )
        llm_calls += lang_llm_calls

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


# ── Refresh command ───────────────────────────────────────────────────────────


def _parse_existing_docstring(docstring: str) -> dict[str, str]:
    """Parse a CodeDNA docstring into field dict, preserving raw values.

    Rules:   Must preserve multi-line field values (rules: with continuations).
             Returns dict with keys: first_line, exports, used_by, rules, agent (+ any message: lines).
    """
    fields: dict[str, str] = {}
    current_field = None
    current_lines: list[str] = []

    for i, line in enumerate(docstring.splitlines()):
        stripped = line.strip()
        if i == 0:
            fields["first_line"] = stripped
            continue

        # Check if line starts a new field
        for field_name in ("exports:", "used_by:", "rules:", "agent:"):
            if stripped.startswith(field_name):
                if current_field:
                    fields[current_field] = "\n".join(current_lines)
                current_field = field_name.rstrip(":")
                current_lines = [stripped]
                break
        else:
            # Continuation line (indented) or blank
            if current_field and stripped:
                current_lines.append(stripped)

    if current_field:
        fields[current_field] = "\n".join(current_lines)

    return fields


def _rebuild_docstring(fields: dict[str, str], new_exports: str, new_used_by: str) -> str:
    """Rebuild a CodeDNA docstring with updated exports/used_by, preserving rules/agent/message.

    Rules:   Must preserve the exact rules: and agent: (including message: sub-fields).
             Only exports: and used_by: are replaced.
    """
    first_line = fields.get("first_line", "module — unknown.")
    rules = fields.get("rules", "rules:   none")
    agent = fields.get("agent", "agent:   unknown")

    lines = [
        f'"""{first_line}',
        "",
        f"exports: {new_exports}",
        f"used_by: {new_used_by}",
        rules,
        agent,
        '"""',
    ]
    return "\n".join(lines) + "\n"


def cmd_refresh(target: Path, repo_root: Optional[Path], exclude: list[str],
                dry_run: bool, verbose: bool):
    """Refresh exports: and used_by: via AST. Zero LLM cost.

    Rules:   Only updates files that already have CodeDNA headers.
             Only changes exports: and used_by: — preserves rules:, agent:, message:.
             Scans the ENTIRE project to build the used_by graph, even if target is a single file.
    """
    if repo_root is None:
        repo_root = target if target.is_dir() else target.parent

    # Scan all Python files in project for complete dependency graph
    all_py = collect_files(repo_root, exclude, extensions=[".py"])

    print("CodeDNA Refresh v0.8")
    print(f"Target      {target}")
    print(f"Mode        {'DRY RUN' if dry_run else 'WRITE'}")
    print(f"Python      {len(all_py)} files scanned for dependency graph")
    print()

    # Pass 1: scan all files
    infos: dict[str, FileInfo] = {}
    for f in all_py:
        info = scan_file(f, repo_root)
        if info.parseable:
            infos[info.rel] = info

    # Pass 2: build used_by graph from ALL files
    ub_graph = build_used_by(infos)

    # Pass 3: determine which files to refresh
    if target.is_file():
        targets = {str(target.relative_to(repo_root)): infos.get(str(target.relative_to(repo_root)))}
    else:
        targets = infos

    updated = 0
    skipped = 0

    for rel, info in targets.items():
        if info is None or not info.has_codedna:
            skipped += 1
            if verbose:
                print(f"  skip (no header)   {rel}")
            continue

        # Parse existing docstring
        if not info.docstring:
            skipped += 1
            continue

        old_fields = _parse_existing_docstring(info.docstring)
        new_exports = _fmt_exports(info.exports)
        new_used_by = _fmt_used_by(ub_graph.get(rel, {}))

        # Check if anything changed
        old_exports_raw = old_fields.get("exports", "")
        old_used_by_raw = old_fields.get("used_by", "")

        # Normalize for comparison
        old_exp_val = old_exports_raw.replace("exports:", "").strip() if old_exports_raw else ""
        old_ub_val = old_used_by_raw.replace("used_by:", "").strip() if old_used_by_raw else ""

        if old_exp_val == new_exports and old_ub_val == new_used_by:
            if verbose:
                print(f"  unchanged          {rel}")
            continue

        # Rebuild docstring
        new_docstring = _rebuild_docstring(old_fields, new_exports, new_used_by)

        # Replace in source
        source = info.path.read_text(encoding="utf-8", errors="replace")
        new_source = inject_module_docstring(source, new_docstring)

        if not dry_run:
            info.path.write_text(new_source, encoding="utf-8")

        updated += 1
        if verbose or True:  # always show updates
            changes = []
            if old_exp_val != new_exports:
                changes.append("exports")
            if old_ub_val != new_used_by:
                changes.append("used_by")
            print(f"  {'DRY ' if dry_run else ''}updated  {rel}  ({', '.join(changes)})")

    print()
    print(f"Refreshed {updated} files ({skipped} skipped, {len(targets)} total)")
    return 0


# ── Check command ─────────────────────────────────────────────────────────────


def cmd_check(target: Path, repo_root: Optional[Path], exclude: list[str], verbose: bool,
              extensions: Optional[list[str]] = None):
    """Report annotation coverage without modifying any files."""
    effective_root = target if target.is_dir() else target.parent
    if repo_root is None:
        repo_root = effective_root
    all_exts = _normalize_extensions(extensions)

    py_files = collect_files(target, exclude, extensions=[".py"])
    lang_files = [f for e in all_exts if e != ".py" for f in collect_files(target, exclude, extensions=[e])]
    print("CodeDNA Check")
    print(f"Target      {target}")
    print(f"Extensions  {', '.join(all_exts)}")
    print(f"Python      {len(py_files)} files")
    if lang_files:
        print(f"Other       {len(lang_files)} files")
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

    # Non-Python coverage
    lang_missing = []
    for path in lang_files:
        adapter = get_adapter(_get_extension(path))
        if adapter is None:
            continue
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(path.relative_to(effective_root))
        if not adapter.has_codedna_header(source):
            lang_missing.append(rel)

    if lang_files:
        lang_annotated = len(lang_files) - len(lang_missing)
        lang_pct = 100 * lang_annotated // len(lang_files) if lang_files else 100
        print(f"L1 non-Python headers  {lang_annotated}/{len(lang_files)}  ({lang_pct}%)")
        if verbose and lang_missing:
            print("Missing non-Python L1:")
            for r in lang_missing:
                print(f"  {r}")
        print()

    ok = (
        (annotated_l1 == total - unparseable)
        and (annotated_l2 == total - unparseable)
        and not lang_missing
    )
    print("OK — fully annotated" if ok else "INCOMPLETE — run `codedna init` to annotate missing files")
    if lang_missing and not py_files:
        return 0 if not lang_missing else 1
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
    sub.add_argument(
        "--extensions", nargs="*", default=None, metavar="EXT",
        help=(
            f"Extra file extensions to annotate (Python always included). "
            f"Examples: ts go  or  .ts .tsx .go. "
            f"Supported non-Python: {', '.join(SUPPORTED_EXTENSIONS)}"
        ),
    )
    sub.add_argument(
        "--auto", action="store_true",
        help="Auto-detect languages in the project and annotate all supported file types",
    )
    sub.add_argument("-v", "--verbose", action="store_true", help="Per-file progress")


# ── Install command ───────────────────────────────────────────────────────────

_TOOL_FILES = {
    "claude":   ("CLAUDE.md",   "CLAUDE.md"),
    "cursor":   (".cursorrules", ".cursorrules"),
    "copilot":  ("copilot-instructions.md", ".github/copilot-instructions.md"),
    "cline":    (".clinerules",  ".clinerules"),
    "windsurf": (".windsurfrules", ".windsurfrules"),
    "opencode": ("AGENTS.md",   "AGENTS.md"),
    "agents":   (".agents/workflows/codedna.md", ".agents/workflows/codedna.md"),
}

# Hook-based integrations: tool name -> (list of (remote_path, local_path), settings_template)
# These require script files + settings.json, not just a prompt file.
_HOOK_TOOLS = {
    "claude-hooks",
    "cursor-hooks",
    "copilot-hooks",
    "cline-hooks",
    "opencode-hooks",
}

# Maps base tool name to its -hooks variant for auto-detect
_TOOL_HOOKS_MAP = {
    "claude": "claude-hooks",
    "cursor": "cursor-hooks",
    "copilot": "copilot-hooks",
    "cline": "cline-hooks",
    "opencode": "opencode-hooks",
}

# Maps -hooks variant back to its base tool (for auto-including the prompt file)
_HOOKS_BASE_MAP = {
    "claude-hooks": "claude",
    "cursor-hooks": "cursor",
    "copilot-hooks": "copilot",
    "cline-hooks": "cline",
    "opencode-hooks": "opencode",
}

_PRE_COMMIT_HOOK = r'''#!/usr/bin/env bash
# CodeDNA v0.8 pre-commit hook — validates staged files.
# Installed by: codedna install

set -euo pipefail

CODEDNA=""
for cmd in codedna; do
    if command -v "$cmd" &>/dev/null; then
        CODEDNA="$cmd"
        break
    fi
done

if [[ -z "$CODEDNA" ]]; then
    echo "WARNING: codedna CLI not found in PATH — skipping validation"
    echo "         pip install codedna"
    exit 0
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"

# Collect staged source files (new, modified, copied)
STAGED=$(git diff --cached --name-only --diff-filter=ACM \
    | grep -E '\.(py|ts|tsx|js|jsx|mjs|go|php|rs|java|kt|kts|rb|cs|swift|blade\.php|j2|jinja2|twig|erb|ejs|hbs|mustache|cshtml|razor|vue|svelte)$' \
    || true)

if [[ -z "$STAGED" ]]; then
    exit 0
fi

echo "CodeDNA v0.8 — validating staged files..."

# Detect extensions in use
EXTS=""
for f in $STAGED; do
    # Handle compound extensions (e.g. .blade.php)
    if [[ "$f" == *.blade.php ]]; then
        EXTS="$EXTS blade.php"
        continue
    fi
    ext="${f##*.}"
    case "$ext" in
        ts|tsx|js|jsx|mjs) EXTS="$EXTS ts" ;;
        go)                EXTS="$EXTS go" ;;
        rs)                EXTS="$EXTS rs" ;;
        java)              EXTS="$EXTS java" ;;
        kt|kts)            EXTS="$EXTS kt" ;;
        rb)                EXTS="$EXTS rb" ;;
        cs)                EXTS="$EXTS cs" ;;
        swift)             EXTS="$EXTS swift" ;;
        j2|jinja2)         EXTS="$EXTS j2" ;;
        twig)              EXTS="$EXTS twig" ;;
        erb)               EXTS="$EXTS erb" ;;
        ejs)               EXTS="$EXTS ejs" ;;
        hbs|mustache)      EXTS="$EXTS hbs" ;;
        cshtml|razor)      EXTS="$EXTS cshtml" ;;
        vue)               EXTS="$EXTS vue" ;;
        svelte)            EXTS="$EXTS svelte" ;;
    esac
done
# Deduplicate
EXTS=$(echo "$EXTS" | tr ' ' '\n' | sort -u | tr '\n' ' ')

# Build codedna check args
ARGS=""
if [[ -n "$EXTS" ]]; then
    ARGS="--extensions $EXTS"
fi

# Validate each staged file individually
ERRORS=0
for FILE in $STAGED; do
    FULL="$REPO_ROOT/$FILE"
    [[ -f "$FULL" ]] || continue

    OUTPUT=$("$CODEDNA" check "$FULL" $ARGS 2>&1) || true

    if echo "$OUTPUT" | grep -q "INCOMPLETE"; then
        ERRORS=$((ERRORS + 1))
        echo ""
        echo "FAIL  $FILE"
        echo "      Missing CodeDNA v0.8 header"
    fi
done

echo ""
if [[ $ERRORS -gt 0 ]]; then
    echo "Commit blocked: $ERRORS file(s) missing CodeDNA v0.8 annotations."
    echo ""
    echo "Quick fix:  codedna init <path> --no-llm    (structural only, instant)"
    echo "Full fix:   codedna init <path>              (with AI-generated rules:)"
    echo "Skip once:  git commit --no-verify"
    exit 1
fi

echo "All staged files pass CodeDNA v0.8 validation."
exit 0
'''

_CODEDNA_TEMPLATE = """# .codedna — CodeDNA project manifest
project: {project_name}
description: "{project_name} project"
mode: semi    # human | semi | agent

packages: {{}}

cross_cutting_patterns: {{}}

agent_sessions: []
"""


def _detect_ai_tools(repo_root: Path) -> list[str]:
    """Detect which AI coding tools are likely in use based on existing config files.

    Rules:   Only checks for file existence — never reads file contents.
             When a tool is detected, include its -hooks variant if available.
    """
    list_str_detected_tools = []
    checks = {
        "claude":   [".claude", "CLAUDE.md"],
        "cursor":   [".cursor", ".cursorrules"],
        "copilot":  [".github/copilot-instructions.md"],
        "cline":    [".clinerules", ".cline"],
        "windsurf": [".windsurfrules", ".windsurf"],
        "opencode": ["AGENTS.md", ".opencode"],
    }
    for tool, paths in checks.items():
        for p in paths:
            if (repo_root / p).exists():
                list_str_detected_tools.append(tool)
                # Anche la variante hooks se disponibile
                if tool in _TOOL_HOOKS_MAP:
                    list_str_detected_tools.append(_TOOL_HOOKS_MAP[tool])
                break
    return list_str_detected_tools


def _install_claude_hooks(repo_root: Path) -> int:
    """Install hook scripts and settings.local.json for Claude Code.

    Rules:   Do not overwrite settings.local.json if it exists — show merge instructions.
             Scripts go in tools/ with chmod +x.
    """
    import stat
    import urllib.request

    str_tools_raw = "https://raw.githubusercontent.com/Larens94/codedna/main/tools"
    int_count = 0

    # Create tools/ directory
    path_tools = repo_root / "tools"
    path_tools.mkdir(exist_ok=True)

    # Download hook scripts
    hooks = {
        "claude_hook_codedna.sh": "PostToolUse validation script",
        "claude_hook_stop.sh": "Stop session-end protocol",
        "validate_manifests.py": "Manifest validator",
    }

    for filename, desc in hooks.items():
        path_dest = path_tools / filename
        str_url = f"{str_tools_raw}/{filename}"
        try:
            urllib.request.urlretrieve(str_url, str(path_dest))
            if filename.endswith(".sh"):
                path_dest.chmod(path_dest.stat().st_mode | stat.S_IEXEC)
            int_count += 1
        except Exception as e:
            print(f"  FAIL  {filename} — could not fetch: {e}")

    if int_count > 0:
        print(f"  OK    Claude Hooks -> tools/ ({int_count} files)")

    # Crea o avvisa per settings.local.json
    path_settings = repo_root / ".claude" / "settings.local.json"
    if path_settings.exists():
        print("  !!    .claude/settings.local.json already exists — merge hooks manually")
        print("        See: https://github.com/Larens94/codedna#claude-code-hooks")
    else:
        path_settings.parent.mkdir(parents=True, exist_ok=True)
        path_settings.write_text(_CLAUDE_HOOKS_SETTINGS, encoding="utf-8")
        print("  OK    .claude/settings.local.json (hooks configured)")
        int_count += 1

    return int_count


def _install_cursor_hooks(repo_root: Path) -> int:
    """Installa hook scripts per Cursor."""
    import stat
    import urllib.request

    str_raw = "https://raw.githubusercontent.com/Larens94/codedna/main/integrations/cursor-hooks"
    str_tools_raw = "https://raw.githubusercontent.com/Larens94/codedna/main/tools"
    int_count = 0

    path_hooks = repo_root / ".cursor" / "hooks"
    path_hooks.mkdir(parents=True, exist_ok=True)
    path_tools = repo_root / "tools"
    path_tools.mkdir(exist_ok=True)

    files = [
        (f"{str_raw}/after-file-edit.sh", path_hooks / "after-file-edit.sh"),
        (f"{str_raw}/stop.sh", path_hooks / "stop.sh"),
        (f"{str_tools_raw}/validate_manifests.py", path_tools / "validate_manifests.py"),
    ]
    for url, dest in files:
        try:
            urllib.request.urlretrieve(url, str(dest))
            if dest.suffix == ".sh":
                dest.chmod(dest.stat().st_mode | stat.S_IEXEC)
            int_count += 1
        except Exception as e:
            print(f"  FAIL  {dest.name} — could not fetch: {e}")

    if int_count > 0:
        print(f"  OK    Cursor Hooks -> .cursor/hooks/ ({int_count} files)")
    return int_count


def _install_copilot_hooks(repo_root: Path) -> int:
    """Installa hook scripts per GitHub Copilot."""
    import stat
    import urllib.request

    str_raw = "https://raw.githubusercontent.com/Larens94/codedna/main/integrations/copilot-hooks"
    str_tools_raw = "https://raw.githubusercontent.com/Larens94/codedna/main/tools"
    int_count = 0

    path_hooks = repo_root / ".github" / "hooks"
    path_hooks.mkdir(parents=True, exist_ok=True)
    path_tools = repo_root / "tools"
    path_tools.mkdir(parents=True, exist_ok=True)

    files = [
        (f"{str_raw}/hooks.json", path_hooks / "hooks.json"),
        (f"{str_raw}/codedna.sh", path_hooks / "codedna.sh"),
        (f"{str_tools_raw}/validate_manifests.py", path_tools / "validate_manifests.py"),
    ]
    for url, dest in files:
        try:
            urllib.request.urlretrieve(url, str(dest))
            if dest.suffix == ".sh":
                dest.chmod(dest.stat().st_mode | stat.S_IEXEC)
            int_count += 1
        except Exception as e:
            print(f"  FAIL  {dest.name} — could not fetch: {e}")

    if int_count > 0:
        print(f"  OK    Copilot Hooks -> .github/hooks/ ({int_count} files)")
    return int_count


def _install_cline_hooks(repo_root: Path) -> int:
    """Installa hook scripts per Cline."""
    import stat
    import urllib.request

    str_raw = "https://raw.githubusercontent.com/Larens94/codedna/main/integrations/cline-hooks"
    int_count = 0

    # .clinerules may be a flat file (prompt) — hooks require it to be a directory
    path_clinerules = repo_root / ".clinerules"
    if path_clinerules.exists() and path_clinerules.is_file():
        # Move existing prompt file inside the new directory as rules.md
        str_content = path_clinerules.read_text(encoding="utf-8", errors="replace")
        path_clinerules.unlink()
        path_clinerules.mkdir(parents=True, exist_ok=True)
        (path_clinerules / "rules.md").write_text(str_content, encoding="utf-8")
        print("  INFO  .clinerules converted: file -> directory (.clinerules/rules.md)")

    path_hooks = path_clinerules / "hooks"
    path_hooks.mkdir(parents=True, exist_ok=True)

    files = [
        (f"{str_raw}/PostToolUse.sh", path_hooks / "PostToolUse.sh"),
        (f"{str_raw}/TaskStart.sh", path_hooks / "TaskStart.sh"),
    ]
    for url, dest in files:
        try:
            urllib.request.urlretrieve(url, str(dest))
            dest.chmod(dest.stat().st_mode | stat.S_IEXEC)
            int_count += 1
        except Exception as e:
            print(f"  FAIL  {dest.name} — could not fetch: {e}")

    if int_count > 0:
        print(f"  OK    Cline Hooks -> .clinerules/hooks/ ({int_count} files)")
    return int_count


def _install_opencode_hooks(repo_root: Path) -> int:
    """Installa il plugin JS per OpenCode (.opencode/plugins/codedna.js)."""
    import urllib.request

    str_raw = "https://raw.githubusercontent.com/Larens94/codedna/main/integrations/opencode-plugin"
    int_count = 0

    path_plugins = repo_root / ".opencode" / "plugins"
    path_plugins.mkdir(parents=True, exist_ok=True)

    path_dest = path_plugins / "codedna.js"
    str_url = f"{str_raw}/codedna.js"
    try:
        urllib.request.urlretrieve(str_url, str(path_dest))
        int_count += 1
        print("  OK    OpenCode Plugin -> .opencode/plugins/codedna.js")
    except Exception as e:
        print(f"  FAIL  codedna.js — could not fetch: {e}")

    return int_count


# Dispatch per hook installers
_HOOK_INSTALLERS = {
    "claude-hooks": _install_claude_hooks,
    "cursor-hooks": _install_cursor_hooks,
    "copilot-hooks": _install_copilot_hooks,
    "cline-hooks": _install_cline_hooks,
    "opencode-hooks": _install_opencode_hooks,
}


_CLAUDE_HOOKS_SETTINGS = r'''{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [{
          "type": "command",
          "command": "codedna=\".codedna\"; if [[ -f \"$codedna\" ]]; then pkgs=$(grep -c 'purpose:' \"$codedna\" 2>/dev/null || echo 0); proj=$(grep '^project:' \"$codedna\" | head -1 | cut -d' ' -f2-); echo \"{\\\"hookSpecificOutput\\\":{\\\"hookEventName\\\":\\\"SessionStart\\\",\\\"additionalContext\\\":\\\"[CodeDNA] Project: $proj — $pkgs documented modules. Read .codedna and CLAUDE.md before editing source files. Every source edit requires updating agent: with today's date.\\\"}}\"; fi",
          "timeout": 5
        }]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{
          "type": "command",
          "command": "f=$(echo $TOOL_INPUT | python3 -c \"import json,sys; print(json.load(sys.stdin).get('file_path',''))\" 2>/dev/null); [[ -n \"$f\" ]] && echo \"$f\" | grep -qE '\\.(py|ts|tsx|js|go|rs|java|kt|swift|rb|cs|php)$' && echo '{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"additionalContext\":\"[CodeDNA] Source file. Before editing: (1) read the docstring, (2) verify exports/used_by/rules/agent, (3) plan agent: update with the current session.\"}}' || true",
          "timeout": 5
        }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [{ "type": "command", "command": "bash tools/claude_hook_codedna.sh", "timeout": 10, "statusMessage": "CodeDNA v0.8 — validating annotations..." }]
      },
      {
        "matcher": "Edit",
        "hooks": [{ "type": "command", "command": "bash tools/claude_hook_codedna.sh", "timeout": 10, "statusMessage": "CodeDNA v0.8 — validating annotations..." }]
      }
    ],
    "Stop": [
      {
        "hooks": [{ "type": "command", "command": "bash tools/claude_hook_stop.sh", "timeout": 5, "statusMessage": "CodeDNA v0.8 — checking session end protocol..." }]
      },
      {
        "hooks": [{
          "type": "command",
          "command": "echo '{\"systemMessage\": \"[CodeDNA] Remember: update .codedna with a new agent_sessions entry (agent, provider, date, session_id, task, changed, visited, message).\"}'",
          "timeout": 5
        }]
      }
    ]
  }
}
'''


def cmd_install(repo_root: Path, tools: list[str], skip_hook: bool = False,
                skip_prompt: bool = False) -> int:
    """Setup CodeDNA in a project: pre-commit hook + AI tool prompt + .codedna.

    Rules:   Never overwrite an existing pre-commit hook without --force.
             Always create .codedna if missing.
             Prompt files are fetched from GitHub raw; fall back to a minimal template on network error.
    """
    import stat
    import urllib.request

    str_raw_base_url = "https://raw.githubusercontent.com/Larens94/codedna/main/integrations"

    print("CodeDNA v0.8 — Project Setup")
    print(f"  Target: {repo_root}")
    print()

    int_count_installed = 0

    # 1. Git pre-commit hook
    if not skip_hook:
        path_git_dir = repo_root / ".git"
        if not path_git_dir.is_dir():
            print("  WARNING: Not a git repository — skipping pre-commit hook")
        else:
            path_hooks_dir = path_git_dir / "hooks"
            path_hooks_dir.mkdir(exist_ok=True)
            path_hook = path_hooks_dir / "pre-commit"

            if path_hook.exists():
                str_existing_content = path_hook.read_text(encoding="utf-8", errors="replace")
                if "CodeDNA" in str_existing_content:
                    print("  SKIP  pre-commit hook (CodeDNA hook already installed)")
                else:
                    print("  SKIP  pre-commit hook (existing hook found — won't overwrite)")
                    print("        To add manually, append CodeDNA validation to your hook")
            else:
                path_hook.write_text(_PRE_COMMIT_HOOK, encoding="utf-8")
                path_hook.chmod(path_hook.stat().st_mode | stat.S_IEXEC)
                print("  OK    pre-commit hook installed")
                int_count_installed += 1

    # 2. AI tool prompt files + hooks
    if not skip_prompt:
        # Auto-include hooks for base tools (e.g. "opencode" → also install "opencode-hooks")
        expanded_tools = list(tools)
        for tool in tools:
            if tool in _TOOL_HOOKS_MAP:
                hooks_variant = _TOOL_HOOKS_MAP[tool]
                if hooks_variant not in expanded_tools:
                    expanded_tools.append(hooks_variant)

        for tool in expanded_tools:
            # Gestione hook-based tools (claude-hooks, cursor-hooks, etc.)
            if tool in _HOOK_INSTALLERS:
                int_count_installed += _HOOK_INSTALLERS[tool](repo_root)
                continue

            if tool not in _TOOL_FILES:
                print(f"  SKIP  {tool} (unknown tool)")
                continue

            str_remote_name, str_local_path = _TOOL_FILES[tool]
            path_dest = repo_root / str_local_path

            if path_dest.exists():
                print(f"  SKIP  {tool} ({str_local_path} already exists)")
                continue

            # Create parent dirs if needed (e.g. .github/)
            path_dest.parent.mkdir(parents=True, exist_ok=True)

            str_url = f"{str_raw_base_url}/{str_remote_name}"
            try:
                urllib.request.urlretrieve(str_url, str(path_dest))
                print(f"  OK    {tool} -> {str_local_path}")
                int_count_installed += 1
            except Exception as e:
                print(f"  FAIL  {tool} — could not fetch {str_url}: {e}")

    # 3. .codedna manifest
    path_codedna = repo_root / ".codedna"
    if path_codedna.exists():
        print("  SKIP  .codedna (already exists)")
    else:
        str_project_name = repo_root.name
        path_codedna.write_text(
            _CODEDNA_TEMPLATE.format(project_name=str_project_name),
            encoding="utf-8",
        )
        print("  OK    .codedna created")
        int_count_installed += 1

    # Summary
    print()
    if int_count_installed > 0:
        print(f"Done — {int_count_installed} component(s) installed.")
    else:
        print("Nothing to install — CodeDNA is already set up.")

    print()
    print("Next steps:")
    print("  codedna init .                  # annotate all detected languages (auto-detect)")
    print("  codedna init . --no-llm         # free — structural only, no API key needed")
    print("  codedna check .                 # verify coverage")
    return 0


# ── Manifest command (Level 0) ────────────────────────────────────────────────

_MANIFEST_SKIP = {"__pycache__", ".git", "venv", ".venv", "node_modules",
                  "migrations", "dist", "build", ".tox", "coverage",
                  "_repo_cache", ".mypy_cache", ".pytest_cache", "htmlcov"}


def _detect_packages(files: list[Path], root: Path) -> dict[str, list[str]]:
    """Group source files by top-level package directory.

    Rules:   A 'package' is the first path segment under root.
             Files directly in root are grouped under '' (root package).
             Directories in _MANIFEST_SKIP are excluded.
    """
    pkgs: dict[str, list[str]] = {}
    for f in files:
        rel = str(f.relative_to(root))
        parts = Path(rel).parts
        pkg = parts[0] if len(parts) > 1 else ""
        if pkg in _MANIFEST_SKIP:
            continue
        pkgs.setdefault(pkg, []).append(rel)
    return pkgs


def _package_depends_on(pkg: str, pkg_files: list[str],
                         infos: dict[str, "FileInfo"]) -> list[str]:
    """Derive inter-package dependencies from import graph.

    Rules:   pkg A depends_on pkg B when any file in A imports from any file in B.
             Self-dependencies are excluded.
    """
    deps: set[str] = set()
    for rel in pkg_files:
        info = infos.get(rel)
        if not info:
            continue
        for dep_rel in info.deps:
            dep_pkg = Path(dep_rel).parts[0] if len(Path(dep_rel).parts) > 1 else ""
            if dep_pkg != pkg and dep_pkg not in _MANIFEST_SKIP:
                deps.add(dep_pkg + "/" if dep_pkg else ".")
    return sorted(deps)


def _key_files(pkg_files: list[str], ub_graph: dict[str, dict],
               infos: dict[str, "FileInfo"], n: int = 5) -> list[str]:
    """Return up to n most-imported (most-referenced) files in a package.

    Rules:   Rank by number of importers in ub_graph; fall back to export count.
             Only return the filename (not full relative path) for readability.
             Deduplicate by filename — skip if same name already included.
    """
    scored: list[tuple[int, str]] = []
    for rel in pkg_files:
        importers = len(ub_graph.get(rel, {}))
        exports = len(infos[rel].exports) if rel in infos else 0
        scored.append((importers * 10 + exports, rel))
    scored.sort(reverse=True)
    seen_names: set[str] = set()
    result: list[str] = []
    for _, rel in scored:
        name = Path(rel).name
        if name not in seen_names:
            seen_names.add(name)
            result.append(name)
        if len(result) >= n:
            break
    return result


def _exports_sample(pkg_files: list[str], infos: dict[str, "FileInfo"]) -> str:
    """Build a compact exports summary for LLM context."""
    parts = []
    for rel in sorted(pkg_files)[:6]:
        info = infos.get(rel)
        if info and info.exports:
            parts.append(f"{Path(rel).name}: {', '.join(info.exports[:4])}")
    return " | ".join(parts)


def _read_existing_codedna(codedna_path: Path) -> dict:
    """Read existing .codedna and extract fields we want to preserve.

    Rules:   Preserves project:, description:, agent_sessions:, cross_cutting_patterns:.
             Uses simple line-based parsing — no PyYAML dependency.
             Returns defaults if file does not exist.
    """
    defaults = {
        "project": codedna_path.parent.name,
        "description": "",
        "agent_sessions_block": "",
        "cross_cutting_block": "cross_cutting_patterns: {}\n",
    }
    if not codedna_path.exists():
        return defaults

    content = codedna_path.read_text(encoding="utf-8")

    # Extract project:
    import re as _re
    m = _re.search(r"^project:\s*(.+)$", content, _re.MULTILINE)
    if m:
        defaults["project"] = m.group(1).strip().strip('"')

    m = _re.search(r'^description:\s*"?(.+?)"?\s*$', content, _re.MULTILINE)
    if m:
        defaults["description"] = m.group(1).strip()

    # Extract agent_sessions block (everything from 'agent_sessions:' to end or next top-level key)
    m = _re.search(r"(^agent_sessions:.*)", content, _re.MULTILINE | _re.DOTALL)
    if m:
        defaults["agent_sessions_block"] = m.group(1)

    # Extract cross_cutting_patterns block
    m = _re.search(r"(^cross_cutting_patterns:.*?)(?=^agent_sessions:|$)",
                   content, _re.MULTILINE | _re.DOTALL)
    if m:
        defaults["cross_cutting_block"] = m.group(1).rstrip() + "\n"

    return defaults


def _write_codedna(
    codedna_path: Path,
    project: str,
    description: str,
    packages: dict[str, dict],  # {pkg_name: {purpose, key_files, depends_on}}
    cross_cutting_block: str,
    agent_sessions_block: str,
    dry_run: bool,
) -> str:
    """Serialise .codedna to YAML-like string and optionally write it.

    Rules:   agent_sessions: block is always appended last and never modified.
             cross_cutting_patterns: is preserved from existing file.
             packages: section is fully regenerated on every manifest run.
             Returns the generated content string regardless of dry_run.
    """
    lines = [
        "# .codedna — CodeDNA project manifest (auto-generated by codedna manifest)",
        f"project: {project}",
    ]
    if description:
        lines.append(f'description: "{description}"')
    lines += ["", "packages:"]

    for pkg_name, data in sorted(packages.items()):
        display = (pkg_name + "/") if pkg_name else "(root)"
        lines.append(f"  {display}:")
        lines.append(f'    purpose: "{data["purpose"]}"')
        if data.get("key_files"):
            kf = ", ".join(data["key_files"])
            lines.append(f"    key_files: [{kf}]")
        if data.get("depends_on"):
            do = ", ".join(data["depends_on"])
            lines.append(f"    depends_on: [{do}]")
        lines.append("")

    lines.append(cross_cutting_block.rstrip())
    lines.append("")

    if agent_sessions_block:
        lines.append(agent_sessions_block.rstrip())
    else:
        lines.append("agent_sessions: []")
    lines.append("")

    content = "\n".join(lines)
    if not dry_run:
        codedna_path.write_text(content, encoding="utf-8")
    return content


def cmd_manifest(
    target: Path,
    repo_root: Optional[Path],
    model: str,
    no_llm: bool,
    dry_run: bool,
    api_key: Optional[str],
    verbose: bool,
    extensions: Optional[list[str]],
    exclude: Optional[list[str]] = None,
):
    """Generate or update .codedna (Level 0 manifest) from codebase structure.

    Rules:   agent_sessions: block is never modified — append-only by design.
             packages: section is regenerated on every run (authoritative from code).
             cross_cutting_patterns: is preserved from existing file unchanged.
             LLM is used only for package purpose: descriptions.
    """
    effective_root = repo_root or target
    all_exts = _normalize_extensions(extensions)
    codedna_path = effective_root / ".codedna"
    excl = exclude or []

    print("CodeDNA Manifest  (Level 0)")
    print(f"Root    {effective_root}")
    print(f"Mode    {'DRY RUN' if dry_run else 'WRITE'}")
    print(f"LLM     {'disabled' if no_llm else model}")
    print()

    # Scan Python files for AST-based import graph
    py_files = collect_files(target, excl, extensions=[".py"])
    infos: dict[str, FileInfo] = {}
    for f in py_files:
        info = scan_file(f, effective_root)
        if info.parseable:
            infos[info.rel] = info
    ub_graph = build_used_by(infos)

    # Also collect non-Python files for package detection
    lang_exts = [e for e in all_exts if e != ".py"]
    all_files = list(py_files)
    for e in lang_exts:
        all_files.extend(collect_files(target, excl, extensions=[e]))

    pkg_map = _detect_packages(all_files, effective_root)
    if not pkg_map:
        print("No source files found.")
        return 1

    print(f"Packages detected: {len(pkg_map)}")
    for pkg, files in sorted(pkg_map.items()):
        print(f"  {pkg or '(root)':20s}  {len(files)} files")
    print()

    # LLM for package purposes
    llm: Optional[LLM] = None
    if not no_llm:
        try:
            llm = LLM(model=model, api_key=api_key)
        except Exception as e:
            print(f"  Warning: LLM unavailable ({e}). purpose: will be generated from file names.")

    # Build package data
    existing = _read_existing_codedna(codedna_path)
    packages: dict[str, dict] = {}
    llm_calls = 0

    for pkg, files in sorted(pkg_map.items()):
        kf = _key_files(files, ub_graph, infos)
        deps = _package_depends_on(pkg, files, infos)
        exports_sample = _exports_sample(files, infos)

        # Purpose: LLM or fallback
        if llm:
            try:
                purpose = llm.package_purpose(pkg or "root", kf, exports_sample)
                llm_calls += 1
            except Exception as e:
                print(f"  Warning: LLM call failed ({e}). Falling back to file-name heuristic.")
                llm = None  # disable for remaining packages
                names = [Path(f).stem.replace("_", " ") for f in files[:3]]
                purpose = f"{', '.join(names)} module" if names else f"{pkg} package"
        else:
            # Fallback: derive from key file names
            names = [Path(f).stem.replace("_", " ") for f in files
                     if Path(f).stem not in ("__init__", "__main__")][:3]
            purpose = f"{', '.join(names)} module" if names else f"{pkg} package"

        packages[pkg] = {
            "purpose": purpose,
            "key_files": kf,
            "depends_on": deps,
        }

        if verbose:
            print(f"  {pkg or '(root)'}/")
            print(f"    purpose:    {purpose}")
            print(f"    key_files:  {kf}")
            if deps:
                print(f"    depends_on: {deps}")

    # Write
    content = _write_codedna(
        codedna_path=codedna_path,
        project=existing["project"],
        description=existing["description"],
        packages=packages,
        cross_cutting_block=existing["cross_cutting_block"],
        agent_sessions_block=existing["agent_sessions_block"],
        dry_run=dry_run,
    )

    print()
    print("=" * 50)
    print(f"Packages   {len(packages)}")
    print(f"LLM calls  {llm_calls}")
    if dry_run:
        print()
        print("Dry run — .codedna not written. Preview:")
        print()
        print(content[:1200])
    else:
        print(f"Written    {codedna_path}")
    return 0


def main():
    p = argparse.ArgumentParser(
        prog="codedna",
        description="CodeDNA v0.8 — in-source annotation protocol",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subs = p.add_subparsers(dest="command", metavar="COMMAND")
    subs.required = True

    # ── install ───────────────────────────────────────────────────────────────
    install_p = subs.add_parser(
        "install",
        help="Setup CodeDNA in a project (pre-commit hook + AI tool prompt + .codedna)",
        description=(
            "One-command setup for any project. Installs:\n"
            "  1. Git pre-commit hook (multi-language validation)\n"
            "  2. AI tool prompt file (CLAUDE.md, .cursorrules, etc.)\n"
            "  3. .codedna project manifest\n\n"
            "Auto-detects which AI tools are in use. Override with --tools.\n\n"
            "Examples:\n"
            "  codedna install                          # auto-detect tools\n"
            "  codedna install --tools claude cursor     # specific tools\n"
            "  codedna install --tools all               # all supported tools\n"
            "  codedna install --skip-hook               # prompt files only\n"
            "  codedna install --skip-prompt              # hook only"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    install_p.add_argument(
        "--path", type=Path, default=Path("."),
        help="Project root (default: current directory)",
    )
    install_p.add_argument(
        "--tools", nargs="*", default=None,
        help="AI tools to install prompts/hooks for: claude cursor copilot cline windsurf opencode claude-hooks cursor-hooks copilot-hooks cline-hooks opencode-hooks all (default: auto-detect)",
    )
    install_p.add_argument("--skip-hook", action="store_true", help="Skip pre-commit hook installation")
    install_p.add_argument("--skip-prompt", action="store_true", help="Skip AI tool prompt installation")

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

    # ── mode ──────────────────────────────────────────────────────────────────
    mode_p = subs.add_parser(
        "mode",
        help="Get or set the CodeDNA mode (human, semi, agent)",
        description=(
            "Modes control how strict CodeDNA enforcement is:\n"
            "  human  — minimal: L1 headers, Rules: on critical functions only, no semantic naming\n"
            "  semi   — balanced: L1+L2 on new code, semantic naming on new vars (default)\n"
            "  agent  — full: all functions annotated, semantic naming enforced, rename vars\n\n"
            "Examples:\n"
            "  codedna mode              # show current mode\n"
            "  codedna mode semi         # set mode to semi\n"
            "  codedna mode agent        # set mode to agent"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode_p.add_argument("value", nargs="?", choices=["human", "semi", "agent"],
                        help="Mode to set (omit to show current)")
    mode_p.add_argument("--path", type=Path, default=Path("."),
                        help="Project root (default: current directory)")

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
    check_p.add_argument(
        "--extensions", nargs="*", default=None, metavar="EXT",
        help=f"Extra extensions to check. Supported: {', '.join(SUPPORTED_EXTENSIONS)}",
    )
    check_p.add_argument(
        "--auto", action="store_true",
        help="Auto-detect languages in the project and check all supported file types",
    )
    check_p.add_argument("-v", "--verbose", action="store_true", help="List specific files missing annotations")


    # ── refresh ──────────────────────────────────────────────────────────────
    refresh_p = subs.add_parser(
        "refresh",
        help="Refresh exports: and used_by: via AST (zero LLM cost, preserves rules:/agent:/message:)",
        description=(
            "Re-scans the project and updates ONLY the structural fields:\n"
            "  - exports: recalculated from AST\n"
            "  - used_by: recalculated from import graph\n\n"
            "Preserves: rules:, agent:, message: (untouched)\n"
            "Skips: files without existing CodeDNA headers\n\n"
            "Use after refactoring, adding/removing files, or when used_by: is stale.\n"
            "Zero LLM cost — pure AST analysis."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    refresh_p.add_argument("path", type=Path, help="File or directory to refresh")
    refresh_p.add_argument("--repo-root", type=Path, default=None)
    refresh_p.add_argument("--exclude", nargs="*", default=[])
    refresh_p.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    refresh_p.add_argument("-v", "--verbose", action="store_true")

    # ── manifest ─────────────────────────────────────────────────────────────
    manifest_p = subs.add_parser(
        "manifest",
        help="Generate or update .codedna Level 0 manifest from codebase structure",
        description=(
            "Scans the project, detects packages, infers depends_on from imports,\n"
            "and writes (or updates) the .codedna manifest at the project root.\n\n"
            "Preserves: agent_sessions: (append-only) and cross_cutting_patterns:\n"
            "Regenerates: packages: section on every run.\n\n"
            "Run once after `codedna init` to complete the Level 0 setup."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    manifest_p.add_argument("path", type=Path, help="Project root directory")
    manifest_p.add_argument(
        "--model", default="claude-haiku-4-5-20251001",
        help="Model for generating package purpose: descriptions",
    )
    manifest_p.add_argument("--no-llm", action="store_true",
                            help="Skip LLM — derive purpose from file names only")
    manifest_p.add_argument("--dry-run", action="store_true",
                            help="Preview .codedna without writing")
    manifest_p.add_argument("--api-key", default=None)
    manifest_p.add_argument(
        "--extensions", nargs="*", default=None, metavar="EXT",
        help="Include non-Python files in package detection (e.g. ts go php)",
    )
    manifest_p.add_argument("--exclude", nargs="*", default=[],
                            help="Glob patterns to exclude from package detection")
    manifest_p.add_argument("-v", "--verbose", action="store_true",
                            help="Show per-package details")

    # ── wiki ─────────────────────────────────────────────────────────────────
    wiki_p = subs.add_parser(
        "wiki",
        help="Scaffold the semantic wiki companion to .codedna (codedna-wiki.md + create-wiki skill)",
        description=(
            "Create the CodeDNA semantic wiki assets at the project root:\n"
            "  - codedna-wiki.md                         (semantic companion to .codedna)\n"
            "  - .agents/skills/create-wiki/SKILL.md     (repo-local skill)\n\n"
            "Idempotent: existing files are never overwritten.\n"
            "Use --dry-run to preview what would be created."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    wiki_p.add_argument("path", type=Path, nargs="?", default=Path("."),
                        help="Project root (default: current directory)")
    wiki_p.add_argument("--dry-run", action="store_true",
                        help="Report missing files without writing them")

    args = p.parse_args()

    # ── dispatch ──────────────────────────────────────────────────────────────
    if args.command == "mode":
        codedna_path = (args.path / ".codedna").resolve()
        if not codedna_path.exists():
            if args.value:
                # Create .codedna with mode
                codedna_path.write_text(
                    _CODEDNA_TEMPLATE.format(project_name=args.path.resolve().name).replace(
                        "mode: semi", f"mode: {args.value}"
                    ),
                    encoding="utf-8",
                )
                print(f"Created .codedna with mode: {args.value}")
            else:
                print("No .codedna found. Run: codedna install")
            return 0

        content = codedna_path.read_text(encoding="utf-8")
        if args.value:
            # Set mode
            import re
            if re.search(r"^mode:\s*\w+", content, re.MULTILINE):
                content = re.sub(r"^mode:\s*\w+.*$", f"mode: {args.value}", content, count=1, flags=re.MULTILINE)
            else:
                # Add mode after description line
                content = content.replace("\n\npackages:", f"\nmode: {args.value}\n\npackages:")
            codedna_path.write_text(content, encoding="utf-8")
            print(f"Mode set to: {args.value}")
        else:
            # Show current mode
            import re
            m = re.search(r"^mode:\s*(\w+)", content, re.MULTILINE)
            if m:
                print(f"Current mode: {m.group(1)}")
            else:
                print("Mode not set. Default: semi")
                print("Set with: codedna mode <human|semi|agent>")
        return 0

    if args.command == "install":
        path_repo_root = args.path.resolve()
        if not path_repo_root.exists():
            print(f"Error: {path_repo_root} does not exist", file=sys.stderr)
            return 1

        # Resolve tools list
        if args.tools is None:
            list_str_tools = _detect_ai_tools(path_repo_root)
            if not list_str_tools:
                list_str_tools = ["claude"]  # sensible default
                print("  No AI tool detected — defaulting to Claude Code")
        elif "all" in args.tools:
            list_str_tools = list(_TOOL_FILES.keys()) + list(_HOOK_INSTALLERS.keys())
        else:
            list_str_tools = list(args.tools)
            # Auto-include base prompt when -hooks variant is requested
            # e.g. claude-hooks -> also install claude (CLAUDE.md)
            for tool in args.tools:
                if tool in _HOOKS_BASE_MAP:
                    str_base_tool = _HOOKS_BASE_MAP[tool]
                    if str_base_tool not in list_str_tools:
                        list_str_tools.insert(list_str_tools.index(tool), str_base_tool)

        return cmd_install(
            repo_root=path_repo_root,
            tools=list_str_tools,
            skip_hook=args.skip_hook,
            skip_prompt=args.skip_prompt,
        )

    if args.command == "manifest":
        target = args.path.resolve()
        if not target.exists():
            print(f"Error: {target} does not exist", file=sys.stderr)
            return 1
        exts = _normalize_extensions(getattr(args, "extensions", None))
        return cmd_manifest(
            target=target,
            repo_root=target,
            model=args.model,
            no_llm=args.no_llm,
            dry_run=args.dry_run,
            api_key=args.api_key,
            verbose=args.verbose,
            extensions=exts,
            exclude=list(args.exclude),
        )

    if args.command == "wiki":
        path_project_root = args.path.resolve()
        if not path_project_root.exists():
            print(f"Error: {path_project_root} does not exist", file=sys.stderr)
            return 1
        obj_wiki_result = ensure_wiki_scaffold(path_project_root, dry_run=args.dry_run)
        if obj_wiki_result.created:
            verb = "Would create" if args.dry_run else "Created"
            for str_path in obj_wiki_result.created:
                print(f"{verb:<11} {str_path}")
        for str_path in obj_wiki_result.existing:
            print(f"Reused      {str_path}")
        if not obj_wiki_result.created and not obj_wiki_result.existing:
            print("No wiki assets to scaffold.")
        return 0

    if args.command == "refresh":
        target = args.path.resolve()
        if not target.exists():
            print(f"Error: {target} does not exist", file=sys.stderr)
            return 1
        repo_root = args.repo_root.resolve() if args.repo_root else None
        return cmd_refresh(target, repo_root, list(args.exclude), args.dry_run, args.verbose)

    if args.command == "check":
        target = args.path.resolve()
        if not target.exists():
            print(f"Error: {target} does not exist", file=sys.stderr)
            return 1
        repo_root = args.repo_root.resolve() if args.repo_root else None
        if not getattr(args, "extensions", None):
            exts = _auto_detect_extensions(target)
            print(f"Auto-detected: {', '.join(exts)}")
        else:
            exts = _normalize_extensions(args.extensions)
        return cmd_check(target, repo_root, list(args.exclude), args.verbose, extensions=exts)

    # init / update share the same run() — only difference is force flag
    target = args.path.resolve()
    if not target.exists():
        print(f"Error: {target} does not exist", file=sys.stderr)
        return 1

    force = getattr(args, "force", False)  # update never forces
    repo_root = args.repo_root.resolve() if args.repo_root else None
    if not getattr(args, "extensions", None):
        exts = _auto_detect_extensions(target)
        print(f"Auto-detected: {', '.join(exts)}")
    else:
        exts = _normalize_extensions(args.extensions)

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
        extensions=exts,
    )

    if args.command == "init":
        path_project_root = repo_root or (target if target.is_dir() else target.parent)
        obj_wiki_result = ensure_wiki_scaffold(path_project_root, dry_run=args.dry_run)
        if obj_wiki_result.created or obj_wiki_result.existing:
            print()
            print("Wiki scaffold")
            if obj_wiki_result.created:
                verb = "Would create" if args.dry_run else "Created"
                for str_path in obj_wiki_result.created:
                    print(f"  {verb:<11} {str_path}")
            for str_path in obj_wiki_result.existing:
                print(f"  Reused      {str_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
