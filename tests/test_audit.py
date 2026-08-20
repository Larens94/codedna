"""test_audit.py — Contract tests for verify, impact, and doctor commands.

exports: test_verify_clean_project_is_ok_and_read_only(tmp_path) | test_verify_reports_export_drift_with_evidence(tmp_path) | test_verify_reports_used_by_drift(tmp_path) | test_verify_subdirectory_honours_repository_excludes(tmp_path) | test_impact_finds_transitive_dependants_and_rules(tmp_path) | test_impact_unknown_query_is_not_ok(tmp_path) | test_doctor_distinguishes_errors_and_optional_warnings(tmp_path) | test_verify_cli_json_has_stable_exit_contract(tmp_path) | test_impact_cli_unknown_query_exits_one(tmp_path)
used_by: none
related: tests/test_cli.py — subprocess CLI contract coverage
rules:   Audit tests operate only on temporary repositories and assert read-only behavior.
agent:   gpt-5 | openai | 2026-08-20 | s_20260820_audit | add evidence, traversal, health, and no-write command tests
message:
"""

from __future__ import annotations

import json
import subprocess
import sys

from codedna_tool.audit import doctor_report, impact_report, verify_repository
from codedna_tool.cli import run


def _annotated_project(tmp_path):
    package = tmp_path / "app"
    package.mkdir()
    (package / "service.py").write_text("def create_user():\n    return 1\n")
    (package / "api.py").write_text("from app.service import create_user\n\ndef route():\n    return create_user()\n")
    run(tmp_path, [1, 2], "test", False, [], False, True, True, False, None,
        repo_root=tmp_path, extensions=[".py"])
    return package


def test_verify_clean_project_is_ok_and_read_only(tmp_path):
    _annotated_project(tmp_path)
    before = {path: path.read_bytes() for path in tmp_path.rglob("*.py")}
    report = verify_repository(tmp_path, [".py"])
    assert report["ok"] is True
    assert report["issues"] == []
    assert before == {path: path.read_bytes() for path in tmp_path.rglob("*.py")}


def test_verify_reports_export_drift_with_evidence(tmp_path):
    package = _annotated_project(tmp_path)
    path = package / "service.py"
    path.write_text(path.read_text().replace("create_user", "register_user", 1))
    report = verify_repository(tmp_path, [".py"])
    issue = next(item for item in report["issues"] if item["code"] == "export_drift")
    assert issue["path"] == "app/service.py"
    assert "create_user" in issue["evidence"]
    assert "register_user" in issue["evidence"]


def test_verify_reports_used_by_drift(tmp_path):
    package = _annotated_project(tmp_path)
    api = package / "api.py"
    api.write_text(api.read_text().replace("from app.service import create_user\n", ""))
    report = verify_repository(tmp_path, [".py"])
    assert any(item["code"] == "used_by_drift" and item["path"] == "app/service.py"
               for item in report["issues"])


def test_verify_subdirectory_honours_repository_excludes(tmp_path):
    package = _annotated_project(tmp_path)
    generated = tmp_path / "generated"
    generated.mkdir()
    (generated / "caller.py").write_text("from app.service import create_user\n")
    (tmp_path / ".codedna").write_text(
        'project: demo\nexclude:\n  - "generated/**"\nagent_sessions: []\n'
    )
    report = verify_repository(package, [".py"])
    assert report["ok"] is True


def test_impact_finds_transitive_dependants_and_rules(tmp_path):
    package = _annotated_project(tmp_path)
    (package / "main.py").write_text("from app.api import route\n\ndef main():\n    return route()\n")
    run(tmp_path, [1, 2], "test", False, [], True, True, True, False, None,
        repo_root=tmp_path, extensions=[".py"])
    report = impact_report(tmp_path, "app/service.py", [".py"])
    assert report["ok"] is True
    assert [item["path"] for item in report["dependants"]] == ["app/api.py", "app/main.py"]
    assert "app/service.py" in report["rules"]


def test_impact_unknown_query_is_not_ok(tmp_path):
    _annotated_project(tmp_path)
    report = impact_report(tmp_path, "missing_symbol", [".py"])
    assert report["ok"] is False
    assert report["matches"] == []


def test_doctor_distinguishes_errors_and_optional_warnings(tmp_path):
    report = doctor_report(tmp_path)
    assert report["ok"] is False
    assert any(check["code"] == "manifest" and check["status"] == "error"
               for check in report["checks"])
    (tmp_path / ".codedna").write_text("project: demo\nagent_sessions: []\n")
    report = doctor_report(tmp_path)
    assert not any(check["status"] == "error" for check in report["checks"])
    assert any(check["status"] == "warning" for check in report["checks"])


def test_verify_cli_json_has_stable_exit_contract(tmp_path):
    _annotated_project(tmp_path)
    result = subprocess.run(
        [sys.executable, "-m", "codedna_tool.cli", "verify", str(tmp_path),
         "--extensions", "py", "--json"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["command"] == "verify"


def test_impact_cli_unknown_query_exits_one(tmp_path):
    _annotated_project(tmp_path)
    result = subprocess.run(
        [sys.executable, "-m", "codedna_tool.cli", "impact", "missing",
         "--path", str(tmp_path), "--extensions", "py", "--json"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1
    assert json.loads(result.stdout)["matches"] == []
