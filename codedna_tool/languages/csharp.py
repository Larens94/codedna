"""csharp.py — CodeDNA v0.9 adapter for C# source files.

exports: _CLASS_RE | _METHOD_RE | _PROP_RE | _USING_RE | class CSharpAdapter | CSharpAdapter.inject_function_rules
used_by: codedna_tool/languages/__init__.py → CSharpAdapter
         codedna_tool/languages/_ts_csharp.py → CSharpAdapter
rules:   regex-based only — no .NET SDK dependency required.
Detects public class/interface/enum/struct/record and public methods.
Namespace-qualified exports: Class::Method for public members.
Attributes ([Attribute]) before declarations are ignored.
inject_function_rules uses /// XML doc comments — has_doc inserts <remarks>Rules:, no-doc inserts new <summary>Rules:.
agent:   claude-opus-4-6 | anthropic | 2026-04-14 | s_20260414_002 | fixed class detection inside namespace blocks: allow indented class/interface/enum/struct/record
claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_001 | fixed inject_header: header now inserted before namespace declaration, not between 'namespace Foo' and its '{'; also fixed leading blank line
claude-sonnet-4-6 | anthropic | 2026-04-18 | s_20260418_ts | GATE 3: add inject_function_rules() — C# XML doc comments (///); has_doc appends <remarks>Rules:, no-doc inserts new <summary>Rules: block
claude-opus-4-6 | anthropic | 2026-04-21 | s_20260421_secfix | fix ReDoS in _METHOD_RE — nested quantifier (?:[\\w<>\\[\\]?,\\s]+\\s+)+ replaced with non-greedy single group (CodeQL #1099, #1098)
claude-opus-4-6 | anthropic | 2026-04-21 | s_20260421_codeql | remove unused _NS_RE regex global (dead declaration) — CodeQL #1100
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import LanguageAdapter, LangFileInfo, LangFuncInfo

_CLASS_RE  = re.compile(
    r"^\s*(?:public\s+)?(?:abstract\s+|sealed\s+|static\s+|partial\s+)*"
    r"(?:class|interface|enum|struct|record)\s+(\w+)",
    re.MULTILINE,
)
_METHOD_RE = re.compile(
    r"^\s+public\s+(?:static\s+|virtual\s+|override\s+|abstract\s+|async\s+)*"
    r"[\w<>\[\]?,\s]+?\s+(\w+)\s*[(<]",
    re.MULTILINE,
)
_PROP_RE   = re.compile(
    r"^\s+public\s+(?:static\s+)?(?:[\w<>\[\]?,]+\s+)+(\w+)\s*\{",
    re.MULTILINE,
)
_USING_RE  = re.compile(r"^using\s+([\w.]+)\s*;", re.MULTILINE)


class CSharpAdapter(LanguageAdapter):
    """CodeDNA adapter for .cs files.

    Rules:   Only public members captured; private/protected/internal are excluded.
             Partial classes are treated as a single export entry.
             Never raises — return LangFileInfo(parseable=False) on OSError.
    """

    @property
    def comment_prefix(self) -> str:
        return "//"

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a C# source file and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any OSError.
                 Public methods are listed as ClassName::Method.
                 Properties are included as exports.
                 using directives are captured but not resolved to file paths
                 (C# assembly refs don't map 1:1 to file paths without project file parsing).
        """
        rel = str(path.relative_to(repo_root))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return LangFileInfo(path=path, rel=rel, parseable=False)

        list_str_exports: list[str] = []
        cls_names: list[str] = []

        for m in _CLASS_RE.finditer(source):
            name = m.group(1)
            if name not in cls_names:
                cls_names.append(name)
                list_str_exports.append(name)

        cls_prefix = cls_names[0] + "::" if cls_names else ""

        seen: set[str] = set(cls_names)
        for m in _METHOD_RE.finditer(source):
            name = m.group(1)
            if name in seen or name in ("class", "interface", "struct", "enum", "record",
                                         "void", "string", "int", "bool", "Task", "IEnumerable"):
                continue
            entry = f"{cls_prefix}{name}"
            if entry not in list_str_exports:
                list_str_exports.append(entry)
                seen.add(name)

        for m in _PROP_RE.finditer(source):
            name = m.group(1)
            if name not in seen:
                entry = f"{cls_prefix}{name}"
                if entry not in list_str_exports:
                    list_str_exports.append(entry)
                    seen.add(name)

        list_str_deps = [m.group(1) for m in _USING_RE.finditer(source)]

        return LangFileInfo(
            path=path,
            rel=rel,
            exports=list_str_exports,
            deps=list_str_deps,
            has_codedna=self.has_codedna_header(source),
        )

    def inject_header(self, source: str, rel: str, exports: str, used_by: str,
                      rules: str, model_id: str, today: str) -> str:
        """Prepend a CodeDNA // comment block between using directives and namespace.

        Rules:   Must be idempotent.
                 using directives are preserved at file top.
                 CodeDNA block is inserted BEFORE the namespace declaration —
                 never between 'namespace Foo' and its opening '{'.
                 If no using/namespace, inserts at file top.
        """
        if self.has_codedna_header(source):
            return source

        header_lines = self._build_header_lines(rel, exports, used_by, rules, model_id, today)
        header = "\n".join(header_lines) + "\n"

        lines = source.splitlines(keepends=True)
        insert_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("using ") or not stripped:
                insert_idx = i + 1
            elif stripped.startswith("[") or stripped.startswith("//"):
                continue
            else:
                break  # stop before namespace / class / anything else

        before = "".join(lines[:insert_idx])
        after = "".join(lines[insert_idx:])
        # Normalize to exactly one blank line between sections
        before_norm = before.rstrip("\n")
        after_norm = after.lstrip("\n")
        separator = "\n\n" if before_norm else ""
        return before_norm + separator + header + "\n" + after_norm

    def inject_function_rules(self, source: str, func: LangFuncInfo, rules_text: str) -> str:
        """Inject a C# XML doc Rules: comment above a public method.

        Rules:   Must be idempotent — if func.has_rules is True, return source unchanged.
                 C# uses /// XML doc comments.
                 If func.has_doc=True: insert /// <remarks>Rules: rules_text</remarks> just
                 above func.start_line (immediately before the method, after existing ///).
                 If func.has_doc=False: insert a /// <summary>Rules: rules_text</summary>
                 block above func.start_line.
                 Operates by line number (func.start_line, 1-based) — caller MUST apply
                 from BOTTOM to TOP to preserve line numbers across multiple injections.
        """
        if func.has_rules:
            return source

        lines = source.splitlines(keepends=True)
        method_idx = func.start_line - 1  # 0-based index of method's first line

        # Detect indentation from the method line
        method_line = lines[method_idx] if method_idx < len(lines) else ""
        indent = len(method_line) - len(method_line.lstrip())
        pad = " " * indent

        if func.has_doc:
            # Insert /// <remarks>Rules: ...</remarks> immediately above the method line
            # (the existing /// lines are above; we add one more just before the method)
            rules_line = f"{pad}/// <remarks>Rules:   {rules_text}</remarks>\n"
            lines = lines[:method_idx] + [rules_line] + lines[method_idx:]
        else:
            # No existing doc — insert a new /// <summary>Rules: ...</summary> block
            doc_block = (
                f"{pad}/// <summary>Rules:   {rules_text}</summary>\n"
            )
            lines = lines[:method_idx] + [doc_block] + lines[method_idx:]

        return "".join(lines)
