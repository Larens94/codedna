"""php.py — CodeDNA v0.8 adapter for PHP source files (Laravel + Phalcon).

exports: _CLASS_RE | _INTERFACE_RE | _TRAIT_RE | _ENUM_RE | _FUNC_RE | _PUBLIC_METHOD_RE | _ROUTE_RE | _NAMESPACE_RE | _USE_RE | _PHALCON_EXTENDS_RE | _PHALCON_ROUTER_RE | _PHALCON_DI_RE | class PhpAdapter | PhpAdapter.inject_function_rules
used_by: codedna_tool/languages/__init__.py → PhpAdapter
         codedna_tool/languages/_ts_php.py → PhpAdapter
rules:   regex-based only — no PHP interpreter dependency required.
Detects exports: public functions/methods, classes, interfaces, traits, enums.
Laravel-aware: detects Route facades, controller methods, Eloquent model fillable.
Phalcon-aware: detects extends Controller/Model, $router->add, $di->set/setShared.
PHP uses block comments (/** ... */ or /* ... */); single-line uses //.
inject_header uses single-line // comments to avoid conflict with PHPDoc blocks.
agent:   claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_005 | remove unused ns_prefix/namespace dead code (ruff F841)
claude-sonnet-4-6 | anthropic | 2026-04-18 | s_20260418_php | fix _resolve_use: lowercase-first candidate order + resolve() for real fs path — fixes macOS case-insensitive match returning App/ instead of app/ (Laravel PSR-4 convention)
claude-sonnet-4-6 | anthropic | 2026-04-18 | s_20260418_php2 | GATE 3: add inject_function_rules() — injects PHPDoc Rules: above public methods; handles existing PHPDoc (append before */) and no-doc (new block)
"""

from __future__ import annotations

import re
from pathlib import Path

from .base import LanguageAdapter, LangFileInfo, LangFuncInfo

# Top-level declarations (public only for classes; all functions at file scope)
_CLASS_RE = re.compile(r"^(?:abstract\s+|final\s+|readonly\s+)*class\s+(\w+)", re.MULTILINE)
_INTERFACE_RE = re.compile(r"^interface\s+(\w+)", re.MULTILINE)
_TRAIT_RE = re.compile(r"^trait\s+(\w+)", re.MULTILINE)
_ENUM_RE = re.compile(r"^enum\s+(\w+)", re.MULTILINE)
_FUNC_RE = re.compile(r"^function\s+(\w+)\s*\(", re.MULTILINE)

# Public methods inside classes
_PUBLIC_METHOD_RE = re.compile(
    r"^\s+public\s+(?:static\s+)?function\s+(\w+)\s*\(", re.MULTILINE
)

# Laravel-specific: Route::get/post/… — captures controller@method or closure routes
_ROUTE_RE = re.compile(
    r"Route\s*::\s*(?:get|post|put|patch|delete|any|match|resource|apiResource)"
    r"\s*\(\s*['\"]([^'\"]+)['\"]",
    re.MULTILINE,
)

# namespace extraction
_NAMESPACE_RE = re.compile(r"^namespace\s+([\w\\]+)\s*;", re.MULTILINE)

# use imports (relative)
_USE_RE = re.compile(r"^use\s+([\w\\]+)(?:\s+as\s+\w+)?\s*;", re.MULTILINE)

# ── Phalcon-specific patterns ──────────────────────────────────────────────

# Phalcon controller/model/service base classes (short or FQCN)
_PHALCON_EXTENDS_RE = re.compile(
    r"class\s+\w+\s+extends\s+"
    r"(?:\\?Phalcon\\(?:Mvc\\)?(?:Controller|Model|Plugin|Injectable)|Controller|Model)",
    re.MULTILINE,
)

# Phalcon router: $router->add/addGet/addPost/addPut/addDelete/addPatch('/uri', ...)
_PHALCON_ROUTER_RE = re.compile(
    r"\$router\s*->\s*add(?:Get|Post|Put|Patch|Delete|Options|Head)?\s*"
    r"\(\s*['\"]([^'\"]+)['\"]",
    re.MULTILINE,
)

# Phalcon DI: $di->set/setShared/setRaw/attempt('serviceName', ...)
_PHALCON_DI_RE = re.compile(
    r"\$(?:di|container)\s*->\s*(?:set|setShared|setRaw|attempt)\s*"
    r"\(\s*['\"](\w+)['\"]",
    re.MULTILINE,
)


class PhpAdapter(LanguageAdapter):
    """CodeDNA adapter for .php files, including Laravel controllers and models.

    Rules:   Uses // comment prefix for the CodeDNA block (not PHPDoc /** */),
             so the block does not interfere with IDE PHPDoc tooling.
             Public methods are captured; private/protected are skipped.
             Laravel Route facades are captured as named exports when present.
             Never raises — return LangFileInfo(parseable=False) on OSError.
    """

    @property
    def comment_prefix(self) -> str:
        return "//"

    def extract_info(self, path: Path, repo_root: Path) -> LangFileInfo:
        """Parse a PHP file and return structural information.

        Rules:   Must never raise — return LangFileInfo(parseable=False) on any OSError.
                 Captures public class methods and top-level functions.
                 Laravel Route definitions are treated as named exports (the URI string).
                 Private/protected methods and magic methods (__construct etc.) are excluded
                 from exports but not from the file scan.
        """
        rel = str(path.relative_to(repo_root))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return LangFileInfo(path=path, rel=rel, parseable=False)

        list_str_exports: list[str] = []

        # Classes, interfaces, traits, enums (type-level exports)
        for pat in [_CLASS_RE, _INTERFACE_RE, _TRAIT_RE, _ENUM_RE]:
            for m in pat.finditer(source):
                name = m.group(1)
                if name not in list_str_exports:
                    list_str_exports.append(name)

        # Top-level functions (outside classes)
        for m in _FUNC_RE.finditer(source):
            name = m.group(1)
            if name not in list_str_exports:
                list_str_exports.append(name)

        # Public methods (only if no class-level export already captured enough context)
        # Limit to 8 to avoid noise on large controllers
        public_methods: list[str] = []
        for m in _PUBLIC_METHOD_RE.finditer(source):
            name = m.group(1)
            if not name.startswith("__") and name not in public_methods:
                public_methods.append(name)
        # Add public methods only when there's no top-level class (e.g. trait files)
        # or when we have a controller (many public methods = route handlers)
        if not list_str_exports and public_methods:
            list_str_exports.extend(public_methods[:8])
        elif public_methods and list_str_exports:
            # Annotate as "ClassName::method" for Laravel controllers
            cls_name = list_str_exports[0] if list_str_exports else ""
            for method in public_methods[:6]:
                entry = f"{cls_name}::{method}" if cls_name else method
                if entry not in list_str_exports:
                    list_str_exports.append(entry)

        # Laravel routes as exports
        routes = _ROUTE_RE.findall(source)
        for route in routes[:5]:
            entry = f"route:{route}"
            if entry not in list_str_exports:
                list_str_exports.append(entry)

        # Phalcon router definitions as exports
        phalcon_routes = _PHALCON_ROUTER_RE.findall(source)
        for route in phalcon_routes[:5]:
            entry = f"route:{route}"
            if entry not in list_str_exports:
                list_str_exports.append(entry)

        # Phalcon DI service registrations as exports
        phalcon_services = _PHALCON_DI_RE.findall(source)
        for svc in phalcon_services[:5]:
            entry = f"service:{svc}"
            if entry not in list_str_exports:
                list_str_exports.append(entry)

        # Deps: use statements → attempt to resolve to repo-relative paths
        list_str_deps: list[str] = []
        for m in _USE_RE.finditer(source):
            fqcn = m.group(1)  # e.g. App\Models\User
            rel_path = self._resolve_use(fqcn, repo_root)
            if rel_path and rel_path not in list_str_deps:
                list_str_deps.append(rel_path)

        has_codedna = self.has_codedna_header(source)

        return LangFileInfo(
            path=path,
            rel=rel,
            exports=list_str_exports,
            deps=list_str_deps,
            has_codedna=has_codedna,
        )

    def inject_header(self, source: str, rel: str, exports: str, used_by: str,
                      rules: str, model_id: str, today: str) -> str:
        """Prepend a CodeDNA // comment block. Returns source unchanged if already present.

        Rules:   Must be idempotent — if has_codedna_header() returns True, return unchanged.
                 Header uses // comments, NOT /** PHPDoc */ — avoids IDE PHPDoc conflicts.
                 The PHP opening tag (<?php) must remain the very first line of the file;
                 CodeDNA block is inserted immediately after <?php on line 2.
                 declare(strict_types=1) lines are preserved after the CodeDNA block.
        """
        if self.has_codedna_header(source):
            return source

        header_lines = self._build_header_lines(rel, exports, used_by, rules, model_id, today)
        header = "\n".join(header_lines) + "\n"

        lines = source.splitlines(keepends=True)

        # Find insertion point: after <?php and optional declare(strict_types)
        insert_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("<?php") or stripped.startswith("<?PHP"):
                insert_idx = i + 1
                break

        # Skip blank lines right after <?php
        while insert_idx < len(lines) and not lines[insert_idx].strip():
            insert_idx += 1

        before = "".join(lines[:insert_idx])
        after = "".join(lines[insert_idx:])
        return before + "\n" + header + "\n" + after

    def inject_function_rules(self, source: str, func: LangFuncInfo, rules_text: str) -> str:
        """Inject a PHPDoc Rules: block above a public PHP method.

        Rules:   Must be idempotent — if func.has_rules is True, return source unchanged.
                 If a PHPDoc block already exists above the method (func.has_doc), append
                 Rules: inside it before the closing */. Otherwise insert a new /** ... */ block.
                 Operates by line number (func.start_line, 1-based) — caller MUST apply
                 from BOTTOM to TOP to preserve line numbers across multiple injections.
        """
        if func.has_rules:
            return source

        lines = source.splitlines(keepends=True)
        method_idx = func.start_line - 1  # 0-based index of method's first line

        # Detect indentation from the method line
        method_line = lines[method_idx] if method_idx < len(lines) else ""
        indent = len(method_line) - len(method_line.lstrip())
        pad = " " * indent

        if func.has_doc:
            # Find the closing */ of the existing PHPDoc above the method
            close_idx = method_idx - 1
            while close_idx >= 0 and "*/" not in lines[close_idx]:
                close_idx -= 1
            if close_idx >= 0:
                # Insert Rules: line before the closing */
                rules_line = f"{pad} * Rules:   {rules_text}\n"
                lines = lines[:close_idx] + [rules_line] + lines[close_idx:]
                return "".join(lines)

        # No existing PHPDoc — insert a new block above the method
        phpdoc = (
            f"{pad}/**\n"
            f"{pad} * Rules:   {rules_text}\n"
            f"{pad} */\n"
        )
        lines = lines[:method_idx] + [phpdoc] + lines[method_idx:]
        return "".join(lines)

    @staticmethod
    def _resolve_use(fqcn: str, repo_root: Path) -> str | None:
        """Resolve a PHP fully-qualified class name to a repo-relative file path.

        Rules:   Only resolves if a matching .php file exists under repo_root.
                 Laravel convention: App\\Models\\User → app/Models/User.php (case-insensitive dir).
                 Returns None for vendor/ classes and built-ins.
        """
        # Convert backslash namespace to path, try both cases for first segment
        parts = fqcn.replace("\\", "/")
        # Laravel: App → app
        lower_parts = parts[0].lower() + parts[1:] if parts else parts

        for candidate_parts in [lower_parts, parts]:
            candidate = repo_root / f"{candidate_parts}.php"
            if candidate.exists():
                try:
                    # Use resolve() to get real filesystem path (fixes macOS
                    # case-insensitive match returning wrong-case rel path).
                    return str(candidate.resolve().relative_to(repo_root.resolve()))
                except ValueError:
                    pass
        return None
