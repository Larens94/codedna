"""conftest.py — Shared fixtures for CodeDNA test suite.

exports: mini_project(tmp_path) | mini_project_annotated(tmp_path) | mini_codedna(tmp_path)
used_by: none
rules:   All fixtures create temporary directories that are cleaned up automatically.
agent:   claude-opus-4-6 | anthropic | 2026-04-15 | s_20260415_002 | initial conftest with shared fixtures
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def mini_project(tmp_path):
    """A minimal Python project with 3 files and cross-file imports."""
    (tmp_path / "app.py").write_text(
        'from utils import helper\n\n'
        'def main():\n'
        '    return helper()\n'
    )
    (tmp_path / "utils.py").write_text(
        'def helper():\n'
        '    return "ok"\n\n'
        'def internal():\n'
        '    pass\n'
    )
    (tmp_path / "models.py").write_text(
        'class User:\n'
        '    def __init__(self, name):\n'
        '        self.name = name\n\n'
        '    def greet(self):\n'
        '        return f"hello {self.name}"\n'
    )
    return tmp_path


@pytest.fixture
def mini_project_annotated(tmp_path):
    """A minimal project already annotated with CodeDNA headers."""
    (tmp_path / "app.py").write_text(
        '"""app.py — Main entry point.\n\n'
        'exports: main() -> str\n'
        'used_by: none\n'
        'rules:   none\n'
        'agent:   test | anthropic | 2026-04-15 | s_001 | initial\n'
        '"""\n\n'
        'from utils import helper\n\n'
        'def main():\n'
        '    """Run app.\n\n'
        '    Rules:   Must call helper() not internal().\n'
        '    """\n'
        '    return helper()\n'
    )
    (tmp_path / "utils.py").write_text(
        '"""utils.py — Utility functions.\n\n'
        'exports: helper() -> str\n'
        'used_by: app.py -> main\n'
        'rules:   none\n'
        'agent:   test | anthropic | 2026-04-15 | s_001 | initial\n'
        '"""\n\n'
        'def helper():\n'
        '    """Return ok.\n\n'
        '    Rules:   Always returns a string, never None.\n'
        '    """\n'
        '    return "ok"\n'
    )
    return tmp_path


@pytest.fixture
def mini_codedna(tmp_path):
    """A .codedna manifest file."""
    (tmp_path / ".codedna").write_text(
        'project: testapp\n'
        'description: "Test project"\n\n'
        'packages:\n'
        '  app/:\n'
        '    purpose: "Main application"\n'
        '    key_files: [app.py, utils.py]\n\n'
        'agent_sessions:\n'
        '  - agent: test-model\n'
        '    provider: anthropic\n'
        '    date: 2026-04-15\n'
        '    session_id: s_001\n'
        '    task: "initial setup"\n'
        '    changed: [app.py]\n'
        '    visited: [app.py, utils.py]\n'
        '    message: >\n'
        '      Test session.\n'
    )
    return tmp_path
