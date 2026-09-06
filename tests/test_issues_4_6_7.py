"""Regression tests for issues #4 (PHP mixed), #6 (VB.NET), #7 (Roo Code)."""

from __future__ import annotations

from codedna_tool.cli import _TOOL_FILES, _detect_ai_tools
from codedna_tool.languages import SUPPORTED_EXTENSIONS, get_adapter


class TestIssue4PhpMixedHtml:
    def test_same_line_php_keeps_header_inside_tags(self):
        php = get_adapter(".php")
        src = "<!DOCTYPE html>\n<html>\n<?php include 'x.php'; ?>\n</html>\n"
        out = php.inject_header(src, "header.php", "none", "none", "none", "test", "2026-09-06")
        assert out.startswith("<!DOCTYPE html>")
        open_at = out.lower().index("<?php")
        exports_at = out.index("exports:")
        close_at = out.index("?>", open_at)
        assert open_at < exports_at < close_at
        assert out.count("exports:") == 1
        assert php.inject_header(out, "header.php", "none", "none", "none", "test", "2026-09-06") == out

    def test_midline_php_keeps_header_inside_tags(self):
        php = get_adapter(".php")
        src = "<title><?php echo $t; ?></title>\n"
        out = php.inject_header(src, "t.php", "none", "none", "none", "test", "2026-09-06")
        assert out.startswith("<title><?php")
        assert "exports:" in out
        open_at = out.lower().index("<?php")
        exports_at = out.index("exports:")
        close_at = out.index("?>", open_at)
        assert open_at < exports_at < close_at

    def test_html_only_wraps_php_block(self):
        php = get_adapter(".php")
        src = "<!DOCTYPE html><html></html>\n"
        out = php.inject_header(src, "t.php", "none", "none", "none", "test", "2026-09-06")
        assert out.startswith("<?php")
        assert "?>" in out
        assert out.index("exports:") < out.index("?>")
        assert "<!DOCTYPE html>" in out[out.index("?>") :]

    def test_large_html_prefix_does_not_duplicate(self):
        php = get_adapter(".php")
        annotated = (
            "<!-- pad -->\n" * 2000
            + "<?php\n"
            + "// Foo.php — x.\n//\n// exports: none\n// used_by: none\n"
            + "// rules:   none\n// agent:   t | codedna-cli | 2026-09-06 | s | n\n"
            + "// message: \nclass Foo {}\n"
        )
        assert php.has_codedna_header(annotated) is True
        out = php.inject_header(annotated, "Foo.php", "none", "none", "none", "test", "2026-09-06")
        assert out.count("exports:") == 1


class TestIssue6VbNet:
    def test_registered_and_extracts_public_members(self, tmp_path):
        assert ".vb" in SUPPORTED_EXTENSIONS
        vb = get_adapter(".vb")
        p = tmp_path / "UserService.vb"
        p.write_text(
            "Option Strict On\n"
            "Imports System\n\n"
            "Public Class UserService\n"
            "    Public Function GetUser(id As Integer) As String\n"
            "        Return \"u\"\n"
            "    End Function\n"
            "    Private Sub Hidden()\n"
            "    End Sub\n"
            "    Public Property Name As String\n"
            "End Class\n"
        )
        info = vb.extract_info(p, tmp_path)
        assert "UserService" in info.exports
        assert any("GetUser" in e for e in info.exports)
        assert not any("Hidden" in e for e in info.exports)

    def test_inject_after_imports_idempotent(self):
        vb = get_adapter(".vb")
        source = (
            "Option Explicit On\nImports System\n\n"
            "Public Module Program\n    Public Sub Main()\n    End Sub\nEnd Module\n"
        )
        r1 = vb.inject_header(source, "Program.vb", "Program", "none", "none", "test", "2026-09-06")
        assert r1.index("Imports System") < r1.index("exports:") < r1.index("Public Module")
        assert vb.inject_header(r1, "Program.vb", "Program", "none", "none", "test", "2026-09-06") == r1


class TestIssue7RooCode:
    def test_tool_files_and_detection(self, tmp_path):
        assert "roo" in _TOOL_FILES
        assert _TOOL_FILES["roo"] == (".roorules", ".roorules")
        (tmp_path / ".roorules").write_text("# roo\n")
        detected = _detect_ai_tools(tmp_path)
        assert "roo" in detected
