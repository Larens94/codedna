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
