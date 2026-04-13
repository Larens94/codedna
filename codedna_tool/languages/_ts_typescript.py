"""_ts_typescript.py — Tree-sitter-powered CodeDNA adapter for TypeScript/JavaScript.

exports: TreeSitterTypeScriptAdapter(TreeSitterAdapter)
used_by: languages/__init__.py → _REGISTRY
rules:   Requires tree-sitter and tree-sitter-typescript installed.
         Falls back to regex TypeScriptAdapter for inject_header().
         Only relative imports (starting with '.') are resolved to file paths.
agent:   claude-opus-4-6 | anthropic | 2026-04-14 | s_20260414_001 | initial tree-sitter TS/JS adapter
"""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Language
import tree_sitter_typescript as ts_ts

from .base import LangFileInfo
from ._treesitter import TreeSitterAdapter
from .typescript import TypeScriptAdapter

_TS_LANG = Language(ts_ts.language_typescript())

_EXPORT_QUERY = """
(export_statement
  declaration: [
    (function_declaration name: (identifier) @name)
    (class_declaration name: (type_identifier) @name)
    (lexical_declaration (variable_declarator name: (identifier) @name))
    (type_alias_declaration name: (type_identifier) @name)
    (interface_declaration name: (type_identifier) @name)
  ])

(export_statement
  "default"
  declaration: [
    (function_declaration name: (identifier) @name)
    (class_declaration name: (type_identifier) @name)
  ])
"""

_IMPORT_QUERY = """
(import_statement source: (string) @source)
"""


class TreeSitterTypeScriptAdapter(TreeSitterAdapter):
    """AST-based CodeDNA adapter for .ts, .tsx, .js, .jsx, .mjs files.

    Rules:   Uses tree-sitter for accurate export/import extraction.
             Captures named exports, default exports, type/interface exports.
             Barrel re-exports (export * from) are not captured (same as regex adapter).
    """

    def __init__(self):
        super().__init__(language=_TS_LANG, regex_fallback=TypeScriptAdapter())

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a TS/JS file via tree-sitter and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any error.
                 Only relative imports (starting with '.') are resolved.
        """
        rel = str(path.relative_to(repo_root))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return LangFileInfo(path=path, rel=rel, parseable=False)

        source_bytes = source.encode("utf-8")

        list_str_exports = self._query_names(source_bytes, _EXPORT_QUERY)

        raw_imports = self._query_strings(source_bytes, _IMPORT_QUERY)
        list_str_deps: list[str] = []
        for imp in raw_imports:
            if not imp.startswith("."):
                continue
            resolved = TypeScriptAdapter._resolve_import(path, imp, repo_root)
            if resolved and resolved not in list_str_deps:
                list_str_deps.append(resolved)

        has_codedna = self.has_codedna_header(source)

        return LangFileInfo(
            path=path,
            rel=rel,
            exports=list_str_exports,
            deps=list_str_deps,
            has_codedna=has_codedna,
        )
