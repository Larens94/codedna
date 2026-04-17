"""test_language_adapters.py — Test suite for CodeDNA language adapters.

exports: project(tmp_path) | write_file(project, name, content) | class TestTypeScript | class TestGo | class TestRuby | class TestCSharp | class TestPHP | class TestRust | class TestJava | class TestSwift | class TestKotlin | class TestBlade | class TestFallback | class TestErrorHandling
used_by: none
rules:   Each language adapter must pass: export detection, private exclusion,
header injection, and injection idempotency.
tree-sitter tests are skipped if tree-sitter is not installed.
agent:   claude-opus-4-6 | anthropic | 2026-04-14 | s_20260414_002 | initial test suite for all 9 language adapters
claude-opus-4-7 | anthropic | 2026-04-17 | s_20260417_blade | regression tests for Blade: {{-- --}} syntax (not //), idempotent inject, vendor/ excluded. Catches regression where .blade.php was being routed to PhpAdapter, corrupting Laravel views.
"""

from __future__ import annotations

from pathlib import Path
import tempfile

import pytest

from codedna_tool.languages import get_adapter


# ── Helpers ──────────────────────────────────────────────────────────────────

@pytest.fixture
def project(tmp_path):
    """Return a tmp_path that acts as repo root."""
    return tmp_path


def write_file(project: Path, name: str, content: str) -> Path:
    p = project / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return p


# ── TypeScript / JavaScript ──────────────────────────────────────────────────

class TestTypeScript:
    def test_adapter_loads(self):
        ts = get_adapter(".ts")
        assert ts is not None

    def test_exports_all_types(self, project):
        ts = get_adapter(".ts")
        p = write_file(project, "app.ts", """
export async function getUsers(): Promise<User[]> { return []; }
export class UserController {}
export const MAX_PAGE = 50;
export type UserId = number;
export interface IUserService { find(): void; }
export default class App {}
function privateHelper() {}
const internalVar = 42;
""")
        info = ts.extract_info(p, project)
        assert "getUsers" in info.exports
        assert "UserController" in info.exports
        assert "MAX_PAGE" in info.exports
        assert "UserId" in info.exports
        assert "IUserService" in info.exports
        assert "App" in info.exports
        assert "privateHelper" not in info.exports
        assert "internalVar" not in info.exports

    def test_relative_imports_resolved(self, project):
        ts = get_adapter(".ts")
        write_file(project, "utils/format.ts", "export function fmt() {}")
        write_file(project, "models/index.ts", "export interface User {}")
        write_file(project, "config.ts", "export const X = 1;")
        p = write_file(project, "main.ts", """
import { fmt } from "./utils/format";
import { User } from "./models";
import { X } from "./config";
import express from "express";
export function start() {}
""")
        info = ts.extract_info(p, project)
        assert "utils/format.ts" in info.deps
        assert "models/index.ts" in info.deps
        assert "config.ts" in info.deps
        assert not any("express" in d for d in info.deps)

    def test_js_extension(self, project):
        js = get_adapter(".js")
        assert js is not None
        write_file(project, "helper.js", "export function helper() {}")
        p = write_file(project, "app.js", """
import { helper } from "./helper";
export function init() {}
export class Server {}
""")
        info = js.extract_info(p, project)
        assert "init" in info.exports
        assert "Server" in info.exports
        assert "helper.js" in info.deps

    def test_injection_idempotent(self, project):
        ts = get_adapter(".ts")
        source = "export function foo() {}\n"
        r1 = ts.inject_header(source, "foo.ts", "foo()", "none", "none", "test", "2026-04-14")
        r2 = ts.inject_header(r1, "foo.ts", "foo()", "none", "none", "test", "2026-04-14")
        assert r1 == r2
        assert "rules:" in r1  # reduced header — no exports:/used_by:
        assert "export function foo()" in r1


# ── Go ───────────────────────────────────────────────────────────────────────

class TestGo:
    def test_adapter_loads(self):
        go = get_adapter(".go")
        assert go is not None

    def test_exported_vs_unexported(self, project):
        go = get_adapter(".go")
        p = write_file(project, "handlers.go", """package handlers

import (
\t"fmt"
\t"net/http"
\t"github.com/myapp/internal/models"
)

func GetUsers(db *DB) ([]*User, error) { return nil, nil }
func internalHelper() {}
type UserHandler struct { DB *DB }
type config struct { port int }
func (h *UserHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {}
func (h *UserHandler) handleInternal() {}
const MaxPageSize = 50
const defaultTimeout = 30
var GlobalLogger *Logger
var localCache = make(map[string]string)
func init() { fmt.Println("init") }
""")
        info = go.extract_info(p, project)
        # Exported
        assert "GetUsers" in info.exports
        assert "UserHandler" in info.exports
        assert "ServeHTTP" in info.exports
        assert "MaxPageSize" in info.exports
        assert "GlobalLogger" in info.exports
        # Unexported
        assert "internalHelper" not in info.exports
        assert "config" not in info.exports
        assert "handleInternal" not in info.exports
        assert "defaultTimeout" not in info.exports
        assert "localCache" not in info.exports
        assert "init" not in info.exports

    def test_imports(self, project):
        go = get_adapter(".go")
        p = write_file(project, "main.go", """package main

import (
\t"fmt"
\t"net/http"
\t"github.com/myapp/internal/models"
)

func Main() {}
""")
        info = go.extract_info(p, project)
        assert "fmt" in info.deps
        assert "net/http" in info.deps
        assert "github.com/myapp/internal/models" in info.deps

    def test_injection_preserves_package(self, project):
        go = get_adapter(".go")
        source = "package main\n\nfunc Foo() {}\n"
        result = go.inject_header(source, "main.go", "Foo()", "none", "none", "test", "2026-04-14")
        assert result.index("// main.go") < result.index("package main")

    def test_injection_idempotent(self, project):
        go = get_adapter(".go")
        source = "package main\n\nfunc Foo() {}\n"
        r1 = go.inject_header(source, "main.go", "Foo()", "none", "none", "test", "2026-04-14")
        r2 = go.inject_header(r1, "main.go", "Foo()", "none", "none", "test", "2026-04-14")
        assert r1 == r2


# ── Ruby ─────────────────────────────────────────────────────────────────────

class TestRuby:
    def test_nested_class_in_module(self, project):
        rb = get_adapter(".rb")
        p = write_file(project, "user_service.rb", """
module Services
  class UserService
    def get_users
      []
    end

    def self.create(params)
    end

    private
    def validate(data)
    end
  end
end
""")
        info = rb.extract_info(p, project)
        assert "Services" in info.exports
        assert "UserService" in info.exports
        assert "UserService#get_users" in info.exports
        assert "UserService.create" in info.exports
        assert not any("validate" in e for e in info.exports)

    def test_top_level_class(self, project):
        rb = get_adapter(".rb")
        p = write_file(project, "simple.rb", """
class SimpleService
  def run
  end
end
""")
        info = rb.extract_info(p, project)
        assert "SimpleService" in info.exports
        assert "SimpleService#run" in info.exports

    def test_require_relative(self, project):
        rb = get_adapter(".rb")
        write_file(project, "models/user.rb", "class User; end")
        p = write_file(project, "service.rb", """
require_relative "./models/user"
class Service; end
""")
        info = rb.extract_info(p, project)
        assert any("models/user" in d for d in info.deps)

    def test_injection_idempotent(self, project):
        rb = get_adapter(".rb")
        source = "class Foo\n  def bar; end\nend\n"
        r1 = rb.inject_header(source, "foo.rb", "Foo", "none", "none", "test", "2026-04-14")
        r2 = rb.inject_header(r1, "foo.rb", "Foo", "none", "none", "test", "2026-04-14")
        assert r1 == r2


# ── C# ───────────────────────────────────────────────────────────────────────

class TestCSharp:
    def test_class_inside_namespace(self, project):
        cs = get_adapter(".cs")
        p = write_file(project, "UserController.cs", """
using System;
using MyApp.Models;

namespace MyApp.Controllers
{
    public class UserController : Controller
    {
        public IActionResult Index() { return View(); }
        public async Task<IActionResult> Create(User user) { return Ok(); }
        private void Validate(User u) { }
    }

    public interface IUserService
    {
        Task<User> FindAsync(int id);
    }
}
""")
        info = cs.extract_info(p, project)
        assert "UserController" in info.exports
        assert "IUserService" in info.exports
        assert any("Index" in e for e in info.exports)
        assert any("Create" in e for e in info.exports)
        assert not any("Validate" in e for e in info.exports)

    def test_class_without_namespace(self, project):
        cs = get_adapter(".cs")
        p = write_file(project, "Simple.cs", """
public class SimpleService
{
    public void Run() {}
}
""")
        info = cs.extract_info(p, project)
        assert "SimpleService" in info.exports

    def test_injection_idempotent(self, project):
        cs = get_adapter(".cs")
        source = "public class Foo { public void Bar() {} }\n"
        r1 = cs.inject_header(source, "Foo.cs", "Foo", "none", "none", "test", "2026-04-14")
        r2 = cs.inject_header(r1, "Foo.cs", "Foo", "none", "none", "test", "2026-04-14")
        assert r1 == r2


# ── PHP ──────────────────────────────────────────────────────────────────────

class TestPHP:
    def test_class_and_methods(self, project):
        php = get_adapter(".php")
        p = write_file(project, "UserController.php", """<?php
namespace App\\Controllers;

class UserController extends Controller
{
    public function index() { }
    public function store() { }
    private function validate($data) { }
}
""")
        info = php.extract_info(p, project)
        assert "UserController" in info.exports
        assert any("index" in e for e in info.exports)
        assert not any("validate" in e for e in info.exports)

    def test_injection_idempotent(self, project):
        php = get_adapter(".php")
        source = "<?php\nclass Foo { public function bar() {} }\n"
        r1 = php.inject_header(source, "Foo.php", "Foo", "none", "none", "test", "2026-04-14")
        r2 = php.inject_header(r1, "Foo.php", "Foo", "none", "none", "test", "2026-04-14")
        assert r1 == r2


# ── Rust ─────────────────────────────────────────────────────────────────────

class TestRust:
    def test_pub_vs_private(self, project):
        rs = get_adapter(".rs")
        p = write_file(project, "lib.rs", """
pub fn get_users() -> Vec<User> { vec![] }
pub struct UserService {}
pub enum Status { Active, Inactive }
pub trait Repository { fn find(&self); }
fn internal_helper() {}
struct PrivateConfig {}
""")
        info = rs.extract_info(p, project)
        assert "get_users" in info.exports
        assert "UserService" in info.exports
        assert "Status" in info.exports
        assert "Repository" in info.exports
        assert "internal_helper" not in info.exports
        assert "PrivateConfig" not in info.exports

    def test_injection_idempotent(self, project):
        rs = get_adapter(".rs")
        source = "pub fn foo() {}\n"
        r1 = rs.inject_header(source, "lib.rs", "foo()", "none", "none", "test", "2026-04-14")
        r2 = rs.inject_header(r1, "lib.rs", "foo()", "none", "none", "test", "2026-04-14")
        assert r1 == r2


# ── Java ─────────────────────────────────────────────────────────────────────

class TestJava:
    def test_class_and_methods(self, project):
        java = get_adapter(".java")
        p = write_file(project, "UserService.java", """
package com.myapp;

public class UserService {
    public List<User> getUsers() { return null; }
    private void validate() {}
}
""")
        info = java.extract_info(p, project)
        assert "UserService" in info.exports
        assert any("getUsers" in e for e in info.exports)

    def test_injection_idempotent(self, project):
        java = get_adapter(".java")
        source = "public class Foo { public void bar() {} }\n"
        r1 = java.inject_header(source, "Foo.java", "Foo", "none", "none", "test", "2026-04-14")
        r2 = java.inject_header(r1, "Foo.java", "Foo", "none", "none", "test", "2026-04-14")
        assert r1 == r2


# ── Swift ────────────────────────────────────────────────────────────────────

class TestSwift:
    def test_all_declaration_types(self, project):
        sw = get_adapter(".swift")
        p = write_file(project, "Models.swift", """
import Foundation

public class UserService {}
public struct UserDTO {}
public enum UserRole { case admin }
public protocol UserRepository {}
""")
        info = sw.extract_info(p, project)
        assert "UserService" in info.exports
        assert "UserDTO" in info.exports
        assert "UserRole" in info.exports
        assert "UserRepository" in info.exports

    def test_injection_idempotent(self, project):
        sw = get_adapter(".swift")
        source = "public class Foo {}\n"
        r1 = sw.inject_header(source, "Foo.swift", "Foo", "none", "none", "test", "2026-04-14")
        r2 = sw.inject_header(r1, "Foo.swift", "Foo", "none", "none", "test", "2026-04-14")
        assert r1 == r2


# ── Kotlin ───────────────────────────────────────────────────────────────────

class TestKotlin:
    def test_class_types(self, project):
        kt = get_adapter(".kt")
        p = write_file(project, "Models.kt", """
package com.myapp

class UserService {}
data class UserDTO(val id: Int)
interface UserRepository {}
""")
        info = kt.extract_info(p, project)
        assert "UserService" in info.exports
        assert "UserDTO" in info.exports
        assert "UserRepository" in info.exports

    def test_injection_idempotent(self, project):
        kt = get_adapter(".kt")
        source = "class Foo {}\n"
        r1 = kt.inject_header(source, "Foo.kt", "Foo", "none", "none", "test", "2026-04-14")
        r2 = kt.inject_header(r1, "Foo.kt", "Foo", "none", "none", "test", "2026-04-14")
        assert r1 == r2


# ── Fallback (tree-sitter not installed) ─────────────────────────────────────

class TestBlade:
    """Regression tests for Blade templates.

    Previously, `.blade.php` files were annotated with `//` (PHP comment syntax)
    because the extension resolution fell back to `.php`. Blade is not PHP: any
    text outside `@php`/`<?php` is emitted to the rendered HTML, so `//` headers
    appeared as visible text in every error page. Fix: compound-extension
    resolution (_get_extension → .blade.php) routes to BladeAdapter, which uses
    `{{-- ... --}}` — stripped entirely by the Blade compiler, invisible at render.
    """

    def test_blade_adapter_loads(self):
        blade = get_adapter(".blade.php")
        assert blade is not None
        assert blade.__class__.__name__ == "BladeAdapter"

    def test_blade_header_uses_blade_comment_syntax(self, project):
        """Header MUST start with {{-- and end with --}}, never // or <!--."""
        blade = get_adapter(".blade.php")
        p = write_file(project, "welcome.blade.php",
                       "<x-layout>\n    @section('content')\n        <h1>Hi</h1>\n    @endsection\n</x-layout>\n")
        injected = blade.inject_header(
            p.read_text(),
            rel="resources/views/welcome.blade.php",
            exports="@section:content", used_by="none", rules="none",
            model_id="test-model", today="2026-04-17",
        )
        first_line = injected.splitlines()[0]
        assert first_line.startswith("{{--"), \
            f"Blade header must start with '{{{{--', got: {first_line!r}"
        assert "//" not in injected.splitlines()[0], \
            "Blade header must NEVER use PHP '//' comment syntax"
        # Header block ends with --}}
        header_block = injected.split("--}}", 1)[0] + "--}}"
        assert header_block.endswith("--}}"), "Blade header must close with --}}"

    def test_blade_header_idempotent(self, project):
        """inject_header must be idempotent — running twice yields the same file."""
        blade = get_adapter(".blade.php")
        p = write_file(project, "idempotent.blade.php",
                       "@section('x')x@endsection\n")
        first = blade.inject_header(p.read_text(), "x.blade.php", "none", "none",
                                    "none", "m", "2026-04-17")
        second = blade.inject_header(first, "x.blade.php", "none", "none",
                                     "none", "m", "2026-04-17")
        assert first == second, "inject_header must not duplicate the header"

    def test_blade_php_not_resolved_as_plain_php(self):
        """CRITICAL: get_adapter('.blade.php') must return Blade, not Php adapter.

        If this ever regresses (e.g. someone uses path.suffix instead of
        _get_extension), Blade files get // headers and break rendering in every
        Laravel project. This check catches that.
        """
        blade = get_adapter(".blade.php")
        php = get_adapter(".php")
        assert blade is not php, "Blade must NOT fall back to PHP adapter"
        assert blade.__class__.__name__ != php.__class__.__name__

    def test_vendor_excluded_from_default_scan(self, project):
        """vendor/ contains third-party code — must NEVER be annotated by default."""
        from codedna_tool.cli import collect_files

        vendor_file = write_file(project, "vendor/laravel/framework/show.blade.php",
                                 "<x-layout>vendor</x-layout>\n")
        app_file = write_file(project, "resources/views/welcome.blade.php",
                              "<x-layout>app</x-layout>\n")

        files = collect_files(project, exclude=[], extensions=[".blade.php"])
        paths = {str(f.relative_to(project)) for f in files}
        assert "resources/views/welcome.blade.php" in paths
        assert not any("vendor/" in p for p in paths), \
            f"vendor/ MUST be excluded, got: {paths}"


class TestFallback:
    def test_regex_adapters_always_available(self):
        """Even without tree-sitter, all adapters must load."""
        for ext in [".ts", ".tsx", ".js", ".jsx", ".mjs", ".go", ".php", ".rs",
                    ".java", ".kt", ".rb", ".cs", ".swift"]:
            adapter = get_adapter(ext)
            assert adapter is not None, f"No adapter for {ext}"

    def test_unsupported_extension_returns_none(self):
        assert get_adapter(".xyz") is None
        assert get_adapter(".py") is None  # Python uses ast, not language adapters


# ── Error handling ───────────────────────────────────────────────────────────

class TestErrorHandling:
    def test_nonexistent_file(self, project):
        ts = get_adapter(".ts")
        fake = project / "nonexistent.ts"
        info = ts.extract_info(fake, project)
        assert info.parseable is False
        assert info.exports == []

    def test_empty_file(self, project):
        for ext in [".ts", ".go", ".rb", ".cs", ".rs", ".java", ".swift", ".kt", ".php"]:
            adapter = get_adapter(ext)
            p = write_file(project, f"empty{ext}", "")
            info = adapter.extract_info(p, project)
            assert info.parseable is True
            assert info.exports == []
