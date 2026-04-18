"""languages/__init__.py — Language adapter registry for CodeDNA v0.8.

exports: SUPPORTED_EXTENSIONS | get_adapter(extension)
used_by: codedna_tool/cli.py → SUPPORTED_EXTENSIONS, get_adapter
         tests/test_integration_langs.py → get_adapter
         tests/test_language_adapters.py → get_adapter
         tests/test_refresh.py → get_adapter
rules:   adapters are stateless; get_adapter returns None for unsupported extensions.
Never import language-specific deps here — keep this registry lightweight.
Tree-sitter adapters are preferred when available; regex adapters are the fallback.
agent:   claude-opus-4-6 | anthropic | 2026-04-01 | s_20260401_001 | added template engine adapters: Blade, Jinja2/Twig, ERB/EJS, Handlebars, Razor, Vue SFC, Svelte — 17 total extensions
claude-sonnet-4-6 | anthropic | 2026-04-02 | s_20260402_001 | added .volt (Phalcon Volt engine) via JinjaAdapter — same {# #} comment syntax
claude-opus-4-6 | anthropic | 2026-04-14 | s_20260414_001 | added tree-sitter adapters for TS/JS and Go with regex fallback
claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_001 | added tree-sitter adapters for PHP, Java, Rust, C#, Ruby, Kotlin — all 9 source languages now AST-powered with regex fallback
claude-sonnet-4-6 | anthropic | 2026-04-18 | s_20260418_001 | removed C#/Rust/Swift — simplified to 8 source languages + 14 template extensions; 22 total
"""

from typing import Optional

from .base import LanguageAdapter
from .blade import BladeAdapter
from .erb import ErbAdapter
from .go import GoAdapter
from .handlebars import HandlebarsAdapter
from .java import JavaAdapter, KotlinAdapter
from .jinja import JinjaAdapter
from .php import PhpAdapter
from .razor import RazorAdapter
from .ruby import RubyAdapter
from .typescript import TypeScriptAdapter
from .vue import VueAdapter, SvelteAdapter

# ── Tree-sitter adapters (AST-based, preferred) ────────────────────────────────
# Each try/except provides graceful degradation to the regex adapter if the
# tree-sitter grammar package is missing or corrupted.
# C# and Rust removed — too niche for current user base; reduces install footprint.

_ts_adapter = None
_go_ts_adapter = None
_php_ts_adapter = None
_java_ts_adapter = None
_ruby_ts_adapter = None
_kotlin_ts_adapter = None

try:
    from ._ts_typescript import TreeSitterTypeScriptAdapter
    _ts_adapter = TreeSitterTypeScriptAdapter()
except ImportError:
    pass

try:
    from ._ts_go import TreeSitterGoAdapter
    _go_ts_adapter = TreeSitterGoAdapter()
except ImportError:
    pass

try:
    from ._ts_php import TreeSitterPhpAdapter
    _php_ts_adapter = TreeSitterPhpAdapter()
except ImportError:
    pass

try:
    from ._ts_java import TreeSitterJavaAdapter
    _java_ts_adapter = TreeSitterJavaAdapter()
except ImportError:
    pass

try:
    from ._ts_ruby import TreeSitterRubyAdapter
    _ruby_ts_adapter = TreeSitterRubyAdapter()
except ImportError:
    pass

try:
    from ._ts_kotlin import TreeSitterKotlinAdapter
    _kotlin_ts_adapter = TreeSitterKotlinAdapter()
except ImportError:
    pass

# ── Resolved adapters (tree-sitter if available, regex fallback) ───────────────
_ts_or_regex      = _ts_adapter      or TypeScriptAdapter()
_go_or_regex      = _go_ts_adapter   or GoAdapter()
_php_or_regex     = _php_ts_adapter  or PhpAdapter()
_java_or_regex    = _java_ts_adapter or JavaAdapter()
_ruby_or_regex    = _ruby_ts_adapter or RubyAdapter()
_kotlin_or_regex  = _kotlin_ts_adapter or KotlinAdapter()

_REGISTRY: dict[str, LanguageAdapter] = {
    # Source code languages
    ".ts":    _ts_or_regex,
    ".tsx":   _ts_or_regex,
    ".js":    _ts_or_regex,
    ".jsx":   _ts_or_regex,
    ".mjs":   _ts_or_regex,
    ".go":    _go_or_regex,
    ".php":   _php_or_regex,
    ".java":  _java_or_regex,
    ".kt":    _kotlin_or_regex,
    ".kts":   _kotlin_or_regex,
    ".rb":    _ruby_or_regex,
    # Template engines
    ".blade.php": BladeAdapter(),
    ".j2":        JinjaAdapter(),
    ".jinja2":    JinjaAdapter(),
    ".twig":      JinjaAdapter(),
    ".volt":      JinjaAdapter(),  # Phalcon Volt — same {# #} comment syntax
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
