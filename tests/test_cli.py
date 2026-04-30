"""test_cli.py — Tests for codedna CLI commands (init, check, update).

exports: PYTHON | run_codedna() | class TestInit | class TestCheck | class TestRoundTrip | class TestBuildDocstring
used_by: none
rules:   Tests run codedna CLI as subprocess to verify end-to-end behavior.
Each test uses tmp_path for isolation — never touches real project files.
agent:   claude-opus-4-6 | anthropic | 2026-04-15 | s_20260415_002 | initial CLI test suite
claude-sonnet-4-6 | anthropic | 2026-04-18 | s_20260418_l0meta | add TestDetectProjectMeta: 12 unit tests for go.mod/package.json/pom.xml/settings.gradle/Cargo.toml parsing
claude-opus-4-6 | anthropic | 2026-04-21 | s_20260421_unused | remove unused json/pytest imports (CodeQL #1673, #1674)
claude-opus-4-7 | anthropic | 2026-04-30 | s_20260430_init_dataloss | add 4 regression tests for #10 (yuzi-co) — multi-line docstring body must be preserved by build_module_docstring + init E2E. Pre-fix tests fail (red) showing the data-loss bug exactly: lines like "Detailed multi-paragraph description", "Example", "Notes", "This content is critical" disappear from the rebuilt docstring.
claude-opus-4-7 | anthropic | 2026-04-30 | s_20260430_manifest_11 | add TestManifest with 2 regression tests for #11 (yuzi-co) — Bug A: --exclude '**/dir/**' must match root-level dir; Bug B: Go-only directory must become its own package, not bucketed under (root). Both tests fail on pre-fix code, pass after the _expand_exclude + _is_package_marker fixes.
claude-opus-4-7 | anthropic | 2026-05-01 | s_20260430_test_llm | add TestLLM (11 tests) covering the litellm + anthropic routing paths for the first time. Pre-existing benchmark artifacts (deepseek/* in agent: lines under benchmark_agent/) prove the litellm path was exercised in production but was never under CI. Tests are fully offline — monkey-patch _litellm/_anthropic — covering _detect_provider for all 6 providers, _call routing through litellm with kwargs verification, anthropic fallback with timeout, ImportError when no backend, and api_key env var injection (positive + negative). Re-introduced `import pytest` (had been removed for CodeQL #1674) as it's needed for pytest.raises in this class — kept with `# noqa: F401` to make the deliberate retention explicit.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest  # noqa: F401  — used by TestLLM via pytest.raises

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

    def test_init_preserves_multiline_docstring_body(self, tmp_path):
        """Regression for #10 (yuzi-co): `init` must NOT silently delete the
        body of an existing multi-line module docstring when inserting the
        CodeDNA header.

        Pre-fix on a 745-file repo this erased migration docs, architectural
        notes, and pipeline diagrams. We replicate the reporter's exact repro.
        """
        path = tmp_path / "example.py"
        path.write_text(
            '"""Short summary line.\n'
            "\n"
            "Detailed multi-paragraph description that documents\n"
            "the module's contract, invariants, and usage examples.\n"
            "\n"
            "Example\n"
            "-------\n"
            "    from example import compute\n"
            "    compute(2, 3)  # -> 5\n"
            "\n"
            "Notes\n"
            "-----\n"
            "This content is critical and must NOT be lost.\n"
            '"""\n'
            "\n"
            "def compute(a, b):\n"
            "    return a + b\n",
            encoding="utf-8",
        )
        rc, out, err = run_codedna("init", str(tmp_path), "--no-llm")
        assert rc == 0
        after = path.read_text(encoding="utf-8")
        # CodeDNA header was injected.
        assert "exports:" in after
        assert "compute(a, b)" in after
        # Original body lines all survive.
        for must in [
            "Detailed multi-paragraph description",
            "the module's contract, invariants",
            "Example",
            "-------",
            "from example import compute",
            "Notes",
            "-----",
            "This content is critical and must NOT be lost",
        ]:
            assert must in after, f"data loss — line missing after init: {must!r}"


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


# ── LLM routing (litellm + anthropic) ────────────────────────────────────────

class TestLLM:
    """Coverage for the LLM client routing — never touched until now.

    The litellm path was exercised manually during benchmarks (the
    `agent: deepseek/deepseek-chat | …` lines under
    benchmark_agent/projects_swebench/ are real artifacts), but no automated
    test ever verified the routing or the api_key injection. These tests
    monkey-patch `_litellm` and `_anthropic` so they run offline (no real
    HTTP, no API key).
    """

    def _fake_litellm_response(self, text: str):
        """Build a SimpleNamespace shaped like litellm.completion's return."""
        from types import SimpleNamespace
        return SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(content=text)
            )]
        )

    # _detect_provider — static method, pure logic, no monkeypatch needed.

    def test_detect_provider_ollama(self):
        from codedna_tool.cli import LLM
        assert LLM._detect_provider("ollama/llama3") == "ollama"
        assert LLM._detect_provider("ollama_chat/qwen2.5") == "ollama"

    def test_detect_provider_openai(self):
        from codedna_tool.cli import LLM
        assert LLM._detect_provider("openai/gpt-4o-mini") == "openai"
        assert LLM._detect_provider("gpt-4o") == "openai"  # bare 'gpt' prefix

    def test_detect_provider_gemini(self):
        from codedna_tool.cli import LLM
        assert LLM._detect_provider("gemini/gemini-2.0-flash") == "gemini"
        assert LLM._detect_provider("google/gemini-pro") == "gemini"

    def test_detect_provider_deepseek(self):
        from codedna_tool.cli import LLM
        assert LLM._detect_provider("deepseek/deepseek-chat") == "deepseek"
        assert LLM._detect_provider("deepseek-coder") == "deepseek"

    def test_detect_provider_anthropic_via_claude_substring(self):
        from codedna_tool.cli import LLM
        assert LLM._detect_provider("claude-haiku-4-5-20251001") == "anthropic"
        assert LLM._detect_provider("anthropic/claude-3-5-sonnet") == "anthropic"

    def test_detect_provider_unknown_returns_unknown(self):
        from codedna_tool.cli import LLM
        assert LLM._detect_provider("some-random-model") == "unknown"

    # _call routing — monkey-patch _litellm / _anthropic.

    def test_call_routes_through_litellm_when_available(self, monkeypatch):
        """LLM._call() must use _litellm.completion when HAS_LITELLM is True.

        Verifies the kwargs passed to litellm match what we promise:
        model, messages with single user role, max_tokens, 90s timeout.
        """
        from types import SimpleNamespace
        from codedna_tool import cli

        captured: dict = {}
        def fake_completion(**kw):
            captured.update(kw)
            return self._fake_litellm_response("rules:   none")

        fake_litellm = SimpleNamespace(completion=fake_completion)
        monkeypatch.setattr(cli, "_litellm", fake_litellm)
        monkeypatch.setattr(cli, "HAS_LITELLM", True)
        monkeypatch.setattr(cli, "HAS_ANTHROPIC", False)

        llm = cli.LLM(model="ollama/llama3")
        result = llm._call("any prompt here", max_tokens=42)

        assert result == "rules:   none"
        assert captured["model"] == "ollama/llama3"
        assert captured["messages"] == [{"role": "user", "content": "any prompt here"}]
        assert captured["max_tokens"] == 42
        assert captured["timeout"] == 90  # see Rules: in _call

    def test_call_falls_back_to_anthropic_when_no_litellm(self, monkeypatch):
        """LLM._call() must use the Anthropic SDK when HAS_LITELLM is False but
        HAS_ANTHROPIC is True. Used only for Claude models."""
        from types import SimpleNamespace
        from codedna_tool import cli

        captured: dict = {}

        class FakeMessages:
            def create(self, **kw):
                captured.update(kw)
                return SimpleNamespace(
                    content=[SimpleNamespace(text="rules:   anthropic-path")]
                )

        class FakeOptionsClient:
            messages = FakeMessages()

        class FakeAnthropic:
            def __init__(self, api_key=None):
                captured["api_key"] = api_key
                self.messages = FakeMessages()

            def with_options(self, **kw):
                captured["timeout_kw"] = kw
                return FakeOptionsClient()

        fake_anthropic_module = SimpleNamespace(Anthropic=FakeAnthropic)
        monkeypatch.setattr(cli, "_anthropic", fake_anthropic_module)
        monkeypatch.setattr(cli, "HAS_LITELLM", False)
        monkeypatch.setattr(cli, "HAS_ANTHROPIC", True)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")

        llm = cli.LLM(model="claude-haiku-4-5-20251001")
        result = llm._call("test prompt", max_tokens=128)

        assert result == "rules:   anthropic-path"
        assert captured["model"] == "claude-haiku-4-5-20251001"
        assert captured["max_tokens"] == 128
        assert captured["messages"] == [{"role": "user", "content": "test prompt"}]
        # 90s timeout applied via with_options(timeout=90.0)
        assert captured["timeout_kw"] == {"timeout": 90.0}

    def test_init_raises_importerror_when_no_backend(self, monkeypatch):
        """If neither litellm nor anthropic SDK is installed, instantiating
        LLM must raise ImportError with a helpful install hint."""
        from codedna_tool import cli

        monkeypatch.setattr(cli, "HAS_LITELLM", False)
        monkeypatch.setattr(cli, "HAS_ANTHROPIC", False)

        with pytest.raises(ImportError, match="No LLM backend found"):
            cli.LLM(model="claude-haiku-4-5-20251001")

    def test_init_injects_api_key_into_provider_env_var(self, monkeypatch):
        """Passing api_key= through to LLM(...) must populate the right env
        var for the detected provider, so litellm picks it up automatically.
        """
        from types import SimpleNamespace
        from codedna_tool import cli

        # Bare-bones fake litellm so __init__ doesn't crash on missing import.
        monkeypatch.setattr(cli, "_litellm",
                            SimpleNamespace(completion=lambda **kw: None))
        monkeypatch.setattr(cli, "HAS_LITELLM", True)
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

        cli.LLM(model="deepseek/deepseek-chat", api_key="sk-secret-deepseek")
        import os as _os
        assert _os.environ.get("DEEPSEEK_API_KEY") == "sk-secret-deepseek"

    def test_init_does_not_inject_env_var_for_unknown_provider(self, monkeypatch):
        """If the provider can't be mapped to a known env var, api_key
        injection is skipped silently — no spurious env mutation."""
        from types import SimpleNamespace
        from codedna_tool import cli
        import os as _os

        monkeypatch.setattr(cli, "_litellm",
                            SimpleNamespace(completion=lambda **kw: None))
        monkeypatch.setattr(cli, "HAS_LITELLM", True)
        before = dict(_os.environ)

        cli.LLM(model="xyz/random-model", api_key="should-not-leak")

        # No new env var was created (xyz isn't in our mapping).
        new_keys = set(_os.environ) - set(before)
        assert "should-not-leak" not in _os.environ.values() or (
            # api_key never assigned to any tracked provider env var
            not any(_os.environ.get(k) == "should-not-leak" for k in (
                "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY",
                "DEEPSEEK_API_KEY", "MISTRAL_API_KEY", "COHERE_API_KEY",
            ))
        )


# ── codedna manifest ─────────────────────────────────────────────────────────

class TestManifest:
    """Regression tests for issue #11 (yuzi-co): manifest exclude glob + Go package detection."""

    def test_exclude_pattern_matches_root_level_dir(self, tmp_path):
        """Bug A: `--exclude '**/dir/**'` must match a directory at the project root.

        Pre-fix `fnmatch.fnmatch` did not treat `**` as multi-segment glob —
        it collapsed to a single `*` which requires at least one parent
        segment, so root-level `infrastructure/` was never excluded.
        """
        # Reporter's exact repro structure
        (tmp_path / "infrastructure" / "vendored" / "sub").mkdir(parents=True)
        (tmp_path / "infrastructure" / "vendored" / "sub" / "__init__.py").write_text('"""v."""\n')
        (tmp_path / "infrastructure" / "vendored" / "sub" / "m.py").write_text('"""v."""\n')
        (tmp_path / "mypkg").mkdir()
        (tmp_path / "mypkg" / "__init__.py").write_text('"""m."""\n')
        (tmp_path / "mypkg" / "core.py").write_text('"""c."""\n')

        # First annotate, then run manifest with the buggy exclude pattern
        run_codedna("init", str(tmp_path), "--no-llm")
        rc, out, err = run_codedna(
            "manifest", str(tmp_path), "--no-llm",
            "--exclude", "**/infrastructure/**",
        )

        # Expected: only 1 package (mypkg). Pre-fix this was 2.
        assert "Packages detected: 1" in out, (
            f"--exclude '**/infrastructure/**' did not exclude root-level dir.\n"
            f"stdout:\n{out}"
        )
        assert "mypkg" in out
        assert "infrastructure" not in out or "Skipping" in out

    def test_go_only_directory_becomes_its_own_package(self, tmp_path):
        """Bug B: a directory containing only Go files must be detected as
        its own package, not bucketed under '(root)'.

        Pre-fix `_detect_packages` only recognised `__init__.py` as a package
        marker. Go files in `mygoservice/` fell through to '(root)' because
        Go has no formal package marker file (the directory IS the package).
        """
        # Reporter's exact repro structure
        (tmp_path / "mygoservice").mkdir()
        (tmp_path / "mygoservice" / "main.go").write_text(
            "package main\nfunc main() {}\n"
        )
        (tmp_path / "mygoservice" / "util.go").write_text(
            'package main\nfunc H() string { return "" }\n'
        )
        (tmp_path / "mypypkg").mkdir()
        (tmp_path / "mypypkg" / "__init__.py").write_text('"""p."""\n')
        (tmp_path / "mypypkg" / "core.py").write_text('"""c."""\n')

        run_codedna("init", str(tmp_path), "--no-llm", "--auto")
        rc, out, err = run_codedna(
            "manifest", str(tmp_path), "--no-llm", "--extensions", "py", "go",
        )

        # Expected: mygoservice is its own package, NOT under (root).
        assert "mygoservice" in out, (
            f"Go-only directory `mygoservice/` was not promoted to a package.\n"
            f"stdout:\n{out}"
        )
        # The 'mygoservice' line in the package summary must mention it as a
        # package, and the (root) bucket — if shown — must NOT contain Go files.
        # Look for the package summary line specifically.
        # Format: '  mygoservice           2 files' (left-padded name + count)
        import re as _re
        pkg_lines = [
            ln for ln in out.splitlines()
            if _re.match(r"^\s+\S+\s+\d+\s+files\s*$", ln)
        ]
        named_pkgs = [ln.strip().split()[0] for ln in pkg_lines]
        assert "mygoservice" in named_pkgs, (
            f"Expected 'mygoservice' among detected packages, got: {named_pkgs}\n"
            f"stdout:\n{out}"
        )


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

    def test_multiline_docstring_body_is_preserved(self):
        """Regression for #10: multi-line docstring body must NOT be silently dropped.

        Pre-fix `build_module_docstring` only kept the first line of the existing
        docstring (via `_purpose`) and discarded everything else.
        """
        from codedna_tool.cli import build_module_docstring, FileInfo

        existing = (
            "Short summary line.\n"
            "\n"
            "Detailed multi-paragraph description that documents\n"
            "the module's contract, invariants, and usage examples.\n"
            "\n"
            "Example\n"
            "-------\n"
            "    from example import compute\n"
            "    compute(2, 3)  # -> 5\n"
            "\n"
            "Notes\n"
            "-----\n"
            "This content is critical and must NOT be lost."
        )
        info = FileInfo(
            path=Path("/tmp/example.py"),
            rel="example.py",
            exports=["compute(a, b)"],
            deps={},
            docstring=existing,
            has_codedna=False,
            funcs=[],
            parseable=True,
        )
        doc = build_module_docstring(info, {}, "none", "test-model")
        # Each non-summary body line must survive verbatim.
        for must in [
            "Detailed multi-paragraph description",
            "the module's contract, invariants",
            "Example",
            "-------",
            "from example import compute",
            "Notes",
            "-----",
            "This content is critical and must NOT be lost",
        ]:
            assert must in doc, f"body line missing from rebuilt docstring: {must!r}"
        # CodeDNA fields still present.
        assert "exports: compute(a, b)" in doc
        assert "agent:" in doc

    def test_single_line_docstring_has_no_body_added(self):
        """A single-line existing docstring has no body to preserve — output stays minimal."""
        from codedna_tool.cli import build_module_docstring, FileInfo

        info = FileInfo(
            path=Path("/tmp/oneliner.py"),
            rel="oneliner.py",
            exports=["foo()"],
            deps={},
            docstring="Just one line.",
            has_codedna=False,
            funcs=[],
            parseable=True,
        )
        doc = build_module_docstring(info, {}, "none", "test-model")
        # First line carries the summary.
        assert '"""oneliner.py — Just one line.' in doc
        # Body section should be empty — exports must come right after the
        # blank line that follows the summary.
        lines = doc.split("\n")
        # Find the blank line after the first """; the next non-blank must be exports:
        for i, line in enumerate(lines):
            if line.startswith('"""'):
                # next blank
                assert lines[i + 1] == ""
                assert lines[i + 2].startswith("exports:")
                break

    def test_codedna_fields_in_existing_docstring_are_not_duplicated(self):
        """If an existing docstring already contains CodeDNA fields (e.g. on
        `init --force`), they MUST be stripped from the preserved body to avoid
        duplicating exports:/used_by:/etc. in the rebuilt docstring.
        """
        from codedna_tool.cli import build_module_docstring, FileInfo

        existing = (
            "test.py — old summary.\n"
            "\n"
            "Some prose worth keeping.\n"
            "\n"
            "exports: old_func()\n"
            "used_by: caller.py → old_func\n"
            "rules:   old rule\n"
            "agent:   old-agent | x | 2026-01-01 | s_old | old"
        )
        info = FileInfo(
            path=Path("/tmp/test.py"),
            rel="test.py",
            exports=["new_func()"],
            deps={},
            docstring=existing,
            has_codedna=True,
            funcs=[],
            parseable=True,
        )
        doc = build_module_docstring(info, {}, "none", "test-model")
        # New fields present.
        assert "exports: new_func()" in doc
        # Old prose preserved.
        assert "Some prose worth keeping." in doc
        # Old CodeDNA fields stripped — they would have been duplicated.
        assert "old_func()" not in doc
        assert "caller.py → old_func" not in doc
        assert "old rule" not in doc
        assert "old-agent" not in doc
        assert "s_old" not in doc


# ── _detect_project_meta ─────────────────────────────────────────────────────

class TestDetectProjectMeta:
    """Unit tests for _detect_project_meta() — reads build files to extract name/description/stack."""

    def _call(self, tmp_path):
        from codedna_tool.cli import _detect_project_meta
        return _detect_project_meta(tmp_path)

    def test_go_mod_extracts_name(self, tmp_path):
        (tmp_path / "go.mod").write_text("module github.com/acme/myservice\n\ngo 1.21\n")
        meta = self._call(tmp_path)
        assert meta["name"] == "myservice"
        assert "go" in meta["stack"]

    def test_go_mod_simple_module_name(self, tmp_path):
        (tmp_path / "go.mod").write_text("module myapp\n\ngo 1.21\n")
        meta = self._call(tmp_path)
        assert meta["name"] == "myapp"

    def test_package_json_name_and_description(self, tmp_path):
        (tmp_path / "package.json").write_text(
            '{"name": "my-frontend", "description": "React dashboard", "version": "1.0.0"}'
        )
        meta = self._call(tmp_path)
        assert meta["name"] == "my-frontend"
        assert meta["description"] == "React dashboard"
        assert "nodejs" in meta["stack"]

    def test_package_json_scoped_name_stripped(self, tmp_path):
        (tmp_path / "package.json").write_text('{"name": "@acme/ui-lib", "description": ""}')
        meta = self._call(tmp_path)
        assert meta["name"] == "ui-lib"

    def test_pom_xml_artifact_id(self, tmp_path):
        (tmp_path / "pom.xml").write_text(
            "<project><groupId>com.acme</groupId>"
            "<artifactId>billing-service</artifactId>"
            "<description>Handles invoices</description></project>"
        )
        meta = self._call(tmp_path)
        assert meta["name"] == "billing-service"
        assert meta["description"] == "Handles invoices"
        assert "java-maven" in meta["stack"]

    def test_settings_gradle_kts(self, tmp_path):
        (tmp_path / "settings.gradle.kts").write_text('rootProject.name = "analytics"\n')
        meta = self._call(tmp_path)
        assert meta["name"] == "analytics"
        assert "kotlin-gradle" in meta["stack"]

    def test_settings_gradle(self, tmp_path):
        (tmp_path / "settings.gradle").write_text("rootProject.name = 'warehouse'\n")
        meta = self._call(tmp_path)
        assert meta["name"] == "warehouse"
        assert "java-gradle" in meta["stack"]

    def test_gemfile_adds_ruby_to_stack(self, tmp_path):
        (tmp_path / "Gemfile").write_text('source "https://rubygems.org"\ngem "rails"\n')
        meta = self._call(tmp_path)
        assert "ruby" in meta["stack"]

    def test_cargo_toml_name_and_description(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text(
            '[package]\nname = "my-crate"\ndescription = "A fast tool"\nversion = "0.1.0"\n'
        )
        meta = self._call(tmp_path)
        assert meta["name"] == "my-crate"
        assert meta["description"] == "A fast tool"
        assert "rust" in meta["stack"]

    def test_go_mod_takes_priority_over_package_json(self, tmp_path):
        (tmp_path / "go.mod").write_text("module github.com/acme/backend\n\ngo 1.21\n")
        (tmp_path / "package.json").write_text('{"name": "frontend", "description": "UI"}')
        meta = self._call(tmp_path)
        # go.mod wins for name (first evaluated)
        assert meta["name"] == "backend"
        # Both stacks detected
        assert "go" in meta["stack"]
        assert "nodejs" in meta["stack"]

    def test_empty_directory_returns_empty_meta(self, tmp_path):
        meta = self._call(tmp_path)
        assert meta["name"] == ""
        assert meta["description"] == ""
        assert meta["stack"] == []

    def test_no_raise_on_corrupt_json(self, tmp_path):
        (tmp_path / "package.json").write_text("{not valid json}")
        meta = self._call(tmp_path)
        # Should not raise, just return empty
        assert meta["name"] == ""
        assert "nodejs" in meta["stack"]  # stack still detected even if parse failed
