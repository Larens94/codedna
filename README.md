<p align="center">
  <img src="./docs/logo.png" width="120" />
</p>

<h1 align="center">CodeDNA</h1>

<p align="center">
  <strong>The file is the channel. Every fragment carries the whole.</strong>
</p>

<p align="center">
  <a href="./SPEC.md"><img src="https://img.shields.io/badge/protocol-v0.8-6366f1" alt="Protocol"></a>
  <a href="https://doi.org/10.5281/zenodo.19158336"><img src="https://img.shields.io/badge/DOI-zenodo.19158336-blue" alt="DOI"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
  <a href="https://github.com/Larens94/codedna/actions/workflows/ci.yml"><img src="https://github.com/Larens94/codedna/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="docs/languages.md"><img src="https://img.shields.io/badge/languages-9-6366f1" alt="Languages"></a>
  <a href="https://discord.gg/7Fs5J2ua"><img src="https://img.shields.io/badge/discord-join-5865F2?logo=discord&logoColor=white" alt="Discord"></a>
</p>

<p align="center">
  <a href="#install">Install</a> · 
  <a href="#the-problem">Problem</a> · 
  <a href="#the-solution">Solution</a> · 
  <a href="#evidence">Evidence</a> · 
  <a href="#live-demo--flask-annotated-in-3-seconds">Live demo</a> · 
  <a href="#how-it-works">How it works</a> · 
  <a href="#docs">Docs</a>
</p>

---

An in-source communication protocol where AI agents embed architectural context directly in the files they write. The next agent — different model, different tool, different session — reads it and knows what to do.

No infrastructure. No retrieval pipeline. No external memory. The code carries its own context.

---

## Install

### For AI coding agents

Install the plugin, then run `/codedna:init` — it guides you through everything interactively.

| Agent | Install command |
|-------|---------|
| **Claude Code** | `claude plugin marketplace add Larens94/codedna && claude plugin install codedna@codedna` |
| **Cursor** | `bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh) cursor-hooks` |
| **Copilot** | `bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh) copilot-hooks` |
| **Cline** | `bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh) cline-hooks` |
| **OpenCode** | `bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh) opencode` |
| **Windsurf** | `bash <(curl -fsSL https://raw.githubusercontent.com/Larens94/codedna/main/integrations/install.sh) windsurf` |

After installing, run `/codedna:init` in your project. It will:

1. Auto-detect your languages (PHP, TypeScript, Go, Python, etc.)
2. Ask how to annotate: **Claude session** (zero API key) or **CLI** (tree-sitter, fast)
3. Ask the depth: **human** (minimal) · **semi** (balanced, default) · **agent** (full protocol)
4. Annotate all files and show a summary

### CLI standalone (optional)

For CI pipelines, scripting, or if you prefer the terminal:

```bash
pip install git+https://github.com/Larens94/codedna.git   # requires Python 3.11+
```

```bash
codedna init . --no-llm                        # free, structural only (exports + used_by)
codedna init . --model deepseek/deepseek-chat  # with LLM rules: (~$0.40 for 200 files)
codedna init . --model ollama/llama3           # local LLM, free
codedna check .                                # coverage report
codedna refresh .                              # update exports + used_by (zero LLM cost)
```

> Languages auto-detected — PHP, TypeScript, Go, Java, Kotlin, Ruby all work out of the box.
> Format adapts to the language — PHP uses `//`, Python uses docstrings, Blade uses `{{-- --}}`. See [docs/languages.md](docs/languages.md).

```diff
+  NAVIGATION ACCURACY    ████████████░░░░   +13pp F1     SWE-bench · 3 models
+  FIX QUALITY            ████████████████   7 / 7        Django #13495 · Claude Sonnet
+  TEAM VELOCITY          █████████████░░░   1.6×         5-agent team · DeepSeek R1
+  PROTOCOL ADOPTION      ███████████████░   98.2%        multi-agent SaaS · no instruction
```

---

## The problem

Agent A fixes a bug in `utils.py`. Doesn't know 18 files import from it. Ships a breaking change.

Agent B opens the same file a week later. Spends 20 minutes re-discovering a constraint Agent A already found — and never wrote down.

Agent C adds a feature. Calls `get_invoices()` without filtering suspended tenants. The filter requirement lived in another file. Never seen. Never followed.

**Knowledge dies between sessions.** Every agent starts from scratch.

---

## The solution

<table>
<tr>
<td width="55%">

```python
"""revenue.py — Monthly revenue aggregation.

exports: monthly_revenue(year, month) -> dict
used_by: api/reports.py → revenue_route
         api/serializers.py → Schema [cascade]
rules:   get_invoices() returns ALL tenants
         — MUST filter is_suspended() BEFORE sum
agent:   claude-sonnet | 2026-03-10
         message: "rounding edge case in
                  multi-currency — investigate"
agent:   gemini-2.5-pro | 2026-03-18
         message: "@prev: confirmed → promoted
                  to rules:"
"""
```

</td>
<td width="45%">

**One read. The agent knows:**

**`used_by:`** — 2 files depend on me. One is `[cascade]` — must update if I change.

**`rules:`** — upstream function returns all tenants. I must filter.

**`message:`** — previous agent found a rounding bug. The one after confirmed it and promoted it to a rule.

No grep. No reading 18 files. No re-discovering constraints.

</td>
</tr>
</table>

---

## Evidence

### Agents find the right files faster

SWE-bench, 5 Django bugs, 3 models. Same prompt, same tools. Only difference: CodeDNA annotations.

| Model | Without | With CodeDNA | Delta |
|---|---|---|---|
| Gemini 2.5 Flash | 60% F1 | **72% F1** | **+13pp** (p=0.040) |
| DeepSeek Chat | 50% F1 | **60% F1** | **+9pp** |
| Gemini 2.5 Pro | 60% F1 | **69% F1** | **+9pp** |

### Agents fix the right pattern

Django bug #13495. Same model (Claude Sonnet). One `Rules:` annotation said *"timezone conversion must happen BEFORE datetime functions."* The control agent saw `time_trunc_sql` on the line below the bug — and didn't touch it. CodeDNA did.

| | Without | With CodeDNA |
|---|---|---|
| Files matching official patch | 6 / 7 | **7 / 7** |
| Failed edits | 5 | **0** |

### Agents leave knowledge for each other

5-agent team builds a SaaS webapp. 83 minutes, DeepSeek R1. Agents were shown the `message:` format but never instructed to use it as a backlog or risk tracker. **They did it on their own.**

**53 notes across 54 files.** Three patterns emerged:

```python
# Backlog — "I built this, here's what's still needed"
message: "implement memory summarization for long conversations"

# Risk flag — "This works but I couldn't verify this part"
message: "verify that refresh token rotation prevents replay attacks"

# Architecture — "Consider this for production"
message: "ensure credit balance uses materialized view for performance"
```

Without these notes, the next agent opens `auth_service.py` and has no idea refresh tokens need verification. With them, **the codebase knows what it's missing**.

| Experiment | Result |
|---|---|
| Multi-agent RPG (5 agents, DeepSeek Chat) | **1.6x faster**, playable game vs static scene |
| Multi-agent SaaS (5 agents, DeepSeek R1) | **98.2% adoption**, lower complexity (2.1 vs 3.1) |
| Fix quality (Claude Sonnet) | **7/7** patch files vs 6/7, zero failed edits |

<details>
<summary>Navigation demo — real benchmark data</summary>

![CodeDNA Navigation Demo](./docs/codedna_viz.gif)

> Without CodeDNA: agent opens random files, misses 8/10 critical files.
> With CodeDNA: follows `used_by:` chain, finds 6/10. Retry risk −52%.
> [Interactive version](./docs/codedna_viz_3metaphors.html)

</details>

> [Full benchmark](docs/benchmark.md) · [Experiment details](docs/experiments.md) · [Raw data](benchmark_agent/runs/)

---

## Live demo — Flask annotated in 3 seconds

> **Zero API key. Zero config. A real open-source project.**

```bash
git clone --depth=1 https://github.com/pallets/flask.git
codedna init flask/src/flask --no-llm
codedna refresh flask/src/flask
codedna check flask/src/flask
```

```
Pass 1/3  Scanning...        24 parsed  (0 skipped)
Pass 2/3  Building graph...  111 edges across 21 files
Pass 3/3  Annotating...

L1 modules   Annotated 24 files
L2 functions Added Rules: to 0 functions   ← requires --llm for semantic rules
LLM calls    0

L1 (module headers)   24/24  ✓ 100%
```

Every file now carries its own architectural context — no external database, no config, no server:

<details>
<summary><strong>globals.py</strong> — most-imported module (12 callers)</summary>

```python
"""globals.py — globals module.

exports: none
used_by: __init__.py → current_app, g, request, session
         app.py → _cv_app, app_ctx, g, request, session
         blueprints.py → current_app
         cli.py → current_app
         ctx.py → _cv_app
         debughelpers.py → _cv_app
         helpers.py → _cv_app, app_ctx, current_app, request, session
         json/__init__.py → current_app
         logging.py → request
         templating.py → app_ctx
         views.py → current_app, request
         wrappers.py → current_app
rules:   none
agent:   codedna-cli (no-llm) | codedna-cli | 2026-04-16 | codedna-cli | initial CodeDNA annotation pass
"""
```

</details>

<details>
<summary><strong>app.py</strong> — the Flask class, 6 dependents</summary>

```python
"""app.py — app module.

exports: F | remove_ctx(f) | add_ctx(f) | class Flask
used_by: __init__.py → Flask
         cli.py → Flask
         ctx.py → Flask
         globals.py → Flask
         sessions.py → Flask
         testing.py → Flask
rules:   none
agent:   codedna-cli (no-llm) | codedna-cli | 2026-04-16 | codedna-cli | initial CodeDNA annotation pass
"""
```

</details>

<details>
<summary><strong>signals.py</strong> — 5 callers, every signal mapped to its subscriber</summary>

```python
"""signals.py — signals module.

exports: none
used_by: __init__.py → appcontext_popped, appcontext_pushed, appcontext_tearing_down,
                        before_render_template, got_request_exception, message_flashed,
                        request_finished, request_started, request_tearing_down, template_rendered
         app.py → appcontext_tearing_down, got_request_exception, request_finished,
                  request_started, request_tearing_down
         ctx.py → appcontext_popped, appcontext_pushed
         helpers.py → message_flashed
         templating.py → before_render_template, template_rendered
rules:   none
agent:   codedna-cli (no-llm) | codedna-cli | 2026-04-16 | codedna-cli | initial CodeDNA annotation pass
"""
```

</details>

**What an AI agent now knows without reading any code:**

| Question | Answer — from headers alone |
|---|---|
| "What does `globals.py` export?" | `current_app`, `g`, `request`, `session`, `_cv_app`, `app_ctx` |
| "If I change `globals.py`, what breaks?" | 12 files — listed by name and symbol |
| "Who subscribes to `appcontext_pushed`?" | `__init__.py`, `ctx.py` |
| "What does `sessions.py` expose?" | 5 classes — `SessionMixin`, `SecureCookieSession`, `NullSession`, `SessionInterface`, `SecureCookieSessionInterface` |
| "What imports `Flask` directly?" | `__init__`, `cli`, `ctx`, `globals`, `sessions`, `testing` |

**With any LLM — add `rules:` to every function in one command:**

```bash
pip install 'codedna[litellm]'
export DEEPSEEK_API_KEY=sk-...
codedna init flask/src/flask --model deepseek/deepseek-chat
```

```
Pass 3/3  Annotating...

L1 modules   Annotated 0 files      ← already done, skipped
L2 functions Added Rules: to 78 functions
LLM calls    19
```

19 API calls. 78 functions annotated. Every hidden constraint surfaced:

```python
# ctx.py — push() and pop()
def push(self) -> None:
    """...
    Rules:   Can be pushed multiple times (streaming/testing),
             but matching/signals only trigger on first push.
    """

def pop(self, exc: BaseException | None = _sentinel) -> None:
    """...
    Rules:   MUST be popped exactly as many times as pushed;
             otherwise RuntimeError or premature cleanup.
    """

# config.py — from_object()
def from_object(self, obj: object | str) -> None:
    """...
    Rules:   String argument must be importable module path;
             only UPPERCASE attributes are loaded (dicts won't work).
    """

# cli.py — find_best_app()
def find_best_app(module: ModuleType) -> Flask:
    """...
    Rules:   Module must have exactly one Flask instance if common
             names ('app', 'application') aren't found;
             multiple Flask instances raise exception.
    """
```

An agent reading this project tomorrow skips the source. It reads the headers, knows the constraints, and acts correctly.

---

## Multi-language — Go, Ruby, PHP, and more

The same command works on all supported languages. DeepSeek generates `rules:` for each file from the source — no language-specific config needed.

```bash
# Go (gin framework — 59 files, 0 test files, 56 LLM calls)
codedna init gin/ --extensions go --model deepseek/deepseek-chat
```

```go
// auth.go — auth module.
//
// exports: BasicAuthForRealm | BasicAuthForProxy | BasicAuth | Accounts | AuthUserKey | AuthProxyUserKey
// used_by: none
// rules:   The authentication system uses constant-time comparison for credentials
//          and requires all authorization logic to maintain this security property.
// agent:   deepseek/deepseek-chat | deepseek | 2026-04-16 | codedna-cli | initial CodeDNA annotation pass

// context.go — context module.
//
// exports: Cookie | FileAttachment | HTML | ... | (+135 more)
// used_by: none
// rules:   1. Context struct fields must maintain compatibility with gin's middleware chaining and abort mechanism.
//          2. The mu mutex must be locked before accessing Keys map to ensure thread safety across concurrent requests.
//          3. Changes to exported constants must preserve backward compatibility as they are part of the public API.
// agent:   deepseek/deepseek-chat | deepseek | 2026-04-16 | codedna-cli | initial CodeDNA annotation pass
```

```bash
# Ruby (Sinatra — 7 files, 6 LLM calls)
codedna init sinatra/lib --extensions rb --model deepseek/deepseek-chat
```

```ruby
# base.rb — base module.
#
# exports: Sinatra | Request | Request#accept | ... | (+89 more)
# used_by: none
# rules:   The module must maintain compatibility with Rack's request interface
#          and Sinatra's internal middleware dependencies.
# agent:   deepseek/deepseek-chat | deepseek | 2026-04-16 | codedna-cli | initial CodeDNA annotation pass
```

> `*_test.go` files are automatically excluded. Exports are capped at 20 entries for readability.
> Large files with many exports still show the full count: `(+135 more)`.

---

## How it works

Four levels, like a zoom lens:

```
  Level 0              Level 1                Level 2              Level 3
  .codedna        →    module header     →    function Rules:  →   # Rules: inline
  project map          exports/used_by        + message:           above complex logic
                       /rules/agent
```

> See also: [architecture diagram](docs/diagrams/codedna_architecture.svg)

**`used_by:`** — reverse dependency graph. Who imports this file. The agent follows it instead of grepping.

**`rules:`** — hard constraints. Specific and actionable: *"amount is cents not euros"*, not *"handle errors gracefully."*

**`message:`** — agent-to-agent chat. Gets promoted to `rules:` when confirmed, or dismissed with a reason.

```
  Agent A writes code
       │
       ▼
  message: "rounding edge case"     ← observation, not yet a rule
       │
       ▼
  Agent B reads it (next session)
       │
       ├── confirmed?  YES  →  promoted to rules:
       │
       └── confirmed?  NO   →  dismissed with reason
```

> See also: [message lifecycle diagram](docs/diagrams/codedna_message_lifecycle.svg)

**Header by language:**
- **All languages** — full L1 header: `exports:` + `used_by:` + `rules:` + `agent:` + `message:`
- **All source languages** — also get L2: function-level `Rules:` docstrings (Python, Go, TypeScript, PHP, Java, Kotlin, Ruby)
- **Template engines** — L1 only (Blade, Jinja2, ERB, Handlebars, Razor, Vue SFC, Svelte)

### Modes

| Mode | For whom | What changes |
|---|---|---|
| **human** | Human-written code | Minimal annotations, no semantic naming |
| **semi** | Human + AI together | Annotations on new code, semantic naming on new vars |
| **agent** | AI-first codebases | Full protocol, rename vars, all functions annotated |

```bash
codedna mode semi     # default
codedna mode agent    # full protocol
```

> Full specification: [SPEC.md](./SPEC.md)

---

## Docs

| | |
|---|---|
| [SPEC.md](./SPEC.md) | Protocol specification v0.8 |
| [docs/languages.md](docs/languages.md) | 9 languages, template engines, framework awareness |
| [docs/benchmark.md](docs/benchmark.md) | SWE-bench results, annotation integrity |
| [docs/experiments.md](docs/experiments.md) | Multi-agent experiments |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | Dev setup, contribution guide |

---

## Roadmap

| Milestone | Status |
|---|---|
| Protocol v0.8 + CLI + modes + `message:` | Done |
| Enforcement hooks (Claude, Cursor, Copilot, Cline, OpenCode) | Done |
| 11 languages + tree-sitter AST | Done |
| SWE-bench Verified (500 tasks, 12 repos) | In progress |
| VSCode extension | Planned |
| arXiv preprint | Planned |

---

<p align="center">

I built CodeDNA because AI agents kept making mistakes — not because they were wrong, but because they had no context. What if the context was already in the file?

The data is reproducible and the spec is open. [ko-fi.com/codedna](https://ko-fi.com/codedna)

— Fabrizio

</p>

---

[![Star History Chart](https://api.star-history.com/svg?repos=Larens94/codedna&type=Date)](https://star-history.com/#Larens94/codedna&Date)

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

[MIT](./LICENSE)
