"""languages/__init__.py — Language adapter registry for CodeDNA v0.8.

exports: get_adapter(extension) -> Optional[LanguageAdapter]
         SUPPORTED_EXTENSIONS
used_by: codedna_tool/cli.py -> collect_files, scan_file_lang
rules:   adapters are stateless; get_adapter returns None for unsupported extensions.
         Never import language-specific deps here — keep this registry lightweight.
agent:   claude-haiku-4-5-20251001 | anthropic | 2026-03-27 | s_20260327_001 | initial multi-language adapter registry
         claude-sonnet-4-6 | anthropic | 2026-03-27 | s_20260327_002 | CodeDNA v0.8 compliance pass: added session_id to agent: field; no logic changes
"""

from typing import Optional

from .base import LanguageAdapter
from .go import GoAdapter
from .typescript import TypeScriptAdapter

_REGISTRY: dict[str, LanguageAdapter] = {
    ".ts": TypeScriptAdapter(),
    ".tsx": TypeScriptAdapter(),
    ".js": TypeScriptAdapter(),
    ".jsx": TypeScriptAdapter(),
    ".mjs": TypeScriptAdapter(),
    ".go": GoAdapter(),
}

SUPPORTED_EXTENSIONS = list(_REGISTRY.keys())


def get_adapter(extension: str) -> Optional[LanguageAdapter]:
    """Return the adapter for a file extension, or None if unsupported."""
    return _REGISTRY.get(extension.lower())
