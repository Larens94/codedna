"""test_refresh.py — Tests for codedna refresh command and relative import resolution.

exports: PYTHON | run_codedna() | class TestRefresh | class TestRelativeImports | class TestReducedHeader | class TestHasCodednaHeader
used_by: none
rules:   Tests verify that refresh updates exports/used_by without touching rules/agent/message.
Tests also verify Python relative imports (from .module) are resolved correctly.
agent:   claude-opus-4-6 | anthropic | 2026-04-15 | s_20260415_003 | initial refresh + relative import tests
claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_002 | updated TestReducedHeader: all languages now emit full headers (exports+used_by+rules+agent); updated validator test to require full PHP header
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PYTHON = sys.executable


def run_codedna(*args, cwd=None):
    result = subprocess.run(
        [PYTHON, "-m", "codedna_tool.cli", *args],
        capture_output=True, text=True, cwd=cwd, timeout=60,
    )
    return result.returncode, result.stdout, result.stderr


class TestRefresh:
    def test_refresh_updates_used_by(self, tmp_path):
        """After adding a new importer, refresh should update used_by."""
        # Create and annotate initial project
        (tmp_path / "utils.py").write_text("def helper(): return 'ok'\n")
        (tmp_path / "app.py").write_text("from utils import helper\ndef main(): return helper()\n")
        run_codedna("init", str(tmp_path), "--no-llm")

        # Verify utils.py has used_by: app.py
        utils_content = (tmp_path / "utils.py").read_text()
        assert "app.py" in utils_content

        # Add a new file that imports utils
        (tmp_path / "worker.py").write_text("from utils import helper\ndef work(): return helper()\n")
        run_codedna("init", str(tmp_path), "--no-llm")  # annotate worker.py

        # Refresh should update utils.py used_by to include worker.py
        run_codedna("refresh", str(tmp_path))
        utils_content = (tmp_path / "utils.py").read_text()
        assert "worker.py" in utils_content

    def test_refresh_preserves_rules(self, tmp_path):
        """Refresh must NOT touch rules: field."""
        (tmp_path / "app.py").write_text(
            '"""app.py — test.\n\n'
            'exports: main() -> str\n'
            'used_by: none\n'
            'rules:   NEVER return None — always return empty string\n'
            'agent:   test | anthropic | 2026-04-15 | s_001 | initial\n'
            '"""\n\ndef main(): return ""\n'
        )
        run_codedna("refresh", str(tmp_path))
        content = (tmp_path / "app.py").read_text()
        assert "NEVER return None" in content

    def test_refresh_preserves_agent(self, tmp_path):
        """Refresh must NOT touch agent: field."""
        (tmp_path / "app.py").write_text(
            '"""app.py — test.\n\n'
            'exports: main() -> str\n'
            'used_by: none\n'
            'rules:   none\n'
            'agent:   my-special-model | anthropic | 2026-04-15 | s_001 | important note\n'
            '"""\n\ndef main(): return ""\n'
        )
        run_codedna("refresh", str(tmp_path))
        content = (tmp_path / "app.py").read_text()
        assert "my-special-model" in content
        assert "important note" in content

    def test_refresh_skips_unannotated(self, tmp_path):
        """Files without CodeDNA headers should be skipped."""
        (tmp_path / "bare.py").write_text("def foo(): pass\n")
        rc, out, err = run_codedna("refresh", str(tmp_path), "-v")
        assert "skip" in out.lower() or "skipped" in out.lower()

    def test_refresh_dry_run(self, tmp_path):
        """Dry run should not modify files."""
        (tmp_path / "app.py").write_text(
            '"""app.py — test.\n\nexports: old_function()\nused_by: none\nrules: none\n'
            'agent: test | 2026-04-15 | test\n"""\n\ndef new_function(): pass\n'
        )
        content_before = (tmp_path / "app.py").read_text()
        run_codedna("refresh", str(tmp_path), "--dry-run")
        content_after = (tmp_path / "app.py").read_text()
        assert content_before == content_after


class TestRelativeImports:
    def test_relative_import_resolves(self, tmp_path):
        """from .module import X should create used_by entry."""
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "base.py").write_text("class Base: pass\n")
        (pkg / "child.py").write_text("from .base import Base\nclass Child(Base): pass\n")

        run_codedna("init", str(tmp_path), "--no-llm")
        base_content = (pkg / "base.py").read_text()
        assert "child.py" in base_content

    def test_relative_import_parent(self, tmp_path):
        """from ..module import X should resolve to parent package."""
        pkg = tmp_path / "mypkg"
        sub = pkg / "sub"
        sub.mkdir(parents=True)
        (pkg / "__init__.py").write_text("")
        (sub / "__init__.py").write_text("")
        (pkg / "utils.py").write_text("def helper(): pass\n")
        (sub / "worker.py").write_text("from ..utils import helper\ndef work(): return helper()\n")

        run_codedna("init", str(tmp_path), "--no-llm")
        utils_content = (pkg / "utils.py").read_text()
        assert "worker.py" in utils_content or "sub" in utils_content


class TestReducedHeader:
    def test_non_python_has_full_header(self, tmp_path):
        """Non-Python files should get full header (exports + used_by + rules + agent)."""
        from codedna_tool.languages import get_adapter

        for ext, code in [
            (".ts", "export function hello() {}"),
            (".go", "package main\nfunc Hello() {}"),
            (".php", "<?php\nclass Foo {}"),
            (".java", "public class Foo {}"),
            (".rs", "pub fn hello() {}"),
        ]:
            adapter = get_adapter(ext)
            result = adapter.inject_header(code, f"test{ext}", "Hello", "none", "none", "test", "2026-04-15")
            assert "exports:" in result, f"{ext} missing exports:"
            assert "used_by:" in result, f"{ext} missing used_by:"
            assert "rules:" in result, f"{ext} missing rules:"
            assert "agent:" in result, f"{ext} missing agent:"

    def test_python_has_full_header(self, tmp_path):
        """Python files must keep full header with exports and used_by."""
        run_codedna("init", str(tmp_path), "--no-llm")
        # Create a Python file and annotate
        (tmp_path / "app.py").write_text("def main(): pass\n")
        run_codedna("init", str(tmp_path), "--no-llm")
        content = (tmp_path / "app.py").read_text()
        assert "exports:" in content
        assert "used_by:" in content
        assert "rules:" in content

    def test_validator_accepts_full_php(self, tmp_path):
        """Validator should accept PHP with full header (exports + used_by + rules + agent)."""
        import sys; sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
        import validate_manifests as vm
        p = tmp_path / "Foo.php"
        p.write_text(
            "<?php\n"
            "// Foo.php — test.\n"
            "//\n"
            "// exports: Foo\n"
            "// used_by: none\n"
            "// rules:   admin only\n"
            "// agent:   test | anthropic | 2026-04-16 | s_001 | test\n"
            "\nclass Foo {}\n"
        )
        r = vm.validate_file(p)
        assert r.valid, f"Full PHP header should pass: {r.errors}"

    def test_validator_rejects_python_without_exports(self, tmp_path):
        """Validator should reject Python with only rules + agent (missing exports/used_by)."""
        import sys; sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
        import validate_manifests as vm
        p = tmp_path / "app.py"
        p.write_text('"""app.py — test.\n\nrules: none\nagent: test | 2026-04-15 | test\n"""\ndef foo(): pass\n')
        r = vm.validate_file(p)
        assert not r.valid, "Python without exports/used_by should fail"


class TestHasCodednaHeader:
    def test_detects_reduced_header(self):
        """has_codedna_header should detect headers with only rules:/agent: (no exports)."""
        from codedna_tool.languages.go import GoAdapter
        adapter = GoAdapter()

        reduced = "// main.go — entry.\n//\n// rules: none\n// agent: test | 2026-04-15 | test\n\npackage main\n"
        assert adapter.has_codedna_header(reduced)

    def test_detects_full_header(self):
        from codedna_tool.languages.go import GoAdapter
        adapter = GoAdapter()

        full = "// main.go — entry.\n//\n// exports: Main\n// used_by: none\n// rules: none\n// agent: test\n\npackage main\n"
        assert adapter.has_codedna_header(full)

    def test_detects_no_header(self):
        from codedna_tool.languages.go import GoAdapter
        adapter = GoAdapter()

        bare = "package main\n\nfunc Main() {}\n"
        assert not adapter.has_codedna_header(bare)
