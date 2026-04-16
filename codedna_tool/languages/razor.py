"""razor.py — CodeDNA v0.8 adapter for Razor templates (.cshtml, .razor).

exports: _MODEL_RE | _INJECT_RE | _USING_RE | _PARTIAL_TAG_RE | _COMPONENT_TAG_RE | _SECTION_RE | _RENDER_SECTION_RE | class RazorAdapter
used_by: codedna_tool/languages/__init__.py → RazorAdapter
rules:   regex-based only — no .NET SDK required.
Uses @* *@ comment syntax for the CodeDNA header.
Detects @model, @inject, @using as structural info.
Detects <partial>, <component> tag helpers as deps.
agent:   claude-opus-4-6 | anthropic | 2026-04-01 | s_20260401_001 | initial Razor template adapter
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import LanguageAdapter, LangFileInfo

_MODEL_RE = re.compile(r"^@model\s+([\w.]+)", re.MULTILINE)
_INJECT_RE = re.compile(r"^@inject\s+([\w.]+)\s+(\w+)", re.MULTILINE)
_USING_RE = re.compile(r"^@using\s+([\w.]+)", re.MULTILINE)
_PARTIAL_TAG_RE = re.compile(r"<partial\s+name=['\"]([^'\"]+)['\"]", re.MULTILINE)
_COMPONENT_TAG_RE = re.compile(r"<component\s+type=['\"]typeof\((\w+)\)['\"]", re.MULTILINE)
_SECTION_RE = re.compile(r"@section\s+(\w+)", re.MULTILINE)
_RENDER_SECTION_RE = re.compile(r"@RenderSection\s*\(\s*['\"](\w+)['\"]", re.MULTILINE)


class RazorAdapter(LanguageAdapter):
    """CodeDNA adapter for .cshtml and .razor files.

    Rules:   Header uses @* *@ Razor comment syntax.
             @model directives are captured as exports (the view's contract).
             @section names and @RenderSection calls are captured as exports.
             <partial> tag helpers and @inject services are captured as deps.
             Never raises — return LangFileInfo(parseable=False) on OSError.
    """

    @property
    def comment_prefix(self) -> str:
        return "@*"

    def has_codedna_header(self, source: str) -> bool:
        """Check for CodeDNA block in @* *@ comment."""
        for line in source.splitlines()[:30]:
            stripped = line.strip()
            for prefix in ("@*", "*@", "*"):
                if stripped.startswith(prefix):
                    stripped = stripped[len(prefix):].strip()
            if stripped.startswith("exports:") or stripped.startswith("used_by:"):
                return True
        return False

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a Razor template and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any OSError.
                 @model type is captured as an export (the view's data contract).
                 @section names are captured as exports.
                 <partial> tag helpers and @inject services are captured as deps.
        """
        rel = str(path.relative_to(repo_root))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return LangFileInfo(path=path, rel=rel, parseable=False)

        list_str_exports: list[str] = []

        for m in _MODEL_RE.finditer(source):
            name = f"@model:{m.group(1)}"
            if name not in list_str_exports:
                list_str_exports.append(name)

        for pat in [_SECTION_RE, _RENDER_SECTION_RE]:
            for m in pat.finditer(source):
                name = f"@section:{m.group(1)}"
                if name not in list_str_exports:
                    list_str_exports.append(name)

        list_str_deps: list[str] = []

        for m in _PARTIAL_TAG_RE.finditer(source):
            str_name_partial_from_tag = m.group(1)
            if str_name_partial_from_tag not in list_str_deps:
                list_str_deps.append(str_name_partial_from_tag)

        for m in _INJECT_RE.finditer(source):
            str_type_service_from_inject = m.group(1)
            if str_type_service_from_inject not in list_str_deps:
                list_str_deps.append(str_type_service_from_inject)

        for m in _COMPONENT_TAG_RE.finditer(source):
            str_name_component_from_tag = m.group(1)
            if str_name_component_from_tag not in list_str_deps:
                list_str_deps.append(str_name_component_from_tag)

        return LangFileInfo(
            path=path,
            rel=rel,
            exports=list_str_exports,
            deps=list_str_deps,
            has_codedna=self.has_codedna_header(source),
        )

    def inject_header(self, source: str, rel: str, exports: str, used_by: str,
                      rules: str, model_id: str, today: str) -> str:
        """Prepend a CodeDNA @* *@ comment block.

        Rules:   Must be idempotent — return source unchanged if header already present.
                 Uses @* ... *@ Razor comment syntax.
        """
        if self.has_codedna_header(source):
            return source

        filename = Path(rel).name
        stem = Path(rel).stem
        header = (
            f"@* {filename} — {stem} template.\n"
            f"*\n"
            f"* exports: {exports}\n"
            f"* used_by: {used_by}\n"
            f"* rules:   {rules}\n"
            f"* agent:   {model_id} | unknown | {today} | unknown | initial CodeDNA annotation pass\n"
            f"*@\n\n"
        )
        return header + source
