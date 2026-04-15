"""_treesitter.py — Base class for tree-sitter-powered CodeDNA adapters.

exports: class TreeSitterAdapter
used_by: codedna_tool/languages/_ts_csharp.py → TreeSitterAdapter
         codedna_tool/languages/_ts_go.py → TreeSitterAdapter
         codedna_tool/languages/_ts_java.py → TreeSitterAdapter
         codedna_tool/languages/_ts_kotlin.py → TreeSitterAdapter
         codedna_tool/languages/_ts_php.py → TreeSitterAdapter
         codedna_tool/languages/_ts_ruby.py → TreeSitterAdapter
         codedna_tool/languages/_ts_rust.py → TreeSitterAdapter
         codedna_tool/languages/_ts_typescript.py → TreeSitterAdapter
rules:   tree-sitter is an optional dependency — import errors must be caught by callers.
All adapters inherit inject_header() from the regex adapter; only extract_info() changes.
extract_info() must never raise — return LangFileInfo(parseable=False) on failure.
tree-sitter 0.25+ API: Query(lang, pattern) → QueryCursor(query) → cursor.captures(node).
_parse_cached() uses identity (is) check — callers must reuse the same bytes object
within a single extract_info() call to get cache hits; re-parse on different object.
agent:   claude-opus-4-6 | anthropic | 2026-04-14 | s_20260414_002 | fixed API for tree-sitter 0.25: Query.captures → QueryCursor.captures
claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_001 | extended used_by to all 6 new tree-sitter adapters (PHP, Java, Rust, C#, Ruby, Kotlin)
claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_002 | add _parse_cached() 1-entry cache — prevents parsing same bytes N times per extract_info() call
"""

from __future__ import annotations


from tree_sitter import Language, Parser, Query, QueryCursor

from .base import LanguageAdapter


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
        self._cached_src: bytes = b""
        self._cached_tree = None

    @property
    def comment_prefix(self) -> str:
        return self._regex_fallback.comment_prefix

    def inject_header(self, source: str, rel: str, exports: str, used_by: str,
                      rules: str, model_id: str, today: str) -> str:
        """Delegate to regex adapter — header injection logic is identical."""
        return self._regex_fallback.inject_header(source, rel, exports, used_by, rules, model_id, today)

    def _parse_cached(self, source_bytes: bytes):
        """Parse source_bytes, returning a cached tree when the same bytes object is reused.

        Rules:   Uses identity (is) not equality — zero-overhead for repeated calls within
                 a single extract_info() call where the same local variable is passed each time.
                 Cache is intentionally per-instance and NOT thread-safe (adapters are singletons).
        """
        if source_bytes is not self._cached_src:
            self._cached_tree = self._parser.parse(source_bytes)
            self._cached_src = source_bytes
        return self._cached_tree

    def _query_names(self, source_bytes: bytes, query_str: str, capture_name: str = "name") -> list[str]:
        """Run a tree-sitter query and return unique captured node texts."""
        tree = self._parse_cached(source_bytes)
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
        tree = self._parse_cached(source_bytes)
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
