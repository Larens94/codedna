"""invoices/invoice_service.py -- Invoice business logic and payment collection.

Depends on: invoices/invoice_model.py, services/stripe_service.py,
            notifications/email.py :: send_invoice_email()
Exports:
    issue_invoice(tenant_id, subscription_id, base_amount_cents, period_month) -> dict
    collect_payment(invoice_id, payment_method) -> dict
    void_invoice(invoice_id) -> None
    get_revenue_for_period(year, month) -> list[dict]
    get_pending_collections() -> list[dict]
Used by: services/billing_service.py, reports/monthly_revenue.py, api/invoices.py

Rules:
  - get_revenue_for_period() chiama invoice_model.get_invoices_for_period() che
    non filtra per tenant.suspended_at (vedi invoices/invoice_model.py :: Rules).
  - TAX_RATE è già applicata in issue_invoice(); non applicarla nuovamente.
"""
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
