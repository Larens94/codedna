"""workers/report_scheduler.py -- Monthly revenue report scheduler.

Depends on: reports/monthly_revenue.py :: generate_monthly_report()
Exports: send_monthly_summary(year, month) -> dict
Used by: cron
"""
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
