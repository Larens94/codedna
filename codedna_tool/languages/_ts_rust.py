"""_ts_rust.py — Tree-sitter-powered CodeDNA adapter for Rust source files.

exports: _RUST_LANG | class TreeSitterRustAdapter
used_by: codedna_tool/languages/__init__.py → TreeSitterRustAdapter
rules:   Requires tree-sitter>=0.25 and tree-sitter-rust>=0.24.
Only pub items captured (visibility_modifier present).
impl blocks traversed explicitly — pub fn inside impl formatted as Type::method.
const_item: identifier node holds name. type_item: type_identifier node holds name.
inject_header() delegated to RustAdapter (// comment at file top).
agent:   claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_001 | initial tree-sitter Rust adapter; fixes critical gap in regex adapter (impl methods not captured)
claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_002 | add const_item and type_item capture (pub const / pub type were silently missing)
"""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Language
import tree_sitter_rust as ts_rust

from .base import LangFileInfo
from ._treesitter import TreeSitterAdapter
from .rust import RustAdapter

_RUST_LANG = Language(ts_rust.language())

def _t(node) -> str:
    return node.text.decode("utf-8", errors="replace")

def _is_pub(node) -> bool:
    return any(c.type == "visibility_modifier" for c in node.named_children)


class TreeSitterRustAdapter(TreeSitterAdapter):
    """AST-based CodeDNA adapter for .rs files.

    Rules:   pub struct/enum/trait captured as type-level exports.
             pub fn inside impl blocks captured as Type::method — fixes the critical
             gap in the regex adapter which only captured top-level struct names.
             use declarations captured as raw strings (module paths, not file paths).
             inject_header() is delegated to RustAdapter.
    """

    def __init__(self):
        super().__init__(language=_RUST_LANG, regex_fallback=RustAdapter())

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a Rust file via tree-sitter and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any error.
                 impl_item handled separately with early return — avoids double-visiting
                 function_item nodes inside the impl body.
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
            if node.type == "impl_item":
                type_node = next(
                    (c for c in node.named_children if c.type == "type_identifier"), None
                )
                impl_type = _t(type_node) if type_node else ""
                body = next(
                    (c for c in node.named_children if c.type == "declaration_list"), None
                )
                if body:
                    for fn in body.named_children:
                        if fn.type == "function_item" and _is_pub(fn):
                            name_node = next(
                                (c for c in fn.named_children if c.type == "identifier"), None
                            )
                            if name_node:
                                entry = f"{impl_type}::{_t(name_node)}" if impl_type else _t(name_node)
                                if entry not in exports:
                                    exports.append(entry)
                return  # don't recurse into impl — already handled

            elif node.type in ("struct_item", "enum_item", "trait_item"):
                if _is_pub(node):
                    name_node = next(
                        (c for c in node.named_children if c.type == "type_identifier"), None
                    )
                    if name_node:
                        n = _t(name_node)
                        if n not in exports:
                            exports.append(n)

            elif node.type == "const_item":
                if _is_pub(node):
                    name_node = next(
                        (c for c in node.named_children if c.type == "identifier"), None
                    )
                    if name_node:
                        n = _t(name_node)
                        if n not in exports:
                            exports.append(n)

            elif node.type == "type_item":
                if _is_pub(node):
                    name_node = next(
                        (c for c in node.named_children if c.type == "type_identifier"), None
                    )
                    if name_node:
                        n = _t(name_node)
                        if n not in exports:
                            exports.append(n)

            elif node.type == "function_item":
                # Only reached for top-level / mod-level functions (impl handled above)
                if _is_pub(node):
                    name_node = next(
                        (c for c in node.named_children if c.type == "identifier"), None
                    )
                    if name_node:
                        n = _t(name_node)
                        if n not in exports:
                            exports.append(n)

            elif node.type == "use_declaration":
                n = _t(node)
                if n not in deps:
                    deps.append(n)

            for child in node.named_children:
                walk(child)

        walk(root)

        return LangFileInfo(
            path=path, rel=rel, exports=exports, deps=deps,
            has_codedna=self.has_codedna_header(source),
        )
