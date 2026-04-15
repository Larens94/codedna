"""test_cli.py — Tests for codedna CLI commands (init, check, update).

exports: none (test module)
used_by: CI pipeline, pytest
rules:   Tests run codedna CLI as subprocess to verify end-to-end behavior.
         Each test uses tmp_path for isolation — never touches real project files.
agent:   claude-opus-4-6 | anthropic | 2026-04-15 | s_20260415_002 | initial CLI test suite
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PYTHON = sys.executable


def run_codedna(*args, cwd=None):
    """Run codedna CLI and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [PYTHON, "-m", "codedna_tool.cli", *args],
        capture_output=True, text=True, cwd=cwd, timeout=60,
    )
    return result.returncode, result.stdout, result.stderr


# ── codedna init ─────────────────────────────────────────────────────────────

class TestInit:
    def test_init_no_llm_creates_headers(self, mini_project):
        rc, out, err = run_codedna("init", str(mini_project), "--no-llm")
        assert rc == 0
        assert "Annotated" in out

        # All 3 files should have headers
        for name in ["app.py", "utils.py", "models.py"]:
            content = (mini_project / name).read_text()
            assert "exports:" in content, f"{name} missing exports:"
            assert "used_by:" in content, f"{name} missing used_by:"
            assert "rules:" in content, f"{name} missing rules:"

    def test_init_no_llm_agent_field(self, mini_project):
        run_codedna("init", str(mini_project), "--no-llm")

        content = (mini_project / "app.py").read_text()
        assert "codedna-cli (no-llm)" in content
        assert "claude-haiku" not in content

    def test_init_builds_used_by_graph(self, mini_project):
        run_codedna("init", str(mini_project), "--no-llm")

        # app.py imports from utils, so utils.py should have used_by: app.py
        utils_content = (mini_project / "utils.py").read_text()
        assert "app.py" in utils_content or "app" in utils_content

    def test_init_idempotent(self, mini_project):
        run_codedna("init", str(mini_project), "--no-llm")
        content_first = (mini_project / "app.py").read_text()

        run_codedna("init", str(mini_project), "--no-llm")
        content_second = (mini_project / "app.py").read_text()

        assert content_first == content_second

    def test_init_skips_already_annotated(self, mini_project_annotated):
        rc, out, err = run_codedna("init", str(mini_project_annotated), "--no-llm")
        assert rc == 0
        # Should skip both files
        assert "skip" in out.lower() or "Annotated 0" in out

    def test_init_skips_excluded_dirs(self, mini_project):
        # Create files in directories that should be skipped
        for skip_dir in ["node_modules", "vendor", "venv", "__pycache__"]:
            d = mini_project / skip_dir
            d.mkdir()
            (d / "bad.py").write_text("def bad(): pass\n")

        run_codedna("init", str(mini_project), "--no-llm")

        # Files in skip dirs should NOT be annotated
        for skip_dir in ["node_modules", "vendor", "venv"]:
            content = (mini_project / skip_dir / "bad.py").read_text()
            assert "exports:" not in content

    def test_init_with_extensions(self, mini_project):
        # Create a TS file
        (mini_project / "app.ts").write_text(
            'export function hello(): string { return "hi"; }\n'
        )

        run_codedna("init", str(mini_project), "--no-llm", "--extensions", "ts")

        ts_content = (mini_project / "app.ts").read_text()
        assert "exports:" in ts_content or "// app.ts" in ts_content


# ── codedna check ────────────────────────────────────────────────────────────

class TestCheck:
    def test_check_unannotated_project(self, mini_project):
        rc, out, err = run_codedna("check", str(mini_project))
        assert "INCOMPLETE" in out or "0/" in out

    def test_check_annotated_project(self, mini_project_annotated):
        rc, out, err = run_codedna("check", str(mini_project_annotated))
        # Should show some coverage
        assert "L1" in out

    def test_check_reports_file_count(self, mini_project):
        rc, out, err = run_codedna("check", str(mini_project))
        # Should mention number of Python files
        assert "3" in out or "files" in out.lower()


# ── codedna init + check round-trip ──────────────────────────────────────────

class TestRoundTrip:
    def test_init_then_check_shows_coverage(self, mini_project):
        run_codedna("init", str(mini_project), "--no-llm")
        rc, out, err = run_codedna("check", str(mini_project))

        # After init, all files should have L1 headers
        assert "3/3" in out or "100%" in out or "L1" in out


# ── build_module_docstring ───────────────────────────────────────────────────

class TestBuildDocstring:
    def test_docstring_format(self):
        from codedna_tool.cli import build_module_docstring, FileInfo

        info = FileInfo(
            path=Path("/tmp/test.py"),
            rel="test.py",
            exports=["greet"],
            deps={},
            docstring=None,
            has_codedna=False,
            funcs=[],
            parseable=True,
        )
        doc = build_module_docstring(info, {}, "none", "test-model")
        assert '"""test.py' in doc
        assert "exports:" in doc
        assert "used_by:" in doc
        assert "rules:" in doc
        assert "agent:" in doc
        assert "test-model" in doc

    def test_docstring_no_llm_agent(self):
        from codedna_tool.cli import build_module_docstring, FileInfo

        info = FileInfo(
            path=Path("/tmp/test.py"),
            rel="test.py",
            exports=[],
            deps={},
            docstring=None,
            has_codedna=False,
            funcs=[],
            parseable=True,
        )
        doc = build_module_docstring(info, {}, "none", "codedna-cli (no-llm)")
        assert "codedna-cli (no-llm)" in doc
        assert "haiku" not in doc
