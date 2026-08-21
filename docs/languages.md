# Language Support

CodeDNA v0.9 supports **12 programming languages** (counting TypeScript and JavaScript separately) across **28 registered extensions**, plus **7 template families**. All are auto-detected — no configuration needed.

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
| Swift | `.swift` | ✅ | ✅ | structural parser | — |
| AXL *(experimental)* | `.axl` | ✅ | native symbol rules | native opcode frames | CodeDNA frames 80–86 |

AXL is intentionally different from comment-based adapters. `codedna init`, `refresh`, `check`, and `verify` read and write structured frames immediately after the numeric AXL version line. Symbol rules are placed directly before opcode `40` declarations. CodeDNA preserves these frames in source; preservation through AX-IR, `pack`, compilation, and generated backends must be implemented and tested in the AXL compiler itself.

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

Python uses the standard-library AST, PHP/TypeScript/JavaScript/Go/Java/Kotlin/Ruby/Rust/C# use tree-sitter, Swift uses its dedicated structural parser, and AXL uses native annotation/declaration frames. Together they provide:

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
