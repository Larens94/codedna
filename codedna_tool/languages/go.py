"""go.py — CodeDNA v0.8 adapter for Go source files.

exports: _FUNC_RE | _TYPE_RE | _VAR_RE | _IMPORT_SINGLE_RE | _IMPORT_BLOCK_RE | class GoAdapter
used_by: codedna_tool/languages/__init__.py → GoAdapter
         codedna_tool/languages/_ts_go.py → GoAdapter
         tests/test_refresh.py → GoAdapter
rules:   regex-based only — no go toolchain dependency required.
Detects exports via capitalized top-level func/type/var/const identifiers.
Import paths from 'import' blocks are captured but not resolved to file paths
(Go module paths don't map 1:1 to repo file paths without go.mod parsing).
agent:   claude-haiku-4-5-20251001 | anthropic | 2026-03-27 | s_20260327_001 | initial Go adapter with regex-based extraction
claude-sonnet-4-6 | anthropic | 2026-03-27 | s_20260327_002 | CodeDNA v0.8 compliance pass: added session_id to agent: field, added Rules: docstrings to extract_info and inject_header
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
