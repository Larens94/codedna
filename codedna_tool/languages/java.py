"""java.py — CodeDNA v0.8 adapter for Java and Kotlin source files.

exports: _JAVA_CLASS_RE | _JAVA_METHOD_RE | _JAVA_IMPORT_RE | _KT_CLASS_RE | _KT_FUN_RE | _KT_CONST_RE | _KT_IMPORT_RE | class JavaAdapter | class KotlinAdapter
used_by: codedna_tool/languages/__init__.py → JavaAdapter, KotlinAdapter
         codedna_tool/languages/_ts_java.py → JavaAdapter
         codedna_tool/languages/_ts_kotlin.py → KotlinAdapter
rules:   regex-based only — no JVM dependency required.
Java: detects public class/interface/enum/record and public methods.
Kotlin: detects class/object/fun/val/const at top level and public members.
Annotations (@Override, @SpringBootApplication etc.) are not captured as exports.
agent:   claude-sonnet-4-6 | anthropic | 2026-03-27 | s_20260327_003 | initial Java + Kotlin adapters
claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_001 | fixed double blank line: strip leading newlines from after before reassembling, both JavaAdapter and KotlinAdapter
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import LanguageAdapter, LangFileInfo

# ── Java ──────────────────────────────────────────────────────────────────────

_JAVA_CLASS_RE  = re.compile(
    r"^public\s+(?:abstract\s+|final\s+|sealed\s+)?(?:class|interface|enum|record)\s+(\w+)",
    re.MULTILINE,
)
_JAVA_METHOD_RE = re.compile(
    r"^\s+public\s+(?:static\s+|final\s+|abstract\s+|synchronized\s+)*"
    r"(?:[\w<>\[\]]+\s+)+(\w+)\s*\(",
    re.MULTILINE,
)
_JAVA_IMPORT_RE = re.compile(r"^import\s+([\w.]+)\s*;", re.MULTILINE)

# ── Kotlin ────────────────────────────────────────────────────────────────────

_KT_CLASS_RE  = re.compile(
    r"^(?:public\s+)?(?:data\s+|sealed\s+|abstract\s+|open\s+)?(?:class|interface|object)\s+(\w+)",
    re.MULTILINE,
)
_KT_FUN_RE    = re.compile(r"^(?:public\s+)?fun\s+(\w+)\s*[(<]", re.MULTILINE)
_KT_CONST_RE  = re.compile(r"^(?:const\s+val|val|var)\s+(\w+)\s*[=:]", re.MULTILINE)
_KT_IMPORT_RE = re.compile(r"^import\s+([\w.]+)", re.MULTILINE)


class JavaAdapter(LanguageAdapter):
    """CodeDNA adapter for .java files.

    Rules:   Only public top-level types and public methods captured.
             Inner classes and private/protected members are excluded.
             Never raises — return LangFileInfo(parseable=False) on OSError.
    """

    @property
    def comment_prefix(self) -> str:
        return "//"

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a Java file and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any OSError.
                 Public methods are listed as ClassName::method when a class is detected.
                 Import paths are captured but not resolved to file paths (package → dir mapping
                 requires project structure knowledge not available here).
        """
        rel = str(path.relative_to(repo_root))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return LangFileInfo(path=path, rel=rel, parseable=False)

        list_str_exports: list[str] = []
        cls_names: list[str] = []

        for m in _JAVA_CLASS_RE.finditer(source):
            name = m.group(1)
            if name not in cls_names:
                cls_names.append(name)
                list_str_exports.append(name)

        cls_prefix = cls_names[0] + "::" if cls_names else ""
        for m in _JAVA_METHOD_RE.finditer(source):
            name = m.group(1)
            if name in ("class", "interface", "enum", "record", "void", "static"):
                continue
            entry = f"{cls_prefix}{name}"
            if entry not in list_str_exports:
                list_str_exports.append(entry)

        list_str_deps = [m.group(1) for m in _JAVA_IMPORT_RE.finditer(source)]

        return LangFileInfo(
            path=path,
            rel=rel,
            exports=list_str_exports,
            deps=list_str_deps,
            has_codedna=self.has_codedna_header(source),
        )

    def inject_header(self, source: str, rel: str, exports: str, used_by: str,
                      rules: str, model_id: str, today: str) -> str:
        """Prepend a CodeDNA // comment block after the package declaration.

        Rules:   Must be idempotent.
                 package declaration must remain the first non-comment statement.
                 CodeDNA block is inserted between package line and import block.
        """
        if self.has_codedna_header(source):
            return source

        header_lines = self._build_header_lines(rel, exports, used_by, rules, model_id, today)
        header = "\n".join(header_lines) + "\n"

        lines = source.splitlines(keepends=True)
        insert_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("package "):
                insert_idx = i + 1
                break

        before = "".join(lines[:insert_idx])
        after = "".join(lines[insert_idx:]).lstrip("\n")
        return before + "\n" + header + "\n" + after


class KotlinAdapter(LanguageAdapter):
    """CodeDNA adapter for .kt files.

    Rules:   Captures top-level fun, class, object, const val.
             Member functions inside classes are not captured (no deep parsing).
             Never raises — return LangFileInfo(parseable=False) on OSError.
    """

    @property
    def comment_prefix(self) -> str:
        return "//"

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        rel = str(path.relative_to(repo_root))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return LangFileInfo(path=path, rel=rel, parseable=False)

        list_str_exports: list[str] = []
        for pat in [_KT_CLASS_RE, _KT_FUN_RE, _KT_CONST_RE]:
            for m in pat.finditer(source):
                name = m.group(1)
                if name not in list_str_exports:
                    list_str_exports.append(name)

        list_str_deps = [m.group(1) for m in _KT_IMPORT_RE.finditer(source)]

        return LangFileInfo(
            path=path,
            rel=rel,
            exports=list_str_exports,
            deps=list_str_deps,
            has_codedna=self.has_codedna_header(source),
        )

    def inject_header(self, source: str, rel: str, exports: str, used_by: str,
                      rules: str, model_id: str, today: str) -> str:
        """Prepend a CodeDNA // comment block after the package declaration.

        Rules:   Must be idempotent.
                 package declaration preserved as first line.
        """
        if self.has_codedna_header(source):
            return source

        header_lines = self._build_header_lines(rel, exports, used_by, rules, model_id, today)
        header = "\n".join(header_lines) + "\n"

        lines = source.splitlines(keepends=True)
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("package "):
                insert_idx = i + 1
                break

        before = "".join(lines[:insert_idx])
        after = "".join(lines[insert_idx:]).lstrip("\n")
        return before + "\n" + header + "\n" + after
