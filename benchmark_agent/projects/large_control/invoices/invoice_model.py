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
