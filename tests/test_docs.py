"""test_docs.py — Guards public documentation against stale product claims.

exports: ROOT | test_public_docs_share_canonical_product_facts() | test_agent_templates_use_current_workflow() | test_key_markdown_local_links_resolve()
used_by: none
related: tests/test_cli.py — validates the commands documented here
rules:   exported module constants must be listed; keep assertions limited to stable product contracts, not editorial wording
agent:   gpt-5 | openai | 2026-08-21 | s_20260821_docs_consistency | added documentation drift guards
message: "update these contracts only when language counts, protocol version, or canonical commands intentionally change"
"""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    """Read a repository document as UTF-8.

    Rules: paths must remain repository-relative so the checks work in every clone.
    """
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_public_docs_share_canonical_product_facts() -> None:
    """Keep version and language-support claims aligned across public entry points.

    Rules: fail on obsolete claims that materially misrepresent released support.
    """
    for relative_path in ("README.md", "README-it.md", "codedna-plugin/README.md"):
        text = _read(relative_path)
        assert "languages-9" not in text
        assert "Supports 9 languages" not in text

    spec = _read("SPEC.md")
    assert "**Protocol version:** 0.9" in spec
    assert "0.9 (proposed)" not in spec
    assert "C/C++" not in spec

    languages = _read("docs/languages.md")
    assert "11 programming languages" in languages
    assert "27 registered extensions" in languages
    assert "7 template families" in languages


def test_agent_templates_use_current_workflow() -> None:
    """Ensure installable agent instructions use the safe canonical workflow.

    Rules: structural mode must be the default example and sessions must use the atomic writer.
    """
    for relative_path in ("integrations/AGENTS.md", "integrations/CLAUDE.md"):
        text = _read(relative_path)
        assert "codedna init . --no-llm" in text
        assert "codedna session append" in text
        assert "annotates every .py file" not in text
        assert "Cost: ~$1–3" not in text

    quickstart = _read("QUICKSTART.md")
    assert "codedna install --path . --tools codex --no-wiki-sync" in quickstart
    assert "curl installer remains available as a prompt-only fallback" in quickstart


def test_key_markdown_local_links_resolve() -> None:
    """Verify repository-relative links in maintained entry-point documents.

    Rules: ignore web URLs and anchors; only local filesystem targets are provable here.
    """
    relative_paths = (
        "README.md",
        "README-it.md",
        "QUICKSTART.md",
        "CONTRIBUTING.md",
        "integrations/README.md",
        "codedna-plugin/README.md",
        "docs/languages.md",
    )
    for relative_path in relative_paths:
        path = ROOT / relative_path
        for target in re.findall(r"(?<!!)\[[^]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            target = target.split()[0].strip("<>")
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            local_target = target.split("#", 1)[0]
            if local_target:
                assert (path.parent / local_target).exists(), f"{relative_path}: missing {target}"
