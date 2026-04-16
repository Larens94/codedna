"""rust.py — CodeDNA v0.8 adapter for Rust source files.

exports: _PUB_FN_RE | _PUB_STRUCT_RE | _PUB_ENUM_RE | _PUB_TRAIT_RE | _PUB_TYPE_RE | _PUB_CONST_RE | _MOD_RE | _USE_RE | class RustAdapter
used_by: codedna_tool/languages/__init__.py → RustAdapter
         codedna_tool/languages/_ts_rust.py → RustAdapter
rules:   regex-based only — no cargo/rustc dependency required.
Detects pub fn, pub struct, pub enum, pub trait, pub type, pub const/static.
impl blocks are not traversed — only top-level pub items are captured.
agent:   claude-sonnet-4-6 | anthropic | 2026-03-27 | s_20260327_003 | initial Rust adapter
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import LanguageAdapter, LangFileInfo

_PUB_FN_RE    = re.compile(r"^pub(?:\s+(?:async|unsafe|extern\s+\S+))?\s+fn\s+(\w+)", re.MULTILINE)
_PUB_STRUCT_RE = re.compile(r"^pub(?:\s+\w+)?\s+struct\s+(\w+)", re.MULTILINE)
_PUB_ENUM_RE   = re.compile(r"^pub(?:\s+\w+)?\s+enum\s+(\w+)", re.MULTILINE)
_PUB_TRAIT_RE  = re.compile(r"^pub(?:\s+\w+)?\s+trait\s+(\w+)", re.MULTILINE)
_PUB_TYPE_RE   = re.compile(r"^pub\s+type\s+(\w+)", re.MULTILINE)
_PUB_CONST_RE  = re.compile(r"^pub\s+(?:const|static)\s+(\w+)", re.MULTILINE)
_MOD_RE        = re.compile(r"^pub\s+mod\s+(\w+)", re.MULTILINE)

# use declarations (internal — path starting with crate:: or super::)
_USE_RE = re.compile(r"^use\s+(crate|super)(::[\w:{}*]+)+\s*;", re.MULTILINE)


class RustAdapter(LanguageAdapter):
    """CodeDNA adapter for .rs files.

    Rules:   Only top-level pub items are captured; items inside impl blocks are skipped.
             Attributes (#[...]) before items are not captured.
             Never raises — return LangFileInfo(parseable=False) on OSError.
    """

    @property
    def comment_prefix(self) -> str:
        return "//"

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a Rust source file and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any OSError.
                 Only pub-visibility items at file scope are captured as exports.
                 crate:: and super:: use paths are captured as internal deps (best-effort).
        """
        rel = str(path.relative_to(repo_root))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return LangFileInfo(path=path, rel=rel, parseable=False)

        list_str_exports: list[str] = []
        for pat in [_PUB_FN_RE, _PUB_STRUCT_RE, _PUB_ENUM_RE,
                    _PUB_TRAIT_RE, _PUB_TYPE_RE, _PUB_CONST_RE, _MOD_RE]:
            for m in pat.finditer(source):
                name = m.group(1)
                if name not in list_str_exports:
                    list_str_exports.append(name)

        list_str_deps: list[str] = [m.group(0).strip() for m in _USE_RE.finditer(source)]

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

        Rules:   Must be idempotent — if has_codedna_header() returns True, return unchanged.
                 #![...] inner attributes (crate-level) must stay as line 1 if present;
                 insert header after inner attributes.
        """
        if self.has_codedna_header(source):
            return source

        header_lines = self._build_header_lines(rel, exports, used_by, rules, model_id, today)
        header = "\n".join(header_lines) + "\n\n"

        lines = source.splitlines(keepends=True)
        insert_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#![") or not stripped:
                insert_idx = i + 1
            else:
                break

        before = "".join(lines[:insert_idx])
        after = "".join(lines[insert_idx:])
        return before + header + after
