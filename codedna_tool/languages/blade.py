"""blade.py — CodeDNA v0.8 adapter for Laravel Blade templates.

exports: _EXTENDS_RE | _INCLUDE_RE | _COMPONENT_RE | _LIVEWIRE_RE | _SECTION_RE | _SLOT_RE | class BladeAdapter
used_by: codedna_tool/languages/__init__.py → BladeAdapter
rules:   regex-based only — no PHP interpreter required.
Uses {{-- --}} block comment for the CodeDNA header.
Detects @extends, @include, @component, @livewire as deps.
Detects @section, @slot, @yield as exports.
agent:   claude-opus-4-6 | anthropic | 2026-04-01 | s_20260401_001 | initial Blade template adapter
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import LanguageAdapter, LangFileInfo

_EXTENDS_RE = re.compile(r"@extends\s*\(\s*['\"]([^'\"]+)['\"]", re.MULTILINE)
_INCLUDE_RE = re.compile(r"@include(?:If|When|Unless)?\s*\(\s*['\"]([^'\"]+)['\"]", re.MULTILINE)
_COMPONENT_RE = re.compile(r"@component\s*\(\s*['\"]([^'\"]+)['\"]", re.MULTILINE)
_LIVEWIRE_RE = re.compile(r"@livewire\s*\(\s*['\"]([^'\"]+)['\"]", re.MULTILINE)
_SECTION_RE = re.compile(r"@(?:section|yield)\s*\(\s*['\"]([^'\"]+)['\"]", re.MULTILINE)
_SLOT_RE = re.compile(r"@slot\s*\(\s*['\"]([^'\"]+)['\"]", re.MULTILINE)


class BladeAdapter(LanguageAdapter):
    """CodeDNA adapter for .blade.php files.

    Rules:   Header uses {{-- --}} Blade comment block, NOT // or <!-- -->.
             @extends and @include are captured as deps (dot-notation to path).
             @section and @yield are captured as exports (named slots).
             Never raises — return LangFileInfo(parseable=False) on OSError.
    """

    @property
    def comment_prefix(self) -> str:
        return "{{--"

    def has_codedna_header(self, source: str) -> bool:
        """Check for CodeDNA block in Blade {{-- --}} comment."""
        for line in source.splitlines()[:30]:
            stripped = line.strip()
            # Strip Blade comment markers
            for prefix in ("{{--", "--}}", "--"):
                if stripped.startswith(prefix):
                    stripped = stripped[len(prefix):].strip()
            if stripped.startswith("exports:") or stripped.startswith("used_by:"):
                return True
        return False

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a Blade template and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any OSError.
                 @extends/@include use dot-notation (e.g. 'layouts.app') — convert to path.
                 @section/@yield names are captured as exports.
        """
        rel = str(path.relative_to(repo_root))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return LangFileInfo(path=path, rel=rel, parseable=False)

        list_str_exports: list[str] = []
        for pat in [_SECTION_RE, _SLOT_RE]:
            for m in pat.finditer(source):
                name = f"@section:{m.group(1)}"
                if name not in list_str_exports:
                    list_str_exports.append(name)

        list_str_deps: list[str] = []
        for pat in [_EXTENDS_RE, _INCLUDE_RE, _COMPONENT_RE, _LIVEWIRE_RE]:
            for m in pat.finditer(source):
                dot_path = m.group(1)
                # Convert dot-notation to file path: layouts.app -> resources/views/layouts/app.blade.php
                str_path_blade_from_dot = dot_path.replace(".", "/") + ".blade.php"
                if str_path_blade_from_dot not in list_str_deps:
                    list_str_deps.append(str_path_blade_from_dot)

        return LangFileInfo(
            path=path,
            rel=rel,
            exports=list_str_exports,
            deps=list_str_deps,
            has_codedna=self.has_codedna_header(source),
        )

    def inject_header(self, source: str, rel: str, exports: str, used_by: str,
                      rules: str, model_id: str, today: str) -> str:
        """Prepend a CodeDNA {{-- --}} comment block.

        Rules:   Must be idempotent — return source unchanged if header already present.
                 Blade comments use {{-- ... --}} syntax.
        """
        if self.has_codedna_header(source):
            return source

        filename = Path(rel).name
        stem = Path(rel).stem.replace(".blade", "")
        header = (
            f"{{{{-- {filename} — {stem} template.\n"
            f"--\n"
            f"-- exports: {exports}\n"
            f"-- used_by: {used_by}\n"
            f"-- rules:   {rules}\n"
            f"-- agent:   {model_id} | unknown | {today} | unknown | initial CodeDNA annotation pass\n"
            f"--}}}}\n\n"
        )
        return header + source
