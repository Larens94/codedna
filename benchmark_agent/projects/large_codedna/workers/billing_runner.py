"""workers/billing_runner.py -- Monthly billing cron worker.

Depends on: services/billing_service.py :: run_monthly_billing()
Exports: run(year, month) -> list[dict]
Used by: cron, workers/scheduler.py
"""
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
