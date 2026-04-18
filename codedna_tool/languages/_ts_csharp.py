"""_ts_csharp.py — Tree-sitter-powered CodeDNA adapter for C# source files.

exports: _CS_LANG | _SKIP_NAMES | class TreeSitterCSharpAdapter
used_by: codedna_tool/languages/__init__.py → TreeSitterCSharpAdapter
rules:   Requires tree-sitter>=0.25 and tree-sitter-c-sharp>=0.23.
Only public types and public methods/properties captured (modifier == b'public').
using directives captured as dependency strings (not resolved to file paths).
inject_header() delegated to CSharpAdapter (// block between using and namespace).
MUST use child_by_field_name('name') for methods/properties — named_children[identifier]
returns the return type first, not the method name.
Return type node is name_node.prev_named_sibling — skip modifier nodes walking backwards.
has_doc: prev_named_sibling of method_declaration is 'comment' starting with '///'.
agent:   claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_001 | initial tree-sitter C# adapter
claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_002 | fix: use child_by_field_name('name') — first identifier in named_children is the return type not the method name
claude-sonnet-4-6 | anthropic | 2026-04-18 | s_20260418_ts | GATE 3: add funcs (LangFuncInfo) extraction — params via parameters field, return type via name_node.prev_named_sibling, has_doc via _has_doc_block_above
"""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Language
import tree_sitter_c_sharp as ts_cs

from .base import LangFileInfo, LangFuncInfo
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
        funcs: list[LangFuncInfo] = []
        lines = source.splitlines()

        def walk(node) -> None:
            if node.type in ("class_declaration", "interface_declaration",
                             "struct_declaration", "enum_declaration", "record_declaration"):
                if _is_public(node):
                    id_node = node.child_by_field_name("name")
                    if id_node:
                        n = _t(id_node)
                        if n not in exports:
                            exports.append(n)

            elif node.type in ("method_declaration", "property_declaration"):
                if _is_public(node):
                    # Rules: MUST use child_by_field_name('name') — the first identifier in
                    # named_children is the return type, not the method name.
                    id_node = node.child_by_field_name("name")
                    if id_node:
                        n = _t(id_node)
                        if n not in _SKIP_NAMES:
                            cls = next((e for e in exports if "::" not in e), "")
                            entry = f"{cls}::{n}" if cls else n
                            if entry not in exports:
                                exports.append(entry)

                            if node.type == "method_declaration":
                                # Return type: prev_named_sibling of name node, skipping
                                # modifier nodes (public, static, etc.)
                                ret_node = id_node.prev_named_sibling
                                while ret_node is not None and ret_node.type == "modifier":
                                    ret_node = ret_node.prev_named_sibling

                                params_node = node.child_by_field_name("parameters")
                                sig = self._fmt_sig(entry, params_node, ret_node)

                                start_line = node.start_point[0] + 1  # 1-based
                                end_line = min(node.end_point[0] + 1, start_line + 19)
                                snippet = "\n".join(lines[start_line - 1:end_line])

                                has_doc = self._has_doc_block_above(node)
                                has_rules = "Rules:" in snippet[:200]

                                funcs.append(LangFuncInfo(
                                    name=sig,
                                    start_line=start_line,
                                    has_doc=has_doc,
                                    has_rules=has_rules,
                                    source_snippet=snippet,
                                    language="csharp",
                                ))

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
            path=path, rel=rel, exports=exports, deps=deps, funcs=funcs,
            has_codedna=self.has_codedna_header(source),
        )
