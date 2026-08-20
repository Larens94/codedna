"""__init__.py — Expose the installed CodeDNA package version.

exports: __version__: str
used_by: none
rules:   __version__ is sourced from package metadata (pyproject.toml is the single source of truth).
importlib.metadata.version() raises PackageNotFoundError if the package is not installed
(e.g. during bare pytest runs) — fallback to "0.0.0.dev" in that case.
agent:   claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_002 | initial __version__ via importlib.metadata
gpt-5 | openai | 2026-08-20 | s_20260820_hardening | correct package export and filename metadata for zero-warning validation
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__: str = version("codedna")
except PackageNotFoundError:
    __version__ = "0.0.0.dev"
