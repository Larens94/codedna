"""_ts_csharp.py — Tree-sitter-powered CodeDNA adapter for C# source files.

exports: TreeSitterCSharpAdapter
used_by: languages/__init__.py → _REGISTRY
rules:   Requires tree-sitter>=0.25 and tree-sitter-c-sharp>=0.23.
         Only public types and public methods/properties captured (modifier == b'public').
         using directives captured as dependency strings (not resolved to file paths).
         inject_header() delegated to CSharpAdapter (// block between using and namespace).
agent:   claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_001 | initial tree-sitter C# adapter
"""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Language
import tree_sitter_c_sharp as ts_cs

from .base import LangFileInfo
from ._treesitter import TreeSitterAdapter
from .csharp import CSharpAdapter

_CS_LANG = Language(ts_cs.language())

_SKIP_NAMES = frozenset({
    "class", "interface", "struct", "enum", "void", "string",
    "int", "bool", "Task", "IEnumerable", "List",
})

def _t(node) -> str:
    return node.text.decode("utf-8", errors="replace")

def _is_public(node) -> bool:
    return any(c.type == "modifier" and c.text == b"public" for c in node.children)


class TreeSitterCSharpAdapter(TreeSitterAdapter):
    """AST-based CodeDNA adapter for .cs files.

    Rules:   Public types (class/interface/struct/enum/record) and public methods/properties.
             modifier node text checked for b'public' — handles 'public static', 'public async' etc.
             inject_header() is delegated to CSharpAdapter (header between using and namespace).
    """

    def __init__(self):
        super().__init__(language=_CS_LANG, regex_fallback=CSharpAdapter())

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a C# file via tree-sitter and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any error.
                 Public methods formatted as ClassName::Method.
                 using directives captured as namespace strings.
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
                             "struct_declaration", "enum_declaration", "record_declaration"):
                if _is_public(node):
                    id_node = next(
                        (c for c in node.named_children if c.type == "identifier"), None
                    )
                    if id_node:
                        n = _t(id_node)
                        if n not in exports:
                            exports.append(n)

            elif node.type in ("method_declaration", "property_declaration"):
                if _is_public(node):
                    id_node = next(
                        (c for c in node.named_children if c.type == "identifier"), None
                    )
                    if id_node:
                        n = _t(id_node)
                        if n not in _SKIP_NAMES:
                            cls = next((e for e in exports if "::" not in e), "")
                            entry = f"{cls}::{n}" if cls else n
                            if entry not in exports:
                                exports.append(entry)

            elif node.type == "using_directive":
                qn = next(
                    (c for c in node.named_children
                     if c.type in ("qualified_name", "identifier")), None
                )
                if qn:
                    pkg = _t(qn)
                    if pkg not in deps:
                        deps.append(pkg)

            for child in node.named_children:
                walk(child)

        walk(root)

        return LangFileInfo(
            path=path, rel=rel, exports=exports, deps=deps,
            has_codedna=self.has_codedna_header(source),
        )
