"""app/services/billing_service.py — Billing, usage tracking, and subscription management.

exports: BillingService
used_by: app/services/container.py → ServiceContainer.billing, API billing endpoints, Stripe webhooks
rules:   must handle usage-based billing; sync with Stripe; enforce plan limits; generate invoices
         get_organization_usage and get_invoices return static demo data — no Stripe calls
agent:   Product Architect | 2024-03-30 | created billing service skeleton
         message: "implement usage aggregation with idempotency to prevent double billing"
         claude-sonnet-4-6 | anthropic | 2026-03-31 | s_20260331_002 | implemented get_organization_usage, get_invoices, handle_stripe_webhook with demo data
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from decimal import Decimal

from app.exceptions import NotFoundError, ValidationError, ServiceUnavailableError
from app.services.container import ServiceContainer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static demo billing data
# ---------------------------------------------------------------------------
_DEMO_USAGE_DAILY = [
    {"date": "2026-03-25", "tokens": 1200, "cost": 5.40},
    {"date": "2026-03-26", "tokens": 1900, "cost": 8.55},
    {"date": "2026-03-27", "tokens": 3000, "cost": 13.50},
    {"date": "2026-03-28", "tokens": 2500, "cost": 11.25},
    {"date": "2026-03-29", "tokens": 1800, "cost": 8.10},
    {"date": "2026-03-30", "tokens": 2200, "cost": 9.90},
    {"date": "2026-03-31", "tokens": 3200, "cost": 14.40},
]

_DEMO_INVOICES = [
    {"id": "INV-2026-03", "date": "2026-03-01", "amount": 45.00, "status": "paid", "download_url": "#"},
    {"id": "INV-2026-02", "date": "2026-02-01", "amount": 45.00, "status": "paid", "download_url": "#"},
]


class BillingService:
    """Billing, usage tracking, and subscription management service.

    Rules:
        Usage records must be immutable once created
        Billing calculations must be idempotent
        Stripe webhook handlers must be idempotent
        All currency amounts stored in cents (integers)
        In-memory / demo mode — no Stripe calls in this environment
    """

    def __init__(self, container: ServiceContainer):
        self.container = container
        logger.info("BillingService initialized")

    # ------------------------------------------------------------------
    # Implemented methods (demo data)
    # ------------------------------------------------------------------

    async def get_organization_usage(
        self,
        user_id: Any = None,
        organization_id: Any = None,
        billing_period: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return demo usage summary for the current billing period."""
        return {
            "plan": "Pro",
            "credits_used": 4500,
            "credits_total": 10000,
            "monthly_cost": 45.00,
            "next_billing_date": "2026-05-01",
            "usage": _DEMO_USAGE_DAILY,
            "invoices": _DEMO_INVOICES,
            # Dashboard summary fields
            "total_agents": 6,
            "active_sessions": 2,
            "dates": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "tokens": [1200, 1900, 3000, 2500, 1800, 2200, 3200],
        }

    async def get_invoices(
        self,
        user_id: Any = None,
        organization_id: Any = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Return demo invoice list."""
        return _DEMO_INVOICES[:limit]

    async def handle_stripe_webhook(
        self,
        payload: Any = None,
        sig_header: str = "",
        event_type: str = "",
        event_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Accept Stripe webhook — demo no-op."""
        return {"received": True}

    # ------------------------------------------------------------------
    # Skeleton stubs (not yet implemented)
    # ------------------------------------------------------------------

    async def record_usage(self, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError("record_usage not yet implemented")

    async def create_stripe_customer(self, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError("create_stripe_customer not yet implemented")

    async def create_subscription(self, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError("create_subscription not yet implemented")

    async def cancel_subscription(self, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError("cancel_subscription not yet implemented")

    async def update_subscription(self, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError("update_subscription not yet implemented")

    async def generate_invoice(self, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError("generate_invoice not yet implemented")

    async def add_payment_method(self, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError("add_payment_method not yet implemented")

    async def get_payment_methods(self, **kwargs: Any) -> List[Dict[str, Any]]:
        raise NotImplementedError("get_payment_methods not yet implemented")

    async def calculate_usage_cost(self, metric_type: str, metric_value: Decimal, plan_tier: str) -> int:
        raise NotImplementedError("calculate_usage_cost not yet implemented")

    async def sync_subscription_status(self) -> int:
        raise NotImplementedError("sync_subscription_status not yet implemented")
