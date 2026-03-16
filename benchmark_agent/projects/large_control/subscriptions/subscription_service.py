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
