"""ruby.py — CodeDNA v0.8 adapter for Ruby source files.

exports: _MODULE_RE | _CLASS_RE | _DEF_RE | _ATTR_RE | _REQUIRE_RE | _PRIVATE_RE | class RubyAdapter
used_by: codedna_tool/languages/__init__.py → RubyAdapter
         codedna_tool/languages/_ts_ruby.py → RubyAdapter
rules:   regex-based only — no Ruby interpreter dependency required.
Detects module/class definitions and public def methods.
attr_accessor/attr_reader/attr_writer are captured as exports.
Rails-aware: before_action, scope, has_many captured as metadata (not exports).
agent:   claude-opus-4-6 | anthropic | 2026-04-14 | s_20260414_002 | fixed nested class/module detection: allow indented class/module, method prefix uses innermost class not first module
claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_001 | fixed inject_header: no leading blank line when file has no shebang/frozen_string_literal (prefix only added when before is non-empty)
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import LanguageAdapter, LangFileInfo

_MODULE_RE   = re.compile(r"^\s*module\s+(\w+)", re.MULTILINE)
_CLASS_RE    = re.compile(r"^\s*class\s+(\w+)", re.MULTILINE)
_DEF_RE      = re.compile(r"^\s+def\s+(self\.)?(\w+)", re.MULTILINE)
_ATTR_RE     = re.compile(r"^\s+attr_(?:accessor|reader|writer)\s+:(\w+)", re.MULTILINE)
_REQUIRE_RE  = re.compile(r"^require(?:_relative)?\s+['\"]([^'\"]+)['\"]", re.MULTILINE)

# Private marker — everything after "private" keyword is private
_PRIVATE_RE  = re.compile(r"^\s*private\s*$", re.MULTILINE)


class RubyAdapter(LanguageAdapter):
    """CodeDNA adapter for .rb files.

    Rules:   Public methods are those defined before the first bare 'private' keyword.
             Class methods (def self.foo) are always considered public exports.
             Never raises — return LangFileInfo(parseable=False) on OSError.
    """

    @property
    def comment_prefix(self) -> str:
        return "#"

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a Ruby file and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any OSError.
                 Methods after the first bare 'private' line are excluded from exports.
                 attr_accessor/reader/writer attributes are included as exports.
                 require/require_relative paths are captured as deps (best-effort).
        """
        rel = str(path.relative_to(repo_root))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return LangFileInfo(path=path, rel=rel, parseable=False)

        list_str_exports: list[str] = []

        # Modules and classes
        cls_names: list[str] = []
        for m in _MODULE_RE.finditer(source):
            name = m.group(1)
            if name not in cls_names:
                cls_names.append(name)
                list_str_exports.append(name)
        for m in _CLASS_RE.finditer(source):
            name = m.group(1)
            if name not in cls_names:
                cls_names.append(name)
                list_str_exports.append(name)

        # Find private boundary (offset in source)
        private_match = _PRIVATE_RE.search(source)
        private_offset = private_match.start() if private_match else len(source)

        # Public methods (before private boundary)
        # Use the last class name as prefix (innermost class for nested definitions)
        class_only = [n for n in cls_names if n not in [m.group(1) for m in _MODULE_RE.finditer(source)]]
        method_owner = class_only[-1] if class_only else (cls_names[-1] if cls_names else "")
        cls_prefix = method_owner + "#" if method_owner else ""
        for m in _DEF_RE.finditer(source):
            if m.start() >= private_offset:
                break
            is_class_method = bool(m.group(1))  # def self.foo
            name = m.group(2)
            if name in ("initialize",):
                continue
            prefix = (method_owner + "." if method_owner else "") if is_class_method else cls_prefix
            entry = f"{prefix}{name}"
            if entry not in list_str_exports:
                list_str_exports.append(entry)

        # attr_accessor/reader/writer
        for m in _ATTR_RE.finditer(source):
            name = m.group(1)
            if name not in list_str_exports:
                list_str_exports.append(name)

        # Deps: require / require_relative
        list_str_deps: list[str] = []
        for m in _REQUIRE_RE.finditer(source):
            dep = m.group(1)
            # Try to resolve require_relative to a real path
            if "require_relative" in source[max(0, m.start()-20):m.start()]:
                candidate = path.parent / f"{dep}.rb"
                if candidate.exists():
                    try:
                        dep = str(candidate.relative_to(repo_root))
                    except ValueError:
                        pass
            if dep not in list_str_deps:
                list_str_deps.append(dep)

        return LangFileInfo(
            path=path,
            rel=rel,
            exports=list_str_exports,
            deps=list_str_deps,
            has_codedna=self.has_codedna_header(source),
        )

    def inject_header(self, source: str, rel: str, exports: str, used_by: str,
                      rules: str, model_id: str, today: str) -> str:
        """Prepend a CodeDNA # comment block.

        Rules:   Must be idempotent.
                 frozen_string_literal magic comment must remain as line 1 if present;
                 insert CodeDNA block immediately after it.
                 Shebang (#!) also preserved as line 1.
        """
        if self.has_codedna_header(source):
            return source

        header_lines = self._build_header_lines(rel, exports, used_by, rules, model_id, today)
        header = "\n".join(header_lines) + "\n"

        lines = source.splitlines(keepends=True)
        insert_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if (stripped.startswith("#!")
                    or "frozen_string_literal" in stripped
                    or "encoding:" in stripped):
                insert_idx = i + 1
            else:
                break

        before = "".join(lines[:insert_idx])
        after = "".join(lines[insert_idx:])
        prefix = "\n" if before else ""
        return before + prefix + header + "\n" + after
