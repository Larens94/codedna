"""vbnet.py — CodeDNA v0.9 adapter for VB.NET source files.

exports: _CLASS_RE | _METHOD_RE | _PROP_RE | _IMPORTS_RE | class VbNetAdapter
used_by: codedna_tool/languages/__init__.py → VbNetAdapter
rules:   regex-based only — no .NET SDK or tree-sitter dependency required.
Detects Public Class/Module/Interface/Structure/Enum and Public Sub/Function/Property.
Type-qualified exports: Class::Member for public members.
Friend/Private/Protected members are excluded (Friend ≈ C# internal).
VB uses apostrophe (' ) comments — no docstring syntax.
agent:   composer | cursor | 2026-09-06 | s_20260906_vbnet | issue #6: initial VB.NET LanguageAdapter (.vb, ' comments)
message:
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import LanguageAdapter, LangFileInfo

# Case-insensitive: VB.NET keywords are not case-sensitive.
_CLASS_RE = re.compile(
    r"^\s*(?:Public\s+)?(?:Partial\s+|MustInherit\s+|NotInheritable\s+)*"
    r"(?:Class|Module|Interface|Structure|Enum)\s+(\w+)",
    re.MULTILINE | re.IGNORECASE,
)
_METHOD_RE = re.compile(
    r"^\s+Public\s+(?:Shared\s+|Overridable\s+|Overrides\s+|MustOverride\s+|Async\s+)*"
    r"(?:Sub|Function)\s+(\w+)\s*[\(\[]",
    re.MULTILINE | re.IGNORECASE,
)
_PROP_RE = re.compile(
    r"^\s+Public\s+(?:Shared\s+|ReadOnly\s+|WriteOnly\s+)*Property\s+(\w+)",
    re.MULTILINE | re.IGNORECASE,
)
_IMPORTS_RE = re.compile(r"^Imports\s+([\w.]+)", re.MULTILINE | re.IGNORECASE)
_OPTION_RE = re.compile(r"^Option\s+\w+", re.MULTILINE | re.IGNORECASE)


class VbNetAdapter(LanguageAdapter):
    """CodeDNA adapter for .vb files.

    Rules:   Only Public members captured; Private/Protected/Friend are excluded.
             Partial classes are treated as a single export entry.
             Never raises — return LangFileInfo(parseable=False) on OSError.
             comment_prefix is apostrophe (' ) — VB has no block-docstring syntax.
    """

    @property
    def comment_prefix(self) -> str:
        return "'"

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a VB.NET source file and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any OSError.
                 Public methods are listed as ClassName::Member.
                 Properties are included as exports.
                 Imports directives are captured but not resolved to file paths.
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
        reserved = {
            "class", "module", "interface", "structure", "enum",
            "sub", "function", "property", "string", "integer", "boolean",
            "object", "task",
        }
        for m in _METHOD_RE.finditer(source):
            name = m.group(1)
            if name in seen or name.lower() in reserved:
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

        list_str_deps = [m.group(1) for m in _IMPORTS_RE.finditer(source)]

        return LangFileInfo(
            path=path,
            rel=rel,
            exports=list_str_exports,
            deps=list_str_deps,
            has_codedna=self.has_codedna_header(source),
        )

    def inject_header(self, source: str, rel: str, exports: str, used_by: str,
                      rules: str, model_id: str, today: str) -> str:
        """Prepend a CodeDNA ' comment block after Option/Imports, before types.

        Rules:   Must be idempotent.
                 Option Explicit/Strict/Infer/Compare and Imports stay at file top.
                 CodeDNA block is inserted BEFORE Namespace / Public Class|Module|…
                 — never inside a type body.
                 If no Option/Imports, inserts at file top.
        """
        if self.has_codedna_header(source):
            return source

        header_lines = self._build_header_lines(rel, exports, used_by, rules, model_id, today)
        header = "\n".join(header_lines) + "\n"

        lines = source.splitlines(keepends=True)
        insert_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            lower = stripped.lower()
            if (
                lower.startswith("option ")
                or lower.startswith("imports ")
                or not stripped
                or stripped.startswith("'")
            ):
                insert_idx = i + 1
            elif stripped.startswith("<"):  # attribute
                continue
            else:
                break

        before = "".join(lines[:insert_idx])
        after = "".join(lines[insert_idx:])
        before_norm = before.rstrip("\n")
        after_norm = after.lstrip("\n")
        separator = "\n\n" if before_norm else ""
        return before_norm + separator + header + "\n" + after_norm
