"""handlebars.py — CodeDNA v0.8 adapter for Handlebars and Mustache templates.

exports: class HandlebarsAdapter
used_by: languages/__init__.py -> _REGISTRY
rules:   regex-based only — no Node.js required.
         Uses {{!-- --}} comment syntax for the CodeDNA header.
         Detects {{> partial}} as deps.
         Detects {{#block}} helpers as exports.
agent:   claude-opus-4-6 | anthropic | 2026-04-01 | s_20260401_001 | initial Handlebars/Mustache adapter
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import LanguageAdapter, LangFileInfo

_PARTIAL_RE = re.compile(r"\{\{>\s*([^\s}]+)", re.MULTILINE)
_BLOCK_RE = re.compile(r"\{\{#(\w+)", re.MULTILINE)
_HELPER_RE = re.compile(r"registerHelper\s*\(\s*['\"](\w+)['\"]", re.MULTILINE)


class HandlebarsAdapter(LanguageAdapter):
    """CodeDNA adapter for .hbs and .mustache files.

    Rules:   Header uses {{!-- --}} Handlebars long comment syntax.
             {{> partial}} references are captured as deps.
             {{#block}} helpers are captured as exports.
             Never raises — return LangFileInfo(parseable=False) on OSError.
    """

    @property
    def comment_prefix(self) -> str:
        return "{{!--"

    def has_codedna_header(self, source: str) -> bool:
        """Check for CodeDNA block in {{!-- --}} comment."""
        for line in source.splitlines()[:30]:
            stripped = line.strip()
            for prefix in ("{{!--", "--}}", "!--", "--"):
                if stripped.startswith(prefix):
                    stripped = stripped[len(prefix):].strip()
            if stripped.startswith("exports:") or stripped.startswith("used_by:"):
                return True
        return False

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a Handlebars/Mustache template and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any OSError.
                 {{> partial}} names are captured as deps.
                 {{#block}} names and registerHelper calls are captured as exports.
        """
        rel = str(path.relative_to(repo_root))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return LangFileInfo(path=path, rel=rel, parseable=False)

        list_str_exports: list[str] = []
        for pat in [_BLOCK_RE, _HELPER_RE]:
            for m in pat.finditer(source):
                name = m.group(1)
                if name not in list_str_exports:
                    list_str_exports.append(name)

        list_str_deps: list[str] = []
        for m in _PARTIAL_RE.finditer(source):
            str_name_partial_from_template = m.group(1)
            if str_name_partial_from_template not in list_str_deps:
                list_str_deps.append(str_name_partial_from_template)

        return LangFileInfo(
            path=path,
            rel=rel,
            exports=list_str_exports,
            deps=list_str_deps,
            has_codedna=self.has_codedna_header(source),
        )

    def inject_header(self, source: str, rel: str, exports: str, used_by: str,
                      rules: str, model_id: str, today: str) -> str:
        """Prepend a CodeDNA {{!-- --}} comment block.

        Rules:   Must be idempotent — return source unchanged if header already present.
                 Uses {{!-- ... --}} long comment syntax (not {{! short }}).
        """
        if self.has_codedna_header(source):
            return source

        filename = Path(rel).name
        stem = Path(rel).stem
        header = (
            f"{{{{!-- {filename} — {stem} template.\n"
            f"\n"
            f"  exports: {exports}\n"
            f"  used_by: {used_by}\n"
            f"  rules:   {rules}\n"
            f"  agent:   {model_id} | unknown | {today} | unknown | initial CodeDNA annotation pass\n"
            f"--}}}}\n\n"
        )
        return header + source
