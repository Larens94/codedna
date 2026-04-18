# Language Support

CodeDNA v0.9 supports **9 source languages** via tree-sitter AST parsing, plus **7 template engines** via regex. All languages are auto-detected — no configuration needed.

| Language | Extensions | L1 | L2 | Parser | Framework awareness |
|---|---|---|---|---|---|
| Python | `.py` | ✅ | ✅ | Built-in `ast` | — |
| PHP | `.php` | ✅ | ✅ | tree-sitter | **Laravel** (Route facades, Eloquent, constructor injection) · **Phalcon** |
| TypeScript / JavaScript | `.ts .tsx .js .jsx .mjs` | ✅ | ✅ | tree-sitter | — |
| Go | `.go` | ✅ | ✅ | tree-sitter | — |
| Java | `.java` | ✅ | ✅ | tree-sitter | — |
| Kotlin | `.kt .kts` | ✅ | ✅ | tree-sitter | — |
| Ruby | `.rb` | ✅ | ✅ | tree-sitter | — |
| Rust | `.rs` | ✅ | ✅ | tree-sitter | — |
| C# | `.cs` | ✅ | ✅ | tree-sitter | — |

**Template engines** (L1 only, regex-based by design):

| Template | Extensions | Comment syntax |
|---|---|---|
| Blade (Laravel) | `.blade.php` | `{{-- --}}` |
| Jinja2 / Twig | `.j2 .jinja2 .twig` | `{# #}` |
| Volt (Phalcon) | `.volt` | `{# #}` |
| ERB / EJS | `.erb .ejs` | `<%# %>` |
| Handlebars / Mustache | `.hbs .mustache` | `{{!-- --}}` |
| Razor / Cshtml | `.cshtml .razor` | `@* *@` |
| Vue SFC / Svelte | `.vue .svelte` | `<!-- -->` |

---

## What tree-sitter extracts

All source languages use tree-sitter for accurate AST-based extraction:

- **Exports**: classes, public methods (with full signatures), interfaces, traits, enums, constants
- **Dependencies**: `use`, `import`, `require` statements resolved to file paths
- **Function info**: start line, doc block detection, Rules: detection — enables L2 injection
- **Framework-specific**: Laravel routes (`Route::get`), PHP 8 attributes (`#[Route]`), enum cases, constructor injection

---

## CLI Commands

```bash
codedna init .                                 # auto-detect all languages
codedna init ./src --extensions ts go          # TypeScript + Go only
codedna init ./app --extensions php            # PHP/Laravel
codedna check . -v                             # coverage report
codedna refresh .                              # update exports + used_by (zero LLM cost)
```

---

## PHP + Laravel Example

```php
<?php
// UserController.php — Handles user CRUD endpoints.
//
// exports: UserController | UserController::index() | UserController::store(Request $request): JsonResponse
// used_by: routes/web.php
// rules:   must extend App\Http\Controllers\Controller
// agent:   codedna-cli (no-llm) | codedna-cli | 2026-04-18 | codedna-cli | initial CodeDNA annotation pass
```

The PHP tree-sitter adapter auto-detects:
- `class`, `interface`, `trait`, `enum` declarations
- Public methods with full signatures (parameters + return types)
- `use App\Models\User` → resolves to `app/Models/User.php` (PSR-4)
- `Route::get('/path', ...)` → exports as `route:/path`
- PHP 8 attributes `#[Middleware('auth')]` → exports as `attr:Middleware`
- Enum cases `Status::Active` → exports as `Status::Active`
- Constructor injection `__construct(UserService $service)` → dep on UserService

## Blade Template Example

```blade
{{-- layout.blade.php — Base application layout.
--
-- exports: none
-- used_by: none
-- rules:   @yield('content') is required — child views must define this section
-- agent:   codedna-cli (no-llm) | codedna-cli | 2026-04-18 | codedna-cli | initial CodeDNA annotation pass
--}}
```

Blade adapter detects `@extends`, `@include`, `@component`, `@livewire` as dependencies.
