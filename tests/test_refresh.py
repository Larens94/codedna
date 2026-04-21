"""test_refresh.py — Tests for codedna refresh command and relative import resolution.

exports: PYTHON | run_codedna() | class TestRefresh | class TestRelativeImports | class TestReducedHeader | class TestHasCodednaHeader | class TestRelatedField | class TestWikiField
used_by: none
rules:   Tests verify that refresh updates exports/used_by without touching rules/agent/message.
Tests also verify Python relative imports (from .module) are resolved correctly.
agent:   claude-opus-4-6 | anthropic | 2026-04-15 | s_20260415_003 | initial refresh + relative import tests
claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_002 | updated TestReducedHeader: all languages now emit full headers (exports+used_by+rules+agent); updated validator test to require full PHP header
claude-sonnet-4-6 | anthropic | 2026-04-18 | s_20260418_l0meta | remove .rs from TestReducedHeader ext list — Rust removed from registry
claude-opus-4-6 | anthropic | 2026-04-21 | s_20260421_wiki | add TestWikiField — 4 tests for the experimental wiki: pointer field (parse, rebuild, refresh preservation, opt-in absence)
claude-sonnet-4-6 | anthropic | 2026-04-22 | s_20260422_refresh | add TestRefreshPreservesLLMAnnotations — 3 regression tests for bug where refresh degraded real annotations to "none" on PHP config + Python files with no AST importers
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PYTHON = sys.executable


def _has_treesitter_php() -> bool:
    try:
        import tree_sitter_php  # noqa: F401
        return True
    except ImportError:
        return False


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


class TestCrossLanguageRefresh:
    @pytest.mark.skipif(
        not _has_treesitter_php(),
        reason="tree-sitter-php not installed",
    )
    def test_refresh_php_used_by(self, tmp_path):
        """PHP file importing a class should populate used_by on the target."""
        # Create a mini PHP project with PSR-4 layout
        app = tmp_path / "app" / "Models"
        app.mkdir(parents=True)
        ctrl = tmp_path / "app" / "Http" / "Controllers"
        ctrl.mkdir(parents=True)

        # Model file
        (app / "User.php").write_text(
            "<?php\n"
            "// User.php — User model.\n//\n"
            "// exports: User\n"
            "// used_by: none\n"
            "// rules:   none\n"
            "// agent:   test | anthropic | 2026-04-18 | s_001 | test\n"
            "\nnamespace App\\Models;\n\nclass User {}\n"
        )

        # Controller that imports User
        (ctrl / "UserController.php").write_text(
            "<?php\n"
            "// UserController.php — handles users.\n//\n"
            "// exports: UserController\n"
            "// used_by: none\n"
            "// rules:   none\n"
            "// agent:   test | anthropic | 2026-04-18 | s_001 | test\n"
            "\nnamespace App\\Http\\Controllers;\n\n"
            "use App\\Models\\User;\n\n"
            "class UserController {\n"
            "    public function show() { return new User(); }\n"
            "}\n"
        )

        # Run refresh
        rc, out, err = run_codedna("refresh", str(tmp_path))
        assert rc == 0, f"refresh failed: {err}"

        # User.php should now have used_by mentioning UserController
        user_content = (app / "User.php").read_text()
        assert "UserController" in user_content or "Controllers" in user_content, \
            f"used_by not populated in User.php:\n{user_content}"

    @pytest.mark.skipif(
        not _has_treesitter_php(),
        reason="tree-sitter-php not installed",
    )
    def test_refresh_php_preserves_rules(self, tmp_path):
        """Refresh must preserve rules: and agent: in PHP headers."""
        (tmp_path / "Foo.php").write_text(
            "<?php\n"
            "// Foo.php — test.\n//\n"
            "// exports: Foo\n"
            "// used_by: none\n"
            "// rules:   NEVER delete — soft delete only\n"
            "// agent:   my-model | anthropic | 2026-04-18 | s_001 | important\n"
            "\nclass Foo {\n"
            "    public function bar() {}\n"
            "}\n"
        )
        rc, out, err = run_codedna("refresh", str(tmp_path))
        assert rc == 0
        content = (tmp_path / "Foo.php").read_text()
        assert "NEVER delete" in content, "rules: was modified"
        assert "my-model" in content, "agent: was modified"
        assert "important" in content, "agent narrative was modified"


class TestRefreshPreservesLLMAnnotations:
    """Regression tests for the bug where refresh degraded real annotations to 'none'.

    Root cause: tree-sitter/AST returning empty results (e.g. unresolved @/ aliases
    in TSX, or PHP config files with no structural importers) caused _fmt_exports /
    _fmt_used_by to emit "none", overwriting LLM-annotated values.

    Fix: if new value is "none" and old value is real, keep the old value.
    """

    def test_refresh_preserves_llm_exports_when_parser_finds_nothing(self, tmp_path):
        """If tree-sitter can't resolve exports, keep the existing LLM-annotated value."""
        (tmp_path / "config.php").write_text(
            "<?php\n"
            "// config.php — App configuration.\n//\n"
            "// exports: config array for app.name, app.env, app.debug\n"
            "// used_by: Laravel framework via config('app.*')\n"
            "// rules:   none\n"
            "// agent:   my-model | anthropic | 2026-04-22 | s_001 | LLM annotated\n"
            "\nreturn ['name' => 'App', 'env' => 'production'];\n"
        )
        rc, out, _ = run_codedna("refresh", str(tmp_path))
        assert rc == 0
        content = (tmp_path / "config.php").read_text()
        assert "config array for app.name" in content, \
            f"exports: was overwritten with 'none':\n{content}"
        assert "Laravel framework" in content, \
            f"used_by: was overwritten with 'none':\n{content}"

    def test_refresh_preserves_python_llm_exports_when_no_imports_found(self, tmp_path):
        """If AST finds no importers for a Python file, keep the existing used_by value."""
        (tmp_path / "constants.py").write_text(
            '"""constants.py — Shared constants.\n\n'
            'exports: MAX_RETRIES | TIMEOUT_SECONDS | DEFAULT_LOCALE\n'
            'used_by: services/billing.py → charge | services/email.py → send\n'
            'rules:   none\n'
            'agent:   my-model | anthropic | 2026-04-22 | s_001 | LLM annotated\n'
            '"""\n\n'
            'MAX_RETRIES = 3\nTIMEOUT_SECONDS = 30\nDEFAULT_LOCALE = "en"\n'
        )
        # No files import constants.py in this tmp dir — AST would compute used_by: none
        rc, out, _ = run_codedna("refresh", str(tmp_path))
        assert rc == 0
        content = (tmp_path / "constants.py").read_text()
        assert "services/billing.py" in content, \
            f"used_by: was overwritten with 'none':\n{content}"

    def test_refresh_still_updates_when_parser_finds_real_data(self, tmp_path):
        """When AST does find importers, used_by SHOULD be updated normally."""
        (tmp_path / "utils.py").write_text(
            '"""utils.py — Utilities.\n\n'
            'exports: helper()\n'
            'used_by: old_caller.py → old_fn\n'
            'rules:   none\n'
            'agent:   my-model | anthropic | 2026-04-22 | s_001 | test\n'
            '"""\n\ndef helper(): return "ok"\n'
        )
        (tmp_path / "app.py").write_text('from utils import helper\ndef main(): return helper()\n')
        rc, out, _ = run_codedna("refresh", str(tmp_path))
        assert rc == 0
        content = (tmp_path / "utils.py").read_text()
        assert "app.py" in content, "used_by was not updated when AST found a real importer"
        assert "old_caller.py" not in content, "stale used_by value was not replaced"


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


class TestRelatedField:
    """Tests for the related: field (v0.9) — semantic cross-cutting links."""

    def test_parser_recognizes_related(self):
        from codedna_tool.cli import _parse_existing_docstring

        doc = '"""test.py — test.\n\nexports: foo()\nused_by: bar.py → baz\nrelated: other.py — shares logic\nrules:   none\nagent:   test | anthropic | 2026-04-20 | s_001 | test\n"""'
        fields = _parse_existing_docstring(doc)
        assert "related" in fields
        assert "shares logic" in fields["related"]

    def test_rebuild_preserves_related(self):
        from codedna_tool.cli import _parse_existing_docstring, _rebuild_docstring

        doc = '"""test.py — test.\n\nexports: foo()\nused_by: bar.py → baz\nrelated: other.py — shares logic\n         another.py — same pattern\nrules:   none\nagent:   test | anthropic | 2026-04-20 | s_001 | test\n"""'
        fields = _parse_existing_docstring(doc)
        rebuilt = _rebuild_docstring(fields, "new_foo()", "new_bar.py → new_baz")
        assert "related:" in rebuilt
        assert "shares logic" in rebuilt
        assert "same pattern" in rebuilt

    def test_refresh_preserves_related(self, tmp_path):
        """codedna refresh must not strip related: when updating used_by."""
        (tmp_path / "utils.py").write_text(
            '"""utils.py — utils.\n\n'
            'exports: helper()\n'
            'used_by: none\n'
            'related: other.py — shares algorithm\n'
            'rules:   none\n'
            'agent:   test | anthropic | 2026-04-20 | s_001 | test\n'
            '"""\n\ndef helper(): return "ok"\n'
        )
        (tmp_path / "app.py").write_text('from utils import helper\ndef main(): return helper()\n')
        run_codedna("init", str(tmp_path), "--no-llm")
        run_codedna("refresh", str(tmp_path))

        utils = (tmp_path / "utils.py").read_text()
        assert "related: other.py — shares algorithm" in utils
        assert "app.py" in utils  # used_by was updated

    def test_has_codedna_header_detects_related_only(self):
        from codedna_tool.languages.go import GoAdapter
        adapter = GoAdapter()

        src = "// main.go — entry.\n//\n// related: other.go — shares logic\n\npackage main\n"
        assert adapter.has_codedna_header(src)


class TestWikiField:
    """Tests for the wiki: field (experimental v0.9) — Karpathy LLM-wiki pointer."""

    def test_parser_recognizes_wiki(self):
        from codedna_tool.cli import _parse_existing_docstring

        doc = (
            '"""test.py — test.\n\n'
            'exports: foo()\n'
            'used_by: bar.py → baz\n'
            'wiki:    docs/wiki/test.md\n'
            'rules:   none\n'
            'agent:   test | anthropic | 2026-04-21 | s_001 | test\n'
            '"""'
        )
        fields = _parse_existing_docstring(doc)
        assert "wiki" in fields
        assert "docs/wiki/test.md" in fields["wiki"]

    def test_rebuild_preserves_wiki(self):
        from codedna_tool.cli import _parse_existing_docstring, _rebuild_docstring

        doc = (
            '"""test.py — test.\n\n'
            'exports: foo()\n'
            'used_by: bar.py → baz\n'
            'related: other.py — shares logic\n'
            'wiki:    docs/wiki/test.md\n'
            'rules:   none\n'
            'agent:   test | anthropic | 2026-04-21 | s_001 | test\n'
            '"""'
        )
        fields = _parse_existing_docstring(doc)
        rebuilt = _rebuild_docstring(fields, "new_foo()", "new_bar.py → new_baz")
        assert "wiki:" in rebuilt
        assert "docs/wiki/test.md" in rebuilt
        # Order check: wiki must come after related, before rules
        assert rebuilt.index("related:") < rebuilt.index("wiki:") < rebuilt.index("rules:")

    def test_refresh_preserves_wiki(self, tmp_path):
        """codedna refresh must not strip wiki: when updating used_by."""
        (tmp_path / "utils.py").write_text(
            '"""utils.py — utils.\n\n'
            'exports: helper()\n'
            'used_by: none\n'
            'wiki:    docs/wiki/utils.md\n'
            'rules:   none\n'
            'agent:   test | anthropic | 2026-04-21 | s_001 | test\n'
            '"""\n\ndef helper(): return "ok"\n'
        )
        (tmp_path / "app.py").write_text('from utils import helper\ndef main(): return helper()\n')
        run_codedna("init", str(tmp_path), "--no-llm")
        run_codedna("refresh", str(tmp_path))

        utils = (tmp_path / "utils.py").read_text()
        assert "wiki:    docs/wiki/utils.md" in utils
        assert "app.py" in utils  # used_by was updated

    def test_wiki_is_optional(self):
        """Missing wiki: must never trigger an error — it's opt-in."""
        from codedna_tool.cli import _parse_existing_docstring

        doc = (
            '"""test.py — test.\n\n'
            'exports: foo()\n'
            'used_by: none\n'
            'rules:   none\n'
            'agent:   test | anthropic | 2026-04-21 | s_001 | test\n'
            '"""'
        )
        fields = _parse_existing_docstring(doc)
        assert "wiki" not in fields  # absent, not empty
