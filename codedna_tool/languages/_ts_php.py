"""_ts_php.py — Tree-sitter-powered CodeDNA adapter for PHP source files.

exports: _PHP_LANG | _ROUTE_RE | class TreeSitterPhpAdapter
used_by: codedna_tool/languages/__init__.py → TreeSitterPhpAdapter
rules:   Requires tree-sitter>=0.25 and tree-sitter-php>=0.24.
language_php() is used — includes full PHP syntax (<?php tag etc.).
Only public methods are captured (visibility_modifier == b'public').
Laravel routes extracted via regex (Route:: calls are nested expressions).
inject_header() delegated to PhpAdapter (// comment format, <?php preserved).
agent:   claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_001 | initial tree-sitter PHP adapter
"""

from __future__ import annotations

import re
from pathlib import Path

from tree_sitter import Language
import tree_sitter_php as ts_php

from .base import LangFileInfo
from ._treesitter import TreeSitterAdapter
from .php import PhpAdapter

_PHP_LANG = Language(ts_php.language_php())

_ROUTE_RE = re.compile(
    r"Route\s*::\s*(?:get|post|put|patch|delete|any|match|resource|apiResource)"
    r"\s*\(\s*['\"]([^'\"]+)['\"]",
    re.MULTILINE,
)

def _t(node) -> str:
    return node.text.decode("utf-8", errors="replace")


class TreeSitterPhpAdapter(TreeSitterAdapter):
    """AST-based CodeDNA adapter for .php files.

    Rules:   Public methods only — visibility_modifier must be b'public'.
             Class/interface/trait names captured unconditionally.
             inject_header() is delegated to PhpAdapter (// format, idempotent).
    """

    def __init__(self):
        super().__init__(language=_PHP_LANG, regex_fallback=PhpAdapter())

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a PHP file via tree-sitter and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any error.
                 One class per file assumed for method prefix (PSR-1 standard).
                 Laravel routes detected via regex — Route:: AST is too nested to query cleanly.
        """
        rel = str(path.relative_to(repo_root))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return LangFileInfo(path=path, rel=rel, parseable=False)

        src = source.encode("utf-8")
        root = self._parser.parse(src).root_node

        exports: list[str] = []
        deps: list[str] = []

        def walk(node) -> None:
            if node.type in ("class_declaration", "interface_declaration",
                             "trait_declaration", "enum_declaration"):
                for c in node.children:
                    if c.type == "name":
                        n = _t(c)
                        if n not in exports:
                            exports.append(n)

            elif node.type == "function_definition":
                if node.parent and node.parent.type in ("program", "namespace_definition"):
                    for c in node.children:
                        if c.type == "name":
                            n = _t(c)
                            if n not in exports:
                                exports.append(n)

            elif node.type == "method_declaration":
                vis = next((c for c in node.children if c.type == "visibility_modifier"), None)
                if vis and vis.text == b"public":
                    for c in node.children:
                        if c.type == "name":
                            n = _t(c)
                            if not n.startswith("__"):
                                cls = next((e for e in exports
                                            if "::" not in e and "route:" not in e), "")
                                entry = f"{cls}::{n}" if cls else n
                                if entry not in exports:
                                    exports.append(entry)

            elif node.type == "namespace_use_declaration":
                for clause in node.children:
                    if clause.type == "namespace_use_clause":
                        for qn in clause.children:
                            if qn.type == "qualified_name":
                                rp = PhpAdapter._resolve_use(_t(qn), repo_root)
                                if rp and rp not in deps:
                                    deps.append(rp)

            for child in node.children:
                walk(child)

        walk(root)

        for route in _ROUTE_RE.findall(source)[:5]:
            entry = f"route:{route}"
            if entry not in exports:
                exports.append(entry)

        return LangFileInfo(
            path=path, rel=rel, exports=exports, deps=deps,
            has_codedna=self.has_codedna_header(source),
        )
