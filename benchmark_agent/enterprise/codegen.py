"""
codegen.py — Generates Python source files from the arch.py registry.

For each file spec:
- control version: clean Python code, NO annotations whatsoever
- codedna version: # === CODEDNA:0.5 === header per lo SPEC.md ufficiale
  Fields: FILE, PURPOSE, CONTEXT_BUDGET, DEPENDS_ON, EXPORTS,
          REQUIRED_BY, DB_TABLES, AGENT_RULES, LAST_MODIFIED
  Inline: @REQUIRES-READ, @SEE, @MODIFIES-ALSO in function bodies
"""

from pathlib import Path


# ── REQUIRED_BY reverse-map: built from arch DEPENDS_ON ─────────────────────

def build_required_by(arch: list) -> dict:
    """Build reverse dependency map: file → list of dependent files."""
    rev = {}
    for spec in arch:
        for dep in spec.get("depends_on", []):
            dep_file = dep.split(" :: ")[0].strip()
            rev.setdefault(dep_file, []).append(spec["path"])
    return rev


# ── DB_TABLES inference ───────────────────────────────────────────────────────

_TABLE_MAP = {
    "tenants": "tenants (id, name, plan, owner_email, suspended_at, deleted_at)",
    "users":   "users (id, tenant_id, email, name, role, active, last_login)",
    "products":"products (id, tenant_id, name, sku, price_cents, stock_qty, deleted_at)",
    "orders":  "orders (id, tenant_id, user_id, items, total_cents, status, created_at)",
    "invoices":"invoices (id, tenant_id, order_id, amount_cents, status, stripe_charge_id)",
    "shipments":"shipments (id, order_id, carrier, tracking_number, status, created_at)",
    "subscriptions":"subscriptions (id, tenant_id, plan, status, next_billing_at)",
    "discounts":"discounts (id, tenant_id, code, percentage, active, expired_at)",
    "sessions":"sessions (id, user_id, tenant_id, token, expires_at)",
    "webhooks":"webhooks (id, tenant_id, url, events, active)",
}

def _infer_db_tables(spec: dict) -> str:
    path = spec["path"]
    module = Path(path).parent.name
    tables = []
    
    # primary table from module
    primary = _TABLE_MAP.get(module)
    if primary:
        tables.append(primary)
    
    # secondary tables from depends_on
    for dep in spec.get("depends_on", []):
        dep_mod = Path(dep.split(" :: ")[0].strip()).parent.name
        tbl = _TABLE_MAP.get(dep_mod)
        if tbl and tbl not in tables:
            tables.append(tbl)
    
    return " | ".join(tables[:2]) if tables else "none"


# ── CONTEXT_BUDGET inference ──────────────────────────────────────────────────

def _infer_budget(spec: dict, required_by: dict) -> str:
    path = spec["path"]
    dependents = required_by.get(path, [])
    
    # Core infrastructure files: always
    if any(kw in path for kw in ["core/config", "core/db", "core/auth", "tenants/models"]):
        return "always"
    # Files depended on by 3+ others
    if len(dependents) >= 3:
        return "always"
    # Utilities and helpers: minimal
    if any(kw in path for kw in ["utils/", "middleware/", "_is_distractor"]):
        return "minimal"
    
    return "normal"


# ── PURPOSE generation ────────────────────────────────────────────────────────

def _purpose(spec: dict) -> str:
    path = spec["path"]
    stem = Path(path).stem.replace("_", " ")
    module = Path(path).parent.name.replace("_", " ")
    
    # Custom purposes for key files
    purposes = {
        "analytics/revenue.py": "Monthly/annual revenue totals from paid invoices",
        "analytics/usage.py": "Per-tenant resource usage metrics for admin dashboard",
        "products/inventory.py": "Stock quantity read/write with low-stock detection",
        "orders/fulfillment.py": "Order fulfillment lifecycle and inventory decrement",
        "orders/checkout.py": "Cart-to-order conversion with tax calculation",
        "payments/invoices.py": "Invoice creation storing pre-taxed total",
        "api/products.py": "CRUD endpoints for products scoped by tenant",
        "tenants/models.py": "Tenant CRUD with soft-suspend and soft-delete",
        "core/auth.py": "JWT sign/verify and role-based access decorators",
        "core/config.py": "Environment config and global constants",
        "core/db.py": "PostgreSQL connection and parameterized query helpers",
        "users/models.py": "User CRUD; role is string field not boolean flag",
        "orders/cart.py": "Redis-backed cart with stock check on item add",
    }
    return purposes.get(path, f"{stem.title()} logic for {module}")


# ── AGENT_RULES generation ────────────────────────────────────────────────────

def _agent_rules(spec: dict) -> str:
    path = spec["path"]
    rules = {
        "analytics/revenue.py":   "MUST filter is_suspended() before summing; see tenants/models.py → is_suspended()",
        "products/inventory.py":  "check_stock + decrement_stock are NOT atomic; use single UPDATE for concurrency safety",
        "orders/fulfillment.py":  "MUST call decrement_stock() for each item in order['items'] before updating status",
        "orders/checkout.py":     "applies TAX_RATE exactly once; do NOT apply tax again in payments/invoices.py",
        "payments/invoices.py":   "total_cents arg is pre-taxed; do NOT re-apply TAX_RATE",
        "api/products.py":        "admin check MUST use payload['role'] == 'admin'; NEVER use user['is_admin']",
        "core/auth.py":           "JWT payload fields: user_id, role, tenant_id. role values: admin/owner/member/viewer",
        "users/models.py":        "role is STRING ('admin'/'owner'/'member'/'viewer'); no boolean is_admin field exists",
        "core/db.py":             "always use parameterized queries; never interpolate user input into SQL",
        "tenants/models.py":      "suspend = soft (suspended_at=NOW()); delete = soft (deleted_at=NOW()); rows stay in DB",
        "payments/models.py":     "get_invoices_for_period does NOT filter suspended tenants; callers must filter if needed",
        "orders/models.py":       "get_orders_for_period does NOT filter suspended tenants",
        "orders/cart.py":         "T1: discount_code field must be stored in cart dict for checkout to apply",
    }
    return rules.get(path, "none")


# ── Inline annotations for functions ─────────────────────────────────────────

_INLINE = {
    "analytics/revenue.py": {
        "monthly_revenue": [
            "# @REQUIRES-READ: payments/models.py → get_invoices_for_period — returns all invoices; NO suspended filter",
            "# @REQUIRES-READ: tenants/models.py → is_suspended — use to exclude suspended tenants",
            "# @SEE: tenants/models.py → list_active_tenants — reference for correct suspension check",
        ]
    },
    "orders/fulfillment.py": {
        "fulfill_order": [
            "# @REQUIRES-READ: products/inventory.py → decrement_stock — MUST call for each item in order['items']",
            "# @MODIFIES-ALSO: products (stock_qty column) — decremented per item",
        ]
    },
    "api/products.py": {
        "create_product_route": [
            "# @REQUIRES-READ: core/auth.py → require_admin — use decorator instead of manual check",
            "# @SEE: core/auth.py AGENT_RULES — admin field is role NOT is_admin",
        ]
    },
    "orders/checkout.py": {
        "checkout": [
            "# @REQUIRES-READ: core/config.py → TAX_RATE — applied exactly once here",
            "# @MODIFIES-ALSO: payments/invoices.py → create_invoice — receives total already-taxed",
        ]
    },
    "payments/invoices.py": {
        "create_invoice": [
            "# @SEE: orders/checkout.py → checkout — tax already included in total_cents arg",
        ]
    },
    "products/inventory.py": {
        "decrement_stock": [
            "# @SEE: orders/fulfillment.py → fulfill_order — this is where decrement SHOULD be called",
        ]
    },
}


# ── Main codegen ──────────────────────────────────────────────────────────────

def _build_codedna_header(spec: dict, required_by: dict) -> str:
    """Build the # === CODEDNA:0.5 === header per the spec."""
    path = spec["path"]
    
    depends_str = " | ".join(spec["depends_on"]) if spec.get("depends_on") else "none"
    
    exports_list = spec.get("exports", [])
    exports_str = " | ".join(exports_list) if exports_list else "none"
    
    req_by = required_by.get(path, [])
    required_by_str = " | ".join(req_by[:3]) if req_by else "none"
    
    db = _infer_db_tables(spec)
    budget = _infer_budget(spec, required_by)
    purpose = _purpose(spec)
    agent_rules = _agent_rules(spec)
    
    lines = [
        "# === CODEDNA:0.5 " + "=" * 46,
        f"# FILE: {path}",
        f"# PURPOSE: {purpose}",
        f"# CONTEXT_BUDGET: {budget}",
        f"# DEPENDS_ON: {depends_str}",
        f"# EXPORTS: {exports_str}",
        f"# REQUIRED_BY: {required_by_str}",
        f"# DB_TABLES: {db}",
        f"# AGENT_RULES: {agent_rules}",
        "# LAST_MODIFIED: initial generation",
        "# " + "=" * 62,
    ]
    return "\n".join(lines) + "\n"


def _build_imports(spec: dict) -> str:
    imports = ["import os", "import json", "import logging"]
    path = spec["path"]

    if "db.py" not in path and "config.py" not in path:
        imports.append("from core.db import execute, execute_one")
    if "config.py" not in path:
        imports.append("from core.config import *")
    if "api/" in path:
        imports.append("from flask import Blueprint, request, jsonify")
        imports.append("from core.auth import verify_token, require_auth, require_admin")
    return "\n".join(imports)


def _build_function(fn: tuple, file_path: str, version: str) -> str:
    name, params, body_lines = fn
    param_str = ", ".join(params)
    lines = [f"def {name}({param_str}):"]
    
    # Add inline annotations for CodeDNA version
    if version == "codedna":
        inline_for_file = _INLINE.get(file_path, {})
        for annotation in inline_for_file.get(name, []):
            lines.append(f"    {annotation}")
    
    for bl in body_lines:
        lines.append(f"    {bl}")
    if not body_lines:
        lines.append("    pass")
    return "\n".join(lines)


def _build_extra_boilerplate(spec: dict) -> str:
    path = spec["path"]
    extra = []

    if path == "core/config.py":
        extra += [
            "DB_URL = os.getenv('DATABASE_URL', 'postgresql://localhost/marketcore')",
            "REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')",
            "STRIPE_KEY = os.getenv('STRIPE_KEY', 'sk_test_xxx')",
            "TAX_RATE = float(os.getenv('TAX_RATE', '0.22'))",
            "CURRENCY = os.getenv('CURRENCY', 'EUR')",
            "MAX_SEATS = int(os.getenv('MAX_SEATS', '500'))",
            "JWT_SECRET = os.getenv('JWT_SECRET', 'supersecret')",
            "SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.sendgrid.net')",
            "LOW_STOCK_THRESHOLD = int(os.getenv('LOW_STOCK_THRESHOLD', '10'))",
        ]
    if path == "core/db.py":
        extra += [
            "import psycopg2",
            "_pool = None",
            "def _get_conn():",
            "    global _pool",
            "    if _pool is None: _pool = psycopg2.connect(DB_URL)",
            "    return _pool",
        ]
    if path == "core/cache.py":
        extra += [
            "import redis as _redis",
            "_client = None",
            "def _r():",
            "    global _client",
            "    if _client is None: _client = _redis.from_url(REDIS_URL)",
            "    return _client",
        ]
    if path == "core/events.py":
        extra.append("_registry: dict = {}")
    if path == "core/auth.py":
        extra += [
            "import jwt",
            "from functools import wraps",
            "",
            "def require_auth(f):",
            "    @wraps(f)",
            "    def decorated(*args, **kwargs):",
            "        token = request.headers.get('Authorization', '').replace('Bearer ', '')",
            "        try:",
            "            request.user = verify_token(token)",
            "        except Exception:",
            "            return {'error': 'Unauthorized'}, 401",
            "        return f(*args, **kwargs)",
            "    return decorated",
            "",
            "def require_admin(f):",
            "    @wraps(f)",
            "    def decorated(*args, **kwargs):",
            "        token = request.headers.get('Authorization', '').replace('Bearer ', '')",
            "        try:",
            "            payload = verify_token(token)",
            "            if payload.get('role') != 'admin':",
            "                return {'error': 'Forbidden'}, 403",
            "        except Exception:",
            "            return {'error': 'Unauthorized'}, 401",
            "        return f(*args, **kwargs)",
            "    return decorated",
        ]
    if path == "tenants/limits.py":
        extra += [
            "PLAN_LIMITS = {",
            "    'starter':    {'seats': 5,   'products': 100},",
            "    'growth':     {'seats': 25,  'products': 1000},",
            "    'business':   {'seats': 100, 'products': 10000},",
            "    'enterprise': {'seats': 500, 'products': 999999},",
            "}",
        ]
    if path == "app.py":
        extra += [
            "from flask import Flask",
            "from api.products import products_bp",
            "from api.orders import orders_bp",
            "from api.reports import reports_bp",
            "from api.admin import admin_bp",
            "from api.webhooks import webhooks_bp",
            "from api.auth_api import auth_bp",
        ]
    if "api/" in path and path != "api/auth_api.py":
        stem = Path(path).stem
        url = "/api/" + stem.replace("_", "-")
        extra.append(f"{stem}_bp = Blueprint('{stem}', __name__, url_prefix='{url}')")
    if path == "api/auth_api.py":
        extra.append("auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')")

    return "\n".join(extra)


def generate_file(spec: dict, version: str, required_by: dict = None) -> str:
    """Generate complete Python file content for the given version."""
    if required_by is None:
        required_by = {}
    
    parts = []

    if version == "codedna":
        parts.append(_build_codedna_header(spec, required_by))

    parts.append(_build_imports(spec))
    parts.append("")

    extra = _build_extra_boilerplate(spec)
    if extra:
        parts.append(extra)
        parts.append("")

    for fn in spec.get("functions", []):
        parts.append(_build_function(fn, spec["path"], version))
        parts.append("")

    return "\n".join(parts)


def write_project(arch: list, version: str, dest: Path):
    """Write all files for the given version to dest directory."""
    import shutil
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    # Build required_by map once
    required_by = build_required_by(arch)

    packages = set()
    for spec in arch:
        pkg = Path(spec["path"]).parent
        if str(pkg) != ".":
            packages.add(pkg)
    for pkg in packages:
        (dest / pkg).mkdir(parents=True, exist_ok=True)
        (dest / pkg / "__init__.py").write_text("")

    total_lines = 0
    for spec in arch:
        content = generate_file(spec, version, required_by)
        filepath = dest / spec["path"]
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")
        total_lines += content.count("\n")

    print(f"✅ {version}: {len(arch)} file, ~{total_lines} righe → {dest}")
    return total_lines
