"""billing.py — Billing and credit management schemas.

exports: CreditPurchase, InvoiceResponse, TransactionResponse, StripeWebhook
used_by: billing.py router
rules:   must validate currency codes; must enforce positive amounts
agent:   BackendEngineer | 2024-01-15 | created billing schemas
         message: "implement Stripe integration with proper webhook handling"
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator
import re


class CreditPurchase(BaseModel):
    """Schema for credit purchase request."""
    
    amount: float = Field(..., gt=0, description="Purchase amount in USD")
    currency: str = Field("USD", description="Currency code (3 letters)")
    payment_method_id: str = Field(..., description="Stripe payment method ID")
    
    @validator("currency")
    def validate_currency(cls, v):
        """Validate currency code."""
        if not re.match(r"^[A-Z]{3}$", v):
            raise ValueError("Currency must be a 3-letter uppercase code")
        return v


class InvoiceResponse(BaseModel):
    """Schema for invoice response."""
    
    public_id: str = Field(..., description="Public invoice ID")
    amount: float = Field(..., description="Invoice amount")
    currency: str = Field(..., description="Currency code")
    status: str = Field(..., description="Invoice status")
    payment_method: Optional[str] = Field(None, description="Payment method used")
    payment_id: Optional[str] = Field(None, description="External payment system ID")
    credits_added: float = Field(..., description="Credits added to account")
    metadata: Dict[str, Any] = Field(..., description="Invoice metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    paid_at: Optional[datetime] = Field(None, description="Payment timestamp")
    
    class Config:
        from_attributes = True


class TransactionResponse(BaseModel):
    """Schema for credit transaction response."""
    
    id: int = Field(..., description="Transaction ID")
    type: str = Field(..., description="Transaction type (purchase, agent_run, refund)")
    amount: float = Field(..., description="Transaction amount")
    balance_before: float = Field(..., description="Balance before transaction")
    balance_after: float = Field(..., description="Balance after transaction")
    description: str = Field(..., description="Transaction description")
    reference_id: Optional[str] = Field(None, description="Reference ID (invoice_id, run_id)")
    metadata: Dict[str, Any] = Field(..., description="Transaction metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True


class StripeWebhook(BaseModel):
    """Schema for Stripe webhook events."""
    
    id: str = Field(..., description="Stripe event ID")
    type: str = Field(..., description="Event type")
    data: Dict[str, Any] = Field(..., description="Event data")
    created: int = Field(..., description="Event creation timestamp")
    livemode: bool = Field(..., description="Whether event is from live mode")
    pending_webhooks: int = Field(..., description="Number of pending webhooks")
    request: Optional[Dict[str, Any]] = Field(None, description="Request information")
    api_version: Optional[str] = Field(None, description="Stripe API version")