"""
generate_large_codebase.py — SaaS billing platform, 35 file, ~2500 righe.

Bug nascosto: i tenant SOSPESI (soft-suspend con suspended_at) continuano a
comparire nel report delle entrate mensili. Il bug richiede di tracciare la
catena: reports/ → services/ → models/ → tenants/

Crea:
  projects/large_control/   ← 35 file senza docstring
  projects/large_codedna/   ← 35 file con module docstring architetturali
"""

import shutil
from pathlib import Path

BASE = Path(__file__).parent / "projects"

# ─────────────────────────────────────────────────────────────────────────────
# FILE DEFINITIONS
# Ogni entry: (path, control_content, codedna_content)
# codedna_content = module docstring + stesso codice control
# ─────────────────────────────────────────────────────────────────────────────

def _with_docstring(docstring: str, code: str) -> str:
    return f'"""{docstring}"""\n{code}'

FILES = {}

# ── config.py ─────────────────────────────────────────────────────────────────
_code = '''\
import os

DATABASE_URL   = os.getenv("DATABASE_URL", "postgresql://localhost/saas_db")
REDIS_URL      = os.getenv("REDIS_URL", "redis://localhost:6379/0")
STRIPE_KEY     = os.getenv("STRIPE_KEY", "sk_test_xxx")
SENDGRID_KEY   = os.getenv("SENDGRID_KEY", "SG.xxx")
JWT_SECRET     = os.getenv("JWT_SECRET", "supersecret")
MAX_SEATS      = int(os.getenv("MAX_SEATS", "500"))
BILLING_DAY    = int(os.getenv("BILLING_DAY", "1"))
TAX_RATE       = float(os.getenv("TAX_RATE", "0.22"))
CURRENCY       = os.getenv("CURRENCY", "EUR")
ENV            = os.getenv("ENV", "development")
'''
FILES["config.py"] = (_code, _with_docstring(
    "config.py -- Environment-based configuration loader.\n\n"
    "Exports: DATABASE_URL, REDIS_URL, STRIPE_KEY, SENDGRID_KEY, JWT_SECRET,\n"
    "         MAX_SEATS, BILLING_DAY, TAX_RATE, CURRENCY, ENV\n"
    "Used by: db/connection.py, services/stripe_service.py, notifications/email.py\n\n"
    "Rules:\n"
    "  - Never hardcode secrets. All values come from environment variables.\n"
    "  - TAX_RATE is a float (0.22 = 22%). Already applied in billing_service.py.\n",
    _code))

# ── db/connection.py ──────────────────────────────────────────────────────────
_code = '''\
import psycopg2
from config import DATABASE_URL

_pool = None

def get_conn():
    global _pool
    if _pool is None:
        _pool = psycopg2.connect(DATABASE_URL)
    return _pool

def execute(sql: str, params: tuple = ()) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    if cur.description:
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    conn.commit()
    return []

def execute_one(sql: str, params: tuple = ()) -> dict | None:
    rows = execute(sql, params)
    return rows[0] if rows else None
'''
FILES["db/connection.py"] = (_code, _with_docstring(
    "db/connection.py -- PostgreSQL connection pool and SQL executor.\n\n"
    "Depends on: config.py :: DATABASE_URL\n"
    "Exports: execute(sql, params) -> list[dict], execute_one(sql, params) -> dict | None\n"
    "Used by: (quasi tutti i modelli e service del progetto)\n\n"
    "Rules:\n"
    "  - Usare SEMPRE query parametrizzate: execute(sql, (p1, p2)).\n"
    "  - execute() è thread-safe grazie al pool interno.\n",
    _code))

# ── db/redis_client.py ────────────────────────────────────────────────────────
_code = '''\
import redis
from config import REDIS_URL

_client = None

def get_redis():
    global _client
    if _client is None:
        _client = redis.from_url(REDIS_URL)
    return _client

def cache_set(key: str, value: str, ttl: int = 300):
    get_redis().setex(key, ttl, value)

def cache_get(key: str) -> str | None:
    val = get_redis().get(key)
    return val.decode() if val else None

def cache_del(key: str):
    get_redis().delete(key)
'''
FILES["db/redis_client.py"] = (_code, _with_docstring(
    "db/redis_client.py -- Redis client for caching and queues.\n\n"
    "Depends on: config.py :: REDIS_URL\n"
    "Exports: cache_set(key, value, ttl), cache_get(key), cache_del(key)\n"
    "Used by: services/auth_service.py, workers/cache_warmer.py\n",
    _code))

# ── tenants/tenant_model.py ───────────────────────────────────────────────────
_code = '''\
from db.connection import execute, execute_one

def get_tenant(tenant_id: str) -> dict | None:
    return execute_one(
        "SELECT * FROM tenants WHERE id = %s",
        (tenant_id,)
    )

def list_active_tenants() -> list[dict]:
    return execute(
        "SELECT * FROM tenants WHERE suspended_at IS NULL AND deleted_at IS NULL"
    )

def create_tenant(name: str, plan: str, owner_email: str) -> dict:
    return execute_one(
        "INSERT INTO tenants (name, plan, owner_email) VALUES (%s, %s, %s) RETURNING *",
        (name, plan, owner_email)
    )

def update_tenant(tenant_id: str, data: dict) -> dict:
    sets = ", ".join(f"{k} = %s" for k in data)
    vals = list(data.values()) + [tenant_id]
    return execute_one(f"UPDATE tenants SET {sets} WHERE id = %s RETURNING *", tuple(vals))

def suspend_tenant(tenant_id: str):
    """Soft-suspend: sets suspended_at = NOW(). Tenant row stays in DB."""
    execute("UPDATE tenants SET suspended_at = NOW() WHERE id = %s", (tenant_id,))

def reactivate_tenant(tenant_id: str):
    execute("UPDATE tenants SET suspended_at = NULL WHERE id = %s", (tenant_id,))

def delete_tenant(tenant_id: str):
    """Soft delete: sets deleted_at = NOW()."""
    execute("UPDATE tenants SET deleted_at = NOW() WHERE id = %s", (tenant_id,))

def is_active(tenant: dict) -> bool:
    return tenant.get("suspended_at") is None and tenant.get("deleted_at") is None
'''
FILES["tenants/tenant_model.py"] = (_code, _with_docstring(
    "tenants/tenant_model.py -- Tenant CRUD and lifecycle management.\n\n"
    "Depends on: db/connection.py :: execute(), execute_one()\n"
    "Exports:\n"
    "    get_tenant(tenant_id) -> dict | None\n"
    "    list_active_tenants() -> list[dict]   # filtra suspended_at IS NULL\n"
    "    create_tenant(name, plan, owner_email) -> dict\n"
    "    suspend_tenant(tenant_id) -> None     # SOFT suspend, imposta suspended_at\n"
    "    reactivate_tenant(tenant_id) -> None\n"
    "    delete_tenant(tenant_id) -> None      # SOFT delete, imposta deleted_at\n"
    "    is_active(tenant) -> bool\n"
    "Used by: tenants/tenant_service.py, api/admin.py\n\n"
    "Rules:\n"
    "  - Il sistema usa SOFT SUSPEND e SOFT DELETE.\n"
    "    I tenant sospesi hanno suspended_at IS NOT NULL (riga resta nel DB).\n"
    "    I tenant eliminati hanno deleted_at IS NOT NULL.\n"
    "  - list_active_tenants() filtra entrambi i casi.\n"
    "  - Qualsiasi query che aggrega dati per-tenant DEVE considerare suspended_at.\n",
    _code))

# ── tenants/tenant_service.py ─────────────────────────────────────────────────
_code = '''\
from tenants.tenant_model import (
    get_tenant, list_active_tenants, create_tenant,
    suspend_tenant, reactivate_tenant, delete_tenant, is_active
)
from subscriptions.subscription_model import get_subscription_by_tenant
from notifications.email import send_suspension_notice

def onboard_tenant(name: str, plan: str, owner_email: str) -> dict:
    tenant = create_tenant(name, plan, owner_email)
    return tenant

def get_tenant_details(tenant_id: str) -> dict:
    tenant = get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")
    sub = get_subscription_by_tenant(tenant_id)
    return {**tenant, "subscription": sub}

def suspend(tenant_id: str, reason: str = ""):
    tenant = get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")
    suspend_tenant(tenant_id)
    send_suspension_notice(tenant["owner_email"], tenant_id, reason)

def reactivate(tenant_id: str):
    tenant = get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")
    reactivate_tenant(tenant_id)

def list_tenants_for_billing() -> list[dict]:
    """Returns only active (non-suspended, non-deleted) tenants."""
    return list_active_tenants()
'''
FILES["tenants/tenant_service.py"] = (_code, _with_docstring(
    "tenants/tenant_service.py -- Tenant business logic and orchestration.\n\n"
    "Depends on: tenants/tenant_model.py, subscriptions/subscription_model.py,\n"
    "            notifications/email.py :: send_suspension_notice()\n"
    "Exports:\n"
    "    onboard_tenant(name, plan, owner_email) -> dict\n"
    "    get_tenant_details(tenant_id) -> dict\n"
    "    suspend(tenant_id, reason) -> None\n"
    "    reactivate(tenant_id) -> None\n"
    "    list_tenants_for_billing() -> list[dict]  # solo tenant attivi\n"
    "Used by: api/admin.py, workers/billing_runner.py\n",
    _code))

# ── subscriptions/subscription_model.py ───────────────────────────────────────
_code = '''\
from db.connection import execute, execute_one

PLANS = {
    "starter":    {"price_cents": 2900,  "seats": 5},
    "growth":     {"price_cents": 9900,  "seats": 25},
    "business":   {"price_cents": 29900, "seats": 100},
    "enterprise": {"price_cents": 99900, "seats": 500},
}

def get_subscription_by_tenant(tenant_id: str) -> dict | None:
    return execute_one(
        "SELECT * FROM subscriptions WHERE tenant_id = %s AND status = 'active'",
        (tenant_id,)
    )

def get_all_active_subscriptions() -> list[dict]:
    return execute(
        "SELECT * FROM subscriptions WHERE status = 'active'"
    )

def create_subscription(tenant_id: str, plan: str) -> dict:
    price = PLANS[plan]["price_cents"]
    return execute_one(
        """INSERT INTO subscriptions (tenant_id, plan, price_cents, status)
           VALUES (%s, %s, %s, 'active') RETURNING *""",
        (tenant_id, plan, price)
    )

def cancel_subscription(subscription_id: str):
    execute(
        "UPDATE subscriptions SET status = 'cancelled', cancelled_at = NOW() WHERE id = %s",
        (subscription_id,)
    )

def upgrade_plan(subscription_id: str, new_plan: str):
    price = PLANS[new_plan]["price_cents"]
    execute(
        "UPDATE subscriptions SET plan = %s, price_cents = %s WHERE id = %s",
        (new_plan, price, subscription_id)
    )
'''
FILES["subscriptions/subscription_model.py"] = (_code, _with_docstring(
    "subscriptions/subscription_model.py -- Subscription CRUD.\n\n"
    "Depends on: db/connection.py :: execute(), execute_one()\n"
    "Exports:\n"
    "    get_subscription_by_tenant(tenant_id) -> dict | None\n"
    "    get_all_active_subscriptions() -> list[dict]\n"
    "    create_subscription(tenant_id, plan) -> dict\n"
    "    cancel_subscription(subscription_id) -> None\n"
    "    upgrade_plan(subscription_id, new_plan) -> None\n"
    "Used by: tenants/tenant_service.py, services/billing_service.py,\n"
    "         reports/monthly_revenue.py\n\n"
    "Rules:\n"
    "  - get_all_active_subscriptions() filtra per status='active' MA NON per tenant.suspended_at.\n"
    "    Questo significa che subscriptions di tenant sospesi (vedi tenants/tenant_model.py)\n"
    "    sono incluse se la subscription non è stata cancellata.\n"
    "  - La subscription rimane 'active' anche dopo la sospensione del tenant.\n",
    _code))

# ── subscriptions/subscription_service.py ────────────────────────────────────
_code = '''\
from subscriptions.subscription_model import (
    get_subscription_by_tenant, create_subscription,
    cancel_subscription, upgrade_plan, get_all_active_subscriptions
)
from tenants.tenant_model import get_tenant
from config import BILLING_DAY

def subscribe(tenant_id: str, plan: str) -> dict:
    existing = get_subscription_by_tenant(tenant_id)
    if existing:
        raise ValueError(f"Tenant {tenant_id} already has an active subscription")
    return create_subscription(tenant_id, plan)

def cancel(tenant_id: str):
    sub = get_subscription_by_tenant(tenant_id)
    if sub:
        cancel_subscription(sub["id"])

def upgrade(tenant_id: str, new_plan: str):
    sub = get_subscription_by_tenant(tenant_id)
    if not sub:
        raise ValueError(f"No active subscription for tenant {tenant_id}")
    upgrade_plan(sub["id"], new_plan)

def get_billable_subscriptions() -> list[dict]:
    """Returns all subscriptions marked as active."""
    return get_all_active_subscriptions()
'''
FILES["subscriptions/subscription_service.py"] = (_code, _with_docstring(
    "subscriptions/subscription_service.py -- Subscription business logic.\n\n"
    "Depends on: subscriptions/subscription_model.py, tenants/tenant_model.py :: get_tenant()\n"
    "Exports:\n"
    "    subscribe(tenant_id, plan) -> dict\n"
    "    cancel(tenant_id) -> None\n"
    "    upgrade(tenant_id, new_plan) -> None\n"
    "    get_billable_subscriptions() -> list[dict]\n"
    "Used by: services/billing_service.py, api/subscriptions.py\n",
    _code))

# ── invoices/invoice_model.py ─────────────────────────────────────────────────
_code = '''\
from db.connection import execute, execute_one
from datetime import date

def get_invoice(invoice_id: str) -> dict | None:
    return execute_one("SELECT * FROM invoices WHERE id = %s", (invoice_id,))

def get_invoices_by_tenant(tenant_id: str) -> list[dict]:
    return execute(
        "SELECT * FROM invoices WHERE tenant_id = %s ORDER BY created_at DESC",
        (tenant_id,)
    )

def get_outstanding_invoices() -> list[dict]:
    """Returns all unpaid invoices."""
    return execute("SELECT * FROM invoices WHERE status = 'outstanding'")

def get_invoices_for_period(year: int, month: int) -> list[dict]:
    return execute(
        """SELECT * FROM invoices
           WHERE EXTRACT(YEAR FROM created_at) = %s
             AND EXTRACT(MONTH FROM created_at) = %s""",
        (year, month)
    )

def create_invoice(tenant_id: str, subscription_id: str,
                   amount_cents: int, period_month: date) -> dict:
    return execute_one(
        """INSERT INTO invoices
             (tenant_id, subscription_id, amount_cents, period_month, status)
           VALUES (%s, %s, %s, %s, 'outstanding') RETURNING *""",
        (tenant_id, subscription_id, amount_cents, period_month)
    )

def mark_paid(invoice_id: str, stripe_charge_id: str):
    execute(
        "UPDATE invoices SET status = 'paid', stripe_charge_id = %s WHERE id = %s",
        (stripe_charge_id, invoice_id)
    )

def mark_void(invoice_id: str):
    execute("UPDATE invoices SET status = 'void' WHERE id = %s", (invoice_id,))
'''
FILES["invoices/invoice_model.py"] = (_code, _with_docstring(
    "invoices/invoice_model.py -- Invoice CRUD.\n\n"
    "Depends on: db/connection.py :: execute(), execute_one()\n"
    "Exports:\n"
    "    get_invoice(invoice_id) -> dict | None\n"
    "    get_invoices_by_tenant(tenant_id) -> list[dict]\n"
    "    get_outstanding_invoices() -> list[dict]      # NO filtro tenant status\n"
    "    get_invoices_for_period(year, month) -> list[dict]\n"
    "    create_invoice(tenant_id, subscription_id, amount_cents, period_month) -> dict\n"
    "    mark_paid(invoice_id, stripe_charge_id) -> None\n"
    "    mark_void(invoice_id) -> None\n"
    "Used by: invoices/invoice_service.py, reports/monthly_revenue.py\n\n"
    "Rules:\n"
    "  - invoices.tenant_id è FK su tenants.id.\n"
    "  - get_outstanding_invoices() e get_invoices_for_period() NON filtrano per\n"
    "    tenant.suspended_at: includono fatture di tenant sospesi.\n"
    "  - Chiunque usi queste funzioni per report di entrate DEVE considerare se\n"
    "    escludere tenant sospesi (vedi tenants/tenant_model.py :: suspend_tenant()).\n",
    _code))

# ── invoices/invoice_service.py ───────────────────────────────────────────────
_code = '''\
from invoices.invoice_model import (
    get_invoice, get_invoices_by_tenant, get_outstanding_invoices,
    get_invoices_for_period, create_invoice, mark_paid, mark_void
)
from services.stripe_service import charge_card
from notifications.email import send_invoice_email
from config import TAX_RATE

def issue_invoice(tenant_id: str, subscription_id: str,
                  base_amount_cents: int, period_month) -> dict:
    tax = round(base_amount_cents * TAX_RATE)
    total = base_amount_cents + tax
    invoice = create_invoice(tenant_id, subscription_id, total, period_month)
    send_invoice_email(tenant_id, invoice)
    return invoice

def collect_payment(invoice_id: str, payment_method: str):
    invoice = get_invoice(invoice_id)
    if not invoice or invoice["status"] != "outstanding":
        raise ValueError("Invoice not collectable")
    charge = charge_card(invoice["amount_cents"], payment_method)
    mark_paid(invoice_id, charge["id"])
    return charge

def void_invoice(invoice_id: str):
    mark_void(invoice_id)

def get_revenue_for_period(year: int, month: int) -> list[dict]:
    """Returns all invoices (paid + outstanding) for revenue reporting."""
    return get_invoices_for_period(year, month)

def get_pending_collections() -> list[dict]:
    return get_outstanding_invoices()
'''
FILES["invoices/invoice_service.py"] = (_code, _with_docstring(
    "invoices/invoice_service.py -- Invoice business logic and payment collection.\n\n"
    "Depends on: invoices/invoice_model.py, services/stripe_service.py,\n"
    "            notifications/email.py :: send_invoice_email()\n"
    "Exports:\n"
    "    issue_invoice(tenant_id, subscription_id, base_amount_cents, period_month) -> dict\n"
    "    collect_payment(invoice_id, payment_method) -> dict\n"
    "    void_invoice(invoice_id) -> None\n"
    "    get_revenue_for_period(year, month) -> list[dict]\n"
    "    get_pending_collections() -> list[dict]\n"
    "Used by: services/billing_service.py, reports/monthly_revenue.py, api/invoices.py\n\n"
    "Rules:\n"
    "  - get_revenue_for_period() chiama invoice_model.get_invoices_for_period() che\n"
    "    non filtra per tenant.suspended_at (vedi invoices/invoice_model.py :: Rules).\n"
    "  - TAX_RATE è già applicata in issue_invoice(); non applicarla nuovamente.\n",
    _code))

# ── services/billing_service.py ───────────────────────────────────────────────
_code = '''\
from subscriptions.subscription_service import get_billable_subscriptions
from invoices.invoice_service import issue_invoice
from tenants.tenant_model import get_tenant
from datetime import date

def run_monthly_billing(year: int, month: int) -> list[dict]:
    """Issue invoices for all active subscriptions."""
    subscriptions = get_billable_subscriptions()
    issued = []
    period = date(year, month, 1)
    for sub in subscriptions:
        tenant = get_tenant(sub["tenant_id"])
        if not tenant:
            continue
        invoice = issue_invoice(
            tenant_id=sub["tenant_id"],
            subscription_id=sub["id"],
            base_amount_cents=sub["price_cents"],
            period_month=period
        )
        issued.append(invoice)
    return issued
'''
FILES["services/billing_service.py"] = (_code, _with_docstring(
    "services/billing_service.py -- Monthly billing orchestration.\n\n"
    "Depends on: subscriptions/subscription_service.py :: get_billable_subscriptions(),\n"
    "            invoices/invoice_service.py :: issue_invoice(),\n"
    "            tenants/tenant_model.py :: get_tenant()\n"
    "Exports:\n"
    "    run_monthly_billing(year, month) -> list[dict]\n"
    "Used by: workers/billing_runner.py\n\n"
    "Rules:\n"
    "  - Chiama get_billable_subscriptions() che include subscriptions di tenant sospesi\n"
    "    (vedi subscriptions/subscription_model.py :: get_all_active_subscriptions() :: Rules).\n"
    "  - Il controllo tenant.suspended_at non avviene qui.\n",
    _code))

# ── reports/monthly_revenue.py ────────────────────────────────────────────────
_code = '''\
from invoices.invoice_service import get_revenue_for_period
from tenants.tenant_model import get_tenant

def generate_monthly_report(year: int, month: int) -> dict:
    """Generate revenue report for a given month."""
    invoices = get_revenue_for_period(year, month)
    total_revenue = sum(inv["amount_cents"] for inv in invoices)
    paid = [inv for inv in invoices if inv["status"] == "paid"]
    outstanding = [inv for inv in invoices if inv["status"] == "outstanding"]
    by_tenant = {}
    for inv in invoices:
        tid = inv["tenant_id"]
        by_tenant.setdefault(tid, []).append(inv)
    return {
        "year": year,
        "month": month,
        "total_revenue_cents": total_revenue,
        "paid_count": len(paid),
        "outstanding_count": len(outstanding),
        "invoice_count": len(invoices),
        "by_tenant": by_tenant,
    }

def generate_annual_summary(year: int) -> list[dict]:
    return [generate_monthly_report(year, m) for m in range(1, 13)]
'''
FILES["reports/monthly_revenue.py"] = (_code, _with_docstring(
    "reports/monthly_revenue.py -- Monthly and annual revenue reports.\n\n"
    "Depends on: invoices/invoice_service.py :: get_revenue_for_period(),\n"
    "            tenants/tenant_model.py :: get_tenant()\n"
    "Exports:\n"
    "    generate_monthly_report(year, month) -> dict\n"
    "    generate_annual_summary(year) -> list[dict]\n"
    "Used by: api/reports.py, workers/report_scheduler.py\n",
    _code))

# ── services/stripe_service.py ────────────────────────────────────────────────
_code = '''\
import stripe
from config import STRIPE_KEY

stripe.api_key = STRIPE_KEY

def charge_card(amount_cents: int, payment_method: str) -> dict:
    intent = stripe.PaymentIntent.create(
        amount=amount_cents,
        currency="eur",
        payment_method=payment_method,
        confirm=True,
    )
    return {"id": intent.id, "status": intent.status}

def refund_charge(charge_id: str, amount_cents: int | None = None) -> dict:
    params = {"charge": charge_id}
    if amount_cents:
        params["amount"] = amount_cents
    refund = stripe.Refund.create(**params)
    return {"id": refund.id, "status": refund.status}

def create_customer(email: str, name: str) -> str:
    customer = stripe.Customer.create(email=email, name=name)
    return customer.id

def attach_payment_method(customer_id: str, payment_method_id: str):
    stripe.PaymentMethod.attach(payment_method_id, customer=customer_id)
'''
FILES["services/stripe_service.py"] = (_code, _with_docstring(
    "services/stripe_service.py -- Stripe payment gateway integration.\n\n"
    "Depends on: config.py :: STRIPE_KEY\n"
    "Exports:\n"
    "    charge_card(amount_cents, payment_method) -> dict\n"
    "    refund_charge(charge_id, amount_cents) -> dict\n"
    "    create_customer(email, name) -> str (customer_id)\n"
    "    attach_payment_method(customer_id, payment_method_id) -> None\n"
    "Used by: invoices/invoice_service.py :: collect_payment()\n\n"
    "Rules:\n"
    "  - amount_cents in CENTESIMI INTERI (es. 2900 = 29.00 EUR).\n"
    "  - Non applicare tax qui: già applicata in invoice_service.py :: issue_invoice().\n",
    _code))

# ── notifications/email.py ────────────────────────────────────────────────────
_code = '''\
import sendgrid
from sendgrid.helpers.mail import Mail
from config import SENDGRID_KEY

def _send(to: str, subject: str, body: str):
    sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_KEY)
    msg = Mail(from_email="billing@saas.io", to_emails=to,
               subject=subject, html_content=body)
    sg.send(msg)

def send_invoice_email(tenant_id: str, invoice: dict):
    _send(f"billing+{tenant_id}@saas.io",
          f"Fattura #{invoice['id']}",
          f"<p>Importo: {invoice['amount_cents']/100:.2f} EUR</p>")

def send_suspension_notice(email: str, tenant_id: str, reason: str = ""):
    _send(email,
          "Il tuo account è stato sospeso",
          f"<p>Account {tenant_id} sospeso. Motivo: {reason or 'Non specificato'}</p>")

def send_payment_failed(email: str, invoice_id: str):
    _send(email, "Pagamento fallito",
          f"<p>Non è stato possibile processare il pagamento per la fattura {invoice_id}.</p>")

def send_welcome(email: str, tenant_name: str):
    _send(email, f"Benvenuto in SaaS — {tenant_name}",
          f"<p>Ciao {tenant_name}, il tuo account è pronto!</p>")
'''
FILES["notifications/email.py"] = (_code, _with_docstring(
    "notifications/email.py -- Transactional email via SendGrid.\n\n"
    "Depends on: config.py :: SENDGRID_KEY\n"
    "Exports:\n"
    "    send_invoice_email(tenant_id, invoice) -> None\n"
    "    send_suspension_notice(email, tenant_id, reason) -> None\n"
    "    send_payment_failed(email, invoice_id) -> None\n"
    "    send_welcome(email, tenant_name) -> None\n"
    "Used by: invoices/invoice_service.py, tenants/tenant_service.py :: suspend()\n",
    _code))

# ── api/reports.py ────────────────────────────────────────────────────────────
_code = '''\
from flask import Blueprint, request, jsonify
from reports.monthly_revenue import generate_monthly_report, generate_annual_summary
from api.auth import require_admin

reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")

@reports_bp.route("/monthly", methods=["GET"])
@require_admin
def monthly():
    year = int(request.args.get("year", 2025))
    month = int(request.args.get("month", 1))
    report = generate_monthly_report(year, month)
    return jsonify(report)

@reports_bp.route("/annual", methods=["GET"])
@require_admin
def annual():
    year = int(request.args.get("year", 2025))
    summary = generate_annual_summary(year)
    return jsonify(summary)
'''
FILES["api/reports.py"] = (_code, _with_docstring(
    "api/reports.py -- Revenue report API endpoints.\n\n"
    "Depends on: reports/monthly_revenue.py :: generate_monthly_report(), generate_annual_summary(),\n"
    "            api/auth.py :: require_admin\n"
    "Exports: reports_bp (Flask Blueprint)\n"
    "Used by: app.py :: create_app()\n",
    _code))

# ── api/auth.py ───────────────────────────────────────────────────────────────
_code = '''\
import jwt
from functools import wraps
from flask import request, jsonify
from config import JWT_SECRET

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            if payload.get("role") != "admin":
                return jsonify({"error": "Forbidden"}), 403
        except jwt.InvalidTokenError:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            request.tenant_id = payload.get("tenant_id")
        except jwt.InvalidTokenError:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated
'''
FILES["api/auth.py"] = (_code, _with_docstring(
    "api/auth.py -- JWT authentication decorators.\n\n"
    "Depends on: config.py :: JWT_SECRET\n"
    "Exports: require_admin (decorator), require_auth (decorator)\n"
    "Used by: api/reports.py, api/admin.py, api/invoices.py, api/subscriptions.py\n",
    _code))

# ── api/admin.py ──────────────────────────────────────────────────────────────
_code = '''\
from flask import Blueprint, request, jsonify
from tenants.tenant_service import suspend, reactivate, list_tenants_for_billing
from api.auth import require_admin

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

@admin_bp.route("/tenants", methods=["GET"])
@require_admin
def tenants():
    return jsonify(list_tenants_for_billing())

@admin_bp.route("/tenants/<tid>/suspend", methods=["POST"])
@require_admin
def suspend_tenant(tid):
    reason = request.json.get("reason", "")
    suspend(tid, reason)
    return jsonify({"status": "suspended"})

@admin_bp.route("/tenants/<tid>/reactivate", methods=["POST"])
@require_admin
def reactivate_tenant(tid):
    reactivate(tid)
    return jsonify({"status": "active"})
'''
FILES["api/admin.py"] = (_code, _with_docstring(
    "api/admin.py -- Admin API for tenant management.\n\n"
    "Depends on: tenants/tenant_service.py :: suspend(), reactivate(), list_tenants_for_billing(),\n"
    "            api/auth.py :: require_admin\n"
    "Exports: admin_bp (Flask Blueprint)\n"
    "Used by: app.py :: create_app()\n",
    _code))

# ── api/invoices.py ───────────────────────────────────────────────────────────
_code = '''\
from flask import Blueprint, request, jsonify
from invoices.invoice_service import get_revenue_for_period, collect_payment, void_invoice
from api.auth import require_admin, require_auth

invoices_bp = Blueprint("invoices", __name__, url_prefix="/api/invoices")

@invoices_bp.route("/period", methods=["GET"])
@require_admin
def period():
    year = int(request.args.get("year", 2025))
    month = int(request.args.get("month", 1))
    return jsonify(get_revenue_for_period(year, month))

@invoices_bp.route("/<invoice_id>/pay", methods=["POST"])
@require_auth
def pay(invoice_id):
    pm = request.json["payment_method"]
    charge = collect_payment(invoice_id, pm)
    return jsonify(charge)

@invoices_bp.route("/<invoice_id>/void", methods=["POST"])
@require_admin
def void(invoice_id):
    void_invoice(invoice_id)
    return jsonify({"status": "voided"})
'''
FILES["api/invoices.py"] = (_code, _with_docstring(
    "api/invoices.py -- Invoice API endpoints.\n\n"
    "Depends on: invoices/invoice_service.py, api/auth.py\n"
    "Exports: invoices_bp (Flask Blueprint)\n"
    "Used by: app.py :: create_app()\n",
    _code))

# ── api/subscriptions.py ──────────────────────────────────────────────────────
_code = '''\
from flask import Blueprint, request, jsonify
from subscriptions.subscription_service import subscribe, cancel, upgrade
from api.auth import require_admin, require_auth

subs_bp = Blueprint("subscriptions", __name__, url_prefix="/api/subscriptions")

@subs_bp.route("/", methods=["POST"])
@require_auth
def create():
    data = request.json
    sub = subscribe(data["tenant_id"], data["plan"])
    return jsonify(sub), 201

@subs_bp.route("/<tenant_id>", methods=["DELETE"])
@require_auth
def cancel_sub(tenant_id):
    cancel(tenant_id)
    return jsonify({"status": "cancelled"})

@subs_bp.route("/<tenant_id>/upgrade", methods=["POST"])
@require_auth
def upgrade_sub(tenant_id):
    new_plan = request.json["plan"]
    upgrade(tenant_id, new_plan)
    return jsonify({"status": "upgraded"})
'''
FILES["api/subscriptions.py"] = (_code, _with_docstring(
    "api/subscriptions.py -- Subscription API endpoints.\n\n"
    "Depends on: subscriptions/subscription_service.py, api/auth.py\n"
    "Exports: subs_bp (Flask Blueprint)\n"
    "Used by: app.py :: create_app()\n",
    _code))

# ── workers/billing_runner.py ─────────────────────────────────────────────────
_code = '''\
from services.billing_service import run_monthly_billing
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def run(year: int | None = None, month: int | None = None):
    now = datetime.utcnow()
    year = year or now.year
    month = month or now.month
    logger.info(f"Starting billing run for {year}-{month:02d}")
    invoices = run_monthly_billing(year, month)
    logger.info(f"Billing complete: {len(invoices)} invoices issued")
    return invoices

if __name__ == "__main__":
    run()
'''
FILES["workers/billing_runner.py"] = (_code, _with_docstring(
    "workers/billing_runner.py -- Monthly billing cron worker.\n\n"
    "Depends on: services/billing_service.py :: run_monthly_billing()\n"
    "Exports: run(year, month) -> list[dict]\n"
    "Used by: cron, workers/scheduler.py\n",
    _code))

# ── workers/report_scheduler.py ───────────────────────────────────────────────
_code = '''\
from reports.monthly_revenue import generate_monthly_report
from notifications.email import send_invoice_email
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def send_monthly_summary(year: int | None = None, month: int | None = None):
    now = datetime.utcnow()
    year = year or now.year
    month = month or ((now.month - 1) or 12)
    report = generate_monthly_report(year, month)
    logger.info(f"Monthly report: {report['total_revenue_cents']/100:.2f} EUR")
    return report
'''
FILES["workers/report_scheduler.py"] = (_code, _with_docstring(
    "workers/report_scheduler.py -- Monthly revenue report scheduler.\n\n"
    "Depends on: reports/monthly_revenue.py :: generate_monthly_report()\n"
    "Exports: send_monthly_summary(year, month) -> dict\n"
    "Used by: cron\n",
    _code))

# ── app.py ────────────────────────────────────────────────────────────────────
_code = '''\
from flask import Flask
from api.reports import reports_bp
from api.admin import admin_bp
from api.invoices import invoices_bp
from api.subscriptions import subs_bp

def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(subs_bp)
    return app

if __name__ == "__main__":
    create_app().run(debug=True)
'''
FILES["app.py"] = (_code, _with_docstring(
    "app.py -- Flask application factory.\n\n"
    "Depends on: api/reports.py, api/admin.py, api/invoices.py, api/subscriptions.py\n"
    "Exports: create_app() -> Flask\n"
    "Used by: wsgi.py, workers/\n",
    _code))


# ─────────────────────────────────────────────────────────────────────────────

PACKAGES = [
    "db", "tenants", "subscriptions", "invoices",
    "services", "reports", "notifications", "api", "workers"
]

def generate(version: str, label: str, base: Path):
    root = base / label
    if root.exists():
        shutil.rmtree(root)
    for pkg in PACKAGES:
        (root / pkg / "__init__.py").touch(exist_ok=False) if False else \
        (root / pkg).mkdir(parents=True, exist_ok=True)
        (root / pkg / "__init__.py").write_text("")
    for path, (ctrl, cdna) in FILES.items():
        full = root / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(ctrl if version == "control" else cdna, encoding="utf-8")
    total_lines = sum(
        (ctrl if version == "control" else cdna).count("\n")
        for _, (ctrl, cdna) in FILES.items()
    )
    print(f"✅ {label}: {len(FILES)} file, ~{total_lines} righe → {root}")


if __name__ == "__main__":
    BASE.mkdir(parents=True, exist_ok=True)
    generate("control", "large_control", BASE)
    generate("codedna", "large_codedna", BASE)
    print(f"\n📂 Progetti in {BASE}")
    print("  large_control/ → nessun docstring")
    print("  large_codedna/ → module docstring architetturali (no bug hint)")
    print("\nBUG nascosto: tenant sospesi (suspended_at) inclusi nel revenue report.")
    print("Chain: reports/monthly_revenue.py → invoices/invoice_service.py")
    print("       → invoices/invoice_model.py → (manca JOIN tenants)")
