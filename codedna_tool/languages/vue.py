"""vue.py — CodeDNA v0.8 adapter for Vue SFC and Svelte components.

exports: class VueAdapter
         class SvelteAdapter
used_by: languages/__init__.py -> _REGISTRY
rules:   regex-based only — no Node.js required.
         Uses <!-- --> HTML comment syntax for the CodeDNA header.
         Vue SFC: detects defineProps, defineEmits, import statements.
         Svelte: detects export let, import statements.
         Header is placed BEFORE the first <template>/<script>/<style> tag.
agent:   claude-opus-4-6 | anthropic | 2026-04-01 | s_20260401_001 | initial Vue SFC and Svelte adapter
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import LanguageAdapter, LangFileInfo

# Vue 3 Composition API
_DEFINE_PROPS_RE = re.compile(r"defineProps\s*[<(]", re.MULTILINE)
_DEFINE_EMITS_RE = re.compile(r"defineEmits\s*[<(]\s*\[?\s*['\"](\w+)['\"]", re.MULTILINE)
_DEFINE_EXPOSE_RE = re.compile(r"defineExpose\s*\(\s*\{([^}]+)\}", re.MULTILINE)

# Vue 2 Options API
_PROPS_RE = re.compile(r"props\s*:\s*[\[{]", re.MULTILINE)

# Common: import ... from '...'
_IMPORT_RE = re.compile(r"""(?:import|from)\s+['"]([^'"]+)['"]""", re.MULTILINE)

# Component registration
_COMPONENTS_RE = re.compile(r"components\s*:\s*\{([^}]+)\}", re.MULTILINE)

# Svelte: export let foo
_SVELTE_EXPORT_RE = re.compile(r"export\s+let\s+(\w+)", re.MULTILINE)

# Svelte: <slot name="...">
_SVELTE_SLOT_RE = re.compile(r'<slot\s+name=[\'"](\w+)[\'"]', re.MULTILINE)


class VueAdapter(LanguageAdapter):
    """CodeDNA adapter for .vue Single File Components.

    Rules:   Header uses <!-- --> HTML comment, placed before <template>/<script>.
             defineProps/defineEmits/defineExpose are captured as exports.
             import statements within <script> are captured as deps.
             Never raises — return LangFileInfo(parseable=False) on OSError.
    """

    @property
    def comment_prefix(self) -> str:
        return "<!--"

    def has_codedna_header(self, source: str) -> bool:
        """Check for CodeDNA block in <!-- --> comment."""
        for line in source.splitlines()[:30]:
            stripped = line.strip()
            for prefix in ("<!--", "-->", "--"):
                if stripped.startswith(prefix):
                    stripped = stripped[len(prefix):].strip()
            if stripped.startswith("exports:") or stripped.startswith("used_by:"):
                return True
        return False

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a Vue SFC and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any OSError.
                 defineProps/defineEmits are captured as exports (component contract).
                 import paths from <script> blocks are captured as deps.
        """
        rel = str(path.relative_to(repo_root))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return LangFileInfo(path=path, rel=rel, parseable=False)

        list_str_exports: list[str] = []

        if _DEFINE_PROPS_RE.search(source):
            list_str_exports.append("defineProps")
        for m in _DEFINE_EMITS_RE.finditer(source):
            name = f"emit:{m.group(1)}"
            if name not in list_str_exports:
                list_str_exports.append(name)
        if _DEFINE_EXPOSE_RE.search(source):
            list_str_exports.append("defineExpose")
        if _PROPS_RE.search(source) and "defineProps" not in list_str_exports:
            list_str_exports.append("props")

        list_str_deps: list[str] = []
        for m in _IMPORT_RE.finditer(source):
            str_relpath_dep_from_import = m.group(1)
            if str_relpath_dep_from_import.startswith(".") and str_relpath_dep_from_import not in list_str_deps:
                list_str_deps.append(str_relpath_dep_from_import)

        return LangFileInfo(
            path=path,
            rel=rel,
            exports=list_str_exports,
            deps=list_str_deps,
            has_codedna=self.has_codedna_header(source),
        )

    def inject_header(self, source: str, rel: str, exports: str, used_by: str,
                      rules: str, model_id: str, today: str) -> str:
        """Prepend a CodeDNA <!-- --> comment block before the first tag.

        Rules:   Must be idempotent — return source unchanged if header already present.
                 Header goes before <template>, <script>, or <style> — whichever comes first.
        """
        if self.has_codedna_header(source):
            return source

        filename = Path(rel).name
        stem = Path(rel).stem
        header = (
            f"<!-- {filename} — {stem} component.\n"
            f"\n"
            f"  exports: {exports}\n"
            f"  used_by: {used_by}\n"
            f"  rules:   {rules}\n"
            f"  agent:   {model_id} | unknown | {today} | unknown | initial CodeDNA annotation pass\n"
            f"-->\n\n"
        )
        return header + source


class SvelteAdapter(LanguageAdapter):
    """CodeDNA adapter for .svelte files.

    Rules:   Header uses <!-- --> HTML comment, placed at the very top.
             export let declarations are captured as exports (component props).
             Named <slot> elements are captured as exports.
             import statements are captured as deps.
             Never raises — return LangFileInfo(parseable=False) on OSError.
    """

    @property
    def comment_prefix(self) -> str:
        return "<!--"

    def has_codedna_header(self, source: str) -> bool:
        """Check for CodeDNA block in <!-- --> comment."""
        for line in source.splitlines()[:30]:
            stripped = line.strip()
            for prefix in ("<!--", "-->", "--"):
                if stripped.startswith(prefix):
                    stripped = stripped[len(prefix):].strip()
            if stripped.startswith("exports:") or stripped.startswith("used_by:"):
                return True
        return False

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a Svelte component and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any OSError.
                 export let declarations are captured as exports (component props).
                 Named <slot> elements are captured as exports.
                 Relative import paths are captured as deps.
        """
        rel = str(path.relative_to(repo_root))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return LangFileInfo(path=path, rel=rel, parseable=False)

        list_str_exports: list[str] = []
        for m in _SVELTE_EXPORT_RE.finditer(source):
            name = f"prop:{m.group(1)}"
            if name not in list_str_exports:
                list_str_exports.append(name)
        for m in _SVELTE_SLOT_RE.finditer(source):
            name = f"slot:{m.group(1)}"
            if name not in list_str_exports:
                list_str_exports.append(name)

        list_str_deps: list[str] = []
        for m in _IMPORT_RE.finditer(source):
            str_relpath_dep_from_import = m.group(1)
            if str_relpath_dep_from_import.startswith(".") and str_relpath_dep_from_import not in list_str_deps:
                list_str_deps.append(str_relpath_dep_from_import)

        return LangFileInfo(
            path=path,
            rel=rel,
            exports=list_str_exports,
            deps=list_str_deps,
            has_codedna=self.has_codedna_header(source),
        )

    def inject_header(self, source: str, rel: str, exports: str, used_by: str,
                      rules: str, model_id: str, today: str) -> str:
        """Prepend a CodeDNA <!-- --> comment block.

        Rules:   Must be idempotent — return source unchanged if header already present.
        """
        if self.has_codedna_header(source):
            return source

        filename = Path(rel).name
        stem = Path(rel).stem
        header = (
            f"<!-- {filename} — {stem} component.\n"
            f"\n"
            f"  exports: {exports}\n"
            f"  used_by: {used_by}\n"
            f"  rules:   {rules}\n"
            f"  agent:   {model_id} | unknown | {today} | unknown | initial CodeDNA annotation pass\n"
            f"-->\n\n"
        )
        return header + source
