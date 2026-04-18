"""_ts_rust.py — Tree-sitter-powered CodeDNA adapter for Rust source files.

exports: _RUST_LANG | class TreeSitterRustAdapter
used_by: codedna_tool/languages/__init__.py → TreeSitterRustAdapter
rules:   Requires tree-sitter>=0.25 and tree-sitter-rust>=0.24.
Only pub items captured (visibility_modifier present).
impl blocks traversed explicitly — pub fn inside impl formatted as Type::method.
const_item: identifier node holds name. type_item: type_identifier node holds name.
inject_header() delegated to RustAdapter (// comment at file top).
funcs populated for pub fn at top-level and inside impl blocks — enables L2 Rules: injection.
agent:   claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_001 | initial tree-sitter Rust adapter; fixes critical gap in regex adapter (impl methods not captured)
claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_002 | add const_item and type_item capture (pub const / pub type were silently missing)
claude-sonnet-4-6 | anthropic | 2026-04-18 | s_20260418_ts | add funcs (LangFuncInfo) + full signatures for pub fn at top-level and inside impl; enables L2 Rules: via RustAdapter
"""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Language
import tree_sitter_rust as ts_rust

from .base import LangFileInfo, LangFuncInfo
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
             funcs populated for pub fn at top-level and inside impl blocks (L2 Rules:).
    """

    def __init__(self):
        super().__init__(language=_RUST_LANG, regex_fallback=RustAdapter())

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a Rust file via tree-sitter and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any error.
                 impl_item handled separately with early return — avoids double-visiting
                 function_item nodes inside the impl body.
                 funcs built for pub fn only (top-level and impl methods).
        """
        rel = str(path.relative_to(repo_root))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return LangFileInfo(path=path, rel=rel, parseable=False)

        src = source.encode("utf-8")
        root = self._parser.parse(src).root_node
        src_lines = source.splitlines()

        exports: list[str] = []
        deps: list[str] = []
        funcs: list[LangFuncInfo] = []

        def _get_return_node(fn_node, params_node):
            """Find return type node after parameters in a function_item.

            Rules:   Walk named_children after params_node.
                     Skip self_parameter nodes and block nodes.
                     First non-block named child after params is the return type.
                     Returns None when no return type is present (void functions).
            """
            found_params = False
            for child in fn_node.named_children:
                if child is params_node:
                    found_params = True
                    continue
                if not found_params:
                    continue
                if child.type == "block":
                    break
                return child
            return None

        def _extract_params_text(params_node) -> str:
            """Build a compact param text from a Rust parameters node.

            Rules:   Skip self_parameter nodes (receiver) — not part of the public API signature.
                     Use raw node text for each non-self parameter.
            """
            if params_node is None:
                return "()"
            parts = []
            for child in params_node.named_children:
                # Rules: skip self_parameter — it's the receiver, not a typed param
                if child.type in ("self_parameter", "variadic_parameter"):
                    continue
                if child.type == "parameter":
                    parts.append(_t(child))
            return "(" + ", ".join(parts) + ")"

        def _build_func_info(fn_node, qualified_name: str, params_node, ret_node) -> LangFuncInfo:
            """Build a LangFuncInfo for a pub fn node."""
            # Build signature using _fmt_sig helper but with our custom params text
            params_text = _extract_params_text(params_node)
            ret_text = _t(ret_node).strip() if ret_node else ""
            if ret_text:
                sig = f"{qualified_name}{params_text}: {ret_text}"
            else:
                sig = f"{qualified_name}{params_text}"

            start_line = fn_node.start_point[0] + 1  # 1-based
            snippet_start = start_line - 1
            snippet_lines = src_lines[snippet_start:snippet_start + 20]
            snippet = "\n".join(snippet_lines)
            has_doc = self._has_doc_block_above(fn_node)
            has_rules = "Rules:" in snippet[:200]
            return LangFuncInfo(
                name=sig,
                start_line=start_line,
                has_doc=has_doc,
                has_rules=has_rules,
                source_snippet=snippet,
                language="rust",
            )

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
                                fn_name = _t(name_node)
                                entry = f"{impl_type}::{fn_name}" if impl_type else fn_name
                                if entry not in exports:
                                    exports.append(entry)
                                # Build LangFuncInfo for L2 Rules:
                                params_node = next(
                                    (c for c in fn.named_children if c.type == "parameters"), None
                                )
                                ret_node = _get_return_node(fn, params_node)
                                qualified = f"{impl_type}::{fn_name}" if impl_type else fn_name
                                funcs.append(_build_func_info(fn, qualified, params_node, ret_node))
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
                        # Build LangFuncInfo for L2 Rules:
                        params_node = next(
                            (c for c in node.named_children if c.type == "parameters"), None
                        )
                        ret_node = _get_return_node(node, params_node)
                        funcs.append(_build_func_info(node, n, params_node, ret_node))

            elif node.type == "use_declaration":
                n = _t(node)
                if n not in deps:
                    deps.append(n)

            for child in node.named_children:
                walk(child)

        walk(root)

        return LangFileInfo(
            path=path, rel=rel, exports=exports, deps=deps, funcs=funcs,
            has_codedna=self.has_codedna_header(source),
        )
