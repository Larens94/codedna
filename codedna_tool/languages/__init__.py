"""languages/__init__.py — Language adapter registry for CodeDNA v0.8.

exports: get_adapter(extension) -> Optional[LanguageAdapter]
         SUPPORTED_EXTENSIONS
used_by: codedna_tool/cli.py -> collect_files, scan_file_lang
rules:   adapters are stateless; get_adapter returns None for unsupported extensions.
         Never import language-specific deps here — keep this registry lightweight.
agent:   claude-haiku-4-5-20251001 | anthropic | 2026-03-27 | s_20260327_001 | initial multi-language adapter registry
         claude-sonnet-4-6 | anthropic | 2026-03-27 | s_20260327_003 | added PHP/Laravel, Rust, Java, Kotlin, Ruby, C#, Swift adapters — full 11-language coverage
         claude-opus-4-6 | anthropic | 2026-04-01 | s_20260401_001 | added template engine adapters: Blade, Jinja2/Twig, ERB/EJS, Handlebars, Razor, Vue SFC, Svelte — 17 total extensions
         claude-sonnet-4-6 | anthropic | 2026-04-02 | s_20260402_001 | added .volt (Phalcon Volt engine) via JinjaAdapter — same {# #} comment syntax
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

_REGISTRY: dict[str, LanguageAdapter] = {
    # Source code languages
    ".ts": TypeScriptAdapter(),
    ".tsx": TypeScriptAdapter(),
    ".js": TypeScriptAdapter(),
    ".jsx": TypeScriptAdapter(),
    ".mjs": TypeScriptAdapter(),
    ".go": GoAdapter(),
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
