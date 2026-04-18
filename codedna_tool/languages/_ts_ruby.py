"""_ts_ruby.py — Tree-sitter-powered CodeDNA adapter for Ruby source files.

exports: _RUBY_LANG | class TreeSitterRubyAdapter
used_by: codedna_tool/languages/__init__.py → TreeSitterRubyAdapter
rules:   Requires tree-sitter>=0.25 and tree-sitter-ruby>=0.23.
Private boundary detected by 'private'/'protected' identifier node in body_statement.
Methods after the boundary are excluded from exports.
require_relative resolved to repo-relative paths; require kept as-is.
inject_header() delegated to RubyAdapter (# comment, shebang/frozen preserved).
has_doc for Ruby: check named children of body_statement — the child IMMEDIATELY before
the method node must be a 'comment' node (Ruby comments are body_statement siblings,
NOT prev_named_sibling of the method node itself — _has_doc_block_above does NOT work here).
agent:   claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_001 | initial tree-sitter Ruby adapter
claude-sonnet-4-6 | anthropic | 2026-04-18 | s_20260418_ts | GATE 3: add funcs (LangFuncInfo) extraction — params from method_parameters, Ruby # comment has_doc via body_statement sibling check
"""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Language
import tree_sitter_ruby as ts_ruby

from .base import LangFileInfo, LangFuncInfo
from ._treesitter import TreeSitterAdapter
from .ruby import RubyAdapter

_RUBY_LANG = Language(ts_ruby.language())

def _t(node) -> str:
    return node.text.decode("utf-8", errors="replace")


class TreeSitterRubyAdapter(TreeSitterAdapter):
    """AST-based CodeDNA adapter for .rb files.

    Rules:   Public methods are those defined before first bare 'private'/'protected' identifier.
             Class methods (singleton_method with self receiver) formatted as ClassName.method.
             Instance methods formatted as ClassName#method.
             inject_header() is delegated to RubyAdapter.
    """

    def __init__(self):
        super().__init__(language=_RUBY_LANG, regex_fallback=RubyAdapter())

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a Ruby file via tree-sitter and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any error.
                 Class/module handled recursively — nested definitions are supported.
                 Private boundary is detected once per body_statement; applies to that scope only.
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

        def _fmt_ruby_params(method_node) -> str:
            """Extract param list string from a Ruby method node's method_parameters child."""
            params_node = next(
                (c for c in method_node.named_children if c.type == "method_parameters"), None
            )
            if params_node is None:
                return ""
            param_parts: list[str] = []
            for child in params_node.named_children:
                if child.type == "identifier":
                    param_parts.append(_t(child))
                elif child.type == "optional_parameter":
                    # name=default — grab identifier child
                    id_child = next(
                        (c for c in child.named_children if c.type == "identifier"), None
                    )
                    if id_child:
                        param_parts.append(f"{_t(id_child)}=nil")
                elif child.type == "splat_parameter":
                    id_child = next(
                        (c for c in child.named_children if c.type == "identifier"), None
                    )
                    if id_child:
                        param_parts.append(f"*{_t(id_child)}")
                    else:
                        param_parts.append("*")
                elif child.type == "keyword_parameter":
                    id_child = next(
                        (c for c in child.named_children if c.type == "identifier"), None
                    )
                    if id_child:
                        param_parts.append(f"{_t(id_child)}:")
                elif child.type == "block_parameter":
                    id_child = next(
                        (c for c in child.named_children if c.type == "identifier"), None
                    )
                    if id_child:
                        param_parts.append(f"&{_t(id_child)}")
            return f"({', '.join(param_parts)})" if param_parts else "()"

        def _ruby_has_doc(body_node, method_node) -> bool:
            """Return True if the named child immediately before method_node is a comment.

            Rules:   Ruby comment nodes appear as siblings in body_statement — they are NOT
                     the prev_named_sibling of the method node itself in the tree-sitter API.
                     Must walk body_node.named_children and check the node immediately before.
            """
            named = body_node.named_children
            for i, child in enumerate(named):
                if child is method_node and i > 0:
                    prev = named[i - 1]
                    return prev.type == "comment"
            return False

        def process_body(body_node, cls_name: str) -> None:
            """Walk body_statement respecting the private boundary."""
            private_seen = False
            for child in body_node.named_children:
                if child.type == "identifier" and child.text in (b"private", b"protected"):
                    private_seen = True
                    continue
                if private_seen:
                    continue
                if child.type == "method":
                    mn = next((c for c in child.named_children if c.type == "identifier"), None)
                    if mn:
                        name = _t(mn)
                        if name != "initialize":
                            entry = f"{cls_name}#{name}" if cls_name else name
                            if entry not in exports:
                                exports.append(entry)

                            params_str = _fmt_ruby_params(child)
                            sig = f"{entry}{params_str}"
                            start_line = child.start_point[0] + 1  # 1-based
                            end_line = min(child.end_point[0] + 1, start_line + 19)
                            snippet = "\n".join(src_lines[start_line - 1:end_line])
                            has_doc = _ruby_has_doc(body_node, child)
                            has_rules = "Rules:" in snippet[:200]
                            funcs.append(LangFuncInfo(
                                name=sig,
                                start_line=start_line,
                                has_doc=has_doc,
                                has_rules=has_rules,
                                source_snippet=snippet,
                                language="ruby",
                            ))
                elif child.type == "singleton_method":
                    mn = next((c for c in child.named_children if c.type == "identifier"), None)
                    if mn:
                        name = _t(mn)
                        entry = f"{cls_name}.{name}" if cls_name else name
                        if entry not in exports:
                            exports.append(entry)

                        params_str = _fmt_ruby_params(child)
                        sig = f"{entry}{params_str}"
                        start_line = child.start_point[0] + 1  # 1-based
                        end_line = min(child.end_point[0] + 1, start_line + 19)
                        snippet = "\n".join(src_lines[start_line - 1:end_line])
                        has_doc = _ruby_has_doc(body_node, child)
                        has_rules = "Rules:" in snippet[:200]
                        funcs.append(LangFuncInfo(
                            name=sig,
                            start_line=start_line,
                            has_doc=has_doc,
                            has_rules=has_rules,
                            source_snippet=snippet,
                            language="ruby",
                        ))
                elif child.type in ("class", "module"):
                    walk(child)  # recurse into nested definitions

        def walk(node) -> None:
            if node.type in ("class", "module"):
                const = next((c for c in node.named_children if c.type == "constant"), None)
                cls_name = _t(const) if const else ""
                if cls_name and cls_name not in exports:
                    exports.append(cls_name)
                body = next((c for c in node.named_children if c.type == "body_statement"), None)
                if body:
                    process_body(body, cls_name)
                return  # body already handled

            elif node.type == "call":
                fn = node.named_children[0] if node.named_children else None
                if fn and fn.type == "identifier" and fn.text in (b"require_relative", b"require"):
                    arg_list = next(
                        (c for c in node.named_children if c.type == "argument_list"), None
                    )
                    if arg_list:
                        for arg in arg_list.named_children:
                            if arg.type == "string":
                                content = next(
                                    (c for c in arg.named_children if c.type == "string_content"), None
                                )
                                if content:
                                    pstr = _t(content)
                                    if fn.text == b"require_relative":
                                        candidate = path.parent / f"{pstr}.rb"
                                        try:
                                            rel_dep = str(candidate.relative_to(repo_root))
                                            if rel_dep not in deps:
                                                deps.append(rel_dep)
                                        except ValueError:
                                            pass
                                    else:
                                        if pstr not in deps:
                                            deps.append(pstr)

            for child in node.named_children:
                walk(child)

        walk(root)

        return LangFileInfo(
            path=path, rel=rel, exports=exports, deps=deps, funcs=funcs,
            has_codedna=self.has_codedna_header(source),
        )
