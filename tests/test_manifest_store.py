"""test_manifest_store.py — Regression tests for concurrent .codedna session persistence.

exports: test_default_retention_keeps_exactly_latest_five(tmp_path) | test_configurable_retention(tmp_path) | test_invalid_retention_uses_default() | test_legacy_multiline_and_block_arrays_are_normalized() | test_custom_metadata_and_top_level_comments_survive() | test_permissions_are_preserved(tmp_path) | test_concurrent_appends_do_not_lose_entries(tmp_path) | test_prune_override_and_yaml_safe_output(tmp_path) | test_section_regeneration_preserves_comments_and_metadata_after_sessions() | test_atomic_replace_failure_preserves_original_and_removes_temp(tmp_path, monkeypatch)
used_by: none
related: tests/test_cli.py — CLI integration coverage
rules:   Tests must use temporary manifests and never mutate the repository .codedna.
agent:   gpt-5 | openai | 2026-08-20 | s_20260820_sessions | added retention, legacy, atomicity, permission, and concurrency coverage
message: "Canonical JSON scalars are deliberately parsed as valid YAML by PyYAML."
gpt-5 | openai | 2026-08-20 | s_20260820_hardening | prove replace failure preserves original content and removes temporary files
"""

from __future__ import annotations

import concurrent.futures
import os

from codedna_tool.manifest_store import (
    atomic_write_text,
    append_session,
    parse_agent_sessions,
    prune_sessions,
    read_max_agent_sessions,
    replace_agent_sessions,
    replace_top_level_section,
)


def _session(index: int) -> dict[str, object]:
    return {
        "agent": f"agent-{index}",
        "provider": "openai",
        "date": "2026-08-20",
        "session_id": f"s-{index}",
        "task": f"task {index}",
        "changed": [f"file-{index}.py"],
        "visited": ["README.md"],
        "message": f'quote " slash \\ newline\n{index}',
    }


def test_default_retention_keeps_exactly_latest_five(tmp_path):
    path = tmp_path / ".codedna"
    path.write_text("project: demo\nagent_sessions: []\n")
    for index in range(6):
        append_session(path, _session(index))
    sessions = parse_agent_sessions(path.read_text())
    assert [item["session_id"] for item in sessions] == ["s-1", "s-2", "s-3", "s-4", "s-5"]


def test_configurable_retention(tmp_path):
    path = tmp_path / ".codedna"
    path.write_text("project: demo\nmax_agent_sessions: 2\nagent_sessions: []\n")
    for index in range(4):
        append_session(path, _session(index))
    assert [item["session_id"] for item in parse_agent_sessions(path.read_text())] == ["s-2", "s-3"]


def test_invalid_retention_uses_default():
    assert read_max_agent_sessions("max_agent_sessions: nope\n") == 5
    assert read_max_agent_sessions("max_agent_sessions: 0\n") == 5


def test_legacy_multiline_and_block_arrays_are_normalized():
    legacy = """project: demo
agent_sessions:
  - agent: legacy
    changed:
      - "a.py"
      - 'b.py'
    message: >
      first line
      regex \\w+
      test-first: preserve this colon line
      --extensions must remain prose
metadata_after: yes
"""
    sessions = parse_agent_sessions(legacy)
    rendered = replace_agent_sessions(legacy, sessions)
    assert sessions[0]["changed"] == ["a.py", "b.py"]
    assert "test-first: preserve this colon line" in sessions[0]["message"]
    assert "--extensions must remain prose" in sessions[0]["message"]
    assert "metadata_after: yes" in rendered
    assert parse_agent_sessions(rendered) == sessions


def test_custom_metadata_and_top_level_comments_survive():
    original = "# human comment\nproject: demo\ncustom: value\nagent_sessions: []\nafter: true\n"
    rendered = replace_agent_sessions(original, [_session(1)])
    assert rendered.startswith("# human comment\nproject: demo\ncustom: value\n")
    assert rendered.endswith("after: true\n")


def test_permissions_are_preserved(tmp_path):
    path = tmp_path / ".codedna"
    path.write_text("project: demo\nagent_sessions: []\n")
    path.chmod(0o640)
    append_session(path, _session(1))
    assert path.stat().st_mode & 0o777 == 0o640


def test_concurrent_appends_do_not_lose_entries(tmp_path):
    path = tmp_path / ".codedna"
    path.write_text("project: demo\nmax_agent_sessions: 20\nagent_sessions: []\n")
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(lambda index: append_session(path, _session(index)), range(12)))
    sessions = parse_agent_sessions(path.read_text())
    assert len(sessions) == 12
    assert {item["session_id"] for item in sessions} == {f"s-{index}" for index in range(12)}


def test_prune_override_and_yaml_safe_output(tmp_path):
    path = tmp_path / ".codedna"
    path.write_text(replace_agent_sessions("project: demo\n", [_session(i) for i in range(4)]))
    prune_sessions(path, 2)
    content = path.read_text()
    assert [item["session_id"] for item in parse_agent_sessions(content)] == ["s-2", "s-3"]
    assert os.path.exists(path)


def test_section_regeneration_preserves_comments_and_metadata_after_sessions():
    current = """# keep
project: demo
packages:
  old/:
    purpose: "old"
agent_sessions: []
custom_after: "keep me"
"""
    generated = """project: demo
packages:
  new/:
    purpose: "new"
cross_cutting_patterns: {}
agent_sessions: []
"""
    merged = replace_top_level_section(current, generated, "packages")
    assert "# keep" in merged
    assert "new/:" in merged
    assert "old/:" not in merged
    assert 'custom_after: "keep me"' in merged


def test_atomic_replace_failure_preserves_original_and_removes_temp(tmp_path, monkeypatch):
    path = tmp_path / "source.py"
    path.write_text("original\n")

    def fail_replace(_source, _destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr("codedna_tool.manifest_store.os.replace", fail_replace)
    try:
        atomic_write_text(path, "replacement\n")
    except OSError as error:
        assert "simulated" in str(error)
    else:
        raise AssertionError("atomic_write_text should propagate replace failure")

    assert path.read_text() == "original\n"
    assert list(tmp_path.glob(".source.py.*.tmp")) == []
