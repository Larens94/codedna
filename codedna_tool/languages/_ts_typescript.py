"""_ts_typescript.py — Tree-sitter-powered CodeDNA adapter for TypeScript/JavaScript.

exports: _TS_LANG | _IMPORT_QUERY | class TreeSitterTypeScriptAdapter
used_by: codedna_tool/languages/__init__.py → TreeSitterTypeScriptAdapter
rules:   Requires tree-sitter and tree-sitter-typescript installed.
Falls back to regex TypeScriptAdapter for inject_header().
Only relative imports (starting with '.') are resolved to file paths.
Bare exports (type_alias, interface, lexical_declaration) are captured as bare names.
Class methods: only public (no accessibility_modifier or modifier == 'public') are captured.
agent:   claude-opus-4-6 | anthropic | 2026-04-14 | s_20260414_001 | initial tree-sitter TS/JS adapter
claude-sonnet-4-6 | anthropic | 2026-04-18 | s_20260418_ts | replace query-based export extraction with walk() for full signature + LangFuncInfo population (GATE 3 TypeScript)
"""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Language
import tree_sitter_typescript as ts_ts

from .base import LangFileInfo, LangFuncInfo
from ._treesitter import TreeSitterAdapter
from .typescript import TypeScriptAdapter

_TS_LANG = Language(ts_ts.language_typescript())

_IMPORT_QUERY = """
(import_statement source: (string) @source)
"""

def _t(node) -> str:
    return node.text.decode("utf-8", errors="replace")


class TreeSitterTypeScriptAdapter(TreeSitterAdapter):
    """AST-based CodeDNA adapter for .ts, .tsx, .js, .jsx, .mjs files.

    Rules:   Uses tree-sitter for accurate export/import extraction.
             Captures named exports, default exports, type/interface exports.
             Barrel re-exports (export * from) are not captured (same as regex adapter).
             Class methods: only public methods (no accessibility_modifier or 'public') are in funcs.
    """

    def __init__(self):
        super().__init__(language=_TS_LANG, regex_fallback=TypeScriptAdapter())

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a TS/JS file via tree-sitter and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any error.
                 Only relative imports (starting with '.') are resolved.
                 export_statement wrapping function_declaration/class_declaration are walked for
                 full signatures; other exports (type, interface, const) captured as bare names.
        """
        rel = str(path.relative_to(repo_root))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return LangFileInfo(path=path, rel=rel, parseable=False)

        source_bytes = source.encode("utf-8")
        src_lines = source.splitlines()

        root = self._parse_cached(source_bytes).root_node

        exports: list[str] = []
        funcs: list[LangFuncInfo] = []

        def _is_public_method(method_node) -> bool:
            """Return True if method has no accessibility_modifier or modifier is 'public'."""
            for child in method_node.children:
                if child.type == "accessibility_modifier":
                    return _t(child) == "public"
            return True

        def _method_sig(class_name: str, method_node) -> str:
            """Build 'ClassName::methodName(params): ReturnType' signature."""
            name_node = next(
                (c for c in method_node.named_children if c.type == "property_identifier"),
                None,
            )
            if name_node is None:
                return ""
            method_name = _t(name_node)
            entry = f"{class_name}::{method_name}"

            params_node = next(
                (c for c in method_node.named_children if c.type == "formal_parameters"),
                None,
            )
            # type_annotation node text starts with ': ' — pass its first named child
            # (the actual type node) so _fmt_sig doesn't produce double ': :'.
            type_ann = next(
                (c for c in method_node.named_children if c.type == "type_annotation"),
                None,
            )
            return_node = type_ann.named_children[0] if (type_ann and type_ann.named_children) else None
            return self._fmt_sig(entry, params_node, return_node)

        def _process_class(class_node, class_name: str) -> None:
            """Walk class_body for public method_definition nodes, populate funcs.

            Rules:   class_name is already added to exports by the caller (walk()).
                     Method sigs go into funcs only — exports keeps bare names for
                     backward compat with existing tests and downstream consumers.
            """
            body = next(
                (c for c in class_node.named_children if c.type == "class_body"),
                None,
            )
            if body is None:
                return
            for member in body.named_children:
                if member.type != "method_definition":
                    continue
                if not _is_public_method(member):
                    continue
                sig = _method_sig(class_name, member)
                if not sig:
                    continue
                # Build LangFuncInfo — full sig stored here, not in exports
                start_line = member.start_point[0] + 1  # 1-based
                snippet_start = start_line - 1
                snippet_lines = src_lines[snippet_start:snippet_start + 20]
                snippet = "\n".join(snippet_lines)
                has_doc = self._has_doc_block_above(member)
                has_rules = "Rules:" in snippet[:200]
                funcs.append(LangFuncInfo(
                    name=sig,
                    start_line=start_line,
                    has_doc=has_doc,
                    has_rules=has_rules,
                    source_snippet=snippet,
                    language="typescript",
                ))

        def _process_function(func_node) -> None:
            """Process a top-level function_declaration export."""
            name_node = next(
                (c for c in func_node.named_children if c.type == "identifier"),
                None,
            )
            if name_node is None:
                return
            func_name = _t(name_node)
            # Add bare name to exports for backward compatibility with existing tests
            if func_name not in exports:
                exports.append(func_name)
            params_node = next(
                (c for c in func_node.named_children if c.type == "formal_parameters"),
                None,
            )
            # type_annotation node text starts with ': ' — pass its first named child
            # so _fmt_sig doesn't produce double ': :' in the signature.
            type_ann = next(
                (c for c in func_node.named_children if c.type == "type_annotation"),
                None,
            )
            return_node = type_ann.named_children[0] if (type_ann and type_ann.named_children) else None
            sig = self._fmt_sig(func_name, params_node, return_node)
            # Build LangFuncInfo (full sig used here for L2 context)
            start_line = func_node.start_point[0] + 1
            snippet_start = start_line - 1
            snippet_lines = src_lines[snippet_start:snippet_start + 20]
            snippet = "\n".join(snippet_lines)
            has_doc = self._has_doc_block_above(func_node)
            has_rules = "Rules:" in snippet[:200]
            funcs.append(LangFuncInfo(
                name=sig,
                start_line=start_line,
                has_doc=has_doc,
                has_rules=has_rules,
                source_snippet=snippet,
                language="typescript",
            ))

        def walk(node) -> None:
            if node.type == "export_statement":
                # Check for 'default' keyword
                # Walk children to find the declaration
                for child in node.named_children:
                    if child.type == "class_declaration":
                        name_node = next(
                            (c for c in child.named_children if c.type == "type_identifier"),
                            None,
                        )
                        class_name = _t(name_node) if name_node else ""
                        if class_name and class_name not in exports:
                            exports.append(class_name)
                        if class_name:
                            _process_class(child, class_name)
                    elif child.type == "function_declaration":
                        _process_function(child)
                    elif child.type in (
                        "type_alias_declaration",
                        "interface_declaration",
                    ):
                        # Capture bare name for types/interfaces
                        name_node = next(
                            (c for c in child.named_children if c.type == "type_identifier"),
                            None,
                        )
                        if name_node:
                            n = _t(name_node)
                            if n not in exports:
                                exports.append(n)
                    elif child.type == "lexical_declaration":
                        # export const/let FOO = ...
                        for decl in child.named_children:
                            if decl.type == "variable_declarator":
                                vname = next(
                                    (c for c in decl.named_children if c.type == "identifier"),
                                    None,
                                )
                                if vname:
                                    n = _t(vname)
                                    if n not in exports:
                                        exports.append(n)
                    elif child.type == "export_clause":
                        # export { A, B, C } — aggregate re-export
                        for spec in child.named_children:
                            if spec.type == "export_specifier":
                                name_node = next(
                                    (c for c in spec.named_children if c.type == "identifier"),
                                    None,
                                )
                                if name_node:
                                    n = _t(name_node)
                                    if n not in exports:
                                        exports.append(n)
                # Don't recurse deeper into export_statement children that we've handled
                return

            for child in node.named_children:
                walk(child)

        walk(root)

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
            exports=exports,
            deps=list_str_deps,
            funcs=funcs,
            has_codedna=has_codedna,
        )
