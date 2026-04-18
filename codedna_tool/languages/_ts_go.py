"""_ts_go.py — Tree-sitter-powered CodeDNA adapter for Go source files.

exports: _GO_LANG | _IMPORT_QUERY | class TreeSitterGoAdapter
used_by: codedna_tool/languages/__init__.py → TreeSitterGoAdapter
rules:   Requires tree-sitter and tree-sitter-go installed.
Falls back to regex GoAdapter for inject_header() and inject_function_rules().
Export detection: only capitalized identifiers (Go convention).
Import paths are captured but not resolved to file paths (requires go.mod parsing).
funcs populated for exported functions/methods — enables L2 Rules: injection via GoAdapter.
agent:   claude-opus-4-6 | anthropic | 2026-04-14 | s_20260414_001 | initial tree-sitter Go adapter
claude-sonnet-4-6 | anthropic | 2026-04-18 | s_20260418_ts | replace 5-query approach with walk(); add funcs (LangFuncInfo) + full signatures for exported funcs/methods
claude-sonnet-4-6 | anthropic | 2026-04-18 | s_20260418_msg | _resolve_go_import() for relative ./pkg imports; absolute module paths kept as raw strings (go.mod not parsed)
"""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Language
import tree_sitter_go as ts_go

from .base import LangFileInfo, LangFuncInfo
from ._treesitter import TreeSitterAdapter
from .go import GoAdapter

_GO_LANG = Language(ts_go.language())

_IMPORT_QUERY = """
(import_spec path: (interpreted_string_literal) @source)
"""


def _t(node) -> str:
    return node.text.decode("utf-8", errors="replace")


class TreeSitterGoAdapter(TreeSitterAdapter):
    """AST-based CodeDNA adapter for .go files.

    Rules:   Uses tree-sitter for accurate export/import extraction.
             Captures functions, methods, types, consts, vars — filtered to exported (capitalized).
             Method receivers are parsed correctly (regex adapter can miss complex receiver types).
             Import paths are package paths — not resolved to file system paths.
             funcs list populated for exported functions and methods (L2 Rules: injection).
    """

    def __init__(self):
        super().__init__(language=_GO_LANG, regex_fallback=GoAdapter())

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a Go file via tree-sitter and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any error.
                 Only capitalized identifiers are treated as exports (Go convention).
                 Import paths are not resolved — go.mod parsing belongs in a separate resolver.
                 funcs is built from function_declaration and method_declaration nodes.
        """
        rel = str(path.relative_to(repo_root))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return LangFileInfo(path=path, rel=rel, parseable=False)

        src = source.encode("utf-8")
        root = self._parse_cached(src).root_node
        src_lines = source.splitlines()

        list_str_exports: list[str] = []
        list_func_info: list[LangFuncInfo] = []

        def _get_return_node(fn_node, params_node):
            """Find return type node after params in a function/method declaration.

            Rules:   Walk named_children after finding params_node.
                     Skip the params_node itself and any 'block' node.
                     First remaining named child is the return type (or None).
                     Multiple returns are a parameter_list — use as-is.
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

        def walk(node) -> None:
            if node.type == "function_declaration":
                # Extract name from identifier child
                name_node = next(
                    (c for c in node.named_children if c.type == "identifier"), None
                )
                if name_node is None:
                    for child in node.named_children:
                        walk(child)
                    return

                name = _t(name_node)
                # Rules: only export capitalized names (Go convention)
                if not name[0].isupper():
                    for child in node.named_children:
                        walk(child)
                    return

                # Params: first parameter_list
                params_node = next(
                    (c for c in node.named_children if c.type == "parameter_list"), None
                )
                # Return type: first named child after params that is not block
                ret_node = _get_return_node(node, params_node) if params_node else None

                sig = self._fmt_sig(name, params_node, ret_node)
                if name not in list_str_exports:
                    list_str_exports.append(name)

                # Build LangFuncInfo for L2 Rules:
                start_line = node.start_point[0] + 1  # 1-based
                snippet_start = start_line - 1
                snippet_lines = src_lines[snippet_start:snippet_start + 20]
                snippet = "\n".join(snippet_lines)
                has_doc = self._has_doc_block_above(node)
                has_rules = "Rules:" in snippet[:200]
                list_func_info.append(LangFuncInfo(
                    name=sig,
                    start_line=start_line,
                    has_doc=has_doc,
                    has_rules=has_rules,
                    source_snippet=snippet,
                    language="go",
                ))
                return  # don't recurse into function body

            elif node.type == "method_declaration":
                # Receiver: first parameter_list → first parameter_declaration → type node
                receiver_params = next(
                    (c for c in node.named_children if c.type == "parameter_list"), None
                )
                receiver_type = ""
                if receiver_params:
                    recv_decl = next(
                        (c for c in receiver_params.named_children
                         if c.type == "parameter_declaration"), None
                    )
                    if recv_decl:
                        # Type node is the non-identifier child (skip the receiver var name)
                        type_node = next(
                            (c for c in recv_decl.named_children
                             if c.type not in ("identifier",)), None
                        )
                        if type_node:
                            raw = _t(type_node)
                            # Rules: strip * from pointer receivers to get bare type name
                            receiver_type = raw.lstrip("*")

                # Method name: field_identifier child
                name_node = next(
                    (c for c in node.named_children if c.type == "field_identifier"), None
                )
                if name_node is None:
                    for child in node.named_children:
                        walk(child)
                    return

                method_name = _t(name_node)
                # Rules: only export capitalized method names (Go convention)
                if not method_name[0].isupper():
                    for child in node.named_children:
                        walk(child)
                    return

                # Params: second parameter_list (after receiver)
                all_param_lists = [c for c in node.named_children if c.type == "parameter_list"]
                # all_param_lists[0] = receiver, all_param_lists[1] = params (if present)
                params_node = all_param_lists[1] if len(all_param_lists) > 1 else None

                # Return type: first named child after params that is not block
                ret_node = _get_return_node(node, params_node) if params_node else (
                    _get_return_node(node, receiver_params) if receiver_params else None
                )

                qualified_name = f"{receiver_type}::{method_name}" if receiver_type else method_name
                sig = self._fmt_sig(qualified_name, params_node, ret_node)

                # Export the method name itself (Go convention: method exported if capitalized)
                if method_name not in list_str_exports:
                    list_str_exports.append(method_name)

                # Build LangFuncInfo for L2 Rules:
                start_line = node.start_point[0] + 1  # 1-based
                snippet_start = start_line - 1
                snippet_lines = src_lines[snippet_start:snippet_start + 20]
                snippet = "\n".join(snippet_lines)
                has_doc = self._has_doc_block_above(node)
                has_rules = "Rules:" in snippet[:200]
                list_func_info.append(LangFuncInfo(
                    name=sig,
                    start_line=start_line,
                    has_doc=has_doc,
                    has_rules=has_rules,
                    source_snippet=snippet,
                    language="go",
                ))
                return  # don't recurse into method body

            elif node.type in ("type_declaration",):
                # Capture exported type names
                for child in node.named_children:
                    if child.type == "type_spec":
                        name_node = next(
                            (c for c in child.named_children if c.type == "type_identifier"), None
                        )
                        if name_node:
                            n = _t(name_node)
                            if n[0].isupper() and n not in list_str_exports:
                                list_str_exports.append(n)

            elif node.type in ("const_spec", "var_spec"):
                name_node = next(
                    (c for c in node.named_children if c.type == "identifier"), None
                )
                if name_node:
                    n = _t(name_node)
                    if n[0].isupper() and n not in list_str_exports:
                        list_str_exports.append(n)

            for child in node.named_children:
                walk(child)

        walk(root)

        # Deps via import query — resolve relative paths to repo-relative file paths
        raw_imports = self._query_strings(src, _IMPORT_QUERY)
        list_str_deps: list[str] = []
        for imp in raw_imports:
            resolved = self._resolve_go_import(path, imp, repo_root)
            entry = resolved if resolved else imp
            if entry not in list_str_deps:
                list_str_deps.append(entry)

        has_codedna = self.has_codedna_header(source)

        return LangFileInfo(
            path=path,
            rel=rel,
            exports=list_str_exports,
            deps=list_str_deps,
            funcs=list_func_info,
            has_codedna=has_codedna,
        )

    @staticmethod
    def _resolve_go_import(file_path: Path, imp: str, repo_root: Path) -> str | None:
        """Resolve a Go import path to a repo-relative directory path.

        Rules:   Only resolves relative imports starting with './' or '../'.
                 Absolute module paths (github.com/...) require go.mod — kept as raw strings.
                 Returns repo-relative path to the package directory (without trailing slash),
                 or None if the path doesn't exist or is outside repo_root.
        """
        if not (imp.startswith("./") or imp.startswith("../")):
            return None
        candidate = (file_path.parent / imp).resolve()
        try:
            return str(candidate.relative_to(repo_root.resolve()))
        except ValueError:
            return None
