"""base.py — Abstract base class for CodeDNA v0.9 language adapters.

exports: parse_codedna_comment_header(source, comment_prefix) | class LangFuncInfo | class LangFileInfo | class LanguageAdapter
used_by: codedna_tool/cli.py → parse_codedna_comment_header
         codedna_tool/languages/__init__.py → LanguageAdapter
         codedna_tool/languages/_treesitter.py → LanguageAdapter
         codedna_tool/languages/_ts_csharp.py → LangFileInfo, LangFuncInfo
         codedna_tool/languages/_ts_go.py → LangFileInfo, LangFuncInfo
         codedna_tool/languages/_ts_java.py → LangFileInfo, LangFuncInfo
         codedna_tool/languages/_ts_kotlin.py → LangFileInfo, LangFuncInfo
         codedna_tool/languages/_ts_php.py → LangFileInfo, LangFuncInfo
         codedna_tool/languages/_ts_ruby.py → LangFileInfo, LangFuncInfo
         codedna_tool/languages/_ts_rust.py → LangFileInfo, LangFuncInfo
         codedna_tool/languages/_ts_typescript.py → LangFileInfo, LangFuncInfo
         codedna_tool/languages/axl.py → LangFileInfo, LanguageAdapter
         codedna_tool/languages/blade.py → LangFileInfo, LanguageAdapter
         codedna_tool/languages/csharp.py → LangFileInfo, LangFuncInfo, LanguageAdapter
         codedna_tool/languages/erb.py → LangFileInfo, LanguageAdapter
         codedna_tool/languages/go.py → LangFileInfo, LanguageAdapter
         codedna_tool/languages/handlebars.py → LangFileInfo, LanguageAdapter
         codedna_tool/languages/java.py → LangFileInfo, LangFuncInfo, LanguageAdapter
         codedna_tool/languages/jinja.py → LangFileInfo, LanguageAdapter
         codedna_tool/languages/php.py → LangFileInfo, LangFuncInfo, LanguageAdapter
         codedna_tool/languages/razor.py → LangFileInfo, LanguageAdapter
         codedna_tool/languages/ruby.py → LangFileInfo, LangFuncInfo, LanguageAdapter
         codedna_tool/languages/rust.py → LangFileInfo, LanguageAdapter
         codedna_tool/languages/swift.py → LangFileInfo, LanguageAdapter
         codedna_tool/languages/typescript.py → LangFileInfo, LangFuncInfo, LanguageAdapter
         codedna_tool/languages/vue.py → LangFileInfo, LanguageAdapter
         tests/test_language_adapters.py → LangFuncInfo
rules:   All adapters must be stateless (no instance state).
extract_info() must never raise — return empty defaults on failure.
inject_header() must be idempotent: if header already present, return source unchanged.
parse_codedna_comment_header() is the single parser for check, verify, refresh, and wiki.
_build_header_lines() MUST emit agent: with 5 fields: model-id | provider | YYYY-MM-DD | session_id | narrative.
Never change the field order in _build_header_lines() — downstream validators parse by position.
agent:   claude-sonnet-4-6 | anthropic | 2026-04-18 | s_20260418_msg | add message: empty field to _build_header_lines() — visible to next agent even when empty
claude-opus-4-6 | anthropic | 2026-04-18 | s_20260418_gate2 | fix multi-line used_by missing comment prefix — _build_header_lines now normalizes used_by like rules
gpt-5 | openai | 2026-08-20 | s_20260820_hardening | document Rules contracts on every abstract public adapter method
gpt-5 | openai | 2026-08-21 | s_20260821_axl | add native structured-annotation extension points for AXL
gpt-5 | openai | 2026-08-27 | s_20260827_header_parser | centralize comment-header parsing and accept compact PHPDoc/JSDoc blocks without leading stars
claude-opus | anthropic | 2026-09-03 | s_20260903_singleline_block | single-line /** */ no longer leaves parse_codedna_comment_header in block mode (refresh deleted code)
message:
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


def parse_codedna_comment_header(source: str, comment_prefix: str) -> dict[str, str] | None:
    """Parse a comment-carried CodeDNA L1 header and its source range.

    Rules:   This is the canonical parser used by coverage, verify, refresh, and wiki.
             Accept //, #, /*, /**, optional leading *, and unprefixed lines inside
             a block comment; never treat unprefixed source outside a block as fields.
    """
    fields: dict[str, str] = {}
    current_field: str | None = None
    current_lines: list[str] = []
    header_started = False
    in_block = False
    header_line_indices: list[int] = []
    pending_open_idx: int | None = None
    field_names = ("exports:", "used_by:", "related:", "wiki:",
                   "rules:", "agent:", "message:")

    for int_line_index, str_line_raw in enumerate(source.splitlines()):
        str_line_stripped = str_line_raw.strip()
        bool_block_opener = str_line_stripped.startswith(("/**", "/*"))
        if bool_block_opener:
            str_content = str_line_stripped[3 if str_line_stripped.startswith("/**") else 2:].strip()
            # Single-line block comment (`/** foo */`): never enter in_block,
            # otherwise every later code line is read as comment content and a
            # stray " — " or `agent:` in source becomes a phantom header that
            # refresh then overwrites — deleting real code.
            if len(str_line_stripped) > 2 and str_content.endswith("*/"):
                str_content = str_content[:-2].strip()
                in_block = False
            else:
                in_block = True
            if not header_started:
                pending_open_idx = int_line_index
        elif in_block and str_line_stripped.endswith("*/"):
            str_content = str_line_stripped[:-2].strip()
            if str_content.startswith("*"):
                str_content = str_content[1:].strip()
            if header_started:
                header_line_indices.append(int_line_index)
            in_block = False
            if not str_content:
                break
        elif in_block:
            str_content = str_line_stripped[1:].strip() if str_line_stripped.startswith("*") else str_line_stripped
        elif comment_prefix and str_line_stripped.startswith(comment_prefix):
            str_content = str_line_stripped[len(comment_prefix):].strip()
        elif str_line_stripped.startswith("//"):
            str_content = str_line_stripped[2:].strip()
        elif str_line_stripped.startswith("#"):
            str_content = str_line_stripped[1:].strip()
        else:
            if header_started:
                break
            continue

        if not header_started:
            if any(str_content.startswith(str_field) for str_field in field_names):
                header_started = True
                fields["first_line"] = ""
            elif " — " in str_content:
                header_started = True
                fields["first_line"] = str_content
                if pending_open_idx is not None:
                    header_line_indices.append(pending_open_idx)
                header_line_indices.append(int_line_index)
                continue
            else:
                continue
            if pending_open_idx is not None:
                header_line_indices.append(pending_open_idx)

        header_line_indices.append(int_line_index)
        for str_field_name in field_names:
            if str_content.startswith(str_field_name):
                if current_field:
                    fields[current_field] = "\n".join(current_lines)
                current_field = str_field_name.rstrip(":")
                current_lines = [str_content]
                break
        else:
            if current_field and str_content:
                current_lines.append(str_content)

    if current_field:
        fields[current_field] = "\n".join(current_lines)
    if not any(str_field in fields for str_field in
               ("exports", "used_by", "related", "wiki", "rules", "agent", "message")):
        return None
    fields["_header_start"] = str(min(header_line_indices)) if header_line_indices else "0"
    fields["_header_end"] = str(max(header_line_indices)) if header_line_indices else "0"
    return fields


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
        """Single-line comment prefix for this language (e.g. '//' or '#').

        Rules:   Concrete adapters must return syntax valid for their language.
        """

    @abstractmethod
    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a source file and return structural information.

        Rules:   Implementations never raise; failures return parseable=False.
        """

    @abstractmethod
    def inject_header(self, source: str, rel: str, exports: str, used_by: str,
                      rules: str, model_id: str, today: str) -> str:
        """Prepend or replace a CodeDNA comment block.

        Rules:   Implementations must preserve valid syntax and be idempotent.
        """

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
        return parse_codedna_comment_header(source[:16 * 1024], self.comment_prefix) is not None

    def parse_codedna_fields(self, source: str) -> dict[str, str] | None:
        """Parse native structured CodeDNA fields when comments are not the carrier.

        Rules:   Return None for ordinary comment-based languages so callers use the
                 canonical comment parser. Native-frame adapters must return raw field
                 values keyed by exports, used_by, related, rules, agent, and message.
        """
        return None

    def refresh_header(self, source: str, exports: str, used_by: str) -> str | None:
        """Refresh native structured exports and used_by fields.

        Rules:   Return None for comment-based languages. Native implementations must
                 preserve semantic and symbol-level annotations byte-for-byte.
        """
        return None

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
        """Build a full CodeDNA v0.9 comment block for non-Python languages.

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

        # Normalize multi-line fields: each continuation line must carry the comment prefix.
        def _normalize_field(value: str, indent: str = "         ") -> str:
            lines = [line.strip() for line in value.splitlines() if line.strip()]
            if len(lines) > 1:
                return f"\n{p}{indent}".join(lines)
            return lines[0] if lines else "none"

        used_by_normalized = _normalize_field(used_by, " " * 9)
        rules_normalized = _normalize_field(rules, " " * 10)

        return [
            f"{p} {filename} — {purpose}.",
            f"{p}",
            f"{p} exports: {exports}",
            f"{p} used_by: {used_by_normalized}",
            f"{p} rules:   {rules_normalized}",
            f"{p} agent:   {model_id} | {provider} | {today} | codedna-cli | initial CodeDNA annotation pass",
            f"{p} message: ",
        ]
