"""_ts_php.py — Tree-sitter-powered CodeDNA adapter for PHP source files.

exports: _PHP_LANG | _ROUTE_RE | class TreeSitterPhpAdapter
used_by: codedna_tool/languages/__init__.py → TreeSitterPhpAdapter
rules:   Requires tree-sitter>=0.25 and tree-sitter-php>=0.24.
language_php() is used — includes full PHP syntax (<?php tag etc.).
Only public methods are captured (visibility_modifier == b'public').
Laravel routes extracted via regex (Route:: calls are nested expressions).
inject_header() delegated to PhpAdapter (// comment format, <?php preserved).
attribute_list nodes are direct named_children of class_declaration and method_declaration.
enum_declaration_list → enum_case → name gives enum case exports (Status::Active).
Constructor injection via property_promotion_parameter: named_type child is the dep class.
Return type node is the FIRST named_child after formal_parameters that is NOT compound_statement.
agent:   claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_001 | initial tree-sitter PHP adapter
claude-sonnet-4-6 | anthropic | 2026-04-18 | s_20260418_php2 | GATE 3: populate funcs list with LangFuncInfo for each public method — enables L2 PHPDoc Rules: injection
claude-sonnet-4-6 | anthropic | 2026-04-18 | s_20260418_ts | full signatures, PHP 8 attributes, enum cases, constructor injection deps, AST-based doc detection
"""

from __future__ import annotations

import re
from pathlib import Path

from tree_sitter import Language
import tree_sitter_php as ts_php

from .base import LangFileInfo, LangFuncInfo
from ._treesitter import TreeSitterAdapter
from .php import PhpAdapter

_PHP_LANG = Language(ts_php.language_php())

_ROUTE_RE = re.compile(
    r"Route\s*::\s*(?:get|post|put|patch|delete|any|match|resource|apiResource)"
    r"\s*\(\s*['\"]([^'\"]+)['\"]",
    re.MULTILINE,
)

def _t(node) -> str:
    return node.text.decode("utf-8", errors="replace")


class TreeSitterPhpAdapter(TreeSitterAdapter):
    """AST-based CodeDNA adapter for .php files.

    Rules:   Public methods only — visibility_modifier must be b'public'.
             Class/interface/trait names captured unconditionally.
             inject_header() is delegated to PhpAdapter (// format, idempotent).
             Full signatures built via _fmt_sig(entry, params_node, return_node).
             PHP 8 attributes (attribute_list) exported as 'attr:AttrName'.
             Enum cases exported as 'EnumName::CaseName'.
             Constructor promotion deps resolved via PhpAdapter._resolve_use().
    """

    def __init__(self):
        super().__init__(language=_PHP_LANG, regex_fallback=PhpAdapter())

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a PHP file via tree-sitter and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any error.
                 One class per file assumed for method prefix (PSR-1 standard).
                 Laravel routes detected via regex — Route:: AST is too nested to query cleanly.
                 Return type is the first named_child after formal_parameters that is NOT compound_statement.
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
        src_lines = source.splitlines()

        def _walk_attribute_list(attr_list_node) -> None:
            """C) Walk attribute_list → attribute_group → attribute → name.

            Rules:   Emits 'attr:AttrName' for every PHP 8 attribute found.
                     Multiple attribute groups in one #[...] block are all captured.
            """
            for group in attr_list_node.named_children:
                if group.type == "attribute_group":
                    for attr in group.named_children:
                        if attr.type == "attribute":
                            for cn in attr.children:
                                if cn.type == "name":
                                    attr_name = _t(cn)
                                    entry = f"attr:{attr_name}"
                                    if entry not in exports:
                                        exports.append(entry)

        def _extract_constructor_deps(constructor_node) -> None:
            """E) Extract constructor-injected class deps from property_promotion_parameter.

            Rules:   Only property_promotion_parameter nodes carry promoted types.
                     Resolved via PhpAdapter._resolve_use — skips unresolvable (e.g. builtins).
            """
            for c in constructor_node.named_children:
                if c.type == "formal_parameters":
                    for param in c.named_children:
                        if param.type == "property_promotion_parameter":
                            for pn in param.named_children:
                                if pn.type == "named_type":
                                    class_name = _t(pn).strip()
                                    rp = PhpAdapter._resolve_use(class_name, repo_root)
                                    if rp and rp not in deps:
                                        deps.append(rp)

        def walk(node) -> None:
            if node.type in ("class_declaration", "interface_declaration",
                             "trait_declaration"):
                for c in node.children:
                    if c.type == "name":
                        n = _t(c)
                        if n not in exports:
                            exports.append(n)
                # C) Capture PHP 8 attribute_list nodes on class/interface/trait
                for c in node.named_children:
                    if c.type == "attribute_list":
                        _walk_attribute_list(c)

            elif node.type == "enum_declaration":
                # D) Capture enum name and all its cases
                enum_name = ""
                for c in node.children:
                    if c.type == "name":
                        enum_name = _t(c)
                        if enum_name not in exports:
                            exports.append(enum_name)
                if enum_name:
                    for c in node.named_children:
                        if c.type == "enum_declaration_list":
                            for case_node in c.named_children:
                                if case_node.type == "enum_case":
                                    for cn in case_node.children:
                                        if cn.type == "name":
                                            case_name = _t(cn)
                                            entry = f"{enum_name}::{case_name}"
                                            if entry not in exports:
                                                exports.append(entry)

            elif node.type == "function_definition":
                if node.parent and node.parent.type in ("program", "namespace_definition"):
                    for c in node.children:
                        if c.type == "name":
                            n = _t(c)
                            if n not in exports:
                                exports.append(n)

            elif node.type == "method_declaration":
                # C) Capture PHP 8 attribute_list on method (before visibility check)
                for c in node.named_children:
                    if c.type == "attribute_list":
                        _walk_attribute_list(c)

                vis = next((c for c in node.children if c.type == "visibility_modifier"), None)
                if vis and vis.text == b"public":
                    method_name = ""
                    for c in node.children:
                        if c.type == "name":
                            method_name = _t(c)

                    if method_name and not method_name.startswith("__"):
                        # Rules: cls must exclude attr: and :: entries to get the bare class name
                        cls = next((e for e in exports
                                    if "::" not in e and "route:" not in e
                                    and not e.startswith("attr:")), "")
                        entry = f"{cls}::{method_name}" if cls else method_name

                        # A) Find formal_parameters node by walking named_children
                        params_node = None
                        for c in node.named_children:
                            if c.type == "formal_parameters":
                                params_node = c
                                break

                        # A) Return type: first named_child AFTER formal_parameters
                        # that is NOT compound_statement (the body)
                        return_node = None
                        if params_node is not None:
                            found_params = False
                            for c in node.named_children:
                                if c is params_node:
                                    found_params = True
                                    continue
                                if found_params and c.type != "compound_statement":
                                    if c.type in ("named_type", "primitive_type",
                                                  "union_type", "nullable_type",
                                                  "intersection_type"):
                                        return_node = c
                                        break

                        # A) Build full signature (e.g. UserController::show(int $id): User)
                        sig = self._fmt_sig(entry, params_node, return_node)

                        if sig not in exports:
                            exports.append(sig)

                        # B) AST-based doc detection via prev_named_sibling
                        has_doc = self._has_doc_block_above(node)
                        start_line = node.start_point[0] + 1  # 1-based
                        snippet_start = start_line - 1
                        snippet_lines = src_lines[snippet_start:snippet_start + 20]
                        snippet = "\n".join(snippet_lines)
                        has_rules = "Rules:" in snippet[:200]

                        funcs.append(LangFuncInfo(
                            name=sig,
                            start_line=start_line,
                            has_doc=has_doc,
                            has_rules=has_rules,
                            source_snippet=snippet,
                            language="php",
                        ))

                    # E) Constructor injection — runs regardless of __ prefix guard above
                    if method_name == "__construct":
                        _extract_constructor_deps(node)

            elif node.type == "namespace_use_declaration":
                for clause in node.children:
                    if clause.type == "namespace_use_clause":
                        for qn in clause.children:
                            if qn.type == "qualified_name":
                                rp = PhpAdapter._resolve_use(_t(qn), repo_root)
                                if rp and rp not in deps:
                                    deps.append(rp)

            for child in node.children:
                walk(child)

        walk(root)

        for route in _ROUTE_RE.findall(source)[:5]:
            entry = f"route:{route}"
            if entry not in exports:
                exports.append(entry)

        return LangFileInfo(
            path=path, rel=rel, exports=exports, deps=deps, funcs=funcs,
            has_codedna=self.has_codedna_header(source),
        )
