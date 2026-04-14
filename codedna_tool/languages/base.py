"""base.py — Abstract base class for CodeDNA v0.8 language adapters.

exports: class LanguageAdapter
used_by: languages/__init__.py → LanguageAdapter
         languages/typescript.py → TypeScriptAdapter [cascade]
         languages/go.py → GoAdapter [cascade]
rules:   All adapters must be stateless (no instance state).
         extract_info() must never raise — return empty defaults on failure.
         inject_header() must be idempotent: if header already present, return source unchanged.
         _build_header_lines() MUST emit agent: with 5 fields: model-id | provider | YYYY-MM-DD | session_id | narrative.
         Never change the field order in _build_header_lines() — downstream validators parse by position.
agent:   claude-haiku-4-5-20251001 | anthropic | 2026-03-27 | s_20260327_001 | initial base adapter for multi-language support
         claude-sonnet-4-6 | anthropic | 2026-03-27 | s_20260327_002 | v0.8 compliance: fixed used_by →, [cascade] tags, 5-field agent: line
         claude-opus-4-6 | anthropic | 2026-04-15 | s_20260415_001 | fixed has_codedna_header to detect headers in any comment format (// # * /** {{-- {# <%#), prevents duplicate headers on re-run
         message: "_build_header_lines currently hard-codes provider as unknown and session_id as unknown — callers should pass these explicitly; consider updating inject_header signature in a future pass"
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class LangFileInfo:
    """Extracted information from a non-Python source file."""
    path: Path
    rel: str
    exports: list[str] = field(default_factory=list)
    deps: list[str] = field(default_factory=list)        # imported module paths (best-effort)
    has_codedna: bool = False
    parseable: bool = True


class LanguageAdapter(ABC):
    """Base class for CodeDNA language adapters.

    Rules:   extract_info() is best-effort — partial results are acceptable.
             inject_header() must preserve the original file if it already has CodeDNA annotations.
    """

    @property
    @abstractmethod
    def comment_prefix(self) -> str:
        """Single-line comment prefix for this language (e.g. '//' or '#')."""

    @abstractmethod
    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a source file and return structural information."""

    @abstractmethod
    def inject_header(self, source: str, rel: str, exports: str, used_by: str,
                      rules: str, model_id: str, today: str) -> str:
        """Prepend (or replace) a CodeDNA comment block in source. Return new source."""

    def has_codedna_header(self, source: str) -> bool:
        """Quick check: does source already contain a CodeDNA block in any comment format?

        Rules:   Must detect headers in // comments, # comments, /** */ blocks,
                 and {# #} / {{-- --}} template blocks. Prevents duplicate headers
                 when re-running codedna init on already-annotated files.
        """
        for line in source.splitlines()[:30]:
            # Strip all common comment prefixes: //, #, *, {{--, {#, <%#, @*, <!--
            stripped = line.strip()
            for prefix in (self.comment_prefix, "//", "#", "*", "{{--", "{#", "<%#", "@*", "<!--"):
                if stripped.startswith(prefix):
                    stripped = stripped[len(prefix):].strip()
                    break
            if stripped.startswith("exports:") or stripped.startswith("used_by:"):
                return True
        return False

    def _build_header_lines(self, rel: str, exports: str, used_by: str,
                            rules: str, model_id: str, today: str,
                            provider: str = "unknown", session_id: str = "unknown") -> list[str]:
        """Build the standard CodeDNA v0.8 comment block lines.

        Rules:   agent: line MUST have exactly 5 pipe-separated fields:
                 model-id | provider | YYYY-MM-DD | session_id | narrative.
                 Do NOT collapse or reorder fields — downstream validators parse by position.
                 provider and session_id default to 'unknown' when callers omit them; callers
                 should pass real values whenever available.
        """
        p = self.comment_prefix
        filename = Path(rel).name
        stem = Path(rel).stem
        purpose = f"{stem} module"
        return [
            f"{p} {filename} — {purpose}.",
            f"{p}",
            f"{p} exports: {exports}",
            f"{p} used_by: {used_by}",
            f"{p} rules:   {rules}",
            f"{p} agent:   {model_id} | {provider} | {today} | {session_id} | initial CodeDNA annotation pass",
        ]
