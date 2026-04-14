"""_treesitter.py — Base class for tree-sitter-powered CodeDNA adapters.

exports: TreeSitterAdapter(LanguageAdapter)
used_by: languages/_ts_typescript.py → TreeSitterTypeScriptAdapter [cascade]
         languages/_ts_go.py → TreeSitterGoAdapter [cascade]
rules:   tree-sitter is an optional dependency — import errors must be caught by callers.
         All adapters inherit inject_header() from the regex adapter; only extract_info() changes.
         extract_info() must never raise — return LangFileInfo(parseable=False) on failure.
         tree-sitter 0.25+ API: Query(lang, pattern) → QueryCursor(query) → cursor.captures(node).
agent:   claude-opus-4-6 | anthropic | 2026-04-14 | s_20260414_001 | initial tree-sitter base adapter
         claude-opus-4-6 | anthropic | 2026-04-14 | s_20260414_002 | fixed API for tree-sitter 0.25: Query.captures → QueryCursor.captures
"""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Language, Parser, Query, QueryCursor

from .base import LanguageAdapter, LangFileInfo


class TreeSitterAdapter(LanguageAdapter):
    """Base class for tree-sitter-powered language adapters.

    Rules:   Subclasses must set _language and _parser in __init__.
             extract_info() uses tree-sitter queries for accurate AST-based extraction.
             inject_header() is delegated to the regex adapter (same output format).
             tree-sitter 0.25+ uses QueryCursor for captures/matches, not Query directly.
    """

    _language: Language
    _parser: Parser

    def __init__(self, language: Language, regex_fallback: LanguageAdapter):
        self._language = language
        self._parser = Parser(language)
        self._regex_fallback = regex_fallback

    @property
    def comment_prefix(self) -> str:
        return self._regex_fallback.comment_prefix

    def inject_header(self, source: str, rel: str, exports: str, used_by: str,
                      rules: str, model_id: str, today: str) -> str:
        """Delegate to regex adapter — header injection logic is identical."""
        return self._regex_fallback.inject_header(source, rel, exports, used_by, rules, model_id, today)

    def _query_names(self, source_bytes: bytes, query_str: str, capture_name: str = "name") -> list[str]:
        """Run a tree-sitter query and return unique captured node texts."""
        tree = self._parser.parse(source_bytes)
        query = Query(self._language, query_str)
        cursor = QueryCursor(query)
        captures = cursor.captures(tree.root_node)
        nodes = captures.get(capture_name, [])
        seen: list[str] = []
        for node in nodes:
            text = node.text.decode("utf-8", errors="replace")
            if text not in seen:
                seen.append(text)
        return seen

    def _query_strings(self, source_bytes: bytes, query_str: str, capture_name: str = "source") -> list[str]:
        """Run a tree-sitter query and return unique captured strings (stripped of quotes)."""
        tree = self._parser.parse(source_bytes)
        query = Query(self._language, query_str)
        cursor = QueryCursor(query)
        captures = cursor.captures(tree.root_node)
        nodes = captures.get(capture_name, [])
        seen: list[str] = []
        for node in nodes:
            text = node.text.decode("utf-8", errors="replace").strip("'\"")
            if text not in seen:
                seen.append(text)
        return seen
