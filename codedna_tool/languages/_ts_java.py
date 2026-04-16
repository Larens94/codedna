"""_ts_java.py — Tree-sitter-powered CodeDNA adapter for Java source files.

exports: _JAVA_LANG | _SKIP_NAMES | class TreeSitterJavaAdapter
used_by: codedna_tool/languages/__init__.py → TreeSitterJavaAdapter
rules:   Requires tree-sitter>=0.25 and tree-sitter-java>=0.23.
Only public types and public methods captured (modifiers contains 'public').
Import paths captured as strings — not resolved to file paths (requires project structure).
inject_header() delegated to JavaAdapter (// comment after package declaration).
agent:   claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_001 | initial tree-sitter Java adapter
"""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Language
import tree_sitter_java as ts_java

from .base import LangFileInfo
from ._treesitter import TreeSitterAdapter
from .java import JavaAdapter

_JAVA_LANG = Language(ts_java.language())

_SKIP_NAMES = frozenset({"class", "interface", "enum", "record", "void", "static"})

def _t(node) -> str:
    return node.text.decode("utf-8", errors="replace")


class TreeSitterJavaAdapter(TreeSitterAdapter):
    """AST-based CodeDNA adapter for .java files.

    Rules:   Only public top-level types and public methods captured.
             modifiers.text is checked for 'public' substring.
             inject_header() is delegated to JavaAdapter.
    """

    def __init__(self):
        super().__init__(language=_JAVA_LANG, regex_fallback=JavaAdapter())

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a Java file via tree-sitter and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any error.
                 Public methods formatted as ClassName::method.
                 Import declarations captured as package-qualified strings (not file paths).
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
                             "enum_declaration", "record_declaration"):
                mods = next((c for c in node.named_children if c.type == "modifiers"), None)
                if mods and b"public" in mods.text:
                    id_node = next((c for c in node.named_children if c.type == "identifier"), None)
                    if id_node:
                        n = _t(id_node)
                        if n not in exports:
                            exports.append(n)

            elif node.type == "method_declaration":
                mods = next((c for c in node.named_children if c.type == "modifiers"), None)
                if mods and b"public" in mods.text:
                    id_node = next((c for c in node.named_children if c.type == "identifier"), None)
                    if id_node:
                        n = _t(id_node)
                        if n not in _SKIP_NAMES:
                            cls = next((e for e in exports if "::" not in e), "")
                            entry = f"{cls}::{n}" if cls else n
                            if entry not in exports:
                                exports.append(entry)

            elif node.type == "import_declaration":
                si = next((c for c in node.named_children
                           if c.type == "scoped_identifier"), None)
                if si:
                    pkg = _t(si)
                    if pkg not in deps:
                        deps.append(pkg)

            for child in node.named_children:
                walk(child)

        walk(root)

        return LangFileInfo(
            path=path, rel=rel, exports=exports, deps=deps,
            has_codedna=self.has_codedna_header(source),
        )
