"""csharp.py — CodeDNA v0.8 adapter for C# source files.

exports: _CLASS_RE | _METHOD_RE | _PROP_RE | _USING_RE | _NS_RE | class CSharpAdapter
used_by: codedna_tool/languages/__init__.py → CSharpAdapter
         codedna_tool/languages/_ts_csharp.py → CSharpAdapter
rules:   regex-based only — no .NET SDK dependency required.
Detects public class/interface/enum/struct/record and public methods.
Namespace-qualified exports: Class::Method for public members.
Attributes ([Attribute]) before declarations are ignored.
agent:   claude-opus-4-6 | anthropic | 2026-04-14 | s_20260414_002 | fixed class detection inside namespace blocks: allow indented class/interface/enum/struct/record
claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_001 | fixed inject_header: header now inserted before namespace declaration, not between 'namespace Foo' and its '{'; also fixed leading blank line
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import LanguageAdapter, LangFileInfo

_CLASS_RE  = re.compile(
    r"^\s*(?:public\s+)?(?:abstract\s+|sealed\s+|static\s+|partial\s+)*"
    r"(?:class|interface|enum|struct|record)\s+(\w+)",
    re.MULTILINE,
)
_METHOD_RE = re.compile(
    r"^\s+public\s+(?:static\s+|virtual\s+|override\s+|abstract\s+|async\s+)*"
    r"(?:[\w<>\[\]?,\s]+\s+)+(\w+)\s*[(<]",
    re.MULTILINE,
)
_PROP_RE   = re.compile(
    r"^\s+public\s+(?:static\s+)?(?:[\w<>\[\]?,]+\s+)+(\w+)\s*\{",
    re.MULTILINE,
)
_USING_RE  = re.compile(r"^using\s+([\w.]+)\s*;", re.MULTILINE)
_NS_RE     = re.compile(r"^namespace\s+([\w.]+)", re.MULTILINE)


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
