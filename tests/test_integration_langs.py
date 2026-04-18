"""test_integration_langs.py — Integration tests for all 8 non-Python language adapters.

exports: FIXTURES_DIR | PYTHON | TODAY | MODEL | run_codedna() | class TestTypeScriptIntegration | class TestGoIntegration | class TestPHPIntegration | class TestJavaIntegration | class TestRubyIntegration | class TestKotlinIntegration | class TestCLIMultiLang
used_by: none
rules:   Tests use realistic fixture files from tests/fixtures/ — not toy examples.
Each language verifies: named exports, inject_header fields, idempotency,
validator acceptance, and CLI round-trip via subprocess.
Fixtures represent real-world patterns (Laravel controller, Spring service, etc.).
Adapter-specific symbols (tree-sitter impl methods) are checked with any() to
pass regardless of whether tree-sitter or regex adapter is active.
C# and Rust removed from registry (2026-04-18) — those test classes skipped.
agent:   claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_002 | initial integration tests for 8 languages with realistic fixtures
claude-sonnet-4-6 | anthropic | 2026-04-18 | s_20260418_l0meta | skip TestRustIntegration/TestCSharpIntegration + remove rs/cs from TestCLIMultiLang
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
from validate_manifests import validate_file  # noqa: E402

from codedna_tool.languages import get_adapter  # noqa: E402

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PYTHON = sys.executable

TODAY = "2026-04-16"
MODEL = "test-model | anthropic | 2026-04-16 | test-session | integration test"


def run_codedna(*args, cwd=None):
    result = subprocess.run(
        [PYTHON, "-m", "codedna_tool.cli", *args],
        capture_output=True, text=True, cwd=cwd, timeout=60,
    )
    return result.returncode, result.stdout, result.stderr


def _assert_header_fields(text: str, comment_prefix: str = "//") -> None:
    """Assert all 4 required CodeDNA fields are present."""
    assert "exports:" in text
    assert "used_by:" in text
    assert "rules:" in text
    assert "agent:" in text


def _assert_idempotent(adapter, source: str, filename: str) -> None:
    """Inject header twice; result must be identical."""
    r1 = adapter.inject_header(source, filename, "X", "none", "none", MODEL, TODAY)
    r2 = adapter.inject_header(r1, filename, "X", "none", "none", MODEL, TODAY)
    assert r1 == r2, "inject_header is not idempotent"


def _assert_validator_accepts(tmp_path: Path, adapter, source: str, exports: str, filename: str) -> None:
    """Write annotated source to tmp_path and validate with validate_file()."""
    annotated = adapter.inject_header(source, filename, exports, "none", "none", MODEL, TODAY)
    p = tmp_path / filename
    p.write_text(annotated)
    result = validate_file(p)
    assert result.valid, f"Validator rejected {filename}: {result.errors}"


# ── TypeScript ────────────────────────────────────────────────────────────────

class TestTypeScriptIntegration:
    FIXTURE = FIXTURES_DIR / "UserService.ts"

    def test_exports_named_symbols(self):
        adapter = get_adapter(".ts")
        info = adapter.extract_info(self.FIXTURE, FIXTURES_DIR)
        assert info.parseable
        assert "IUserService" in info.exports
        assert "CreateUserDto" in info.exports
        assert "UpdateUserDto" in info.exports
        assert "USER_CACHE_TTL" in info.exports
        assert "UserService" in info.exports
        assert "UserServiceFactory" in info.exports
        # private class method — not exported
        assert "buildUrl" not in info.exports

    def test_inject_header_produces_valid_header(self):
        adapter = get_adapter(".ts")
        source = self.FIXTURE.read_text()
        result = adapter.inject_header(
            source, "UserService.ts", "UserService", "none", "none", MODEL, TODAY
        )
        _assert_header_fields(result)
        assert "export interface IUserService" in result  # original source preserved

    def test_idempotency(self):
        adapter = get_adapter(".ts")
        _assert_idempotent(adapter, self.FIXTURE.read_text(), "UserService.ts")

    def test_validator_accepts_annotated(self, tmp_path):
        adapter = get_adapter(".ts")
        _assert_validator_accepts(tmp_path, adapter, self.FIXTURE.read_text(),
                                  "UserService, IUserService", "UserService.ts")


# ── Go ────────────────────────────────────────────────────────────────────────

class TestGoIntegration:
    FIXTURE = FIXTURES_DIR / "user_service.go"

    def test_exports_named_symbols(self):
        adapter = get_adapter(".go")
        info = adapter.extract_info(self.FIXTURE, FIXTURES_DIR)
        assert info.parseable
        assert "ErrUserNotFound" in info.exports
        assert "DefaultPageSize" in info.exports
        assert "User" in info.exports
        assert "UserService" in info.exports
        assert "NewUserService" in info.exports
        assert "GetByID" in info.exports
        assert "ListUsers" in info.exports
        # unexported functions — must be absent
        assert "validateEmail" not in info.exports
        assert "contains" not in info.exports

    def test_deps_include_stdlib_and_third_party(self):
        adapter = get_adapter(".go")
        info = adapter.extract_info(self.FIXTURE, FIXTURES_DIR)
        assert "context" in info.deps
        assert any("uuid" in d for d in info.deps)

    def test_inject_header_preserves_package_line(self):
        adapter = get_adapter(".go")
        source = self.FIXTURE.read_text()
        result = adapter.inject_header(
            source, "user_service.go", "UserService", "none", "none", MODEL, TODAY
        )
        _assert_header_fields(result)
        # Go header is injected before package — package must still be present
        assert "package users" in result

    def test_idempotency(self):
        adapter = get_adapter(".go")
        _assert_idempotent(adapter, self.FIXTURE.read_text(), "user_service.go")

    def test_validator_accepts_annotated(self, tmp_path):
        adapter = get_adapter(".go")
        _assert_validator_accepts(tmp_path, adapter, self.FIXTURE.read_text(),
                                  "UserService", "user_service.go")


# ── PHP ───────────────────────────────────────────────────────────────────────

class TestPHPIntegration:
    FIXTURE = FIXTURES_DIR / "UserController.php"

    def test_exports_named_symbols(self):
        adapter = get_adapter(".php")
        info = adapter.extract_info(self.FIXTURE, FIXTURES_DIR)
        assert info.parseable
        assert "UserController" in info.exports
        assert any("index" in e for e in info.exports)
        assert any("show" in e for e in info.exports)
        assert any("store" in e for e in info.exports)
        assert any("update" in e for e in info.exports)
        assert any("destroy" in e for e in info.exports)
        # protected and private — must be absent
        assert not any("authorize" in e for e in info.exports)
        assert not any("resolveUser" in e for e in info.exports)

    def test_inject_header_preserves_php_open_tag(self):
        adapter = get_adapter(".php")
        source = self.FIXTURE.read_text()
        result = adapter.inject_header(
            source, "UserController.php", "UserController", "none", "none", MODEL, TODAY
        )
        _assert_header_fields(result)
        assert result.startswith("<?php")

    def test_idempotency(self):
        adapter = get_adapter(".php")
        _assert_idempotent(adapter, self.FIXTURE.read_text(), "UserController.php")

    def test_validator_accepts_annotated(self, tmp_path):
        adapter = get_adapter(".php")
        _assert_validator_accepts(tmp_path, adapter, self.FIXTURE.read_text(),
                                  "UserController", "UserController.php")


# ── Java ──────────────────────────────────────────────────────────────────────

class TestJavaIntegration:
    FIXTURE = FIXTURES_DIR / "UserService.java"

    def test_exports_named_symbols(self):
        adapter = get_adapter(".java")
        info = adapter.extract_info(self.FIXTURE, FIXTURES_DIR)
        assert info.parseable
        assert "UserService" in info.exports
        assert any("findAll" in e for e in info.exports)
        assert any("findById" in e for e in info.exports)
        assert any("create" in e for e in info.exports)
        assert any("update" in e for e in info.exports)
        assert any("delete" in e for e in info.exports)
        # private method — must be absent
        assert not any("validate" in e for e in info.exports)

    def test_deps_include_repository(self):
        adapter = get_adapter(".java")
        info = adapter.extract_info(self.FIXTURE, FIXTURES_DIR)
        assert any("UserRepository" in d for d in info.deps)

    def test_inject_header_preserves_package(self):
        adapter = get_adapter(".java")
        source = self.FIXTURE.read_text()
        result = adapter.inject_header(
            source, "UserService.java", "UserService", "none", "none", MODEL, TODAY
        )
        _assert_header_fields(result)
        assert "package com.example.app.services;" in result

    def test_idempotency(self):
        adapter = get_adapter(".java")
        _assert_idempotent(adapter, self.FIXTURE.read_text(), "UserService.java")

    def test_validator_accepts_annotated(self, tmp_path):
        adapter = get_adapter(".java")
        _assert_validator_accepts(tmp_path, adapter, self.FIXTURE.read_text(),
                                  "UserService", "UserService.java")


# ── Rust ──────────────────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Rust removed from registry (2026-04-18)")
class TestRustIntegration:
    FIXTURE = FIXTURES_DIR / "user_service.rs"

    def test_exports_pub_items(self):
        adapter = get_adapter(".rs")
        info = adapter.extract_info(self.FIXTURE, FIXTURES_DIR)
        assert info.parseable
        # Top-level pub items — captured by both tree-sitter and regex adapters
        assert "MAX_USERS_PER_PAGE" in info.exports
        assert "UserId" in info.exports
        assert "UserService" in info.exports
        assert "UserFilter" in info.exports
        assert "UserRepository" in info.exports
        # Private items — must be absent
        assert "internal_helper" not in info.exports
        assert not any("validate_user" in e for e in info.exports)

    def test_exports_impl_methods(self):
        """Tree-sitter adapter captures pub fn inside impl blocks as Type::method."""
        adapter = get_adapter(".rs")
        info = adapter.extract_info(self.FIXTURE, FIXTURES_DIR)
        # Tree-sitter captures impl methods; regex adapter does not
        # Use any() so the test passes with either adapter active
        has_new = any("new" in e for e in info.exports)
        has_get = any("get_user" in e for e in info.exports)
        # At minimum, UserService (struct) must be present — confirm baseline
        assert "UserService" in info.exports
        # If tree-sitter is active, impl methods appear — log for visibility
        if has_new and has_get:
            assert "UserService::new" in info.exports
            assert "UserService::get_user" in info.exports
            assert "UserService::create_user" in info.exports

    def test_inject_header_is_valid(self):
        adapter = get_adapter(".rs")
        source = self.FIXTURE.read_text()
        result = adapter.inject_header(
            source, "user_service.rs", "UserService", "none", "none", MODEL, TODAY
        )
        _assert_header_fields(result)
        assert "pub struct UserService" in result

    def test_idempotency(self):
        adapter = get_adapter(".rs")
        _assert_idempotent(adapter, self.FIXTURE.read_text(), "user_service.rs")

    def test_validator_accepts_annotated(self, tmp_path):
        adapter = get_adapter(".rs")
        _assert_validator_accepts(tmp_path, adapter, self.FIXTURE.read_text(),
                                  "UserService", "user_service.rs")


# ── C# ────────────────────────────────────────────────────────────────────────

@pytest.mark.skip(reason="C# removed from registry (2026-04-18)")
class TestCSharpIntegration:
    FIXTURE = FIXTURES_DIR / "UserService.cs"

    def test_exports_named_symbols(self):
        adapter = get_adapter(".cs")
        info = adapter.extract_info(self.FIXTURE, FIXTURES_DIR)
        assert info.parseable
        assert "UserService" in info.exports
        assert "IUserService" in info.exports
        assert any("GetAll" in e for e in info.exports)
        assert any("GetByIdAsync" in e for e in info.exports)
        assert any("CreateAsync" in e for e in info.exports)
        assert any("DeleteAsync" in e for e in info.exports)
        assert any("Count" in e for e in info.exports)
        # private method — must be absent
        assert not any("Validate" in e for e in info.exports)

    def test_deps_include_system_namespaces(self):
        adapter = get_adapter(".cs")
        info = adapter.extract_info(self.FIXTURE, FIXTURES_DIR)
        assert any("System" in d for d in info.deps)

    def test_inject_header_between_using_and_namespace(self):
        adapter = get_adapter(".cs")
        source = self.FIXTURE.read_text()
        result = adapter.inject_header(
            source, "UserService.cs", "UserService", "none", "none", MODEL, TODAY
        )
        _assert_header_fields(result)
        # using directives before namespace before class body
        assert "using System;" in result
        assert "namespace MyApp.Services" in result
        idx_using = result.index("using System;")
        idx_ns = result.index("namespace MyApp.Services")
        assert idx_using < idx_ns

    def test_idempotency(self):
        adapter = get_adapter(".cs")
        _assert_idempotent(adapter, self.FIXTURE.read_text(), "UserService.cs")

    def test_validator_accepts_annotated(self, tmp_path):
        adapter = get_adapter(".cs")
        _assert_validator_accepts(tmp_path, adapter, self.FIXTURE.read_text(),
                                  "UserService, IUserService", "UserService.cs")


# ── Ruby ──────────────────────────────────────────────────────────────────────

class TestRubyIntegration:
    FIXTURE = FIXTURES_DIR / "user_service.rb"

    def test_exports_named_symbols(self):
        adapter = get_adapter(".rb")
        info = adapter.extract_info(self.FIXTURE, FIXTURES_DIR)
        assert info.parseable
        assert "Services" in info.exports
        assert "UserService" in info.exports
        assert any("find_all" in e for e in info.exports)
        assert any("find_by_id" in e for e in info.exports)
        assert any("create" in e for e in info.exports)
        assert any("update" in e for e in info.exports)
        assert any("for_tenant" in e for e in info.exports)
        # private methods — must be absent
        assert not any("validate" in e for e in info.exports)
        assert not any("log_action" in e for e in info.exports)

    def test_deps_include_required_files(self):
        adapter = get_adapter(".rb")
        info = adapter.extract_info(self.FIXTURE, FIXTURES_DIR)
        assert any("models/user" in d for d in info.deps)
        assert any("logger" in d for d in info.deps)

    def test_inject_header_preserves_frozen_string_literal(self):
        adapter = get_adapter(".rb")
        source = self.FIXTURE.read_text()
        result = adapter.inject_header(
            source, "user_service.rb", "UserService", "none", "none", MODEL, TODAY
        )
        _assert_header_fields(result)
        # frozen_string_literal must remain as first line
        first_line = result.splitlines()[0]
        assert first_line == "# frozen_string_literal: true"

    def test_idempotency(self):
        adapter = get_adapter(".rb")
        _assert_idempotent(adapter, self.FIXTURE.read_text(), "user_service.rb")

    def test_validator_accepts_annotated(self, tmp_path):
        adapter = get_adapter(".rb")
        _assert_validator_accepts(tmp_path, adapter, self.FIXTURE.read_text(),
                                  "Services, UserService", "user_service.rb")


# ── Kotlin ────────────────────────────────────────────────────────────────────

class TestKotlinIntegration:
    FIXTURE = FIXTURES_DIR / "UserService.kt"

    def test_exports_named_symbols(self):
        adapter = get_adapter(".kt")
        info = adapter.extract_info(self.FIXTURE, FIXTURES_DIR)
        assert info.parseable
        assert "CreateUserRequest" in info.exports
        assert "UserService" in info.exports
        assert "UserServiceDefaults" in info.exports
        assert "MAX_PAGE_SIZE" in info.exports
        assert "formatUser" in info.exports
        # companion object fn — tree-sitter: 'UserService.create', regex: 'create'
        assert any("create" in e for e in info.exports)
        # object declaration fn — tree-sitter: 'UserServiceDefaults.defaultRepository',
        # regex: 'defaultRepository'
        assert any("defaultRepository" in e for e in info.exports)

    def test_inject_header_preserves_package(self):
        adapter = get_adapter(".kt")
        source = self.FIXTURE.read_text()
        result = adapter.inject_header(
            source, "UserService.kt", "UserService", "none", "none", MODEL, TODAY
        )
        _assert_header_fields(result)
        assert "package com.example.app.services" in result

    def test_idempotency(self):
        adapter = get_adapter(".kt")
        _assert_idempotent(adapter, self.FIXTURE.read_text(), "UserService.kt")

    def test_validator_accepts_annotated(self, tmp_path):
        adapter = get_adapter(".kt")
        _assert_validator_accepts(tmp_path, adapter, self.FIXTURE.read_text(),
                                  "UserService, UserServiceDefaults", "UserService.kt")


# ── CLI round-trip tests ──────────────────────────────────────────────────────

class TestCLIMultiLang:
    """One CLI round-trip test per language: copy fixture → codedna init --no-llm → verify."""

    def _run_and_verify(self, tmp_path: Path, fixture_name: str, ext: str) -> None:
        src = FIXTURES_DIR / fixture_name
        dst = tmp_path / fixture_name
        dst.write_text(src.read_text())

        rc, out, err = run_codedna(
            "init", str(tmp_path), "--no-llm",
            "--extensions", ext.lstrip("."),
        )
        assert rc == 0, f"codedna init failed (exit {rc}):\nstdout: {out}\nstderr: {err}"

        content = dst.read_text()
        for field in ("exports:", "used_by:", "rules:", "agent:"):
            assert field in content, f"{fixture_name} missing {field!r} after codedna init"

    def test_cli_typescript(self, tmp_path):
        self._run_and_verify(tmp_path, "UserService.ts", ".ts")

    def test_cli_go(self, tmp_path):
        self._run_and_verify(tmp_path, "user_service.go", ".go")

    def test_cli_php(self, tmp_path):
        self._run_and_verify(tmp_path, "UserController.php", ".php")

    def test_cli_java(self, tmp_path):
        self._run_and_verify(tmp_path, "UserService.java", ".java")

    @pytest.mark.skip(reason="Rust removed from registry (2026-04-18)")
    def test_cli_rust(self, tmp_path):
        self._run_and_verify(tmp_path, "user_service.rs", ".rs")

    @pytest.mark.skip(reason="C# removed from registry (2026-04-18)")
    def test_cli_csharp(self, tmp_path):
        self._run_and_verify(tmp_path, "UserService.cs", ".cs")

    def test_cli_ruby(self, tmp_path):
        self._run_and_verify(tmp_path, "user_service.rb", ".rb")

    def test_cli_kotlin(self, tmp_path):
        self._run_and_verify(tmp_path, "UserService.kt", ".kt")

    def test_cli_idempotent(self, tmp_path):
        """Running init twice on TypeScript must produce identical content."""
        src = FIXTURES_DIR / "UserService.ts"
        dst = tmp_path / "UserService.ts"
        dst.write_text(src.read_text())

        run_codedna("init", str(tmp_path), "--no-llm", "--extensions", "ts")
        content_first = dst.read_text()

        run_codedna("init", str(tmp_path), "--no-llm", "--extensions", "ts")
        content_second = dst.read_text()

        assert content_first == content_second, "codedna init is not idempotent on TypeScript"
