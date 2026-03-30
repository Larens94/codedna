"""app/api/v1/billing.py — Billing and subscription endpoints.

exports: router
used_by: app/api/v1/router.py -> billing router
rules:   Stripe webhook must verify signature before processing; credits in cents
agent:   claude-sonnet-4-6 | anthropic | 2026-03-31 | s_20260331_001 | created stub router to unblock startup
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.dependencies import get_current_user, get_services
from app.services import ServiceContainer

router = APIRouter()


@router.get("/usage")
async def get_usage(
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
):
    """Get current billing period usage."""
    try:
        return await services.billing.get_organization_usage(user_id=current_user.id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/invoices")
async def list_invoices(
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
):
    """List invoices for current organization."""
    try:
        return await services.billing.get_invoices(user_id=current_user.id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events.

    Rules:
        Must verify Stripe signature before processing any event.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        services: ServiceContainer = request.app.state.services
        return await services.billing.handle_stripe_webhook(
            payload=payload, sig_header=sig_header
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
