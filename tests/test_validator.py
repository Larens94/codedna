"""test_validator.py — Tests for validate_manifests.py.

exports: class TestPythonValidation | class TestPHPValidation | class TestGoValidation | class TestTypeScriptValidation | class TestCSharpValidation | class TestRubyValidation | class TestUnsupported | class TestDirectoryValidation | class TestCodeDNAManifest
used_by: none
rules:   Tests cover Python, PHP, Go, TS, C#, Ruby — all must FAIL without header.
Validator is imported directly, not via subprocess.
agent:   claude-opus-4-6 | anthropic | 2026-04-15 | s_20260415_002 | initial validator test suite
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add tools/ to path so we can import validate_manifests
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
from validate_manifests import validate_file, validate_directory


# ── Python files ─────────────────────────────────────────────────────────────

class TestPythonValidation:
    def test_python_no_header_fails(self, tmp_path):
        p = tmp_path / "bare.py"
        p.write_text("def foo(): pass\n")
        r = validate_file(p)
        assert not r.valid
        assert any("No module docstring" in e for e in r.errors)

    def test_python_with_header_passes(self, tmp_path):
        p = tmp_path / "good.py"
        p.write_text(
            '"""good.py — test.\n\n'
            'exports: foo() -> None\n'
            'used_by: none\n'
            'rules:   none\n'
            'agent:   test | anthropic | 2026-04-15 | s_001 | test\n'
            '"""\n\n'
            'def foo(): pass\n'
        )
        r = validate_file(p)
        assert r.valid

    def test_python_missing_field_fails(self, tmp_path):
        p = tmp_path / "partial.py"
        p.write_text(
            '"""partial.py — test.\n\n'
            'exports: foo()\n'
            '"""\n\n'
            'def foo(): pass\n'
        )
        r = validate_file(p)
        assert not r.valid or r.warnings  # missing used_by/rules/agent

    def test_python_empty_file(self, tmp_path):
        p = tmp_path / "empty.py"
        p.write_text("")
        r = validate_file(p)
        assert not r.valid

    def test_python_syntax_error(self, tmp_path):
        p = tmp_path / "broken.py"
        p.write_text("def foo(:\n")
        r = validate_file(p)
        assert not r.valid


# ── PHP files ────────────────────────────────────────────────────────────────

class TestPHPValidation:
    def test_php_no_header_fails(self, tmp_path):
        p = tmp_path / "Foo.php"
        p.write_text("<?php\nclass Foo {}\n")
        r = validate_file(p)
        assert not r.valid
        assert any(".php" in e for e in r.errors)

    def test_php_with_header_passes(self, tmp_path):
        p = tmp_path / "Foo.php"
        p.write_text(
            "<?php\n"
            "// Foo.php — test file.\n"
            "//\n"
            "// exports: Foo\n"
            "// used_by: none\n"
            "// rules: none\n"
            "// agent: test | 2026-04-15 | test\n"
            "\n"
            "class Foo {}\n"
        )
        r = validate_file(p)
        assert r.valid

    def test_php_phpdoc_header_not_detected_by_validator(self, tmp_path):
        """PHPDoc format (/** */) is detected by has_codedna_header (prevents duplicates)
        but NOT by the validator (which uses // prefix for PHP). This is a known limitation —
        the canonical PHP format is // comments, not PHPDoc."""
        p = tmp_path / "Bar.php"
        p.write_text(
            "<?php\n"
            "/**\n"
            " * Bar.php — test file.\n"
            " *\n"
            " * exports: Bar\n"
            " * used_by: none\n"
            " * rules: none\n"
            " */\n"
            "class Bar {}\n"
        )
        r = validate_file(p)
        # Validator uses // prefix — PHPDoc * prefix not detected
        assert not r.valid


# ── Go files ─────────────────────────────────────────────────────────────────

class TestGoValidation:
    def test_go_no_header_fails(self, tmp_path):
        p = tmp_path / "main.go"
        p.write_text("package main\n\nfunc Main() {}\n")
        r = validate_file(p)
        assert not r.valid

    def test_go_with_header_passes(self, tmp_path):
        p = tmp_path / "main.go"
        p.write_text(
            "// main.go — entry point.\n"
            "//\n"
            "// exports: Main()\n"
            "// used_by: none\n"
            "// rules: none\n"
            "// agent: test | 2026-04-15 | test\n"
            "\n"
            "package main\n\nfunc Main() {}\n"
        )
        r = validate_file(p)
        assert r.valid


# ── TypeScript files ─────────────────────────────────────────────────────────

class TestTypeScriptValidation:
    def test_ts_no_header_fails(self, tmp_path):
        p = tmp_path / "app.ts"
        p.write_text("export function hello() {}\n")
        r = validate_file(p)
        assert not r.valid

    def test_ts_with_header_passes(self, tmp_path):
        p = tmp_path / "app.ts"
        p.write_text(
            "// app.ts — test.\n"
            "//\n"
            "// exports: hello()\n"
            "// used_by: none\n"
            "// rules: none\n"
            "// agent: test | 2026-04-15 | test\n"
            "\n"
            "export function hello() {}\n"
        )
        r = validate_file(p)
        assert r.valid


# ── C# files ─────────────────────────────────────────────────────────────────

class TestCSharpValidation:
    def test_cs_no_header_fails(self, tmp_path):
        p = tmp_path / "Foo.cs"
        p.write_text("public class Foo {}\n")
        r = validate_file(p)
        assert not r.valid

    def test_cs_with_header_passes(self, tmp_path):
        p = tmp_path / "Foo.cs"
        p.write_text(
            "// Foo.cs — test.\n"
            "//\n"
            "// exports: Foo\n"
            "// used_by: none\n"
            "// rules: none\n"
            "// agent: test | 2026-04-15 | test\n"
            "\n"
            "public class Foo {}\n"
        )
        r = validate_file(p)
        assert r.valid


# ── Ruby files ───────────────────────────────────────────────────────────────

class TestRubyValidation:
    def test_rb_no_header_fails(self, tmp_path):
        p = tmp_path / "foo.rb"
        p.write_text("class Foo; end\n")
        r = validate_file(p)
        assert not r.valid

    def test_rb_with_header_passes(self, tmp_path):
        p = tmp_path / "foo.rb"
        p.write_text(
            "# foo.rb — test.\n"
            "#\n"
            "# exports: Foo\n"
            "# used_by: none\n"
            "# rules: none\n"
            "# agent: test | 2026-04-15 | test\n"
            "\n"
            "class Foo; end\n"
        )
        r = validate_file(p)
        assert r.valid


# ── Unsupported extension ────────────────────────────────────────────────────

class TestUnsupported:
    def test_unsupported_extension_warns(self, tmp_path):
        p = tmp_path / "data.csv"
        p.write_text("a,b,c\n1,2,3\n")
        r = validate_file(p)
        # Should warn, not error
        assert r.valid
        assert any("not supported" in w for w in r.warnings)


# ── Directory validation ─────────────────────────────────────────────────────

class TestDirectoryValidation:
    def test_validate_directory_counts(self, mini_project):
        results = validate_directory(mini_project)
        assert len(results) == 3  # 3 Python files
        # All should fail (no headers)
        assert all(not r.valid for r in results)

    def test_validate_directory_annotated(self, mini_project_annotated):
        results = validate_directory(mini_project_annotated)
        assert len(results) == 2  # 2 files
        assert all(r.valid for r in results)

    def test_validate_directory_with_extensions(self, tmp_path):
        (tmp_path / "app.ts").write_text("export function foo() {}\n")
        (tmp_path / "app.py").write_text("def foo(): pass\n")

        results = validate_directory(tmp_path, extensions=[".ts"])
        ts_results = [r for r in results if r.path.endswith(".ts")]
        assert len(ts_results) == 1
        assert not ts_results[0].valid


# ── .codedna manifest ────────────────────────────────────────────────────────

class TestCodeDNAManifest:
    def test_codedna_file_parseable(self, mini_codedna):
        """Verify .codedna YAML is valid and has expected structure."""
        import yaml

        codedna_path = mini_codedna / ".codedna"
        data = yaml.safe_load(codedna_path.read_text())

        assert data["project"] == "testapp"
        assert "packages" in data
        assert "agent_sessions" in data
        assert len(data["agent_sessions"]) == 1
        assert data["agent_sessions"][0]["agent"] == "test-model"

    def test_codedna_missing_does_not_crash(self, tmp_path):
        """Validator should not crash if .codedna doesn't exist."""
        (tmp_path / "app.py").write_text("def foo(): pass\n")
        results = validate_directory(tmp_path)
        # Should still validate files, just no manifest
        assert len(results) == 1
