"""go.py — CodeDNA v0.9 adapter for Go source files.

exports: _FUNC_RE | _TYPE_RE | _VAR_RE | _IMPORT_SINGLE_RE | _IMPORT_BLOCK_RE | class GoAdapter
used_by: codedna_tool/languages/__init__.py → GoAdapter
         codedna_tool/languages/_ts_go.py → GoAdapter
         tests/test_refresh.py → GoAdapter
rules:   regex-based only — no go toolchain dependency required.
Detects exports via capitalized top-level func/type/var/const identifiers.
Import paths from 'import' blocks are captured but not resolved to file paths
(Go module paths don't map 1:1 to repo file paths without go.mod parsing).
inject_function_rules() uses // line comments (NOT /** */ blocks — Go has no block doc).
agent:   claude-haiku-4-5-20251001 | anthropic | 2026-03-27 | s_20260327_001 | initial Go adapter with regex-based extraction
claude-sonnet-4-6 | anthropic | 2026-03-27 | s_20260327_002 | CodeDNA v0.9 compliance pass: added session_id to agent: field, added Rules: docstrings to extract_info and inject_header
claude-sonnet-4-6 | anthropic | 2026-04-18 | s_20260418_ts | add inject_function_rules() — injects // Rules: above exported Go functions/methods; handles existing godoc block and no-doc cases
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import LanguageAdapter, LangFileInfo

# Exported identifiers start with a capital letter
_FUNC_RE = re.compile(r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?([A-Z]\w*)\s*\(", re.MULTILINE)
_TYPE_RE = re.compile(r"^type\s+([A-Z]\w*)\s+", re.MULTILINE)
_VAR_RE = re.compile(r"^(?:var|const)\s+([A-Z]\w*)\s", re.MULTILINE)

# Import block: single or multi-line
_IMPORT_SINGLE_RE = re.compile(r'^import\s+"([^"]+)"', re.MULTILINE)
_IMPORT_BLOCK_RE = re.compile(r'"([^"]+)"', re.MULTILINE)


class GoAdapter(LanguageAdapter):
    """CodeDNA adapter for .go files.

    Rules:   Only captures single-file exports (exported = capitalized).
             Internal (unexported) symbols are skipped.
             Import path resolution is omitted — go module paths require go.mod parsing.
    """

    @property
    def comment_prefix(self) -> str:
        return "//"

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a Go source file and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any OSError.
                 Only top-level exported identifiers (capitalized) are captured; method names on
                 unexported receiver types are intentionally skipped.
                 Import paths are package paths only — not resolved to file system paths.
                 Do not add go.mod parsing here; that belongs in a separate resolver layer.
        """
        rel = str(path.relative_to(repo_root))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return LangFileInfo(path=path, rel=rel, parseable=False)

        # Exports: capitalized funcs, types, vars/consts
        list_str_exports: list[str] = []
        for pat in [_FUNC_RE, _TYPE_RE, _VAR_RE]:
            for m in pat.finditer(source):
                name = m.group(1)
                if name not in list_str_exports:
                    list_str_exports.append(name)

        # Imports (package paths only — not resolved to file paths)
        list_str_deps: list[str] = []
        for m in _IMPORT_SINGLE_RE.finditer(source):
            pkg = m.group(1)
            if pkg not in list_str_deps:
                list_str_deps.append(pkg)
        # Multi-line import blocks
        in_block = False
        for line in source.splitlines():
            stripped = line.strip()
            if stripped == "import (":
                in_block = True
                continue
            if in_block:
                if stripped == ")":
                    in_block = False
                    continue
                for m in _IMPORT_BLOCK_RE.finditer(stripped):
                    pkg = m.group(1)
                    if pkg not in list_str_deps:
                        list_str_deps.append(pkg)

        has_codedna = self.has_codedna_header(source)

        return LangFileInfo(
            path=path,
            rel=rel,
            exports=list_str_exports,
            deps=list_str_deps,
            has_codedna=has_codedna,
        )

    def inject_header(self, source: str, rel: str, exports: str, used_by: str,
                      rules: str, model_id: str, today: str) -> str:
        """Prepend a CodeDNA comment block. Returns source unchanged if header already present.

        Rules:   Must be idempotent — if has_codedna_header() returns True, return source unchanged.
                 MUST preserve //go:build and // +build constraint lines before the package declaration;
                 inserting header before these constraints would break the Go toolchain.
                 The 'package' declaration must remain the first non-comment, non-blank statement.
        """
        if self.has_codedna_header(source):
            return source

        header_lines = self._build_header_lines(rel, exports, used_by, rules, model_id, today)
        header = "\n".join(header_lines) + "\n\n"

        # In Go, the 'package' declaration must be first (after optional build constraints).
        # Insert header before the first 'package' line.
        lines = source.splitlines(keepends=True)
        insert_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Preserve //go:build constraints and blank lines before package
            if stripped.startswith("//go:build") or stripped.startswith("// +build") or not stripped:
                insert_idx = i + 1
            elif stripped.startswith("package "):
                break

        before = "".join(lines[:insert_idx])
        after = "".join(lines[insert_idx:])
        return before + header + after

    def inject_function_rules(self, source: str, func, rules_text: str) -> str:
        """Inject a // Rules: line above an exported Go function or method.

        Rules:   Must be idempotent — if func.has_rules is True, return source unchanged.
                 Go uses // line comments for godoc, NOT block comments (/** */).
                 If func.has_doc=True: insert // Rules: line just above func.start_line
                 (at end of the existing // comment block immediately preceding the func).
                 If func.has_doc=False: insert // Rules: as a single line above func.start_line.
                 Detect indentation from the function line — supports indented methods.
                 Caller MUST apply bottom-to-top when injecting multiple funcs to preserve line numbers.
        """
        if func.has_rules:
            return source

        lines = source.splitlines(keepends=True)
        method_idx = func.start_line - 1  # 0-based index of function's first line

        # Detect indentation from the function line
        method_line = lines[method_idx] if method_idx < len(lines) else ""
        indent = len(method_line) - len(method_line.lstrip())
        pad = " " * indent

        rules_line = f"{pad}// Rules:   {rules_text}\n"

        if func.has_doc:
            # Find the last // comment line of the existing godoc block above the function.
            # Walk upward from method_idx-1 while lines are // comments at the same indent.
            insert_before = method_idx
            idx = method_idx - 1
            while idx >= 0:
                stripped = lines[idx].strip()
                if stripped.startswith("//"):
                    insert_before = idx
                    idx -= 1
                else:
                    break
            # Insert Rules: at insert_before (start of existing comment block) is wrong —
            # we want to append at the END of the block, just before func.start_line.
            # So insert just before method_idx (after the last // comment line).
            lines = lines[:method_idx] + [rules_line] + lines[method_idx:]
        else:
            # No existing doc — insert a single // Rules: line above the function
            lines = lines[:method_idx] + [rules_line] + lines[method_idx:]

        return "".join(lines)
