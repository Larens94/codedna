"""_ts_java.py — Tree-sitter-powered CodeDNA adapter for Java source files.

exports: _JAVA_LANG | _SKIP_NAMES | class TreeSitterJavaAdapter
used_by: codedna_tool/languages/__init__.py → TreeSitterJavaAdapter
rules:   Requires tree-sitter>=0.25 and tree-sitter-java>=0.23.
Only public types and public methods captured (modifiers contains 'public').
Import paths captured as strings — not resolved to file paths (requires project structure).
inject_header() delegated to JavaAdapter (// comment after package declaration).
Return type: first named child before the method name identifier (type_identifier or void_type).
agent:   claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_001 | initial tree-sitter Java adapter
claude-sonnet-4-6 | anthropic | 2026-04-18 | s_20260418_ts | GATE 3: populate funcs with LangFuncInfo + full signatures (return type + params) for each public method
claude-sonnet-4-6 | anthropic | 2026-04-18 | s_20260418_msg | _resolve_java_import(): com.example.User → com/example/User.java; wildcard imports dropped
"""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Language
import tree_sitter_java as ts_java

from .base import LangFileInfo, LangFuncInfo
from ._treesitter import TreeSitterAdapter
from .java import JavaAdapter

_JAVA_LANG = Language(ts_java.language())

_SKIP_NAMES = frozenset({"class", "interface", "enum", "record", "void", "static"})

def _t(node) -> str:
    return node.text.decode("utf-8", errors="replace")


def _resolve_java_import(fqcn: str, repo_root: Path) -> str | None:
    """Resolve a Java fully-qualified class name to a repo-relative .java file path.

    Rules:   Converts com.example.UserService → com/example/UserService.java.
             Only resolves if the file actually exists under repo_root.
             Wildcard imports (ending with .*) are dropped — not resolvable to a single file.
    """
    if fqcn.endswith(".*"):
        return None
    candidate = repo_root / (fqcn.replace(".", "/") + ".java")
    if candidate.exists():
        try:
            return str(candidate.resolve().relative_to(repo_root.resolve()))
        except ValueError:
            pass
    return None


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
        funcs: list[LangFuncInfo] = []
        src_lines = source.splitlines()

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

                            # Extract return type: first named child that is a type node,
                            # appearing before the method name identifier in named_children.
                            # Rules: stop scanning once we hit the identifier (method name).
                            return_node = None
                            for child in node.named_children:
                                if child is id_node:
                                    break
                                if child.type in ("type_identifier", "void_type",
                                                  "integral_type", "floating_point_type",
                                                  "boolean_type", "generic_type",
                                                  "array_type", "scoped_type_identifier"):
                                    return_node = child

                            params_node = next(
                                (c for c in node.named_children if c.type == "formal_parameters"),
                                None,
                            )
                            sig = self._fmt_sig(entry, params_node, return_node)

                            # Build LangFuncInfo for L2 Rules: injection
                            start_line = node.start_point[0] + 1  # 1-based
                            snippet_start = start_line - 1
                            snippet_lines = src_lines[snippet_start:snippet_start + 20]
                            snippet = "\n".join(snippet_lines)
                            has_doc = self._has_doc_block_above(node)
                            has_rules = "Rules:" in snippet[:200]
                            funcs.append(LangFuncInfo(
                                name=sig,
                                start_line=start_line,
                                has_doc=has_doc,
                                has_rules=has_rules,
                                source_snippet=snippet,
                                language="java",
                            ))

            elif node.type == "import_declaration":
                si = next((c for c in node.named_children
                           if c.type == "scoped_identifier"), None)
                if si:
                    pkg = _t(si)
                    # Try to resolve to a filesystem path within the repo
                    resolved = _resolve_java_import(pkg, repo_root)
                    entry = resolved if resolved else pkg
                    if entry not in deps:
                        deps.append(entry)

            for child in node.named_children:
                walk(child)

        walk(root)

        return LangFileInfo(
            path=path, rel=rel, exports=exports, deps=deps, funcs=funcs,
            has_codedna=self.has_codedna_header(source),
        )
