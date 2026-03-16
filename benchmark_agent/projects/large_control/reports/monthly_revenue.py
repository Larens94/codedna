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
