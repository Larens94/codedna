"""base.py — Abstract base class for CodeDNA v0.8 language adapters.

exports: class LangFuncInfo | class LangFileInfo | class LanguageAdapter
used_by: codedna_tool/languages/__init__.py → LanguageAdapter
         codedna_tool/languages/_treesitter.py → LanguageAdapter
         codedna_tool/languages/_ts_csharp.py → LangFileInfo
         codedna_tool/languages/_ts_go.py → LangFileInfo
         codedna_tool/languages/_ts_java.py → LangFileInfo
         codedna_tool/languages/_ts_kotlin.py → LangFileInfo
         codedna_tool/languages/_ts_php.py → LangFileInfo
         codedna_tool/languages/_ts_ruby.py → LangFileInfo
         codedna_tool/languages/_ts_rust.py → LangFileInfo
         codedna_tool/languages/_ts_typescript.py → LangFileInfo
         codedna_tool/languages/blade.py → LangFileInfo, LanguageAdapter
         codedna_tool/languages/csharp.py → LangFileInfo, LanguageAdapter
         codedna_tool/languages/erb.py → LangFileInfo, LanguageAdapter
         codedna_tool/languages/go.py → LangFileInfo, LanguageAdapter
         codedna_tool/languages/handlebars.py → LangFileInfo, LanguageAdapter
         codedna_tool/languages/java.py → LangFileInfo, LanguageAdapter
         codedna_tool/languages/jinja.py → LangFileInfo, LanguageAdapter
         codedna_tool/languages/php.py → LangFileInfo, LanguageAdapter
         codedna_tool/languages/razor.py → LangFileInfo, LanguageAdapter
         codedna_tool/languages/ruby.py → LangFileInfo, LanguageAdapter
         codedna_tool/languages/rust.py → LangFileInfo, LanguageAdapter
         codedna_tool/languages/swift.py → LangFileInfo, LanguageAdapter
         codedna_tool/languages/typescript.py → LangFileInfo, LanguageAdapter
         codedna_tool/languages/vue.py → LangFileInfo, LanguageAdapter
rules:   All adapters must be stateless (no instance state).
extract_info() must never raise — return empty defaults on failure.
inject_header() must be idempotent: if header already present, return source unchanged.
_build_header_lines() MUST emit agent: with 5 fields: model-id | provider | YYYY-MM-DD | session_id | narrative.
Never change the field order in _build_header_lines() — downstream validators parse by position.
agent:   claude-sonnet-4-6 | anthropic | 2026-04-15 | s_20260415_002 | emit full 4-field header (exports/used_by/rules/agent) for all non-Python languages — adapters already extract them, _build_header_lines was discarding them
claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_004 | fix provider/session_id always "unknown" — added _detect_provider() in base, derives from model_id; removed caller-supplied provider param
claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_005 | fix multi-line rules normalization; ruff cleanup: ambiguous var l→line, removed unused Optional import
claude-sonnet-4-6 | anthropic | 2026-04-18 | s_20260418_php2 | GATE 3: add LangFuncInfo dataclass + funcs field to LangFileInfo — enables L2 function Rules: for non-Python adapters (PHP first)
claude-sonnet-4-6 | anthropic | 2026-04-18 | s_20260418_msg | add message: empty field to _build_header_lines() — visible to next agent even when empty
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class LangFuncInfo:
    """Info about a public function/method in a non-Python source file (for L2 Rules:)."""
    name: str
    start_line: int        # 1-based line of the function/method keyword
    has_doc: bool          # True if a doc block (PHPDoc, JSDoc, etc.) already exists above
    has_rules: bool        # True if a Rules: annotation already exists
    source_snippet: str    # ≤20 lines of method body for LLM context
    language: str          # e.g. "php", "typescript", "go"


@dataclass
class LangFileInfo:
    """Extracted information from a non-Python source file."""
    path: Path
    rel: str
    exports: list[str] = field(default_factory=list)
    deps: list[str] = field(default_factory=list)        # imported module paths (best-effort)
    funcs: list["LangFuncInfo"] = field(default_factory=list)  # public funcs for L2 (GATE 3)
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

    def inject_function_rules(self, source: str, func: "LangFuncInfo", rules_text: str) -> str:
        """Inject a Rules: annotation above a public function/method.

        Rules:   Default implementation returns source unchanged — only adapters
                 that support L2 (e.g. PHP via PHPDoc) override this method.
                 Must be idempotent: if func.has_rules is True, return source unchanged.
        """
        return source

    def has_codedna_header(self, source: str) -> bool:
        """Quick check: does source already contain a CodeDNA block in any comment format?

        Rules:   Must detect headers in // comments, # comments, /** */ blocks,
                 and {# #} / {{-- --}} template blocks. Prevents duplicate headers
                 when re-running codedna init on already-annotated files.
                 Detects both full headers (exports:/used_by:) and reduced headers (rules:/agent:).
        """
        for line in source.splitlines()[:30]:
            # Strip all common comment prefixes: //, #, *, {{--, {#, <%#, @*, <!--
            stripped = line.strip()
            for prefix in (self.comment_prefix, "//", "#", "*", "{{--", "{#", "<%#", "@*", "<!--"):
                if stripped.startswith(prefix):
                    stripped = stripped[len(prefix):].strip()
                    break
            if stripped.startswith(("exports:", "used_by:", "rules:", "agent:", "message:")):
                return True
        return False

    @staticmethod
    def _detect_provider(model_id: str) -> str:
        """Derive provider string from model_id without importing cli.py (avoids circular import)."""
        m = model_id.lower()
        if m == "codedna-cli (no-llm)":
            return "codedna-cli"
        if m.startswith("deepseek/") or m.startswith("deepseek-"):
            return "deepseek"
        if m.startswith("ollama/") or m.startswith("ollama_chat/"):
            return "ollama"
        if m.startswith("openai/") or m.startswith("gpt"):
            return "openai"
        if m.startswith("gemini/") or m.startswith("google/"):
            return "gemini"
        if m.startswith("anthropic/") or "claude" in m:
            return "anthropic"
        return "unknown"

    def _build_header_lines(self, rel: str, exports: str, used_by: str,
                            rules: str, model_id: str, today: str) -> list[str]:
        """Build a full CodeDNA v0.8 comment block for non-Python languages.

        Rules:   All languages emit the full 4-field header: exports, used_by, rules, agent.
                 exports: and used_by: are written as 'none' when not available — explicit
                 'none' lets the next agent verify the value rather than assume the field is missing.
                 agent: line MUST have exactly 5 pipe-separated fields.
                 provider is derived from model_id — callers must NOT pass it separately.
        """
        p = self.comment_prefix
        filename = Path(rel).name
        stem = Path(rel).stem
        purpose = f"{stem} module"
        provider = self._detect_provider(model_id)

        # Normalize multi-line rules: each continuation line must carry the comment prefix.
        # LLMs sometimes return numbered lists with embedded newlines — join them with a separator.
        rules_lines = [line.strip() for line in rules.splitlines() if line.strip()]
        if len(rules_lines) > 1:
            rules_normalized = f"\n{p}          ".join(rules_lines)
        else:
            rules_normalized = rules_lines[0] if rules_lines else "none"

        return [
            f"{p} {filename} — {purpose}.",
            f"{p}",
            f"{p} exports: {exports}",
            f"{p} used_by: {used_by}",
            f"{p} rules:   {rules_normalized}",
            f"{p} agent:   {model_id} | {provider} | {today} | codedna-cli | initial CodeDNA annotation pass",
            f"{p} message: ",
        ]
