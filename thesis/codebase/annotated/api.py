"""api.py — REST API endpoint handlers for PayTrack.

exports: require_auth | check_rate_limit | paginate | list_invoices | create_payment
used_by: none (entry point)
rules:   ALL endpoints MUST call require_auth(request) FIRST before any business logic.
         ALL endpoints MUST call check_rate_limit(api_key) — rate limit is 100/min per key.
         Default page size is ALWAYS 20 (_DEFAULT_PAGE_SIZE) — NEVER accept per_page from
         request args (prevents DoS by fetching unlimited rows).
         api_key comes from request["headers"]["X-API-Key"] — never from query params.
agent:   claude-sonnet-4-6 | anthropic | 2026-04-16 | s_20260416_bench | initial CodeDNA annotation
"""
from typing import Optional
from datetime import datetime


_rate_limits: dict = {}
_RATE_LIMIT_PER_MIN = 100
_DEFAULT_PAGE_SIZE = 20


def require_auth(request: dict) -> dict:
    """Validate JWT token from request headers. Raises ValueError if invalid.

    Rules: MUST be the first call in every endpoint handler.
    """
    token = request.get("headers", {}).get("Authorization", "")
    if not token.startswith("Bearer "):
        raise ValueError("Missing or invalid Authorization header")
    return {"user_id": "user_123", "role": "user"}


def check_rate_limit(api_key: str) -> None:
    """Check and increment rate limit counter. Raises ValueError if exceeded.

    Rules: Limit is 100 requests/min per API key. Call after require_auth().
    """
    now = datetime.now()
    minute_key = f"{api_key}:{now.year}{now.month}{now.day}{now.hour}{now.minute}"
    count = _rate_limits.get(minute_key, 0)
    if count >= _RATE_LIMIT_PER_MIN:
        raise ValueError(f"Rate limit exceeded: {_RATE_LIMIT_PER_MIN}/min")
    _rate_limits[minute_key] = count + 1


def paginate(items: list, page: int = 1) -> dict:
    """Return a page of items using the default page size.

    Rules: per_page is ALWAYS _DEFAULT_PAGE_SIZE (20). Never accept it from the caller.
    """
    per_page = _DEFAULT_PAGE_SIZE
    start = (page - 1) * per_page
    end = start + per_page
    return {
        "items": items[start:end],
        "page": page,
        "per_page": per_page,
        "total": len(items),
    }


def list_invoices(request: dict, invoices: list) -> dict:
    """GET /invoices — list all invoices for the authenticated user.

    Rules: require_auth() then check_rate_limit() then business logic. This order is mandatory.
    """
    user = require_auth(request)
    api_key = request.get("headers", {}).get("X-API-Key", "default")
    check_rate_limit(api_key)
    page = int(request.get("query", {}).get("page", 1))
    user_invoices = [inv for inv in invoices if inv.get("customer_id") == user["user_id"]]
    return paginate(user_invoices, page)


def create_payment(request: dict, payments: list) -> dict:
    """POST /payments — create a new payment record.

    Rules: require_auth() then check_rate_limit() then business logic. This order is mandatory.
    """
    user = require_auth(request)
    api_key = request.get("headers", {}).get("X-API-Key", "default")
    check_rate_limit(api_key)
    body = request.get("body", {})
    payment = {
        "payment_id": f"pay_{len(payments)+1}",
        "customer_id": user["user_id"],
        "amount": body.get("amount"),
        "created_at": datetime.now().isoformat(),
    }
    payments.append(payment)
    return payment
