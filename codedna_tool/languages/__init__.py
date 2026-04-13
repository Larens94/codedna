"""languages/__init__.py — Language adapter registry for CodeDNA v0.8.

exports: get_adapter(extension) -> Optional[LanguageAdapter]
         SUPPORTED_EXTENSIONS
used_by: codedna_tool/cli.py -> collect_files, scan_file_lang
rules:   adapters are stateless; get_adapter returns None for unsupported extensions.
         Never import language-specific deps here — keep this registry lightweight.
         Tree-sitter adapters are preferred when available; regex adapters are the fallback.
agent:   claude-sonnet-4-6 | anthropic | 2026-03-27 | s_20260327_003 | added PHP/Laravel, Rust, Java, Kotlin, Ruby, C#, Swift adapters — full 11-language coverage
         claude-opus-4-6 | anthropic | 2026-04-01 | s_20260401_001 | added template engine adapters: Blade, Jinja2/Twig, ERB/EJS, Handlebars, Razor, Vue SFC, Svelte — 17 total extensions
         claude-sonnet-4-6 | anthropic | 2026-04-02 | s_20260402_001 | added .volt (Phalcon Volt engine) via JinjaAdapter — same {# #} comment syntax
         claude-opus-4-6 | anthropic | 2026-04-14 | s_20260414_001 | added tree-sitter adapters for TS/JS and Go with regex fallback
"""

from typing import Optional

from .base import LanguageAdapter
from .blade import BladeAdapter
from .csharp import CSharpAdapter
from .erb import ErbAdapter
from .go import GoAdapter
from .handlebars import HandlebarsAdapter
from .java import JavaAdapter, KotlinAdapter
from .jinja import JinjaAdapter
from .php import PhpAdapter
from .razor import RazorAdapter
from .ruby import RubyAdapter
from .rust import RustAdapter
from .swift import SwiftAdapter
from .typescript import TypeScriptAdapter
from .vue import VueAdapter, SvelteAdapter

# Try tree-sitter adapters (more accurate AST-based extraction)
_ts_adapter = None
_go_ts_adapter = None
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

_ts_or_regex = _ts_adapter or TypeScriptAdapter()
_go_or_regex = _go_ts_adapter or GoAdapter()

_REGISTRY: dict[str, LanguageAdapter] = {
    # Source code languages
    ".ts": _ts_or_regex,
    ".tsx": _ts_or_regex,
    ".js": _ts_or_regex,
    ".jsx": _ts_or_regex,
    ".mjs": _ts_or_regex,
    ".go": _go_or_regex,
    ".php": PhpAdapter(),
    ".rs": RustAdapter(),
    ".java": JavaAdapter(),
    ".kt": KotlinAdapter(),
    ".kts": KotlinAdapter(),
    ".rb": RubyAdapter(),
    ".cs": CSharpAdapter(),
    ".swift": SwiftAdapter(),
    # Template engines
    ".blade.php": BladeAdapter(),
    ".j2": JinjaAdapter(),
    ".jinja2": JinjaAdapter(),
    ".twig": JinjaAdapter(),
    ".volt": JinjaAdapter(),  # Phalcon Volt — same {# #} comment syntax
    ".erb": ErbAdapter(),
    ".ejs": ErbAdapter(),
    ".hbs": HandlebarsAdapter(),
    ".mustache": HandlebarsAdapter(),
    ".cshtml": RazorAdapter(),
    ".razor": RazorAdapter(),
    ".vue": VueAdapter(),
    ".svelte": SvelteAdapter(),
}

SUPPORTED_EXTENSIONS = list(_REGISTRY.keys())


def get_adapter(extension: str) -> Optional[LanguageAdapter]:
    """Return the adapter for a file extension, or None if unsupported.

    Rules:   For compound extensions like .blade.php, callers must pass
             the full compound extension, not just .php.
    """
    return _REGISTRY.get(extension.lower())
