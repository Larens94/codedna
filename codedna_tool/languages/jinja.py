"""jinja.py — CodeDNA v0.8 adapter for Jinja2 and Twig templates.

exports: _EXTENDS_RE | _INCLUDE_RE | _IMPORT_RE | _BLOCK_RE | _MACRO_RE | class JinjaAdapter
used_by: codedna_tool/languages/__init__.py → JinjaAdapter
rules:   regex-based only — no Python/PHP interpreter required.
Uses {# #} block comment for the CodeDNA header.
Covers both Jinja2 (.j2, .jinja2) and Twig (.twig) — same comment syntax.
Detects {% extends %}, {% include %}, {% import %}, {% from %} as deps.
Detects {% block %} and {% macro %} as exports.
agent:   claude-opus-4-6 | anthropic | 2026-04-01 | s_20260401_001 | initial Jinja2/Twig template adapter
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import LanguageAdapter, LangFileInfo

_EXTENDS_RE = re.compile(r"\{%[-\s]*extends\s+['\"]([^'\"]+)['\"]", re.MULTILINE)
_INCLUDE_RE = re.compile(r"\{%[-\s]*include\s+['\"]([^'\"]+)['\"]", re.MULTILINE)
_IMPORT_RE = re.compile(r"\{%[-\s]*(?:import|from)\s+['\"]([^'\"]+)['\"]", re.MULTILINE)
_BLOCK_RE = re.compile(r"\{%[-\s]*block\s+(\w+)", re.MULTILINE)
_MACRO_RE = re.compile(r"\{%[-\s]*macro\s+(\w+)", re.MULTILINE)


class JinjaAdapter(LanguageAdapter):
    """CodeDNA adapter for .j2, .jinja2, .twig files.

    Rules:   Header uses {# #} Jinja/Twig comment syntax.
             {% extends %} and {% include %} are captured as deps.
             {% block %} and {% macro %} are captured as exports.
             Never raises — return LangFileInfo(parseable=False) on OSError.
    """

    @property
    def comment_prefix(self) -> str:
        return "{#"

    def has_codedna_header(self, source: str) -> bool:
        """Check for CodeDNA block in {# #} comment."""
        for line in source.splitlines()[:30]:
            stripped = line.strip()
            for prefix in ("{#", "#}", "#"):
                if stripped.startswith(prefix):
                    stripped = stripped[len(prefix):].strip()
            if stripped.startswith("exports:") or stripped.startswith("used_by:"):
                return True
        return False

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a Jinja2/Twig template and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any OSError.
                 {% extends %} and {% include %} paths are captured as-is (relative template paths).
                 {% block %} and {% macro %} names are captured as exports.
        """
        rel = str(path.relative_to(repo_root))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return LangFileInfo(path=path, rel=rel, parseable=False)

        list_str_exports: list[str] = []
        for pat in [_BLOCK_RE, _MACRO_RE]:
            for m in pat.finditer(source):
                name = m.group(1)
                if name not in list_str_exports:
                    list_str_exports.append(name)

        list_str_deps: list[str] = []
        for pat in [_EXTENDS_RE, _INCLUDE_RE, _IMPORT_RE]:
            for m in pat.finditer(source):
                str_path_dep_from_template = m.group(1)
                if str_path_dep_from_template not in list_str_deps:
                    list_str_deps.append(str_path_dep_from_template)

        return LangFileInfo(
            path=path,
            rel=rel,
            exports=list_str_exports,
            deps=list_str_deps,
            has_codedna=self.has_codedna_header(source),
        )

    def inject_header(self, source: str, rel: str, exports: str, used_by: str,
                      rules: str, model_id: str, today: str) -> str:
        """Prepend a CodeDNA {# #} comment block.

        Rules:   Must be idempotent — return source unchanged if header already present.
                 Uses multi-line {# ... #} syntax.
        """
        if self.has_codedna_header(source):
            return source

        filename = Path(rel).name
        stem = Path(rel).stem
        header = (
            f"{{# {filename} — {stem} template.\n"
            f"#\n"
            f"# exports: {exports}\n"
            f"# used_by: {used_by}\n"
            f"# rules:   {rules}\n"
            f"# agent:   {model_id} | unknown | {today} | unknown | initial CodeDNA annotation pass\n"
            f"#}}\n\n"
        )
        return header + source
