"""_ts_kotlin.py — Tree-sitter-powered CodeDNA adapter for Kotlin source files.

exports: TreeSitterKotlinAdapter
used_by: languages/__init__.py → _REGISTRY
rules:   Requires tree-sitter>=0.25 and tree-sitter-kotlin>=1.1.
         Top-level class_declaration, function_declaration, and const property_declaration captured.
         object_declaration captured with its functions as ObjectName.fn (idiomatic Kotlin singleton).
         companion_object functions captured as ClassName.fn using grandparent class_declaration name.
         import qualified_identifier captured as dependency string.
         inject_header() delegated to KotlinAdapter (// comment after package declaration).
agent:   claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_001 | initial tree-sitter Kotlin adapter
         claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_002 | add object_declaration and companion_object function capture
"""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Language
import tree_sitter_kotlin as ts_kotlin

from .base import LangFileInfo
from ._treesitter import TreeSitterAdapter
from .java import KotlinAdapter

_KOTLIN_LANG = Language(ts_kotlin.language())

def _t(node) -> str:
    return node.text.decode("utf-8", errors="replace")


class TreeSitterKotlinAdapter(TreeSitterAdapter):
    """AST-based CodeDNA adapter for .kt and .kts files.

    Rules:   Top-level declarations only: class, fun, const val.
             Class-level functions excluded — parent type check prevents double capture.
             Public is the default in Kotlin; no visibility filter applied.
             inject_header() is delegated to KotlinAdapter.
    """

    def __init__(self):
        super().__init__(language=_KOTLIN_LANG, regex_fallback=KotlinAdapter())

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a Kotlin file via tree-sitter and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any error.
                 Only source_file direct children considered for function/property exports.
                 class_declaration captured at any depth (handles nested classes in objects).
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

        def _capture_fns_in_body(body_node, prefix: str) -> None:
            """Capture function_declarations inside a class_body as prefix.fn."""
            for child in body_node.named_children:
                if child.type == "function_declaration":
                    id_node = next(
                        (c for c in child.named_children if c.type == "identifier"), None
                    )
                    if id_node:
                        entry = f"{prefix}.{_t(id_node)}" if prefix else _t(id_node)
                        if entry not in exports:
                            exports.append(entry)

        def walk(node) -> None:
            if node.type == "class_declaration":
                id_node = next(
                    (c for c in node.named_children if c.type == "identifier"), None
                )
                if id_node:
                    n = _t(id_node)
                    if n not in exports:
                        exports.append(n)

            elif node.type == "object_declaration":
                # Kotlin singleton object — capture name and its methods as ObjectName.fn
                id_node = next(
                    (c for c in node.named_children if c.type == "identifier"), None
                )
                obj_name = _t(id_node) if id_node else ""
                if obj_name and obj_name not in exports:
                    exports.append(obj_name)
                body = next(
                    (c for c in node.named_children if c.type == "class_body"), None
                )
                if body:
                    _capture_fns_in_body(body, obj_name)
                return  # body already handled — don't recurse into class_body

            elif node.type == "companion_object":
                # companion object — capture methods as ClassName.fn using grandparent class name
                cls_decl = node.parent and node.parent.parent
                cls_name = ""
                if cls_decl and cls_decl.type == "class_declaration":
                    id_node = next(
                        (c for c in cls_decl.named_children if c.type == "identifier"), None
                    )
                    cls_name = _t(id_node) if id_node else ""
                body = next(
                    (c for c in node.named_children if c.type == "class_body"), None
                )
                if body:
                    _capture_fns_in_body(body, cls_name)
                return  # body already handled

            elif node.type == "function_declaration":
                # Top-level only (source_file direct child)
                if node.parent and node.parent.type == "source_file":
                    id_node = next(
                        (c for c in node.named_children if c.type == "identifier"), None
                    )
                    if id_node:
                        n = _t(id_node)
                        if n not in exports:
                            exports.append(n)

            elif node.type == "property_declaration":
                # Top-level const val only
                if node.parent and node.parent.type == "source_file":
                    mods = next(
                        (c for c in node.named_children if c.type == "modifiers"), None
                    )
                    if mods and b"const" in mods.text:
                        var_decl = next(
                            (c for c in node.named_children
                             if c.type == "variable_declaration"), None
                        )
                        if var_decl:
                            id_node = next(
                                (c for c in var_decl.named_children
                                 if c.type == "identifier"), None
                            )
                            if id_node:
                                n = _t(id_node)
                                if n not in exports:
                                    exports.append(n)

            elif node.type == "import":
                qi = next(
                    (c for c in node.named_children if c.type == "qualified_identifier"), None
                )
                if qi:
                    pkg = _t(qi)
                    if pkg not in deps:
                        deps.append(pkg)

            for child in node.named_children:
                walk(child)

        walk(root)

        return LangFileInfo(
            path=path, rel=rel, exports=exports, deps=deps,
            has_codedna=self.has_codedna_header(source),
        )
