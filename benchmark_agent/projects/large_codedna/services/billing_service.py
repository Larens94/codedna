"""services/billing_service.py -- Monthly billing orchestration.

Depends on: subscriptions/subscription_service.py :: get_billable_subscriptions(),
            invoices/invoice_service.py :: issue_invoice(),
            tenants/tenant_model.py :: get_tenant()
Exports:
    run_monthly_billing(year, month) -> list[dict]
Used by: workers/billing_runner.py

Rules:
  - Chiama get_billable_subscriptions() che include subscriptions di tenant sospesi
    (vedi subscriptions/subscription_model.py :: get_all_active_subscriptions() :: Rules).
  - Il controllo tenant.suspended_at non avviene qui.
"""
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
