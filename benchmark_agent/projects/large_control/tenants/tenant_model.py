from db.connection import execute, execute_one

def get_tenant(tenant_id: str) -> dict | None:
    return execute_one(
        "SELECT * FROM tenants WHERE id = %s",
        (tenant_id,)
    )

def list_active_tenants() -> list[dict]:
    return execute(
        "SELECT * FROM tenants WHERE suspended_at IS NULL AND deleted_at IS NULL"
    )

def create_tenant(name: str, plan: str, owner_email: str) -> dict:
    return execute_one(
        "INSERT INTO tenants (name, plan, owner_email) VALUES (%s, %s, %s) RETURNING *",
        (name, plan, owner_email)
    )

def update_tenant(tenant_id: str, data: dict) -> dict:
    sets = ", ".join(f"{k} = %s" for k in data)
    vals = list(data.values()) + [tenant_id]
    return execute_one(f"UPDATE tenants SET {sets} WHERE id = %s RETURNING *", tuple(vals))

def suspend_tenant(tenant_id: str):
    """Soft-suspend: sets suspended_at = NOW(). Tenant row stays in DB."""
    execute("UPDATE tenants SET suspended_at = NOW() WHERE id = %s", (tenant_id,))

def reactivate_tenant(tenant_id: str):
    execute("UPDATE tenants SET suspended_at = NULL WHERE id = %s", (tenant_id,))

def delete_tenant(tenant_id: str):
    """Soft delete: sets deleted_at = NOW()."""
    execute("UPDATE tenants SET deleted_at = NOW() WHERE id = %s", (tenant_id,))

def is_active(tenant: dict) -> bool:
    return tenant.get("suspended_at") is None and tenant.get("deleted_at") is None
