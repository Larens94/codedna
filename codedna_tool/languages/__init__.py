"""languages/__init__.py — Language adapter registry for CodeDNA v0.8.

exports: SUPPORTED_EXTENSIONS | get_adapter(extension)
used_by: codedna_tool/cli.py → SUPPORTED_EXTENSIONS, get_adapter
         tests/test_integration_langs.py → get_adapter
         tests/test_language_adapters.py → get_adapter
         tests/test_refresh.py → get_adapter
rules:   adapters are stateless; get_adapter returns None for unsupported extensions.
Never import language-specific deps here — keep this registry lightweight.
Tree-sitter is REQUIRED for source languages — no regex fallback.
Regex adapters (php.py, go.py, etc.) still exist as utility classes for inject_header/resolve.
agent:   claude-opus-4-6 | anthropic | 2026-04-01 | s_20260401_001 | added template engine adapters: Blade, Jinja2/Twig, ERB/EJS, Handlebars, Razor, Vue SFC, Svelte — 17 total extensions
claude-sonnet-4-6 | anthropic | 2026-04-02 | s_20260402_001 | added .volt (Phalcon Volt engine) via JinjaAdapter — same {# #} comment syntax
claude-opus-4-6 | anthropic | 2026-04-14 | s_20260414_001 | added tree-sitter adapters for TS/JS and Go with regex fallback
claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_001 | added tree-sitter adapters for PHP, Java, Rust, C#, Ruby, Kotlin — all 9 source languages now AST-powered with regex fallback
claude-opus-4-6 | anthropic | 2026-04-18 | s_20260418_gate6 | GATE 6: removed regex fallback — tree-sitter is now required for all source languages; regex adapters kept only as utility classes
"""

from typing import Optional

from .base import LanguageAdapter
from .blade import BladeAdapter
from .erb import ErbAdapter
from .handlebars import HandlebarsAdapter
from .jinja import JinjaAdapter
from .razor import RazorAdapter
from .vue import VueAdapter, SvelteAdapter

# ── Tree-sitter adapters (required) ──────────────────────────────────────────
from ._ts_typescript import TreeSitterTypeScriptAdapter
from ._ts_go import TreeSitterGoAdapter
from ._ts_php import TreeSitterPhpAdapter
from ._ts_java import TreeSitterJavaAdapter
from ._ts_ruby import TreeSitterRubyAdapter
from ._ts_kotlin import TreeSitterKotlinAdapter

_ts_adapter = TreeSitterTypeScriptAdapter()
_go_adapter = TreeSitterGoAdapter()
_php_adapter = TreeSitterPhpAdapter()
_java_adapter = TreeSitterJavaAdapter()
_ruby_adapter = TreeSitterRubyAdapter()
_kotlin_adapter = TreeSitterKotlinAdapter()

_REGISTRY: dict[str, LanguageAdapter] = {
    # Source code languages (tree-sitter powered)
    ".ts":    _ts_adapter,
    ".tsx":   _ts_adapter,
    ".js":    _ts_adapter,
    ".jsx":   _ts_adapter,
    ".mjs":   _ts_adapter,
    ".go":    _go_adapter,
    ".php":   _php_adapter,
    ".java":  _java_adapter,
    ".kt":    _kotlin_adapter,
    ".kts":   _kotlin_adapter,
    ".rb":    _ruby_adapter,
    # Template engines (regex-based by design)
    ".blade.php": BladeAdapter(),
    ".j2":        JinjaAdapter(),
    ".jinja2":    JinjaAdapter(),
    ".twig":      JinjaAdapter(),
    ".volt":      JinjaAdapter(),
    ".erb":       ErbAdapter(),
    ".ejs":       ErbAdapter(),
    ".hbs":       HandlebarsAdapter(),
    ".mustache":  HandlebarsAdapter(),
    ".cshtml":    RazorAdapter(),
    ".razor":     RazorAdapter(),
    ".vue":       VueAdapter(),
    ".svelte":    SvelteAdapter(),
}

SUPPORTED_EXTENSIONS = list(_REGISTRY.keys())


def get_adapter(extension: str) -> Optional[LanguageAdapter]:
    """Return the adapter for a file extension, or None if unsupported.

    Rules:   For compound extensions like .blade.php, callers must pass
             the full compound extension, not just .php.
    """
    return _REGISTRY.get(extension.lower())
