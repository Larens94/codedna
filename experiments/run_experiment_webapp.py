#!/usr/bin/env python3
"""run_experiment_webapp.py — A/B experiment: CodeDNA v0.8 vs Standard Python on a SaaS web app.

exports: run_experiment(condition: str) -> dict, reset_runs(run_id: str | None) -> None
used_by: [manual execution] → see --help
rules:   SHARED_TASK must be byte-identical for both conditions;
         agents must never know they are part of an experiment;
         the word 'codedna' must NEVER appear in any standard-condition instruction or comment;
         each condition writes only inside its own isolated output_dir (os.chdir + FileTools base_dir);
         --reset deletes only experiments/runs/ — never other project files
agent:   claude-sonnet-4-6 | anthropic | 2026-03-30 | s_20260330_002 | New experiment — AgentHub webapp
         message: "message: field now included in condition-A prompt — verify adoption rate vs experiment 1 (0/50 files)"

USAGE:
    python run_experiment_webapp.py                          # run both conditions
    python run_experiment_webapp.py --condition a            # run condition-A only
    python run_experiment_webapp.py --condition b            # run condition-B only
    python run_experiment_webapp.py --list-runs              # show all saved runs
    python run_experiment_webapp.py --reset                  # delete ALL runs
    python run_experiment_webapp.py --clean-run <run_id>     # delete one specific run
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Sequence, Union

from agno.agent import Agent
from agno.team import Team
from agno.team.mode import TeamMode
from agno.models.deepseek import DeepSeek
from agno.tools.file import FileTools
from agno.tools.shell import ShellTools

RUNS_ROOT = Path(__file__).parent / "runs"


# ─────────────────────────────────────────────────────────────────────────────
# REAL-TIME LOGGER
# ─────────────────────────────────────────────────────────────────────────────

class RunLogger:
    """Writes timestamped log entries to run.log and stdout.

    Rules:   Always append — never overwrite; flush after every write.
    """
    def __init__(self, run_dir: Path):
        self.log_file = run_dir / "run.log"
        self._fh = open(self.log_file, "a", buffering=1, encoding="utf-8")

    def log(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        print(line, flush=True)
        self._fh.write(line + "\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()


# ─────────────────────────────────────────────────────────────────────────────
# SHARED TASK — byte-identical for both conditions
# ─────────────────────────────────────────────────────────────────────────────

SHARED_TASK = """
Build a complete, production-ready SaaS web application called "AgentHub" —
a platform where businesses and individuals can rent, configure, and deploy
AI agents for their workflows using the Agno framework.

═══════════════════════════════════════════════════════
PRODUCT VISION
═══════════════════════════════════════════════════════
AgentHub lets users browse a marketplace of pre-built AI agents, configure
their own custom agents, schedule recurring tasks, and monitor usage and costs
in real-time — all via a clean web interface and a REST API.

═══════════════════════════════════════════════════════
CORE FEATURES TO IMPLEMENT
═══════════════════════════════════════════════════════

1. AGENT MARKETPLACE
   - Catalog of pre-built agents: SEO Optimizer, Customer Support Bot,
     Data Analyst, Code Reviewer, Email Drafter, Research Assistant
   - Each agent has: name, description, category, pricing tier, example prompts
   - Browse by category, search by keyword, preview capabilities
   - One-click "Rent Agent" → creates a user session with that agent

2. AGENT STUDIO (Custom Agent Builder)
   - Users configure their own agent: pick base model, write system prompt,
     select tools (web search, file read/write, code execution, calculator)
   - Set memory type: none / session / persistent (SQLite)
   - Save, version, and share agents with teammates
   - Live test console: send a message, see the agent reply in real-time

3. TASK SCHEDULER
   - Define recurring tasks: "Run SEO report every Monday 09:00"
   - Cron-style scheduling with human-readable labels
   - Task history: last 10 runs with status (success/error/timeout)
   - Email/webhook notification on task completion or failure

4. LIVE DASHBOARD
   - Real-time token usage and cost per agent session (SSE stream)
   - Charts: daily token spend, top agents by usage, error rate
   - Global usage cap: stop all agents if monthly budget exceeded
   - Export usage report as CSV

5. TEAM WORKSPACE
   - Create an organisation, invite members by email
   - Roles: Admin (full access), Member (run agents, view own usage),
     Viewer (read-only dashboard)
   - Shared agent library: agents published to the org are visible to all members
   - Audit log: who ran what agent, when, with what input

6. REST API + CLI SDK
   - POST /api/agents/{id}/run — run an agent with a prompt, return result
   - POST /api/tasks — create a scheduled task
   - GET  /api/usage — current billing period usage
   - API key authentication (Bearer token)
   - OpenAPI/Swagger docs auto-generated at /docs

7. BILLING & CREDITS
   - Credit system: 1 credit = 1000 tokens
   - Plans: Free (10k credits/mo), Starter (100k), Pro (1M), Enterprise (custom)
   - Stripe checkout integration for plan upgrades
   - Invoice history, downloadable PDF
   - Hard cap enforcement: agents return 402 when credits exhausted

8. AGENT MEMORY MANAGER
   - Per-agent persistent memory stored in SQLite (key-value + vector similarity)
   - Memory viewer in the UI: inspect, edit, delete individual memories
   - Memory export/import as JSON
   - Automatic memory summarisation when context exceeds 80% of model limit

═══════════════════════════════════════════════════════
TECH STACK
═══════════════════════════════════════════════════════
- Backend  : FastAPI (Python 3.11+)
- AI layer : Agno framework (agno.agent.Agent, agno.team.Team)
- Database : SQLite via SQLAlchemy ORM (models: User, Agent, Task, Run, Credit)
- Frontend : Jinja2 templates + TailwindCSS (CDN) + minimal vanilla JS
- Auth     : JWT (python-jose), bcrypt password hashing
- Scheduler: APScheduler (BackgroundScheduler)
- Billing  : Stripe Python SDK (stripe.checkout.Session)
- Realtime : Server-Sent Events (SSE) for live dashboard

═══════════════════════════════════════════════════════
DIRECTORY STRUCTURE
═══════════════════════════════════════════════════════
agenthub/
├── api/          ← FastAPI routers: agents, tasks, billing, auth, usage
├── agents/       ← Agno agent wrappers + marketplace catalog
├── db/           ← SQLAlchemy models, migrations, seed data
├── scheduler/    ← APScheduler setup, task runner, notification hooks
├── billing/      ← Stripe integration, credit engine, invoice generator
├── frontend/     ← Jinja2 templates, static CSS/JS
├── auth/         ← JWT, OAuth2 password flow, API key management
└── main.py       ← FastAPI app factory, router registration, startup

═══════════════════════════════════════════════════════
QUALITY REQUIREMENTS
═══════════════════════════════════════════════════════
- Every route must have input validation (Pydantic models)
- Database operations use SQLAlchemy sessions (no raw SQL)
- All Agno agent calls must be wrapped with token counting
- Authentication required on all routes except /docs, /health, /marketplace (read-only)
- Stripe webhooks must verify signature before processing
- Error responses follow RFC 7807 (application/problem+json)
- Include a seed script (db/seed.py) that creates demo user + 6 marketplace agents

OUTPUT: A complete, runnable AgentHub application.
        Run with: uvicorn agenthub.main:app --reload
"""


# ─────────────────────────────────────────────────────────────────────────────
# CONDITION-A INSTRUCTIONS  (CodeDNA v0.8 annotation protocol + message: field)
# ─────────────────────────────────────────────────────────────────────────────

def _instr_a_director() -> str:
    return """You are the Product Architect on a professional SaaS development team.
You design the overall system, own the FastAPI app factory, and coordinate four specialists.

Your team uses an in-source annotation protocol as its communication standard.
Every Python file your team produces must open with this exact header:

    \"\"\"filename.py — <purpose, max 15 words>.

    exports: <function(arg) -> return_type or class>
    used_by: <consumer_file.py → consumer_function>
    rules:   <hard architectural constraints — update in-place when you discover new ones>
    agent:   <YourName> | <YYYY-MM-DD> | <what you implemented and what you noticed>
             message: "<open hypothesis or unverified observation for the next agent to verify>"
    \"\"\"

The message: sub-field is the inter-agent chat channel. Use it for observations not yet
certain enough to become rules. The next agent must either:
  - promote it to rules: and reply "@prev: promoted to rules:"
  - dismiss it and reply "@prev: not applicable because <reason>"
Never delete a message: line — always append.

For functions with non-obvious constraints, add a Rules: docstring:

    def create_agent_session(user_id: int) -> Session:
        \"\"\"One-line description.
        Rules:   must deduct credits before starting the Agno run; rollback on AgnoError
        message: claude-sonnet-4-6 | 2026-03-30 | verify credit deduction is atomic with session creation
        \"\"\"

Semantic naming — data-carrying variables use <type>_<shape>_<domain>_<origin>:
    list_dict_agents_from_db   = db.query(Agent).all()    # correct
    dict_config_stripe_from_env = load_stripe_config()   # correct
    data = db.query(Agent).all()                          # avoid

YOUR RESPONSIBILITIES:
1. Create the full directory structure: agenthub/api/, agenthub/agents/,
   agenthub/db/, agenthub/scheduler/, agenthub/billing/, agenthub/frontend/, agenthub/auth/
2. Write agenthub/main.py — FastAPI app factory, router registration, lifespan hook
3. Write agenthub/db/models.py — SQLAlchemy models: User, Agent, AgentRun, ScheduledTask,
   CreditAccount, Invoice, OrgMembership, AuditLog
4. Write agenthub/db/session.py — engine, SessionLocal, get_db dependency
5. Delegate each domain to the right specialist with clear used_by contracts
6. Verify all files follow the annotation protocol before integration
7. Log architectural decisions in docs/architecture.md
"""


def _instr_a_backend() -> str:
    return """You are the Backend Engineer on a professional SaaS development team.
Your domain is agenthub/api/ — all FastAPI routers and business logic.

Your team uses an in-source annotation protocol as its communication standard.
Every Python file you produce must open with this exact header:

    \"\"\"filename.py — <purpose, max 15 words>.

    exports: <router or function>
    used_by: <consumer_file.py → consumer_function>
    rules:   <hard architectural constraints>
    agent:   BackendEngineer | <YYYY-MM-DD> | <what you implemented>
             message: "<open hypothesis for the next agent>"
    \"\"\"

Semantic naming:
    router_agents    = APIRouter(prefix="/api/agents")    # correct
    obj = APIRouter()                                     # avoid

DELIVERABLES for agenthub/api/:
- api/agents.py    — CRUD agents, POST /{id}/run (triggers Agno, streams response via SSE)
- api/auth.py      — POST /register, POST /login (JWT), GET /me, POST /api-keys
- api/tasks.py     — CRUD scheduled tasks, GET /{id}/history
- api/billing.py   — GET /usage, POST /checkout (Stripe), GET /invoices, webhook handler
- api/usage.py     — GET /usage/stream (SSE real-time token counter)
- api/workspace.py — org CRUD, member invite, role management, audit log

Rules for ALL routes:
- Input: Pydantic request schema (schemas.py in same folder)
- Output: Pydantic response schema — never return raw ORM objects
- Auth: Depends(get_current_user) on every route except /health and /marketplace
- Errors: raise HTTPException with RFC 7807 detail dict
- Credit check: call billing.deduct_credits() before any Agno run; rollback on failure

Log decisions in docs/api_decisions.md
"""


def _instr_a_agent_integrator() -> str:
    return """You are the Agent Integrator on a professional SaaS development team.
Your domain is agenthub/agents/ — all Agno agent wrappers and the marketplace catalog.

Your team uses an in-source annotation protocol as its communication standard.
Every Python file you produce must open with this exact header:

    \"\"\"filename.py — <purpose, max 15 words>.

    exports: <class or function>
    used_by: <consumer_file.py → consumer_function>
    rules:   <hard architectural constraints>
    agent:   AgentIntegrator | <YYYY-MM-DD> | <what you implemented>
             message: "<open hypothesis for the next agent>"
    \"\"\"

Semantic naming:
    dict_tools_available_from_agno = {"web_search": WebSearchTool(), ...}  # correct
    tools = {...}                                                            # avoid

DELIVERABLES for agenthub/agents/:
- agents/base.py       — AgentWrapper: wraps agno.Agent, counts tokens, enforces credit cap
- agents/catalog.py    — MARKETPLACE_AGENTS: list of 6 AgentSpec dataclasses
                         (SEO Optimizer, Customer Support Bot, Data Analyst,
                          Code Reviewer, Email Drafter, Research Assistant)
- agents/studio.py     — build_custom_agent(config: AgentConfig) -> agno.Agent
                         accepts: model, system_prompt, tools list, memory_type
- agents/memory.py     — PersistentMemory: SQLite-backed key-value + simple similarity search
                         methods: store(key, value), retrieve(query, top_k=5), clear()
- agents/runner.py     — run_agent_stream(agent, prompt, user_id, db) -> AsyncGenerator[str]
                         streams SSE chunks, updates AgentRun record, deducts credits

Rules:
- Never call agno.Agent directly from API layer — always go through AgentWrapper
- Token count must be extracted from agno response metadata and stored in AgentRun.tokens_used
- AgentWrapper must raise CreditExhaustedError (HTTP 402) before starting if balance < min_credits
- All agent instructions must be sanitised (strip HTML, limit to 10k chars)

Log decisions in docs/agent_decisions.md
"""


def _instr_a_data() -> str:
    return """You are the Data Engineer on a professional SaaS development team.
Your domain is agenthub/db/, agenthub/billing/, and agenthub/scheduler/.

Your team uses an in-source annotation protocol as its communication standard.
Every Python file you produce must open with this exact header:

    \"\"\"filename.py — <purpose, max 15 words>.

    exports: <class or function>
    used_by: <consumer_file.py → consumer_function>
    rules:   <hard architectural constraints>
    agent:   DataEngineer | <YYYY-MM-DD> | <what you implemented>
             message: "<open hypothesis for the next agent>"
    \"\"\"

Semantic naming:
    int_credits_remaining_from_db = account.credits - used   # correct
    credits = account.credits - used                          # avoid

DELIVERABLES:

agenthub/db/:
- db/models.py   — SQLAlchemy models (see ProductArchitect spec)
- db/session.py  — engine, SessionLocal, get_db FastAPI dependency
- db/seed.py     — creates demo@agenthub.io user + 6 marketplace agents + Free plan credits
- db/migrations/ — Alembic env.py + initial migration

agenthub/billing/:
- billing/credits.py  — CreditEngine: deduct(user_id, amount), refund(user_id, amount),
                         get_balance(user_id) → int, enforce_cap(user_id) → bool
- billing/stripe.py   — create_checkout_session(user_id, plan) → str (URL),
                         handle_webhook(payload, sig) → None (idempotent)
- billing/invoices.py — generate_invoice_pdf(invoice_id) → bytes (using reportlab or fpdf2)
- billing/plans.py    — PLANS dict: Free/Starter/Pro/Enterprise credit limits and prices

agenthub/scheduler/:
- scheduler/setup.py  — APScheduler BackgroundScheduler, add_job, remove_job
- scheduler/runner.py — execute_scheduled_task(task_id, db) — runs agent, saves result,
                         sends webhook/email notification

Rules:
- All DB writes must be in explicit transactions; rollback on any exception
- Stripe webhook must verify X-Stripe-Signature before processing — raise 400 on invalid
- Credit deduction must be atomic: use SELECT FOR UPDATE pattern or SQLite EXCLUSIVE transaction
- Never store raw Stripe secret keys in DB — only last4 of card and customer_id

Log decisions in docs/data_decisions.md
"""


def _instr_a_frontend() -> str:
    return """You are the Frontend Designer on a professional SaaS development team.
Your domain is agenthub/frontend/ and agenthub/auth/.

Your team uses an in-source annotation protocol as its communication standard.
Every Python file you produce must open with this exact header:

    \"\"\"filename.py — <purpose, max 15 words>.

    exports: <router or function>
    used_by: <consumer_file.py → consumer_function>
    rules:   <hard architectural constraints>
    agent:   FrontendDesigner | <YYYY-MM-DD> | <what you implemented>
             message: "<open hypothesis for the next agent>"
    \"\"\"

Semantic naming:
    router_frontend = APIRouter()            # correct
    r = APIRouter()                          # avoid

DELIVERABLES:

agenthub/auth/:
- auth/jwt.py     — create_access_token(data) -> str, decode_token(token) -> dict,
                    get_current_user(token, db) -> User FastAPI dependency
- auth/security.py — hash_password(plain) -> str, verify_password(plain, hashed) -> bool,
                     generate_api_key() -> str (hex 32 bytes)
- auth/oauth2.py  — OAuth2PasswordBearer scheme, login_for_access_token route

agenthub/frontend/:
- frontend/routes.py  — Jinja2 page routes: /, /marketplace, /studio, /dashboard,
                         /scheduler, /workspace, /billing
- frontend/templates/ — base.html (nav + TailwindCSS CDN), index.html, marketplace.html,
                         studio.html, dashboard.html (with SSE chart), scheduler.html,
                         workspace.html, billing.html
- frontend/static/    — app.js: SSE client for live dashboard, studio chat console,
                         agent run streaming

UI requirements:
- TailwindCSS via CDN — no build step required
- Dark sidebar navigation with active state
- Marketplace grid: agent cards with icon, description, pricing badge, "Rent" button
- Studio: split pane (config left, chat console right) with streaming reply
- Dashboard: usage bar chart (Chart.js CDN), cost counter, recent runs table
- All forms use HTMX (CDN) for partial page updates — no full page reloads

Rules:
- Templates must extend base.html — never inline full HTML in Python
- CSRF token required on all POST forms
- SSE endpoint /api/usage/stream must be called with EventSource, not fetch
- Never render raw user input in templates — always use Jinja2 autoescape

Log decisions in docs/frontend_decisions.md
"""


# ─────────────────────────────────────────────────────────────────────────────
# CONDITION-B INSTRUCTIONS  (standard Python best practices — no annotations)
# ─────────────────────────────────────────────────────────────────────────────

def _instr_b_director() -> str:
    return """You are the Product Architect on a professional SaaS development team.
You design the overall system, own the FastAPI app factory, and coordinate four specialists.

YOUR RESPONSIBILITIES:
1. Create the full directory structure: agenthub/api/, agenthub/agents/,
   agenthub/db/, agenthub/scheduler/, agenthub/billing/, agenthub/frontend/, agenthub/auth/
2. Write agenthub/main.py — FastAPI app factory, router registration, lifespan hook
3. Write agenthub/db/models.py — SQLAlchemy models: User, Agent, AgentRun, ScheduledTask,
   CreditAccount, Invoice, OrgMembership, AuditLog
4. Write agenthub/db/session.py — engine, SessionLocal, get_db dependency
5. Delegate each domain to the right specialist with clear interfaces
6. Log architectural decisions in docs/architecture.md

CODING STANDARDS:
- Follow PEP 8 style guidelines
- Write clear Google-style docstrings for all public APIs
- Use type hints for all public functions
- Apply SOLID principles and separation of concerns
- Prefer composition over inheritance
"""


def _instr_b_backend() -> str:
    return """You are the Backend Engineer on a professional SaaS development team.
Your domain is agenthub/api/ — all FastAPI routers and business logic.

DELIVERABLES for agenthub/api/:
- api/agents.py    — CRUD agents, POST /{id}/run (triggers Agno, streams response via SSE)
- api/auth.py      — POST /register, POST /login (JWT), GET /me, POST /api-keys
- api/tasks.py     — CRUD scheduled tasks, GET /{id}/history
- api/billing.py   — GET /usage, POST /checkout (Stripe), GET /invoices, webhook handler
- api/usage.py     — GET /usage/stream (SSE real-time token counter)
- api/workspace.py — org CRUD, member invite, role management, audit log

Rules for ALL routes:
- Input validation with Pydantic
- JWT authentication required on protected routes
- Proper HTTP error responses

CODING STANDARDS:
- Follow PEP 8 style guidelines
- Write clear Google-style docstrings for all public APIs
- Use type hints for all public functions
- Apply SOLID principles and separation of concerns

Log decisions in docs/api_decisions.md
"""


def _instr_b_agent_integrator() -> str:
    return """You are the Agent Integrator on a professional SaaS development team.
Your domain is agenthub/agents/ — all Agno agent wrappers and the marketplace catalog.

DELIVERABLES for agenthub/agents/:
- agents/base.py       — AgentWrapper: wraps agno.Agent, counts tokens, enforces credit cap
- agents/catalog.py    — MARKETPLACE_AGENTS: list of 6 AgentSpec dataclasses
                         (SEO Optimizer, Customer Support Bot, Data Analyst,
                          Code Reviewer, Email Drafter, Research Assistant)
- agents/studio.py     — build_custom_agent(config: AgentConfig) -> agno.Agent
- agents/memory.py     — PersistentMemory: SQLite-backed key-value store
- agents/runner.py     — run_agent_stream(agent, prompt, user_id, db) -> AsyncGenerator[str]

CODING STANDARDS:
- Follow PEP 8 style guidelines
- Write clear Google-style docstrings for all public APIs
- Use type hints for all public functions
- Apply SOLID principles and separation of concerns

Log decisions in docs/agent_decisions.md
"""


def _instr_b_data() -> str:
    return """You are the Data Engineer on a professional SaaS development team.
Your domain is agenthub/db/, agenthub/billing/, and agenthub/scheduler/.

DELIVERABLES:

agenthub/db/:
- db/models.py, db/session.py, db/seed.py, db/migrations/

agenthub/billing/:
- billing/credits.py, billing/stripe.py, billing/invoices.py, billing/plans.py

agenthub/scheduler/:
- scheduler/setup.py, scheduler/runner.py

CODING STANDARDS:
- Follow PEP 8 style guidelines
- Write clear Google-style docstrings for all public APIs
- Use type hints for all public functions
- Apply SOLID principles and separation of concerns

Log decisions in docs/data_decisions.md
"""


def _instr_b_frontend() -> str:
    return """You are the Frontend Designer on a professional SaaS development team.
Your domain is agenthub/frontend/ and agenthub/auth/.

DELIVERABLES:

agenthub/auth/:
- auth/jwt.py, auth/security.py, auth/oauth2.py

agenthub/frontend/:
- frontend/routes.py, frontend/templates/, frontend/static/

UI: TailwindCSS CDN, dark sidebar nav, marketplace grid, studio split-pane,
    dashboard with Chart.js, HTMX for partial updates.

CODING STANDARDS:
- Follow PEP 8 style guidelines
- Write clear Google-style docstrings for all public APIs
- Use type hints for all public functions
- Apply SOLID principles and separation of concerns

Log decisions in docs/frontend_decisions.md
"""


# ─────────────────────────────────────────────────────────────────────────────
# TEAM FACTORY
# ─────────────────────────────────────────────────────────────────────────────

def _build_team(condition: str, output_dir: Path) -> Team:
    """Build the 5-agent webapp team for the given condition.

    Rules:   output_dir must be absolute and already exist;
             caller must os.chdir(output_dir) before team.run() to isolate stray writes.
    """
    model = DeepSeek(id="deepseek-chat")
    tools = [FileTools(base_dir=output_dir), ShellTools()]

    if condition == "a":
        specs = [
            ("ProductArchitect",  "Design system architecture and own app factory",  _instr_a_director()),
            ("BackendEngineer",   "Implement agenthub/api/ FastAPI routers",          _instr_a_backend()),
            ("AgentIntegrator",   "Implement agenthub/agents/ Agno wrappers",         _instr_a_agent_integrator()),
            ("DataEngineer",      "Implement db/, billing/, scheduler/",              _instr_a_data()),
            ("FrontendDesigner",  "Implement frontend/ templates and auth/",          _instr_a_frontend()),
        ]
    else:
        specs = [
            ("ProductArchitect",  "Design system architecture and own app factory",  _instr_b_director()),
            ("BackendEngineer",   "Implement agenthub/api/ FastAPI routers",          _instr_b_backend()),
            ("AgentIntegrator",   "Implement agenthub/agents/ Agno wrappers",         _instr_b_agent_integrator()),
            ("DataEngineer",      "Implement db/, billing/, scheduler/",              _instr_b_data()),
            ("FrontendDesigner",  "Implement frontend/ templates and auth/",          _instr_b_frontend()),
        ]

    members: List[Union[Agent, Team]] = [
        Agent(name=name, role=role, instructions=instr, model=model, tools=tools,
              tool_call_limit=30)
        for name, role, instr in specs
    ]

    return Team(
        name=f"AgentHub Dev Team [{condition.upper()}]",
        members=members,
        model=model,
        mode=TeamMode.coordinate,
        max_iterations=200,
    )


# ─────────────────────────────────────────────────────────────────────────────
# METRICS
# ─────────────────────────────────────────────────────────────────────────────

def _collect_metrics(output_dir: Path) -> dict:
    """Scan output_dir for code metrics. Read-only."""
    py_files = list(output_dir.rglob("*.py"))
    total_lines = 0
    files_with_header = 0
    annotation_counts = {"exports": 0, "used_by": 0, "rules": 0, "agent": 0, "message": 0}
    html_files = len(list(output_dir.rglob("*.html")))
    js_files   = len(list(output_dir.rglob("*.js")))

    for f in py_files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            lines = text.splitlines()
            total_lines += len(lines)
            header = "\n".join(lines[:25])
            if "exports:" in header:
                files_with_header += 1
            for key in annotation_counts:
                if f"{key}:" in header:
                    annotation_counts[key] += 1
        except OSError:
            pass

    n = len(py_files)
    return {
        "python_file_count": n,
        "html_file_count": html_files,
        "js_file_count": js_files,
        "total_lines_of_code": total_lines,
        "files_with_annotation_header": files_with_header,
        "annotation_coverage_pct": round(100 * files_with_header / n, 1) if n else 0.0,
        "annotation_counts": annotation_counts,
    }


def _validate_application(output_dir: Path) -> dict:
    """Validate generated application structure and syntax.
    
    Returns dict with validation results.
    """
    import ast
    import subprocess
    import sys
    
    validation = {
        "has_main_py": False,
        "main_py_syntax_valid": False,
        "essential_dirs": [],
        "total_files": 0,
        "syntax_errors": [],
        "import_errors": [],
        "basic_test_passed": False,
    }
    
    # Check essential structure
    main_py = output_dir / "agenthub" / "main.py"
    validation["has_main_py"] = main_py.exists()
    
    essential_dirs = ["api", "agents", "db", "scheduler", "billing", "frontend", "auth"]
    for d in essential_dirs:
        if (output_dir / "agenthub" / d).exists():
            validation["essential_dirs"].append(d)
    
    # Count total Python files
    py_files = list(output_dir.rglob("*.py"))
    validation["total_files"] = len(py_files)
    
    # Syntax check for all Python files
    for f in py_files[:20]:  # Limit to first 20 files to avoid timeout
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            ast.parse(content)
        except SyntaxError as e:
            validation["syntax_errors"].append({
                "file": str(f.relative_to(output_dir)),
                "error": str(e),
                "line": e.lineno,
            })
    
    # Specific validation for main.py
    if main_py.exists():
        try:
            content = main_py.read_text(encoding="utf-8")
            ast.parse(content)
            validation["main_py_syntax_valid"] = True
            
            # Try to check if it's a valid FastAPI app (basic heuristic)
            if "FastAPI" in content or "from fastapi import FastAPI" in content:
                validation["basic_test_passed"] = True
                
        except SyntaxError as e:
            validation["syntax_errors"].append({
                "file": "agenthub/main.py",
                "error": str(e),
                "line": e.lineno,
            })
    
    # Try to run a simple syntax check via python -m py_compile (optional)
    if py_files:
        test_file = py_files[0]
        try:
            subprocess.run(
                [sys.executable, "-m", "py_compile", str(test_file)],
                capture_output=True,
                timeout=5,
                check=True
            )
            validation["py_compile_test"] = True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            validation["py_compile_test"] = False
    
    validation["score"] = (
        (validation["has_main_py"] * 2) +
        (validation["main_py_syntax_valid"] * 2) +
        (len(validation["essential_dirs"]) / len(essential_dirs) * 3) +
        (validation["basic_test_passed"] * 2) +
        (0 if validation["syntax_errors"] else 1)
    ) / 10.0  # Normalize to 0-1
    
    return validation


def _measure_code_quality(output_dir: Path) -> dict:
    """Measure code quality metrics using AST analysis."""
    import ast
    
    py_files = list(output_dir.rglob("*.py"))
    quality = {
        "total_files": len(py_files),
        "functions": 0,
        "classes": 0,
        "avg_function_length": 0.0,
        "avg_class_length": 0.0,
        "files_with_docstrings": 0,
        "functions_with_docstrings": 0,
        "classes_with_docstrings": 0,
        "cyclomatic_complexity_total": 0,
        "max_function_complexity": 0,
        "import_count": 0,
        "avg_imports_per_file": 0.0,
        "avg_function_complexity": 0.0,
        "quality_score": 0.0,
    }
    
    if not py_files:
        return quality
    
    total_function_lines = 0
    total_class_lines = 0
    total_imports = 0
    files_with_docstring = 0
    
    for f in py_files[:30]:  # Limit analysis to 30 files
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content)
            
            # Count imports
            imports = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)))
            total_imports += imports
            
            # Check module-level docstring
            if ast.get_docstring(tree):
                files_with_docstring += 1
            
            # Walk through AST nodes
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    quality["functions"] += 1
                    # Function length (lines)
                    func_lines = node.end_lineno - node.lineno if node.end_lineno else 0
                    total_function_lines += func_lines
                    # Docstring
                    if ast.get_docstring(node):
                        quality["functions_with_docstrings"] += 1
                    # Cyclomatic complexity approximation
                    complexity = 1  # base complexity
                    for subnode in ast.walk(node):
                        if isinstance(subnode, (ast.If, ast.While, ast.For, ast.AsyncFor,
                                               ast.Try, ast.ExceptHandler, ast.Assert,
                                               ast.And, ast.Or)):
                            complexity += 1
                    quality["cyclomatic_complexity_total"] += complexity
                    if complexity > quality["max_function_complexity"]:
                        quality["max_function_complexity"] = complexity
                        
                elif isinstance(node, ast.ClassDef):
                    quality["classes"] += 1
                    # Class length
                    class_lines = node.end_lineno - node.lineno if node.end_lineno else 0
                    total_class_lines += class_lines
                    # Docstring
                    if ast.get_docstring(node):
                        quality["classes_with_docstrings"] += 1
        
        except (SyntaxError, UnicodeDecodeError):
            continue
    
    quality["files_with_docstrings"] = files_with_docstring
    quality["import_count"] = total_imports
    
    if quality["functions"] > 0:
        quality["avg_function_length"] = round(total_function_lines / quality["functions"], 1)
        quality["avg_function_complexity"] = round(quality["cyclomatic_complexity_total"] / quality["functions"], 2)
    else:
        quality["avg_function_complexity"] = 0
    
    if quality["classes"] > 0:
        quality["avg_class_length"] = round(total_class_lines / quality["classes"], 1)
    
    if len(py_files[:30]) > 0:
        quality["avg_imports_per_file"] = round(total_imports / len(py_files[:30]), 1)
    
    # Calculate overall quality score (0-1)
    score_components = []
    
    # Docstring coverage
    if quality["functions"] > 0:
        docstring_coverage = quality["functions_with_docstrings"] / quality["functions"]
        score_components.append(docstring_coverage * 0.3)
    
    # File docstring coverage
    file_doc_coverage = files_with_docstring / len(py_files[:30]) if py_files[:30] else 0
    score_components.append(file_doc_coverage * 0.2)
    
    # Complexity penalty (lower is better)
    if quality["functions"] > 0:
        complexity_norm = max(0, 1 - (quality["avg_function_complexity"] - 2) / 10)  # Target ~2
        score_components.append(complexity_norm * 0.3)
    
    # Import organization (simple heuristic)
    import_norm = min(1, 10 / (quality["avg_imports_per_file"] + 1))  # Lower imports better
    score_components.append(import_norm * 0.2)
    
    quality["quality_score"] = round(sum(score_components), 3) if score_components else 0
    
    return quality


def _generate_reports(run_dir: Path, results: dict) -> None:
    """Generate HTML and CSV reports for the experiment results."""
    import csv
    
    reports_dir = run_dir / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    # CSV summary report
    csv_path = reports_dir / "summary.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "condition", "label", "success", "duration_seconds",
            "python_files", "html_files", "total_loc",
            "annotation_coverage_pct", "message_count",
            "validation_score", "quality_score",
            "functions", "classes", "docstring_coverage_pct",
            "avg_complexity", "syntax_errors"
        ])
        
        for cond, res in results.get("conditions", {}).items():
            m = res.get("metrics", {})
            v = res.get("validation", {})
            q = res.get("code_quality", {})
            
            doc_cov = 0
            if q.get("functions", 0) > 0:
                doc_cov = round(100 * q.get("functions_with_docstrings", 0) / q["functions"], 1)
            
            writer.writerow([
                cond,
                res.get("label", ""),
                res.get("success", False),
                res.get("duration_seconds", 0),
                m.get("python_file_count", 0),
                m.get("html_file_count", 0),
                m.get("total_lines_of_code", 0),
                m.get("annotation_coverage_pct", 0),
                m.get("annotation_counts", {}).get("message", 0),
                v.get("score", 0),
                q.get("quality_score", 0),
                q.get("functions", 0),
                q.get("classes", 0),
                doc_cov,
                q.get("avg_function_complexity", 0),
                len(v.get("syntax_errors", []))
            ])
    
    # HTML report
    html_path = reports_dir / "report.html"
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Experiment Report - {results.get('run_id', 'unknown')}</title>
    <style>
        body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #f8f9fa; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: #2c3e50; color: white; padding: 2rem; border-radius: 10px; }}
        .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; margin: 2rem 0; }}
        .card {{ background: white; border-radius: 8px; padding: 1.5rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .card h3 {{ margin-top: 0; color: #2c3e50; }}
        .comparison {{ display: flex; gap: 2rem; margin-top: 2rem; }}
        .condition {{ flex: 1; background: white; padding: 1.5rem; border-radius: 8px; }}
        .condition-a {{ border-left: 5px solid #3498db; }}
        .condition-b {{ border-left: 5px solid #f39c12; }}
        .metric {{ display: flex; justify-content: space-between; margin: 0.5rem 0; }}
        .metric .value {{ font-weight: bold; }}
        .success {{ color: #27ae60; }}
        .error {{ color: #e74c3c; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
        th, td {{ padding: 0.75rem; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Experiment Report</h1>
            <p>Run ID: <strong>{results.get('run_id', 'unknown')}</strong></p>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="cards">
            <div class="card">
                <h3>📊 Overview</h3>
                <p>Comparison between Annotation Protocol (Condition A) and Standard Practices (Condition B).</p>
                <p><strong>Total Conditions:</strong> {len(results.get('conditions', {}))}</p>
                <p><strong>Successful:</strong> {sum(1 for r in results.get('conditions', {}).values() if r.get('success'))}</p>
            </div>
            <div class="card">
                <h3>📈 Key Metrics</h3>
                <div class="metric"><span>Total Python Files:</span> <span class="value">{sum(r.get('metrics', {}).get('python_file_count', 0) for r in results.get('conditions', {}).values())}</span></div>
                <div class="metric"><span>Total Lines of Code:</span> <span class="value">{sum(r.get('metrics', {}).get('total_lines_of_code', 0) for r in results.get('conditions', {}).values())}</span></div>
                <div class="metric"><span>Average Validation Score:</span> <span class="value">{round(sum(r.get('validation', {}).get('score', 0) for r in results.get('conditions', {}).values()) / max(len(results.get('conditions', {})), 1), 2)}</span></div>
            </div>
        </div>
        
        <div class="comparison">
    """
    
    # Add condition details
    labels = {"a": "Annotation Protocol", "b": "Standard Practices"}
    for cond, res in results.get("conditions", {}).items():
        m = res.get("metrics", {})
        v = res.get("validation", {})
        q = res.get("code_quality", {})
        
        doc_cov = "N/A"
        if q.get("functions", 0) > 0:
            doc_cov = f"{round(100 * q.get('functions_with_docstrings', 0) / q['functions'], 1)}%"
        
        html_content += f"""
            <div class="condition condition-{cond}">
                <h2>Condition {cond.upper()} - {labels.get(cond, cond)}</h2>
                <p class="{'success' if res.get('success') else 'error'}">
                    <strong>Status:</strong> {'✅ Success' if res.get('success') else '❌ Error'}
                </p>
                <p><strong>Duration:</strong> {res.get('duration_seconds', 0)} seconds</p>
                
                <h3>📁 Files & Structure</h3>
                <div class="metric"><span>Python Files:</span> <span class="value">{m.get('python_file_count', 0)}</span></div>
                <div class="metric"><span>HTML Files:</span> <span class="value">{m.get('html_file_count', 0)}</span></div>
                <div class="metric"><span>Total LOC:</span> <span class="value">{m.get('total_lines_of_code', 0)}</span></div>
                <div class="metric"><span>Annotation Coverage:</span> <span class="value">{m.get('annotation_coverage_pct', 0)}%</span></div>
                <div class="metric"><span>Message Count:</span> <span class="value">{m.get('annotation_counts', {{}}).get('message', 0)}</span></div>
                
                <h3>✅ Validation</h3>
                <div class="metric"><span>Validation Score:</span> <span class="value">{v.get('score', 0):.2f}</span></div>
                <div class="metric"><span>Syntax Errors:</span> <span class="value">{len(v.get('syntax_errors', []))}</span></div>
                <div class="metric"><span>Has Main.py:</span> <span class="value">{'✅' if v.get('has_main_py') else '❌'}</span></div>
                
                <h3>⚙️ Code Quality</h3>
                <div class="metric"><span>Quality Score:</span> <span class="value">{q.get('quality_score', 0):.3f}</span></div>
                <div class="metric"><span>Functions/Classes:</span> <span class="value">{q.get('functions', 0)} / {q.get('classes', 0)}</span></div>
                <div class="metric"><span>Docstring Coverage:</span> <span class="value">{doc_cov}</span></div>
                <div class="metric"><span>Avg Complexity:</span> <span class="value">{q.get('avg_function_complexity', 0):.2f}</span></div>
            </div>
        """
    
    html_content += """
        </div>
        
        <div class="card">
            <h3>📋 Detailed Metrics</h3>
            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
    """
    
    # Table headers
    for cond in results.get("conditions", {}).keys():
        html_content += f"<th>Condition {cond.upper()}</th>"
    html_content += "</tr></thead><tbody>"
    
    # Table rows
    metrics = [
        ("Python Files", lambda r: r.get("metrics", {}).get("python_file_count", 0)),
        ("HTML Files", lambda r: r.get("metrics", {}).get("html_file_count", 0)),
        ("Total LOC", lambda r: r.get("metrics", {}).get("total_lines_of_code", 0)),
        ("Annotation Coverage", lambda r: f"{r.get('metrics', {}).get('annotation_coverage_pct', 0)}%"),
        ("Message Count", lambda r: r.get("metrics", {}).get("annotation_counts", {}).get("message", 0)),
        ("Validation Score", lambda r: f"{r.get('validation', {}).get('score', 0):.2f}"),
        ("Quality Score", lambda r: f"{r.get('code_quality', {}).get('quality_score', 0):.3f}"),
        ("Functions", lambda r: r.get("code_quality", {}).get("functions", 0)),
        ("Classes", lambda r: r.get("code_quality", {}).get("classes", 0)),
        ("Syntax Errors", lambda r: len(r.get("validation", {}).get("syntax_errors", []))),
    ]
    
    for metric_name, extractor in metrics:
        html_content += f"<tr><td><strong>{metric_name}</strong></td>"
        for cond, res in results.get("conditions", {}).items():
            html_content += f"<td>{extractor(res)}</td>"
        html_content += "</tr>"
    
    html_content += """
                </tbody>
            </table>
        </div>
        
        <div class="card">
            <h3>📄 Files</h3>
            <p>Detailed results available in:</p>
            <ul>
                <li><code>comparison.json</code> - Full JSON results</li>
                <li><code>reports/summary.csv</code> - CSV summary</li>
                <li><code>run.log</code> - Execution log</li>
            </ul>
        </div>
    </div>
</body>
</html>
    """
    
    html_path.write_text(html_content, encoding="utf-8")
    
    print(f"  Reports generated: {reports_dir}/")


def _run_with_retry(team, task: str, max_retries: int = 3, logger=None) -> tuple[bool, list, list]:
    """Run team task with exponential backoff retry on failure.
    
    Returns: (success, chunks, error_events)
    """
    import time
    
    chunks = []
    error_events = []
    base_delay = 2  # seconds
    
    for attempt in range(max_retries):
        if attempt > 0 and logger:
            logger.log(f"Retry attempt {attempt}/{max_retries} after {base_delay * (2 ** (attempt-1))}s delay")
            time.sleep(base_delay * (2 ** (attempt-1)))
        
        try:
            current_chunks = []
            current_errors = []
            _last_member = None
            _SKIP = {"RunContentEvent", "RunResponseContentEvent",
                     "TeamRunResponseContentEvent", "AgentRunResponseContentEvent"}
            
            for event in team.run(task, stream=True):
                event_type = type(event).__name__
                current_chunks.append(str(event))
                
                if "Error" in event_type:
                    err_content = (getattr(event, "content", None)
                                   or getattr(event, "error", None)
                                   or event_type)
                    current_errors.append(str(err_content))
                    if logger:
                        logger.log(f"ERROR EVENT ({event_type}): {str(err_content)[:120]}")
                    continue
                
                if event_type in _SKIP:
                    continue
                
                member    = (getattr(event, "member_name", None)
                             or getattr(event, "agent_name", None)
                             or "Team")
                tool      = getattr(event, "tool_name", None)
                tool_args = getattr(event, "tool_args", None) or getattr(event, "function_call", None)
                
                if tool and logger:
                    args_str = ""
                    if isinstance(tool_args, dict):
                        first    = next(iter(tool_args.values()), "")
                        args_str = f"({str(first)[:60]})"
                    logger.log(f"{member}: {tool}{args_str} completed")
                elif logger:
                    if member != _last_member:
                        logger.log(f"→ {member} [{event_type}]")
                        _last_member = member
                    elif event_type not in ("RunEvent", "TeamRunEvent"):
                        content = getattr(event, "content", None)
                        if content and len(str(content)) > 20:
                            snippet = str(content)[:100].replace("\n", " ")
                            logger.log(f"{member}: {snippet}")
            
            # If we got here without exception, consider successful
            chunks = current_chunks
            error_events = current_errors
            return True, chunks, error_events
            
        except Exception as exc:
            if logger:
                logger.log(f"Attempt {attempt+1} failed: {exc}")
            if attempt == max_retries - 1:
                return False, chunks, [str(exc)]
            # Continue to next retry
    
    return False, chunks, error_events


# ─────────────────────────────────────────────────────────────────────────────
# SINGLE CONDITION RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def run_condition(condition: str, run_dir: Path, logger: "RunLogger") -> dict:
    """Run one condition inside its isolated output directory."""
    output_dir = (run_dir / condition).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    label = "Annotation Protocol" if condition == "a" else "Standard Practices"
    logger.log(f"=== CONDITION {condition.upper()} — {label} ===")
    logger.log(f"Output dir: {output_dir}")

    original_cwd = Path.cwd()
    result: dict = {
        "condition": condition,
        "label": label,
        "output_dir": str(output_dir),
        "start_time": datetime.now().isoformat(),
        "end_time": None,
        "duration_seconds": None,
        "success": False,
        "error": None,
        "agent_response_preview": None,
        "metrics": {},
    }

    try:
        os.chdir(output_dir)
        logger.log(f"[{condition.upper()}] Building team...")
        team = _build_team(condition, output_dir)
        logger.log(f"[{condition.upper()}] Team ready — starting task...")
        # Run with retry mechanism
        success, chunks, error_events = _run_with_retry(
            team, SHARED_TASK, max_retries=3, logger=logger
        )
        
        result["agent_response_preview"] = "".join(chunks)[:800]
        if error_events:
            result["error"] = "; ".join(error_events[:3])
        result["success"] = success
        if success:
            logger.log(f"[{condition.upper()}] Task completed successfully.")
        else:
            logger.log(f"[{condition.upper()}] Task failed after retries.")

    except Exception as exc:
        result["error"] = str(exc)
        logger.log(f"[{condition.upper()}] ERROR: {exc}")
    finally:
        os.chdir(original_cwd)

    result["end_time"] = datetime.now().isoformat()
    result["duration_seconds"] = round(
        (datetime.fromisoformat(result["end_time"]) -
         datetime.fromisoformat(result["start_time"])).total_seconds(), 1
    )
    result["metrics"] = _collect_metrics(output_dir)
    m = result["metrics"]
    
    # Validate application structure and syntax
    validation = _validate_application(output_dir)
    result["validation"] = validation
    
    # Measure code quality
    code_quality = _measure_code_quality(output_dir)
    result["code_quality"] = code_quality
    
    if result["success"] and m.get("python_file_count", 0) == 0:
        result["success"] = False
        if not result["error"]:
            result["error"] = "No Python files produced — agent may have failed silently"
        logger.log(f"[{condition.upper()}] WARNING: 0 files produced — marking success=False")
    
    # Log validation results
    if validation.get("syntax_errors"):
        logger.log(f"[{condition.upper()}] Validation: {len(validation['syntax_errors'])} syntax errors")
    else:
        logger.log(f"[{condition.upper()}] Validation: No syntax errors")
    
    # Log code quality highlights
    if code_quality["functions"] > 0:
        logger.log(
            f"[{condition.upper()}] Quality: funcs={code_quality['functions']}"
            f" classes={code_quality['classes']}"
            f" doc_cov={code_quality['functions_with_docstrings']}/{code_quality['functions']}"
            f" avg_complexity={code_quality['avg_function_complexity']:.1f}"
            f" quality_score={code_quality['quality_score']:.3f}"
        )
    
    logger.log(
        f"[{condition.upper()}] Metrics: py={m.get('python_file_count',0)}"
        f" html={m.get('html_file_count',0)}"
        f" LOC={m.get('total_lines_of_code',0)}"
        f" annotated={m.get('annotation_coverage_pct',0):.1f}%"
        f" message:{m.get('annotation_counts',{}).get('message',0)}"
        f" | valid_score={validation.get('score', 0):.2f}"
        f" | quality_score={code_quality.get('quality_score', 0):.3f}"
    )
    return result


# ─────────────────────────────────────────────────────────────────────────────
# RESET / LIST / RESUME / MAIN RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def reset_runs(run_id: str | None = None) -> None:
    if not RUNS_ROOT.exists():
        print("  Nothing to reset.")
        return
    if run_id:
        target = RUNS_ROOT / run_id
        if not target.exists():
            print(f"  Not found: {run_id}")
            return
        shutil.rmtree(target)
        print(f"  Deleted: {target}")
    else:
        shutil.rmtree(RUNS_ROOT)
        print(f"  Deleted: {RUNS_ROOT}")


def list_runs() -> None:
    if not RUNS_ROOT.exists() or not any(RUNS_ROOT.iterdir()):
        print("  No runs found.")
        return
    print(f"\n  {'RUN ID':<30} {'CONDITIONS':<12} {'STATUS'}")
    print(f"  {'-'*30} {'-'*12} {'-'*30}")
    for run_dir in sorted(RUNS_ROOT.iterdir()):
        cmp = run_dir / "comparison.json"
        if cmp.exists():
            data   = json.loads(cmp.read_text())
            conds  = list(data.get("conditions", {}).keys())
            status = " | ".join(
                f"{c}={'ok' if data['conditions'][c]['success'] else 'err'}" for c in conds
            )
            print(f"  {run_dir.name:<30} {','.join(conds):<12} {status}")
        else:
            subdirs = [d.name for d in run_dir.iterdir() if d.is_dir()]
            print(f"  {run_dir.name:<30} {','.join(subdirs):<12} (in progress)")
    print()


def _load_partial(run_dir: Path) -> dict:
    f = run_dir / "partial_results.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def _save_partial(run_dir: Path, results: dict) -> None:
    (run_dir / "partial_results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False)
    )


def resume_experiment(run_id: str) -> dict:
    run_dir = RUNS_ROOT / run_id
    if not run_dir.exists():
        print(f"  Run not found: {run_id}")
        sys.exit(1)

    partial = _load_partial(run_dir)
    done    = {c for c, r in partial.items()
               if r.get("success") and r.get("metrics", {}).get("python_file_count", 0) > 0}
    todo    = [c for c in ("a", "b") if c not in done]

    print(f"\n{'#'*68}")
    print(f"  RESUME    : {run_id}")
    print(f"  Done      : {', '.join(done) or 'none'}")
    print(f"  To run    : {', '.join(todo) or 'none — complete!'}")
    print(f"{'#'*68}")

    if not todo:
        print("  Nothing to do.")
        return partial

    logger  = RunLogger(run_dir)
    results = dict(partial)
    for cond in todo:
        results[cond] = run_condition(cond, run_dir, logger)
        _save_partial(run_dir, results)

    final    = {"run_id": run_id, "run_dir": str(run_dir), "conditions": results}
    cmp_file = run_dir / "comparison.json"
    cmp_file.write_text(json.dumps(final, indent=2, ensure_ascii=False))
    logger.log("Resume complete — comparison.json saved.")
    logger.close()
    return final


def run_experiment(condition: str = "both") -> dict:
    """Create a fresh timestamped run and execute the requested condition(s).

    Rules:   Never reuses an existing run_id; use resume_experiment() to continue.
    """
    run_id  = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir = RUNS_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'#'*68}")
    print(f"  EXPERIMENT: AgentHub SaaS webapp A/B test")
    print(f"  RUN ID    : {run_id}")
    print(f"  CONDITION : {condition}")
    print(f"  OUTPUT    : {run_dir}")
    print(f"{'#'*68}")

    logger = RunLogger(run_dir)
    logger.log(f"Experiment started — run_id={run_id}  condition={condition}")

    to_run  = ["a", "b"] if condition == "both" else [condition]
    results: dict = {"run_id": run_id, "run_dir": str(run_dir), "conditions": {}}

    for cond in to_run:
        results["conditions"][cond] = run_condition(cond, run_dir, logger)
        _save_partial(run_dir, results["conditions"])

    cmp_file = run_dir / "comparison.json"
    cmp_file.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    logger.log("Experiment finished — comparison.json saved.")
    
    # Generate detailed reports
    logger.log("Generating HTML and CSV reports...")
    _generate_reports(run_dir, results)
    logger.log("Reports generated in reports/ directory.")
    
    logger.close()

    print(f"\n{'='*68}")
    print("  SUMMARY")
    print(f"{'='*68}")
    labels = {"a": "Annotation Protocol", "b": "Standard Practices  "}
    for cond, res in results["conditions"].items():
        m = res["metrics"]
        print(
            f"  [{cond.upper()}] {labels.get(cond, cond)}"
            f" | py={m.get('python_file_count', 0):3d}"
            f" | html={m.get('html_file_count', 0):2d}"
            f" | LOC={m.get('total_lines_of_code', 0):6d}"
            f" | ann={m.get('annotation_coverage_pct', 0):5.1f}%"
            f" | msg={m.get('annotation_counts', {}).get('message', 0):2d}"
            f" | {res['duration_seconds']}s"
            f" | {'OK' if res['success'] else 'ERROR'}"
        )
    print(f"\n  Saved → {cmp_file}")
    print(f"{'='*68}\n")
    return results


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli = argparse.ArgumentParser(
        description="A/B experiment: AgentHub SaaS webapp — CodeDNA vs Standard.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_experiment_webapp.py                        # run both conditions
  python run_experiment_webapp.py --condition a          # condition-A only
  python run_experiment_webapp.py --condition b          # condition-B only
  python run_experiment_webapp.py --list-runs
  python run_experiment_webapp.py --reset
  python run_experiment_webapp.py --resume run_20260330_120000
        """
    )
    cli.add_argument("--condition", choices=["a", "b", "both"], default="both")
    cli.add_argument("--reset",     action="store_true", help="Delete ALL runs")
    cli.add_argument("--clean-run", metavar="RUN_ID",    help="Delete one specific run")
    cli.add_argument("--list-runs", action="store_true", help="List all runs")
    cli.add_argument("--resume",    metavar="RUN_ID",    help="Resume an interrupted run")
    args = cli.parse_args()

    if args.reset:
        confirm = input("  Delete ALL runs? [y/N] ").strip().lower()
        if confirm == "y":
            reset_runs()
    elif args.clean_run:
        reset_runs(args.clean_run)
    elif args.list_runs:
        list_runs()
    elif args.resume:
        resume_experiment(args.resume)
    else:
        run_experiment(args.condition)
