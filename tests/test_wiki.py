"""test_wiki.py — Tests for codedna_tool.wiki (Obsidian vault bootstrap + project wiki).

exports: class TestWikilink | class TestSlug | class TestPageMarkdown | class TestBuildVault | class TestAgentNotesPreservation | class TestProjectWiki | class TestWikiFieldTarget
used_by: none
rules:   Tests must never require network or LLM access.
         Vault generation uses tmp_path only — never touches the real repo.
agent:   claude-opus-4-6 | anthropic | 2026-04-21 | s_20260421_wiki | initial test suite for wiki vault generator — wikilinks, slug, markdown rendering, AGENT NOTES preservation
claude-opus-4-6 | anthropic | 2026-04-21 | s_20260421_wiki2 | add TestProjectWiki — 4 tests for render_project_wiki + build_project_wiki (workingfm template integration)
claude-opus-4-6 | anthropic | 2026-04-21 | s_20260421_wiki4 | update tests for nested vault layout — slug preserves folders, wikilinks use `path|display` format, build_vault mirrors source hierarchy
claude-opus-4-6 | anthropic | 2026-04-21 | s_20260421_wiki5 | add TestWikiFieldTarget + page render tests for the wiki: opt-in field — covers callout layout and missing-field behavior
"""

from __future__ import annotations

from pathlib import Path

import pytest

from codedna_tool.wiki import (
    _AGENT_NOTES_MARKER,
    _AUTO_HEADER,
    _PROJECT_WIKI_MARKER_AGENT,
    _read_project_name,
    _slug_for_rel,
    _wiki_field_target,
    _wikilink,
    build_project_wiki,
    render_project_wiki,
    _page_markdown,
    _preserve_agent_notes,
    build_wiki_vault,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def write_annotated(project: Path, rel: str, exports: str, used_by: str,
                    rules: str = "none", related: str | None = None,
                    wiki: str | None = None) -> Path:
    """Write a minimal annotated Python file. Returns its path."""
    path = project / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f'"""{Path(rel).name} — test module.',
        "",
        f"exports: {exports}",
        f"used_by: {used_by}",
    ]
    if related:
        lines.append(f"related: {related}")
    if wiki:
        lines.append(f"wiki:    {wiki}")
    lines.extend([
        f"rules:   {rules}",
        "agent:   test | anthropic | 2026-04-21 | s_001 | initial",
        '"""',
        "",
        "def placeholder(): pass",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


class TestSlug:
    def test_slug_strips_extension_preserves_folders(self):
        assert _slug_for_rel("foo/bar.py") == "foo/bar"

    def test_slug_deterministic(self):
        assert _slug_for_rel("a/b/c.py") == _slug_for_rel("a/b/c.py")

    def test_slug_handles_compound_blade_php(self):
        assert _slug_for_rel("resources/views/show.blade.php") == "resources/views/show"

    def test_slug_handles_nested_paths(self):
        assert _slug_for_rel("deep/nested/path.py") == "deep/nested/path"


class TestWikilink:
    def test_wikilink_format(self):
        link = _wikilink("foo/bar.py")
        assert link.startswith("[[")
        assert link.endswith("]]")
        assert "foo/bar" in link  # nested target (without .py)
        assert "|foo/bar.py]]" in link  # display keeps original path

    def test_wikilink_extracts_path_from_arrow_entry(self):
        """used_by entries like 'foo.py → bar' should strip after the arrow."""
        link = _wikilink("foo.py → some_symbol")
        assert "[[foo|foo.py]]" in link
        assert "some_symbol" not in link

    def test_wikilink_extracts_path_from_dash_entry(self):
        """related entries like 'foo.py — note' should strip after the dash."""
        link = _wikilink("foo.py — shares logic")
        assert "[[foo|foo.py]]" in link
        assert "shares logic" not in link


class TestPageMarkdown:
    def test_page_has_auto_header(self):
        fields = {"first_line": "test — test.", "exports": "exports: foo()",
                  "used_by": "used_by: none", "rules": "rules:   none",
                  "agent": "agent:   m | p | 2026-04-21 | s_001 | init"}
        page = _page_markdown("foo.py", fields)
        assert page.startswith(_AUTO_HEADER)

    def test_page_has_agent_notes_marker(self):
        fields = {"first_line": "test — test.", "exports": "exports: foo()",
                  "used_by": "used_by: none", "rules": "rules:   none",
                  "agent": "agent:   m | p | 2026-04-21 | s_001 | init"}
        page = _page_markdown("foo.py", fields)
        assert _AGENT_NOTES_MARKER in page

    def test_page_uses_wikilinks_for_used_by(self):
        fields = {"first_line": "test — test.", "exports": "exports: foo()",
                  "used_by": "used_by: app.py → main",
                  "rules": "rules:   none",
                  "agent": "agent:   m | p | 2026-04-21 | s_001 | init"}
        page = _page_markdown("foo.py", fields)
        assert "[[app|app.py]]" in page

    def test_page_uses_wikilinks_for_related(self):
        fields = {"first_line": "test — test.", "exports": "exports: foo()",
                  "used_by": "used_by: none",
                  "related": "related: other.py — shares pattern",
                  "rules": "rules:   none",
                  "agent": "agent:   m | p | 2026-04-21 | s_001 | init"}
        page = _page_markdown("foo.py", fields)
        assert "[[other|other.py]]" in page
        assert "shares pattern" in page

    def test_page_filters_non_agent_lines_from_agent_field(self):
        """Parser sometimes folds trailing prose into agent: — filter by | separator."""
        fields = {"first_line": "test — test.", "exports": "exports: foo()",
                  "used_by": "used_by: none", "rules": "rules:   none",
                  "agent": ("agent:   m | p | 2026-04-21 | s_001 | real entry\n"
                            "this is trailing prose no pipe")}
        page = _page_markdown("foo.py", fields)
        assert "real entry" in page
        assert "trailing prose" not in page

    def test_page_renders_wiki_field_as_callout(self):
        """When wiki: is present, render a clickable [[wikilink]] to the curated page."""
        fields = {"first_line": "test — test.", "exports": "exports: foo()",
                  "used_by": "used_by: none",
                  "wiki": "wiki: docs/wiki/cli.md",
                  "rules": "rules:   none",
                  "agent": "agent:   m | p | 2026-04-21 | s_001 | init"}
        page = _page_markdown("foo.py", fields)
        assert "📖 Extended documentation" in page
        assert "[[cli|docs/wiki/cli.md]]" in page
        assert "Read it **before editing**" in page

    def test_page_skips_wiki_section_when_field_absent(self):
        """If wiki: is not in the fields, the section must not appear."""
        fields = {"first_line": "test — test.", "exports": "exports: foo()",
                  "used_by": "used_by: none", "rules": "rules:   none",
                  "agent": "agent:   m | p | 2026-04-21 | s_001 | init"}
        page = _page_markdown("foo.py", fields)
        assert "Extended documentation" not in page


class TestWikiFieldTarget:
    def test_strips_vault_prefix_and_extension(self):
        assert _wiki_field_target("docs/wiki/cli.md") == "cli"

    def test_preserves_nested_path(self):
        assert _wiki_field_target("docs/wiki/codedna_tool/cli.md") == "codedna_tool/cli"

    def test_returns_empty_when_not_markdown(self):
        """Non-.md paths are an invalid wiki: value — skip rendering."""
        assert _wiki_field_target("docs/wiki/cli.txt") == ""

    def test_handles_value_without_vault_prefix(self):
        """If the field uses a path not starting with docs/wiki/, still strip .md."""
        assert _wiki_field_target("other/place/foo.md") == "other/place/foo"


class TestBuildVault:
    def test_generates_one_page_per_annotated_file(self, tmp_path):
        write_annotated(tmp_path, "src/a.py", "a()", "none")
        write_annotated(tmp_path, "src/b.py", "b()", "src/a.py → a")
        out = tmp_path / "vault"
        n = build_wiki_vault(tmp_path, out, extensions=[".py"])
        assert n == 2
        assert (out / "src" / "a.md").exists()
        assert (out / "src" / "b.md").exists()

    def test_vault_mirrors_source_hierarchy(self, tmp_path):
        write_annotated(tmp_path, "deep/nested/file.py", "f()", "none")
        out = tmp_path / "vault"
        build_wiki_vault(tmp_path, out, extensions=[".py"])
        assert (out / "deep" / "nested" / "file.md").exists()
        # Hierarchy mirrors source layout
        assert (out / "deep" / "nested").is_dir()

    def test_index_and_log_are_generated(self, tmp_path):
        write_annotated(tmp_path, "a.py", "a()", "none")
        out = tmp_path / "vault"
        build_wiki_vault(tmp_path, out, extensions=[".py"])
        assert (out / "README.md").exists()
        assert (out / "log.md").exists()

    def test_skips_files_without_codedna(self, tmp_path):
        (tmp_path / "plain.py").write_text("def foo(): pass\n")
        out = tmp_path / "vault"
        n = build_wiki_vault(tmp_path, out, extensions=[".py"])
        assert n == 0
        # Index still generated
        assert (out / "README.md").exists()


class TestAgentNotesPreservation:
    def test_agent_notes_survive_rerun(self, tmp_path):
        write_annotated(tmp_path, "a.py", "a()", "none")
        out = tmp_path / "vault"
        build_wiki_vault(tmp_path, out, extensions=[".py"])

        page_path = out / "a.md"
        original = page_path.read_text(encoding="utf-8")
        # Append agent notes below the marker
        augmented = original + "\n## My note\n\nThis is a durable observation.\n"
        page_path.write_text(augmented, encoding="utf-8")

        # Regenerate — the augmented note must survive
        build_wiki_vault(tmp_path, out, extensions=[".py"])
        final = page_path.read_text(encoding="utf-8")
        assert "This is a durable observation." in final
        assert "My note" in final

    def test_preserve_returns_empty_when_no_marker(self):
        assert _preserve_agent_notes("no marker here") == ""

    def test_preserve_returns_everything_from_marker(self):
        text = f"auto content\n{_AGENT_NOTES_MARKER}\nmy notes\nmore"
        preserved = _preserve_agent_notes(text)
        assert preserved.startswith(_AGENT_NOTES_MARKER)
        assert "my notes" in preserved
        assert "auto content" not in preserved


class TestProjectWiki:
    """Tests for the project-level narrative wiki (codedna wiki sync).
    Template adapted from @workingfm PR #2 — see wiki.py header comment.
    """

    def test_project_name_from_codedna(self, tmp_path):
        (tmp_path / ".codedna").write_text('project: "myproject"\n')
        assert _read_project_name(tmp_path) == "myproject"

    def test_project_name_fallback_to_dirname(self, tmp_path):
        assert _read_project_name(tmp_path) == tmp_path.name

    def test_render_contains_seven_sections(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()
        page = render_project_wiki("myproject", tmp_path)
        for section in ["Identity", "How this wiki relates to L0", "Semantic topology",
                        "Operational workflows", "Testing and validation model",
                        "Hotspots and likely drift", "Refresh protocol"]:
            assert f"## {section}" in page, f"missing section: {section}"

    def test_render_lists_top_level_dirs(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()
        (tmp_path / "__pycache__").mkdir()  # must be skipped
        page = render_project_wiki("proj", tmp_path)
        assert "`src/`" in page
        assert "`tests/`" in page
        assert "`__pycache__/`" not in page

    def test_build_writes_file_and_preserves_agent_notes(self, tmp_path):
        (tmp_path / ".codedna").write_text('project: "proj"\n')
        out = tmp_path / "docs" / "codedna-wiki.md"
        build_project_wiki(tmp_path, out)
        assert out.exists()

        # Append curated note
        original = out.read_text(encoding="utf-8")
        augmented = original + "\n## Curated\n\nDurable human note.\n"
        out.write_text(augmented, encoding="utf-8")

        # Regenerate
        build_project_wiki(tmp_path, out)
        final = out.read_text(encoding="utf-8")
        assert "Durable human note." in final
        assert _PROJECT_WIKI_MARKER_AGENT in final

    def test_render_has_workingfm_attribution(self, tmp_path):
        """Attribution comment must remain visible for credit + origin."""
        page = render_project_wiki("proj", tmp_path)
        assert "@workingfm" in page
        assert "PR #2" in page
