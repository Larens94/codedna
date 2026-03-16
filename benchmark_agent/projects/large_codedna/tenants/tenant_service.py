"""tenants/tenant_service.py -- Tenant business logic and orchestration.

Depends on: tenants/tenant_model.py, subscriptions/subscription_model.py,
            notifications/email.py :: send_suspension_notice()
Exports:
    onboard_tenant(name, plan, owner_email) -> dict
    get_tenant_details(tenant_id) -> dict
    suspend(tenant_id, reason) -> None
    reactivate(tenant_id) -> None
    list_tenants_for_billing() -> list[dict]  # solo tenant attivi
Used by: api/admin.py, workers/billing_runner.py
"""
from tenants.tenant_model import (
    get_tenant, list_active_tenants, create_tenant,
    suspend_tenant, reactivate_tenant, delete_tenant, is_active
)
from subscriptions.subscription_model import get_subscription_by_tenant
from notifications.email import send_suspension_notice

def onboard_tenant(name: str, plan: str, owner_email: str) -> dict:
    tenant = create_tenant(name, plan, owner_email)
    return tenant

def get_tenant_details(tenant_id: str) -> dict:
    tenant = get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")
    sub = get_subscription_by_tenant(tenant_id)
    return {**tenant, "subscription": sub}

def suspend(tenant_id: str, reason: str = ""):
    tenant = get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")
    suspend_tenant(tenant_id)
    send_suspension_notice(tenant["owner_email"], tenant_id, reason)

def reactivate(tenant_id: str):
    tenant = get_tenant(tenant_id)
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} not found")
    reactivate_tenant(tenant_id)

def list_tenants_for_billing() -> list[dict]:
    """Returns only active (non-suspended, non-deleted) tenants."""
    return list_active_tenants()
