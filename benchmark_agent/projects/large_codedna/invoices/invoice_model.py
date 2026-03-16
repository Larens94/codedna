"""invoices/invoice_model.py -- Invoice CRUD.

Depends on: db/connection.py :: execute(), execute_one()
Exports:
    get_invoice(invoice_id) -> dict | None
    get_invoices_by_tenant(tenant_id) -> list[dict]
    get_outstanding_invoices() -> list[dict]      # NO filtro tenant status
    get_invoices_for_period(year, month) -> list[dict]
    create_invoice(tenant_id, subscription_id, amount_cents, period_month) -> dict
    mark_paid(invoice_id, stripe_charge_id) -> None
    mark_void(invoice_id) -> None
Used by: invoices/invoice_service.py, reports/monthly_revenue.py

Rules:
  - invoices.tenant_id è FK su tenants.id.
  - get_outstanding_invoices() e get_invoices_for_period() NON filtrano per
    tenant.suspended_at: includono fatture di tenant sospesi.
  - Chiunque usi queste funzioni per report di entrate DEVE considerare se
    escludere tenant sospesi (vedi tenants/tenant_model.py :: suspend_tenant()).
"""
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
