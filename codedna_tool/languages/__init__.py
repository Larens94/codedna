"""languages/__init__.py — Language adapter registry for CodeDNA v0.8.

exports: get_adapter(extension) -> Optional[LanguageAdapter]
         SUPPORTED_EXTENSIONS
used_by: codedna_tool/cli.py -> collect_files, scan_file_lang
rules:   adapters are stateless; get_adapter returns None for unsupported extensions.
         Never import language-specific deps here — keep this registry lightweight.
agent:   claude-haiku-4-5-20251001 | anthropic | 2026-03-27 | s_20260327_001 | initial multi-language adapter registry
         claude-sonnet-4-6 | anthropic | 2026-03-27 | s_20260327_002 | CodeDNA v0.8 compliance pass: added session_id to agent: field; no logic changes
         claude-sonnet-4-6 | anthropic | 2026-03-27 | s_20260327_003 | added PHP/Laravel, Rust, Java, Kotlin, Ruby, C#, Swift adapters — full 11-language coverage
"""

from typing import Optional

from .base import LanguageAdapter
from .csharp import CSharpAdapter
from .go import GoAdapter
from .java import JavaAdapter, KotlinAdapter
from .php import PhpAdapter
from .ruby import RubyAdapter
from .rust import RustAdapter
from .swift import SwiftAdapter
from .typescript import TypeScriptAdapter

_REGISTRY: dict[str, LanguageAdapter] = {
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
}

SUPPORTED_EXTENSIONS = list(_REGISTRY.keys())


def get_adapter(extension: str) -> Optional[LanguageAdapter]:
    """Return the adapter for a file extension, or None if unsupported."""
    return _REGISTRY.get(extension.lower())
