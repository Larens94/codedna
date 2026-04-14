# Language Support

CodeDNA v0.8 supports **11 languages**. Python is the reference implementation with full AST-based extraction (L1 module headers + L2 function `Rules:`). TypeScript and Go have optional tree-sitter AST support (`pip install codedna[treesitter]`). All other languages get L1-only annotation via regex adapters — no external toolchain required.

| Language | Extensions | L1 | L2 | AST | Framework awareness |
|---|---|---|---|---|---|
| Python | `.py` | ✅ | ✅ | Built-in `ast` | — |
| TypeScript / JavaScript | `.ts .tsx .js .jsx .mjs` | ✅ | — | tree-sitter (optional) | — |
| Go | `.go` | ✅ | — | tree-sitter (optional) | — |
| PHP | `.php` | ✅ | — | Regex | **Laravel** (Route facades, Eloquent) · **Phalcon** (Controller/Model, DI, Router) |
| Rust | `.rs` | ✅ | — | Regex | — |
| Java | `.java` | ✅ | — | Regex | — |
| Kotlin | `.kt .kts` | ✅ | — | Regex | — |
| C# | `.cs` | ✅ | — | Regex | — |
| Swift | `.swift` | ✅ | — | Regex | — |
| Ruby | `.rb` | ✅ | — | Regex | — |

**Template engines** (L1 via block-comment extraction):

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

## CLI Commands

```bash
codedna init ./src --extensions ts go              # TypeScript + Go
codedna init ./app --extensions php                # PHP/Laravel or PHP/Phalcon
codedna init ./templates --extensions volt blade   # Phalcon Volt + Laravel Blade
codedna init . --extensions ts go php rs java      # mixed project
codedna check . --extensions ts go -v              # coverage report
```

---

## Tree-sitter AST Support

For more accurate extraction on TypeScript and Go:

```bash
pip install codedna[treesitter]
```

This adds AST-based parsing via tree-sitter (accurate export/import extraction, cross-file dependency graph). Falls back to regex when tree-sitter is not installed — zero breaking changes.

---

## PHP + Laravel Example

```php
<?php
// app/Http/Controllers/UserController.php — Handles user CRUD endpoints.
//
// exports: UserController::index() -> Response
//          UserController::store(Request) -> JsonResponse
// used_by: routes/web.php -> Route::resource('users', UserController::class)
// rules:   must extend App\Http\Controllers\Controller.
//          all public methods are auto-detected as exports.
// agent:   claude-sonnet-4-6 | anthropic | 2026-04-02 | s_20260402_001 | initial controller scaffold
```

## PHP + Phalcon Example

```php
<?php
// app/controllers/UserController.php — Handles user CRUD in Phalcon MVC.
//
// exports: UserController::indexAction() -> Response
//          UserController::createAction() -> Response
//          route:/users
//          service:userService
// used_by: app/config/router.php -> $router->addGet('/users', ...)
// rules:   extends Phalcon\Mvc\Controller — do not add constructor, use DI.
//          $di->set('userService', ...) registers this service globally.
// agent:   claude-sonnet-4-6 | anthropic | 2026-04-02 | s_20260402_001 | initial Phalcon controller

namespace App\Controllers;

use Phalcon\Mvc\Controller;

class UserController extends Controller
{
    public function indexAction() { ... }
    public function createAction() { ... }
}
```

The PHP adapter auto-detects:
- `extends Controller` / `extends Model` / `extends Phalcon\Mvc\Controller` → marks as Phalcon component
- `$router->addGet('/uri', ...)` → exports as `route:/uri`
- `$di->set('serviceName', ...)` / `$di->setShared(...)` → exports as `service:serviceName`
- Public methods → annotated as `ClassName::method`
