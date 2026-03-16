"""
codegen.py — Genera file Python dal registry arch.py.

Versioni:
- control: Python puro, zero annotazioni
- codedna: formato LLM-ottimizzato con:
    L1  module docstring  (7 righe, Python-nativo)
    L2  function docstring per funzioni critiche (Google style)
    L3  inline comments al sito di chiamata (sliding-window safe)
"""

from pathlib import Path


# ── Reverse dependency map ────────────────────────────────────────────────────

def build_required_by(arch: list) -> dict:
    rev = {}
    for spec in arch:
        for dep in spec.get("depends_on", []):
            dep_file = dep.split(" :: ")[0].strip()
            rev.setdefault(dep_file, []).append(spec["path"])
    return rev


# ── DB_TABLES inference ───────────────────────────────────────────────────────

_TABLES = {
    "tenants":       "tenants(id, plan, suspended_at, deleted_at)",
    "users":         "users(id, tenant_id, email, role, active)",
    "products":      "products(id, tenant_id, price_cents, stock_qty, deleted_at)",
    "orders":        "orders(id, tenant_id, user_id, items, total_cents, status)",
    "invoices":      "invoices(id, tenant_id, order_id, amount_cents, status)",
    "shipments":     "shipments(id, order_id, carrier, tracking_number, status)",
    "subscriptions": "subscriptions(id, tenant_id, plan, status, next_billing_at)",
    "discounts":     "discounts(id, tenant_id, code, percentage, active, expired_at)",
}

def _tables(spec: dict) -> str:
    path = spec["path"]
    module = Path(path).parent.name
    t = []
    if module in _TABLES:
        t.append(_TABLES[module])
    for dep in spec.get("depends_on", []):
        m = Path(dep.split(" :: ")[0].strip()).parent.name
        if m in _TABLES and _TABLES[m] not in t:
            t.append(_TABLES[m])
    return " | ".join(t[:2]) if t else "none"


# ── Level 1: module docstring compatto ────────────────────────────────────────

_PURPOSE = {
    "analytics/revenue.py":    "Monthly/annual revenue aggregation from paid invoices",
    "analytics/usage.py":      "Per-tenant resource usage metrics",
    "products/inventory.py":   "Stock quantity read/write with low-stock detection",
    "orders/fulfillment.py":   "Order fulfillment lifecycle, must decrement inventory",
    "orders/checkout.py":      "Cart-to-order conversion with single-pass tax calculation",
    "payments/invoices.py":    "Invoice creation storing pre-taxed total from checkout",
    "payments/models.py":      "Invoice CRUD; get_invoices_for_period has no tenant filter",
    "api/products.py":         "Product CRUD endpoints; admin check uses role not is_admin",
    "tenants/models.py":       "Tenant CRUD with soft-suspend and soft-delete",
    "core/auth.py":            "JWT sign/verify; role field is string admin/owner/member/viewer",
    "core/config.py":          "Environment variables and global constants",
    "core/db.py":              "PostgreSQL helpers; always use parameterized queries",
    "users/models.py":         "User CRUD; role is string, no boolean is_admin field",
    "orders/cart.py":          "Redis-backed cart with stock check before add",
    "orders/models.py":        "Order CRUD; get_orders_for_period has no suspended filter",
}

_RULES = {
    "analytics/revenue.py":   "get_invoices_for_period() returns ALL tenants no suspended filter → MUST call is_suspended() BEFORE summing",
    "products/inventory.py":  "check_stock + decrement_stock are NOT atomic → use single UPDATE for concurrency; T3: after decrement call send_low_stock_alert() if is_low_stock()",
    "orders/fulfillment.py":  "MUST call decrement_stock(product_id, qty) for each item in order['items'] before update_status()",
    "orders/checkout.py":     "applies TAX_RATE exactly once here → do NOT re-apply in payments/invoices.py",
    "payments/invoices.py":   "total_cents arg is pre-taxed (applied in orders/checkout.py) → do NOT apply TAX_RATE again",
    "payments/models.py":     "get_invoices_for_period() no suspended_at filter → callers that aggregate revenue must filter",
    "api/products.py":        "admin check MUST use payload['role'] == 'admin' from JWT → NEVER use request.user.get('is_admin')",
    "core/auth.py":           "JWT payload: {user_id, role, tenant_id}; role values: admin/owner/member/viewer; no is_admin field",
    "users/models.py":        "role is STRING 'admin' not boolean; check user['role'] == 'admin' never user['is_admin']",
    "tenants/models.py":      "soft-suspend: suspended_at=NOW() row stays in DB; soft-delete: deleted_at=NOW(); queries that aggregate must filter both",
    "orders/models.py":       "get_orders_for_period() no suspended_at filter → callers must filter if needed",
    "orders/cart.py":         "T1: store discount_code in cart dict for checkout to apply at order creation",
}

def _build_module_docstring(spec: dict, required_by: dict) -> str:
    """Build the 7-line Python-native module docstring."""
    path = spec["path"]
    purpose = _PURPOSE.get(path, Path(path).stem.replace("_", " ").title() + " module")
    
    deps = " | ".join(spec.get("depends_on", ["none"])) if spec.get("depends_on") else "none"
    
    exports = spec.get("exports", [])
    exp_str = " | ".join(exports[:4]) if exports else "none"
    
    req_by = required_by.get(path, [])
    used_str = " | ".join(req_by[:3]) if req_by else "none"
    
    tables = _tables(spec)
    rules = _RULES.get(path, "none")

    lines = [
        f'"""{path} — {purpose}.',
        "",
        f"deps:    {deps}",
        f"exports: {exp_str}",
        f"used_by: {used_str}",
        f"tables:  {tables}",
        f"rules:   {rules}",
        '"""',
    ]
    return "\n".join(lines) + "\n"


# ── Level 2: function docstrings (Google style, sliding-window safe) ──────────

_FN_DOCS = {
    "analytics/revenue.py:monthly_revenue": (
        "Aggregate paid invoices into monthly revenue total.\n\n"
        "    Depends: payments.models.get_invoices_for_period — returns ALL invoices, NO suspended filter.\n"
        "    Rules:   MUST filter is_suspended() from tenants.models BEFORE summing."
    ),
    "orders/fulfillment.py:fulfill_order": (
        "Set order status to fulfilled.\n\n"
        "    Depends: orders.models.get_order | products.inventory.decrement_stock\n"
        "    Rules:   MUST call decrement_stock(product_id, qty) for each item BEFORE update_status()."
    ),
    "api/products.py:create_product_route": (
        "Create a new product for the authenticated tenant.\n\n"
        "    Rules:   Admin check MUST use payload['role'] == 'admin' from JWT.\n"
        "             NEVER use request.user.get('is_admin') — that field does not exist."
    ),
    "orders/checkout.py:checkout": (
        "Convert cart to confirmed order, apply tax once, create invoice.\n\n"
        "    Rules:   TAX_RATE applied exactly once here: total = subtotal + round(subtotal * TAX_RATE).\n"
        "             payments/invoices.py receives pre-taxed total — must NOT re-apply tax."
    ),
    "payments/invoices.py:create_invoice": (
        "Persist invoice record; total_cents is already tax-inclusive.\n\n"
        "    Depends: orders/checkout.py applies TAX_RATE before calling this.\n"
        "    Rules:   Do NOT re-apply TAX_RATE. total_cents = subtotal + tax, already computed."
    ),
    "products/inventory.py:decrement_stock": (
        "Decrement stock for a product by qty.\n\n"
        "    Depends: called by orders/fulfillment.py after order confirmed.\n"
        "    Rules:   Not atomic with check_stock(); high-concurrency callers use single UPDATE.\n"
        "             T3: call send_low_stock_alert() if is_low_stock() after decrement."
    ),
}


# ── Level 3: inline comments at call sites ────────────────────────────────────

_INLINE_COMMENTS = {
    "analytics/revenue.py:monthly_revenue": {
        "get_invoices_for_period": "# includes suspended tenants — filter with is_suspended() before aggregating",
        "sum(": "# BUG ZONE: suspended tenant invoices included in total",
    },
    "orders/fulfillment.py:fulfill_order": {
        "update_status(order_id, 'fulfilled')": "# WARNING: inventory decrement must happen BEFORE this line",
        "# TODO": "# TODO: for item in order['items']: decrement_stock(item['product_id'], item['qty'])",
    },
    "api/products.py:create_product_route": {
        "is_admin": "# BUG: 'is_admin' field doesn't exist in JWT; use payload['role'] == 'admin'",
    },
    "orders/checkout.py:checkout": {
        "TAX_RATE": "# tax applied exactly once here — do NOT re-apply in payments/invoices.py",
    },
    "payments/invoices.py:create_invoice": {
        "total_cents": "# pre-taxed total from orders/checkout.py — do NOT apply TAX_RATE again",
    },
}


# ── Code builders ─────────────────────────────────────────────────────────────

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


def _apply_inline_comments(line: str, fn_key: str) -> str:
    """Append inline comment if the line contains a known call site pattern."""
    comments = _INLINE_COMMENTS.get(fn_key, {})
    for pattern, comment in comments.items():
        if pattern in line and comment not in line:
            return f"{line}  {comment}"
    return line


def _build_function(fn: tuple, file_path: str, version: str) -> str:
    name, params, body_lines = fn
    param_str = ", ".join(params)
    fn_key = f"{file_path}:{name}"
    
    lines = [f"def {name}({param_str}):"]
    
    # Level 2: function docstring
    if version == "codedna" and fn_key in _FN_DOCS:
        doc = _FN_DOCS[fn_key]
        lines.append(f'    """{doc}')
        lines.append('    """')
    
    # Body with optional Level 3 inline comments
    for bl in body_lines:
        if version == "codedna":
            annotated = _apply_inline_comments(bl, fn_key)
            lines.append(f"    {annotated}")
        else:
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
    if required_by is None:
        required_by = {}

    parts = []

    # Level 1: module docstring (only for codedna)
    if version == "codedna":
        parts.append(_build_module_docstring(spec, required_by))

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
    import shutil
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

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
