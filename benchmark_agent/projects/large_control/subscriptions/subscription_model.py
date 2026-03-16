from db.connection import execute, execute_one

PLANS = {
    "starter":    {"price_cents": 2900,  "seats": 5},
    "growth":     {"price_cents": 9900,  "seats": 25},
    "business":   {"price_cents": 29900, "seats": 100},
    "enterprise": {"price_cents": 99900, "seats": 500},
}

def get_subscription_by_tenant(tenant_id: str) -> dict | None:
    return execute_one(
        "SELECT * FROM subscriptions WHERE tenant_id = %s AND status = 'active'",
        (tenant_id,)
    )

def get_all_active_subscriptions() -> list[dict]:
    return execute(
        "SELECT * FROM subscriptions WHERE status = 'active'"
    )

def create_subscription(tenant_id: str, plan: str) -> dict:
    price = PLANS[plan]["price_cents"]
    return execute_one(
        """INSERT INTO subscriptions (tenant_id, plan, price_cents, status)
           VALUES (%s, %s, %s, 'active') RETURNING *""",
        (tenant_id, plan, price)
    )

def cancel_subscription(subscription_id: str):
    execute(
        "UPDATE subscriptions SET status = 'cancelled', cancelled_at = NOW() WHERE id = %s",
        (subscription_id,)
    )

def upgrade_plan(subscription_id: str, new_plan: str):
    price = PLANS[new_plan]["price_cents"]
    execute(
        "UPDATE subscriptions SET plan = %s, price_cents = %s WHERE id = %s",
        (new_plan, price, subscription_id)
    )
