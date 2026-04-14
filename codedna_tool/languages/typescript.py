"""typescript.py — CodeDNA v0.8 adapter for TypeScript and JavaScript files.

exports: class TypeScriptAdapter
used_by: languages/__init__.py -> _REGISTRY
rules:   regex-based only — never parse TS/JS AST (no Node.js dependency).
         Detects exports via 'export function', 'export class', 'export const', 'export default'.
         Import resolution is path-only (relative imports starting with '.' or './').
agent:   claude-haiku-4-5-20251001 | anthropic | 2026-03-27 | s_20260327_001 | initial TS/JS adapter with regex-based extraction
         claude-sonnet-4-6 | anthropic | 2026-03-27 | s_20260327_002 | CodeDNA v0.8 compliance pass: added session_id to agent: field, added Rules: docstrings to extract_info and inject_header
         claude-opus-4-6 | anthropic | 2026-04-14 | s_20260414_002 | fixed _resolve_import: check is_file() not exists() to avoid resolving directories as files
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import LanguageAdapter, LangFileInfo

# Patterns for exported symbols
_EXPORT_PATTERNS = [
    re.compile(r"^export\s+(?:async\s+)?function\s+(\w+)", re.MULTILINE),
    re.compile(r"^export\s+class\s+(\w+)", re.MULTILINE),
    re.compile(r"^export\s+(?:const|let|var)\s+(\w+)", re.MULTILINE),
    re.compile(r"^export\s+(?:type|interface)\s+(\w+)", re.MULTILINE),
    re.compile(r"^export\s+default\s+(?:function|class)\s+(\w+)", re.MULTILINE),
]

# Pattern for relative imports: import ... from './foo' or '../bar'
_IMPORT_RE = re.compile(r"""from\s+['"](\.[^'"]+)['"]""")


class TypeScriptAdapter(LanguageAdapter):
    """CodeDNA adapter for .ts, .tsx, .js, .jsx, .mjs files.

    Rules:   Uses regex only — no exec, no subprocess, no Node.js.
             export detection covers the most common patterns; exotic re-exports are skipped.
    """

    @property
    def comment_prefix(self) -> str:
        return "//"

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a TS/JS file and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any OSError.
                 Export detection is regex-only; barrel re-exports (export * from) are not captured.
                 Only relative imports (starting with '.') are resolved; bare specifiers are skipped.
        """
        rel = str(path.relative_to(repo_root))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return LangFileInfo(path=path, rel=rel, parseable=False)

        # Exports
        list_str_exports: list[str] = []
        for pat in _EXPORT_PATTERNS:
            for m in pat.finditer(source):
                name = m.group(1)
                if name not in list_str_exports:
                    list_str_exports.append(name)

        # Relative imports → attempt to resolve to repo-relative path
        list_str_deps: list[str] = []
        for m in _IMPORT_RE.finditer(source):
            import_path = m.group(1)
            resolved = self._resolve_import(path, import_path, repo_root)
            if resolved and resolved not in list_str_deps:
                list_str_deps.append(resolved)

        has_codedna = self.has_codedna_header(source)

        return LangFileInfo(
            path=path,
            rel=rel,
            exports=list_str_exports,
            deps=list_str_deps,
            has_codedna=has_codedna,
        )

    def inject_header(self, source: str, rel: str, exports: str, used_by: str,
                      rules: str, model_id: str, today: str) -> str:
        """Prepend a CodeDNA comment block. Returns source unchanged if header already present.

        Rules:   Must be idempotent — if has_codedna_header() returns True, return source unchanged.
                 Preserve shebang lines (#!) at position 0; insert header after shebang.
                 Do not strip trailing newlines from original source.
        """
        if self.has_codedna_header(source):
            return source

        header_lines = self._build_header_lines(rel, exports, used_by, rules, model_id, today)
        header = "\n".join(header_lines) + "\n\n"

        # Preserve shebang if present
        lines = source.splitlines(keepends=True)
        if lines and lines[0].startswith("#!"):
            return lines[0] + header + "".join(lines[1:])
        return header + source

    @staticmethod
    def _resolve_import(current_file: Path, import_path: str, repo_root: Path) -> str | None:
        """Resolve a relative TS/JS import to a repo-relative path."""
        base = current_file.parent / import_path
        # Try common extensions — file extensions first, then index files
        for suffix in [".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.js"]:
            candidate = Path(str(base) + suffix)
            if candidate.is_file():
                try:
                    return str(candidate.relative_to(repo_root))
                except ValueError:
                    return None
        # Exact match only if it's a file (not a directory)
        if base.is_file():
            try:
                return str(base.relative_to(repo_root))
            except ValueError:
                return None
        return None
