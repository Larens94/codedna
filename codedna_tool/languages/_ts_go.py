"""_ts_go.py — Tree-sitter-powered CodeDNA adapter for Go source files.

exports: _GO_LANG | _FUNC_QUERY | _METHOD_QUERY | _TYPE_QUERY | _CONST_QUERY | _VAR_QUERY | _IMPORT_QUERY | class TreeSitterGoAdapter
used_by: codedna_tool/languages/__init__.py → TreeSitterGoAdapter
rules:   Requires tree-sitter and tree-sitter-go installed.
Falls back to regex GoAdapter for inject_header().
Export detection: only capitalized identifiers (Go convention).
Import paths are captured but not resolved to file paths (requires go.mod parsing).
agent:   claude-opus-4-6 | anthropic | 2026-04-14 | s_20260414_001 | initial tree-sitter Go adapter
"""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Language
import tree_sitter_go as ts_go

from .base import LangFileInfo
from ._treesitter import TreeSitterAdapter
from .go import GoAdapter

_GO_LANG = Language(ts_go.language())

_FUNC_QUERY = """
(function_declaration
  name: (identifier) @name)
"""

_METHOD_QUERY = """
(method_declaration
  name: (field_identifier) @name)
"""

_TYPE_QUERY = """
(type_declaration
  (type_spec name: (type_identifier) @name))
"""

_CONST_QUERY = """
(const_spec name: (identifier) @name)
"""

_VAR_QUERY = """
(var_spec name: (identifier) @name)
"""

_IMPORT_QUERY = """
(import_spec path: (interpreted_string_literal) @source)
"""


class TreeSitterGoAdapter(TreeSitterAdapter):
    """AST-based CodeDNA adapter for .go files.

    Rules:   Uses tree-sitter for accurate export/import extraction.
             Captures functions, methods, types, consts, vars — filtered to exported (capitalized).
             Method receivers are parsed correctly (regex adapter can miss complex receiver types).
             Import paths are package paths — not resolved to file system paths.
    """

    def __init__(self):
        super().__init__(language=_GO_LANG, regex_fallback=GoAdapter())

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a Go file via tree-sitter and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any error.
                 Only capitalized identifiers are treated as exports (Go convention).
                 Import paths are not resolved — go.mod parsing belongs in a separate resolver.
        """
        rel = str(path.relative_to(repo_root))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return LangFileInfo(path=path, rel=rel, parseable=False)

        source_bytes = source.encode("utf-8")

        list_str_exports: list[str] = []
        for query_str in [_FUNC_QUERY, _METHOD_QUERY, _TYPE_QUERY, _CONST_QUERY, _VAR_QUERY]:
            names = self._query_names(source_bytes, query_str)
            for name in names:
                if name[0].isupper() and name not in list_str_exports:
                    list_str_exports.append(name)

        raw_imports = self._query_strings(source_bytes, _IMPORT_QUERY)
        list_str_deps: list[str] = []
        for imp in raw_imports:
            if imp not in list_str_deps:
                list_str_deps.append(imp)

        has_codedna = self.has_codedna_header(source)

        return LangFileInfo(
            path=path,
            rel=rel,
            exports=list_str_exports,
            deps=list_str_deps,
            has_codedna=has_codedna,
        )
