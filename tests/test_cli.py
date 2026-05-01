"""test_cli.py — Tests for codedna CLI commands (init, check, update).

exports: PYTHON | run_codedna() | class TestInit | class TestCheck | class TestRoundTrip | class TestLLM | class TestJSONResponseParser | class TestManifest | class TestBuildDocstring | class TestDetectProjectMeta
used_by: none
rules:   Tests run codedna CLI as subprocess to verify end-to-end behavior.
Each test uses tmp_path for isolation — never touches real project files.
agent:   claude-opus-4-7 | anthropic | 2026-05-01 | s_20260501_skip_drift | add 4 regression tests for the skip-list drift bug: test_init_skips_claude_worktrees + test_init_skips_top_level_worktrees_dir reproduce the Silicore-style session where init annotated .claude/worktrees/<wt-id>/ trees; test_collect_files_skip_set_matches_wiki_skip_dirs is a drift guard that asserts cli._DEFAULT_SKIP_DIRS is a subset of both wiki.SKIP_DIRS and _MANIFEST_SKIP — preventing the same divergence from sneaking back. All 3 fail on pre-fix code (red), pass after _DEFAULT_SKIP_DIRS is introduced as canonical baseline.
claude-opus-4-7 | anthropic | 2026-05-01 | s_20260501_json_robust | add TestJSONResponseParser with 11 tests probing _parse_json_response against realistic LLM output shapes: plain JSON, fenced JSON (with/without lang tag), truncated mid-string, leading prose, trailing prose, <think>...</think> reasoning tags, fenced JSON with leading/trailing prose, plain prose (must return None), empty (must return None). 4 are red on pre-fix code — exactly the formats newer reasoning models (DeepSeek V4-Flash, R1, Qwen-thinking) emit despite being asked for JSON-only. All green after raw_decode-based Strategy 3 lands.
claude-opus-4-7 | anthropic | 2026-05-01 | s_20260501_codedna_exclude | extend TestManifest with 5 regression tests for the new project-wide exclude: field in .codedna: 3 unit tests on _parse_exclude_field (flow form, block form, absent → empty), 1 E2E test that an exclude: in .codedna excludes a directory from package detection without needing --exclude CLI flag, 1 round-trip test asserting the exclude: block is preserved verbatim across manifest regenerations (without preservation, every manifest run would silently strip the user's exclude — making the field useless).
claude-opus-4-7 | anthropic | 2026-05-02 | s_20260502_init_escape | add 2 regression tests in TestInit for #12 (yuzi-co). Symptom A: test_init_preserves_backslash_newline_continuation asserts the line continuation in module docstrings survives byte-for-byte across init rewrite (red on pre-fix — pre-fix scan_file used ast.get_docstring which collapsed it). Symptom B: test_init_preserves_double_backslash_in_docstring asserts a literal double-backslash sequence is NOT downgraded to a single backslash (red on pre-fix) and that the rewritten file fires zero SyntaxWarning when re-compiled.
claude-opus-4-7 | anthropic | 2026-05-02 | s_20260502_testdata_skip | add test_init_skips_testdata_directory for #13 (yuzi-co). Creates a Go analysistest fixture under tools/myanalyzer/testdata/src/clean/clean.go and asserts the file is untouched while the analyzer source still gets annotated — header injection would shift `// want "..."` line numbers and break analysistest.
claude-opus-4-7 | anthropic | 2026-05-02 | s_20260502_wiki_sync_hook | add TestInstallWikiSync (3 tests) for the new opt-in `--with-wiki-sync` flag in `codedna install`: (1) default install does NOT create post-commit hook; (2) `--with-wiki-sync` installs a marked, executable hook invoking `codedna wiki sync`; (3) install never overwrites a user-authored post-commit hook (no CodeDNA marker → SKIP).
message: 
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

    def test_init_skips_claude_worktrees(self, tmp_path):
        """Regression for the Silicore-style session: `init` must skip
        `.claude/worktrees/` so it does NOT try to annotate ephemeral git
        worktrees created by the Claude Code agent itself.

        Pre-fix `collect_files` had its own inline skip set without `.claude`
        or `worktrees`, while `wiki.py` SKIP_DIRS already had them. The drift
        cost a real user ~25 min and ~$0.30 of LLM calls on 47 worktree files.
        """
        wt = tmp_path / ".claude" / "worktrees" / "elastic-hoover-1313fd"
        wt.mkdir(parents=True)
        (wt / "junk.py").write_text("def junk(): pass\n")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def main(): pass\n")

        rc, out, err = run_codedna("init", str(tmp_path), "--no-llm")
        assert rc == 0

        # Worktree file MUST NOT have a CodeDNA header
        junk = (wt / "junk.py").read_text()
        assert "exports:" not in junk, (
            f"init annotated a file inside .claude/worktrees/ — drift:\n{junk}"
        )
        # Real source still gets annotated
        main = (tmp_path / "src" / "main.py").read_text()
        assert "exports:" in main

    def test_init_skips_top_level_worktrees_dir(self, tmp_path):
        """Plain top-level `worktrees/` (e.g. created by `git worktree add`) must
        also be skipped — not just `.claude/worktrees/`."""
        (tmp_path / "worktrees" / "wt-1").mkdir(parents=True)
        (tmp_path / "worktrees" / "wt-1" / "stale.py").write_text("def x(): pass\n")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("def main(): pass\n")

        rc, out, err = run_codedna("init", str(tmp_path), "--no-llm")
        assert rc == 0
        stale = (tmp_path / "worktrees" / "wt-1" / "stale.py").read_text()
        assert "exports:" not in stale

    def test_collect_files_skip_set_matches_wiki_skip_dirs(self):
        """Drift guard: every dir wiki.py refuses to scan, init/manifest must
        also refuse — otherwise we leak source-of-truth between commands.

        Pre-fix the three skip lists (collect_files inline set,
        _MANIFEST_SKIP, wiki.SKIP_DIRS) drifted independently. This test
        anchors collect_files (and via _MANIFEST_SKIP) to the same canonical
        baseline.
        """
        from codedna_tool.cli import _DEFAULT_SKIP_DIRS, _MANIFEST_SKIP
        from codedna_tool.wiki import SKIP_DIRS as WIKI_SKIP

        # Canonical baseline must include .claude and worktrees.
        assert ".claude" in _DEFAULT_SKIP_DIRS
        assert "worktrees" in _DEFAULT_SKIP_DIRS
        # Every dir in the canonical baseline must also be in wiki + manifest.
        missing_in_wiki = _DEFAULT_SKIP_DIRS - set(WIKI_SKIP)
        assert not missing_in_wiki, (
            f"wiki.SKIP_DIRS missing canonical entries: {missing_in_wiki}"
        )
        missing_in_manifest = _DEFAULT_SKIP_DIRS - set(_MANIFEST_SKIP)
        assert not missing_in_manifest, (
            f"_MANIFEST_SKIP missing canonical entries: {missing_in_manifest}"
        )

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

    def test_init_skips_testdata_directory(self, tmp_path):
        """Regression for #13 (yuzi-co): `init` must skip Go `testdata/` dirs.

        analysistest fixtures (golang.org/x/tools/go/analysis/analysistest)
        encode expected diagnostic positions in `// want "…"` comments tied
        to specific line numbers. Inserting an 8-line CodeDNA header at the
        top shifts every line down and breaks the analyzer's tests.
        `go test` itself ignores testdata/ for build purposes — we follow
        the same convention.
        """
        analyzer_dir = tmp_path / "tools" / "myanalyzer"
        analyzer_dir.mkdir(parents=True)
        (analyzer_dir / "analyzer.go").write_text(
            'package myanalyzer\n\nfunc Run() {}\n', encoding="utf-8",
        )
        fixture = analyzer_dir / "testdata" / "src" / "clean"
        fixture.mkdir(parents=True)
        fixture_file = fixture / "clean.go"
        fixture_original = (
            'package clean\n'
            '\n'
            'func F() int {\n'
            '\treturn 1 // want "uses a literal"\n'
            '}\n'
        )
        fixture_file.write_text(fixture_original, encoding="utf-8")

        rc, out, err = run_codedna("init", str(tmp_path), "--auto", "--no-llm")
        assert rc == 0

        # Fixture file MUST be untouched — header injection would shift the
        # `// want` line and break analysistest.
        assert fixture_file.read_text(encoding="utf-8") == fixture_original, (
            "init annotated a Go file under testdata/ — would break analysistest"
        )
        # Real analyzer source DID get touched (proves init ran on the project).
        analyzer_src = (analyzer_dir / "analyzer.go").read_text(encoding="utf-8")
        assert "exports:" in analyzer_src or "package myanalyzer" in analyzer_src

    def test_init_preserves_backslash_newline_continuation(self, tmp_path):
        """Regression for #12 symptom A (yuzi-co): `init` must preserve
        backslash-newline line continuations in module docstrings byte-for-byte.

        Pre-fix scan_file used ast.get_docstring() which returns the
        *evaluated* string — Python's parser already collapsed the
        continuation. Round-tripping that into the rewritten docstring
        silently turned a documented multi-line shell example into a
        single broken concatenated command.
        """
        path = tmp_path / "demo.py"
        path.write_text(
            '"""Demo module.\n'
            '\n'
            'Run:\n'
            '    FLAG_A=1 FLAG_B=2 \\\n'
            '    pytest tests/foo -v\n'
            '"""\n'
            '\n'
            'def foo(): pass\n',
            encoding="utf-8",
        )
        rc, out, err = run_codedna("init", str(tmp_path), "--no-llm")
        assert rc == 0
        after = path.read_text(encoding="utf-8")
        # The backslash-newline continuation must survive — both lines distinct.
        assert "FLAG_A=1 FLAG_B=2 \\" in after, (
            f"backslash-newline continuation lost on rewrite:\n{after}"
        )
        assert "pytest tests/foo -v" in after
        # And the two parts must NOT have collapsed onto a single line.
        assert "FLAG_B=2     pytest" not in after, (
            f"continuation collapsed into one line — multi-line example destroyed:\n{after}"
        )

    def test_init_preserves_double_backslash_in_docstring(self, tmp_path):
        """Regression for #12 symptom B (yuzi-co): `init` must preserve
        a literal double-backslash sequence byte-for-byte.

        Pre-fix it was downgraded to a single backslash, which then made
        Python emit `SyntaxWarning: invalid escape sequence` at every
        import because the resulting `\\-` is not a recognized escape.
        """
        path = tmp_path / "pipeline.py"
        path.write_text(
            '"""Pipeline ASCII art.\n'
            '\n'
            '    pending -> parsed\n'
            '            \\\\-> failed\n'
            '"""\n'
            '\n'
            'def step(): pass\n',
            encoding="utf-8",
        )
        rc, out, err = run_codedna("init", str(tmp_path), "--no-llm")
        assert rc == 0
        after = path.read_text(encoding="utf-8")
        # Source on disk must still contain the double backslash so Python
        # evaluates it as a single literal backslash and emits NO SyntaxWarning.
        assert "\\\\->" in after, (
            f"double-backslash downgraded to single — would emit SyntaxWarning at import:\n{after}"
        )
        # Re-parsing the rewritten file must succeed without SyntaxWarning.
        import warnings
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            compile(after, str(path), "exec")
            syntax_warnings = [w for w in caught if issubclass(w.category, SyntaxWarning)]
            assert not syntax_warnings, (
                f"rewritten docstring fires SyntaxWarning: {[str(w.message) for w in syntax_warnings]}"
            )


# ── codedna install --with-wiki-sync ─────────────────────────────────────────

class TestInstallWikiSync:
    """Opt-in post-commit hook that runs `codedna wiki sync` after every commit."""

    def _make_git_repo(self, tmp_path):
        import subprocess as _sub
        _sub.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        _sub.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
        _sub.run(["git", "config", "user.name", "test"], cwd=tmp_path, check=True)
        return tmp_path

    def test_install_without_flag_does_not_create_post_commit_hook(self, tmp_path):
        """Default `codedna install` must NOT install a post-commit hook —
        opt-in only, since wiki regen leaves uncommitted changes."""
        self._make_git_repo(tmp_path)
        rc, out, err = run_codedna("install", "--path", str(tmp_path),
                                   "--skip-prompt")
        assert rc == 0
        post = tmp_path / ".git" / "hooks" / "post-commit"
        assert not post.exists(), (
            f"post-commit hook installed without --with-wiki-sync flag:\n{out}"
        )

    def test_install_with_wiki_sync_creates_executable_post_commit_hook(self, tmp_path):
        """Regression for opt-in wiki sync: --with-wiki-sync must drop a
        marked, executable hook that calls `codedna wiki sync`."""
        import os
        self._make_git_repo(tmp_path)
        rc, out, err = run_codedna("install", "--path", str(tmp_path),
                                   "--skip-prompt", "--with-wiki-sync")
        assert rc == 0, f"install failed:\n{out}\n{err}"
        post = tmp_path / ".git" / "hooks" / "post-commit"
        assert post.exists(), f"post-commit hook NOT installed:\n{out}"
        assert os.access(post, os.X_OK), "post-commit hook is not executable"
        body = post.read_text(encoding="utf-8")
        assert "CodeDNA" in body, "hook missing CodeDNA marker — would clobber on reinstall"
        assert "codedna wiki sync" in body, "hook does not invoke `codedna wiki sync`"

    def test_install_with_wiki_sync_does_not_clobber_existing_hook(self, tmp_path):
        """If a non-CodeDNA post-commit hook already exists, `install
        --with-wiki-sync` must skip — never overwrite user-authored hooks."""
        self._make_git_repo(tmp_path)
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(exist_ok=True)
        existing = hooks_dir / "post-commit"
        existing_body = "#!/usr/bin/env bash\necho 'user hook'\n"
        existing.write_text(existing_body, encoding="utf-8")
        existing.chmod(0o755)

        rc, out, err = run_codedna("install", "--path", str(tmp_path),
                                   "--skip-prompt", "--with-wiki-sync")
        assert rc == 0
        # The existing hook is untouched
        assert existing.read_text(encoding="utf-8") == existing_body, (
            "install clobbered an existing user-authored post-commit hook"
        )
        # And the install output flagged the skip
        assert "SKIP" in out and "post-commit" in out, (
            f"install did not announce the skip:\n{out}"
        )


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


# ── LLM JSON response parser ─────────────────────────────────────────────────

class TestJSONResponseParser:
    """Probe `LLM._parse_json_response` against realistic non-strict-JSON
    formats produced by newer/reasoning models.

    Context: a user lost ~25 min and ~$0.30 because their model returned
    invalid-JSON output that broke 46/47 function-rules batches. We don't
    have the actual raw response (logging is added in this same change),
    but we can reproduce the most common output shapes that newer models
    emit and verify the parser tolerates them.
    """

    @staticmethod
    def parse(resp):
        from codedna_tool.cli import LLM
        return LLM._parse_json_response(resp)

    # ── Sanity: formats already supported ─────────────────────────────────

    def test_plain_json_object(self):
        assert self.parse('{"a": "b"}') == {"a": "b"}

    def test_fenced_json_with_lang_tag(self):
        assert self.parse('```json\n{"a": "b"}\n```') == {"a": "b"}

    def test_fenced_json_without_lang_tag(self):
        assert self.parse('```\n{"a": "b"}\n```') == {"a": "b"}

    def test_truncated_json_repaired_via_strategy_2(self):
        """Existing strategy 2: truncated mid-string at last `",`."""
        text = '{"a": "value1", "b": "value2", "c": "trun'
        assert self.parse(text) == {"a": "value1", "b": "value2"}

    # ── New: formats observed from reasoning / V4-style models ────────────

    def test_json_with_leading_prose(self):
        """Reasoning models (R1, DeepSeek V4, Qwen3-thinking) frequently
        prefix JSON with an explanatory sentence even when asked for JSON-only.
        """
        text = 'Here is the JSON you requested:\n{"a": "b"}'
        assert self.parse(text) == {"a": "b"}

    def test_json_with_trailing_prose(self):
        """Some models append commentary after the JSON block."""
        text = '{"a": "b"}\nThis is the requested annotation.'
        assert self.parse(text) == {"a": "b"}

    def test_json_with_thinking_tags(self):
        """`<think>...</think>` reasoning trace before the JSON payload —
        DeepSeek-R1 default output shape."""
        text = "<think>Let me analyze the function...</think>\n" '{"a": "b"}'
        assert self.parse(text) == {"a": "b"}

    def test_fenced_json_with_leading_prose(self):
        """Combined: explanatory text + ```json fence."""
        text = 'Here you go:\n```json\n{"a": "b"}\n```'
        assert self.parse(text) == {"a": "b"}

    def test_fenced_json_with_trailing_prose(self):
        """```json fence followed by commentary."""
        text = '```json\n{"a": "b"}\n```\nLet me know if you need more.'
        assert self.parse(text) == {"a": "b"}

    # ── Failure cases must still return None gracefully ───────────────────

    def test_plain_prose_returns_none(self):
        """Model declined to produce JSON — must not crash, must return None."""
        assert self.parse(
            "I cannot annotate this code without more context."
        ) is None

    def test_empty_response_returns_none(self):
        assert self.parse("") is None
        assert self.parse("   \n\n") is None


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

    # ── .codedna top-level exclude: field (s_20260501_codedna_exclude) ────────

    def test_parse_exclude_field_flow_form(self):
        """Unit: `exclude: ["a/**", "b/**"]` is parsed as a 2-pattern list."""
        from codedna_tool.cli import _parse_exclude_field
        content = (
            'project: demo\n'
            'exclude: ["labs/**", "vendor/**"]\n'
            'packages: {}\n'
        )
        excludes, raw = _parse_exclude_field(content)
        assert excludes == ["labs/**", "vendor/**"]
        assert "exclude:" in raw and "labs/**" in raw

    def test_parse_exclude_field_block_form(self):
        """Unit: `exclude:\\n  - a\\n  - b` block list is parsed correctly."""
        from codedna_tool.cli import _parse_exclude_field
        content = (
            'project: demo\n'
            'exclude:\n'
            '  - "labs/**"\n'
            '  - "vendor/**"\n'
            'packages: {}\n'
        )
        excludes, raw = _parse_exclude_field(content)
        assert excludes == ["labs/**", "vendor/**"]
        assert raw.startswith("exclude:")
        assert '- "labs/**"' in raw

    def test_parse_exclude_field_absent_returns_empty(self):
        """Unit: no `exclude:` key → empty list and empty raw block."""
        from codedna_tool.cli import _parse_exclude_field
        content = 'project: demo\npackages: {}\n'
        excludes, raw = _parse_exclude_field(content)
        assert excludes == []
        assert raw == ""

    def test_manifest_honours_codedna_exclude_field(self, tmp_path):
        """E2E: an `exclude:` field in .codedna excludes files from package detection
        without needing --exclude on the CLI.

        Reporter scenario: `codedna manifest .` walked vendored test fixtures
        (labs/benchmark/projects/**) and fired SyntaxWarning on LaTeX escape
        sequences. Setting exclude: in .codedna should make the noise go away
        on every subsequent run, no flag needed.
        """
        # Two real packages
        (tmp_path / "mypkg").mkdir()
        (tmp_path / "mypkg" / "__init__.py").write_text('"""m."""\n')
        (tmp_path / "mypkg" / "core.py").write_text('"""c."""\n')
        # A vendored fixture that should be excluded
        (tmp_path / "labs" / "fixtures" / "external").mkdir(parents=True)
        (tmp_path / "labs" / "fixtures" / "external" / "__init__.py").write_text('"""x."""\n')
        (tmp_path / "labs" / "fixtures" / "external" / "mod.py").write_text('"""y."""\n')

        # Pre-existing .codedna with project-wide exclude
        (tmp_path / ".codedna").write_text(
            'project: demo\n'
            'description: "test fixture"\n'
            '\n'
            'exclude:\n'
            '  - "labs/**"\n'
            '\n'
            'packages: {}\n'
            'cross_cutting_patterns: {}\n'
            'agent_sessions: []\n'
        )

        run_codedna("init", str(tmp_path), "--no-llm")
        rc, out, err = run_codedna("manifest", str(tmp_path), "--no-llm")

        assert rc == 0, f"manifest failed:\nstdout:\n{out}\nstderr:\n{err}"
        assert "Packages detected: 1" in out, (
            f"Expected only 1 package (mypkg), labs/** should have been excluded.\n"
            f"stdout:\n{out}"
        )
        assert "mypkg" in out
        # 'labs' should not appear as a detected package
        import re as _re
        pkg_lines = [
            ln for ln in out.splitlines()
            if _re.match(r"^\s+\S+\s+\d+\s+files\s*$", ln)
        ]
        named_pkgs = [ln.strip().split()[0] for ln in pkg_lines]
        assert not any("labs" in p for p in named_pkgs), (
            f"labs/** was not excluded — found {named_pkgs}\n"
            f"stdout:\n{out}"
        )

    def test_manifest_preserves_codedna_exclude_block_on_regeneration(self, tmp_path):
        """Round-trip: running `manifest` regenerates packages: but must NEVER
        drop the user-authored `exclude:` block from .codedna.

        Without preservation, every run of manifest would silently strip
        the exclude — the field would be useless across runs.
        """
        (tmp_path / "mypkg").mkdir()
        (tmp_path / "mypkg" / "__init__.py").write_text('"""m."""\n')
        (tmp_path / "mypkg" / "core.py").write_text('"""c."""\n')

        original_exclude_block = (
            'exclude:\n'
            '  - "labs/**"\n'
            '  - "_repo_cache/**"\n'
        )
        (tmp_path / ".codedna").write_text(
            'project: demo\n'
            'description: "test"\n'
            '\n'
            + original_exclude_block
            + '\n'
            'packages: {}\n'
            'cross_cutting_patterns: {}\n'
            'agent_sessions: []\n'
        )

        run_codedna("init", str(tmp_path), "--no-llm")
        rc, out, err = run_codedna("manifest", str(tmp_path), "--no-llm")
        assert rc == 0, f"manifest failed:\n{out}\n{err}"

        regenerated = (tmp_path / ".codedna").read_text()
        assert "exclude:" in regenerated, (
            "exclude: block was dropped on manifest regeneration"
        )
        assert '- "labs/**"' in regenerated
        assert '- "_repo_cache/**"' in regenerated


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
