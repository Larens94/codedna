"""swift.py — CodeDNA v0.8 adapter for Swift source files.

exports: class SwiftAdapter
used_by: languages/__init__.py -> _REGISTRY
rules:   regex-based only — no Swift compiler dependency required.
         Detects public/open func, class, struct, enum, protocol, typealias.
         Internal (no modifier) and private/fileprivate symbols are excluded.
agent:   claude-sonnet-4-6 | anthropic | 2026-03-27 | s_20260327_003 | initial Swift adapter
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import LanguageAdapter, LangFileInfo

# public or open visibility
_PUB = r"(?:public|open)\s+"

_FUNC_RE     = re.compile(rf"^{_PUB}(?:static\s+|class\s+|mutating\s+)?func\s+(\w+)", re.MULTILINE)
_CLASS_RE    = re.compile(rf"^{_PUB}(?:final\s+)?class\s+(\w+)", re.MULTILINE)
_STRUCT_RE   = re.compile(rf"^{_PUB}struct\s+(\w+)", re.MULTILINE)
_ENUM_RE     = re.compile(rf"^{_PUB}enum\s+(\w+)", re.MULTILINE)
_PROTOCOL_RE = re.compile(rf"^{_PUB}protocol\s+(\w+)", re.MULTILINE)
_TYPEALIAS_RE= re.compile(rf"^{_PUB}typealias\s+(\w+)", re.MULTILINE)
_VAR_RE      = re.compile(rf"^{_PUB}(?:static\s+)?(?:var|let)\s+(\w+)", re.MULTILINE)

_IMPORT_RE   = re.compile(r"^import\s+(\w+)", re.MULTILINE)


class SwiftAdapter(LanguageAdapter):
    """CodeDNA adapter for .swift files.

    Rules:   Only public/open symbols are captured as exports.
             internal (default), private, and fileprivate symbols are excluded.
             Never raises — return LangFileInfo(parseable=False) on OSError.
    """

    @property
    def comment_prefix(self) -> str:
        return "//"

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a Swift source file and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any OSError.
                 Only public/open top-level declarations are captured.
                 import statements are captured as deps (module names, not file paths).
        """
        rel = str(path.relative_to(repo_root))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return LangFileInfo(path=path, rel=rel, parseable=False)

        list_str_exports: list[str] = []
        for pat in [_CLASS_RE, _STRUCT_RE, _ENUM_RE, _PROTOCOL_RE,
                    _TYPEALIAS_RE, _FUNC_RE, _VAR_RE]:
            for m in pat.finditer(source):
                name = m.group(1)
                if name not in list_str_exports:
                    list_str_exports.append(name)

        list_str_deps = [m.group(1) for m in _IMPORT_RE.finditer(source)]

        return LangFileInfo(
            path=path,
            rel=rel,
            exports=list_str_exports,
            deps=list_str_deps,
            has_codedna=self.has_codedna_header(source),
        )

    def inject_header(self, source: str, rel: str, exports: str, used_by: str,
                      rules: str, model_id: str, today: str) -> str:
        """Prepend a CodeDNA // comment block.

        Rules:   Must be idempotent.
                 import statements preserved before CodeDNA block.
                 No special file-structural constraints in Swift (no package declaration).
        """
        if self.has_codedna_header(source):
            return source

        header_lines = self._build_header_lines(rel, exports, used_by, rules, model_id, today)
        header = "\n".join(header_lines) + "\n\n"

        lines = source.splitlines(keepends=True)
        insert_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("@") or not stripped:
                insert_idx = i + 1
            else:
                break

        before = "".join(lines[:insert_idx])
        after = "".join(lines[insert_idx:])
        return before + header + after
