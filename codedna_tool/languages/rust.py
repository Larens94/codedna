"""rust.py — CodeDNA v0.8 adapter for Rust source files.

exports: _PUB_FN_RE | _PUB_STRUCT_RE | _PUB_ENUM_RE | _PUB_TRAIT_RE | _PUB_TYPE_RE | _PUB_CONST_RE | _MOD_RE | _USE_RE | class RustAdapter
used_by: codedna_tool/languages/__init__.py → RustAdapter
         codedna_tool/languages/_ts_rust.py → RustAdapter
rules:   regex-based only — no cargo/rustc dependency required.
Detects pub fn, pub struct, pub enum, pub trait, pub type, pub const/static.
impl blocks are not traversed — only top-level pub items are captured.
inject_function_rules() uses /// line comments (Rust doc convention, NOT /** */).
agent:   claude-sonnet-4-6 | anthropic | 2026-03-27 | s_20260327_003 | initial Rust adapter
claude-sonnet-4-6 | anthropic | 2026-04-18 | s_20260418_ts | add inject_function_rules() — injects /// Rules: above pub fn; handles existing /// doc block and no-doc cases
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

    def inject_function_rules(self, source: str, func, rules_text: str) -> str:
        """Inject a /// Rules: line above a pub Rust function or method.

        Rules:   Must be idempotent — if func.has_rules is True, return source unchanged.
                 Rust uses /// line comments for doc comments (NOT /** */ blocks).
                 If func.has_doc=True: insert /// Rules: just above func.start_line
                 (at the end of the existing /// block immediately preceding the fn).
                 If func.has_doc=False: insert /// Rules: as a single line above func.start_line.
                 Detect indentation from the function line.
                 Caller MUST apply bottom-to-top when injecting multiple funcs to preserve line numbers.
        """
        if func.has_rules:
            return source

        lines = source.splitlines(keepends=True)
        method_idx = func.start_line - 1  # 0-based index of function's first line

        # Detect indentation from the function line
        method_line = lines[method_idx] if method_idx < len(lines) else ""
        indent = len(method_line) - len(method_line.lstrip())
        pad = " " * indent

        rules_line = f"{pad}/// Rules:   {rules_text}\n"

        # Insert just above func.start_line regardless of has_doc —
        # for has_doc=True this places Rules: as the last line of the existing /// block;
        # for has_doc=False this inserts a standalone /// Rules: line.
        lines = lines[:method_idx] + [rules_line] + lines[method_idx:]
        return "".join(lines)
