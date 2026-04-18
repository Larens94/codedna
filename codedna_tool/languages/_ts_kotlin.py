"""_ts_kotlin.py — Tree-sitter-powered CodeDNA adapter for Kotlin source files.

exports: _KOTLIN_LANG | class TreeSitterKotlinAdapter
used_by: codedna_tool/languages/__init__.py → TreeSitterKotlinAdapter
rules:   Requires tree-sitter>=0.25 and tree-sitter-kotlin>=1.1.
Top-level class_declaration, function_declaration, and const property_declaration captured.
object_declaration captured with its functions as ObjectName.fn (idiomatic Kotlin singleton).
companion_object functions captured as ClassName.fn using grandparent class_declaration name.
import qualified_identifier captured as dependency string.
inject_header() delegated to KotlinAdapter (// comment after package declaration).
Visibility: no modifiers OR public modifier → include; private/protected/internal → skip.
has_doc: block_comment prev_named_sibling starting with /** (KDoc).
Return type: first user_type or nullable_type named child of function_declaration.
agent:   claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_001 | initial tree-sitter Kotlin adapter
claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_002 | add object_declaration and companion_object function capture
claude-sonnet-4-6 | anthropic | 2026-04-18 | s_20260418_ts | GATE 3: add funcs (LangFuncInfo) extraction — visibility filter, params, return type, KDoc has_doc via _has_doc_block_above
claude-sonnet-4-6 | anthropic | 2026-04-18 | s_20260418_msg | _resolve_kotlin_import(): com.example.UserService → com/example/UserService.kt; star imports dropped
"""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Language
import tree_sitter_kotlin as ts_kotlin

from .base import LangFileInfo, LangFuncInfo
from ._treesitter import TreeSitterAdapter
from .java import KotlinAdapter

_KOTLIN_LANG = Language(ts_kotlin.language())

def _t(node) -> str:
    return node.text.decode("utf-8", errors="replace")


def _resolve_kotlin_import(fqcn: str, repo_root: Path) -> str | None:
    """Resolve a Kotlin fully-qualified class name to a repo-relative .kt file path.

    Rules:   Same convention as Java: com.example.UserService → com/example/UserService.kt.
             Also tries .kts extension. Returns None if file doesn't exist or is outside repo.
             Star imports (ending with .*) are dropped.
    """
    if fqcn.endswith(".*"):
        return None
    base = fqcn.replace(".", "/")
    for ext in (".kt", ".kts"):
        candidate = repo_root / (base + ext)
        if candidate.exists():
            try:
                return str(candidate.resolve().relative_to(repo_root.resolve()))
            except ValueError:
                pass
    return None


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
        funcs: list[LangFuncInfo] = []
        src_lines = source.splitlines()

        def _is_kotlin_private(fn_node) -> bool:
            """Return True if function has private/protected/internal visibility modifier."""
            mods = next(
                (c for c in fn_node.named_children if c.type == "modifiers"), None
            )
            if mods is None:
                return False  # no modifiers → public by default in Kotlin
            for child in mods.named_children:
                if child.type == "visibility_modifier":
                    vis = _t(child)
                    if vis in ("private", "protected", "internal"):
                        return True
            return False

        def _capture_fn_info(fn_node, entry: str) -> None:
            """Build and append LangFuncInfo for a Kotlin function_declaration node."""
            params_node = next(
                (c for c in fn_node.named_children
                 if c.type == "function_value_parameters"), None
            )
            # Return type: first user_type or nullable_type named child
            ret_node = next(
                (c for c in fn_node.named_children
                 if c.type in ("user_type", "nullable_type")), None
            )
            sig = self._fmt_sig(entry, params_node, ret_node)

            start_line = fn_node.start_point[0] + 1  # 1-based
            end_line = min(fn_node.end_point[0] + 1, start_line + 19)
            snippet = "\n".join(src_lines[start_line - 1:end_line])

            has_doc = self._has_doc_block_above(fn_node)
            has_rules = "Rules:" in snippet[:200]

            funcs.append(LangFuncInfo(
                name=sig,
                start_line=start_line,
                has_doc=has_doc,
                has_rules=has_rules,
                source_snippet=snippet,
                language="kotlin",
            ))

        def _capture_fns_in_body(body_node, prefix: str) -> None:
            """Capture function_declarations inside a class_body as prefix.fn."""
            for child in body_node.named_children:
                if child.type == "function_declaration":
                    # Rules: skip private/protected/internal functions
                    if _is_kotlin_private(child):
                        continue
                    id_node = next(
                        (c for c in child.named_children if c.type == "identifier"), None
                    )
                    if id_node:
                        entry = f"{prefix}.{_t(id_node)}" if prefix else _t(id_node)
                        if entry not in exports:
                            exports.append(entry)
                        _capture_fn_info(child, entry)

        def walk(node) -> None:
            if node.type == "class_declaration":
                id_node = next(
                    (c for c in node.named_children if c.type == "identifier"), None
                )
                if id_node:
                    n = _t(id_node)
                    if n not in exports:
                        exports.append(n)
                # Capture public methods in class body as ClassName.fn
                body = next(
                    (c for c in node.named_children if c.type == "class_body"), None
                )
                if body:
                    _capture_fns_in_body(body, n if id_node else "")
                return  # body already handled — don't recurse into class_body

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
                    if not _is_kotlin_private(node):
                        id_node = next(
                            (c for c in node.named_children if c.type == "identifier"), None
                        )
                        if id_node:
                            n = _t(id_node)
                            if n not in exports:
                                exports.append(n)
                            _capture_fn_info(node, n)

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
                    # Try to resolve com.example.UserService → com/example/UserService.kt
                    resolved = _resolve_kotlin_import(pkg, repo_root)
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
