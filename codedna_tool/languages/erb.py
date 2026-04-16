"""erb.py — CodeDNA v0.8 adapter for ERB and EJS templates.

exports: _RENDER_RE | _INCLUDE_RE | _CONTENT_FOR_RE | _YIELD_RE | class ErbAdapter
used_by: codedna_tool/languages/__init__.py → ErbAdapter
rules:   regex-based only — no Ruby/Node.js interpreter required.
Uses <%# %> comment syntax for the CodeDNA header.
Covers both ERB (.erb) and EJS (.ejs) — same comment syntax.
Detects render/partial calls as deps.
agent:   claude-opus-4-6 | anthropic | 2026-04-01 | s_20260401_001 | initial ERB/EJS template adapter
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import LanguageAdapter, LangFileInfo

# ERB: render partial: 'shared/nav'
_RENDER_RE = re.compile(r"render\s*(?:partial:\s*)?['\"]([^'\"]+)['\"]", re.MULTILINE)
# EJS: include('partials/header')
_INCLUDE_RE = re.compile(r"include\s*\(\s*['\"]([^'\"]+)['\"]", re.MULTILINE)
# content_for :head / yield :sidebar
_CONTENT_FOR_RE = re.compile(r"content_for\s*[:(]\s*:?(\w+)", re.MULTILINE)
_YIELD_RE = re.compile(r"yield\s*[:(]\s*:?(\w+)", re.MULTILINE)


class ErbAdapter(LanguageAdapter):
    """CodeDNA adapter for .erb and .ejs files.

    Rules:   Header uses <%# %> comment syntax.
             render/partial calls are captured as deps.
             content_for/yield names are captured as exports.
             Never raises — return LangFileInfo(parseable=False) on OSError.
    """

    @property
    def comment_prefix(self) -> str:
        return "<%#"

    def has_codedna_header(self, source: str) -> bool:
        """Check for CodeDNA block in <%# %> comment."""
        for line in source.splitlines()[:30]:
            stripped = line.strip()
            for prefix in ("<%#", "%>", "#"):
                if stripped.startswith(prefix):
                    stripped = stripped[len(prefix):].strip()
            if stripped.startswith("exports:") or stripped.startswith("used_by:"):
                return True
        return False

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse an ERB/EJS template and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any OSError.
                 render/partial calls are captured as deps.
                 content_for/yield names are captured as exports.
        """
        rel = str(path.relative_to(repo_root))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return LangFileInfo(path=path, rel=rel, parseable=False)

        list_str_exports: list[str] = []
        for pat in [_CONTENT_FOR_RE, _YIELD_RE]:
            for m in pat.finditer(source):
                name = m.group(1)
                if name not in list_str_exports:
                    list_str_exports.append(name)

        list_str_deps: list[str] = []
        for pat in [_RENDER_RE, _INCLUDE_RE]:
            for m in pat.finditer(source):
                str_path_dep_from_render = m.group(1)
                if str_path_dep_from_render not in list_str_deps:
                    list_str_deps.append(str_path_dep_from_render)

        return LangFileInfo(
            path=path,
            rel=rel,
            exports=list_str_exports,
            deps=list_str_deps,
            has_codedna=self.has_codedna_header(source),
        )

    def inject_header(self, source: str, rel: str, exports: str, used_by: str,
                      rules: str, model_id: str, today: str) -> str:
        """Prepend a CodeDNA <%# %> comment block.

        Rules:   Must be idempotent — return source unchanged if header already present.
                 Uses multi-line <%# ... %> syntax.
        """
        if self.has_codedna_header(source):
            return source

        filename = Path(rel).name
        stem = Path(rel).stem
        header = (
            f"<%# {filename} — {stem} template.\n"
            f"#\n"
            f"# exports: {exports}\n"
            f"# used_by: {used_by}\n"
            f"# rules:   {rules}\n"
            f"# agent:   {model_id} | unknown | {today} | unknown | initial CodeDNA annotation pass\n"
            f"%>\n\n"
        )
        return header + source
