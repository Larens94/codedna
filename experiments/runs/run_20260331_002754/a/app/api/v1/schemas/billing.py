"""app/api/v1/schemas/billing.py — Pydantic schemas for billing endpoints.

exports: InvoiceResponse, LineItemResponse, PaymentIntentCreate, PaymentMethodResponse, SubscriptionCreate, SubscriptionResponse
used_by: app/api/v1/billing.py → request/response validation
rules:   invoice numbers must follow INV-YYYY-NNN format; currency must be ISO 4217
agent:   BackendEngineer | 2024-03-31 | created billing schemas with validation
         message: "verify Stripe webhook signature validation"
"""

import re
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator
from .base import BaseSchema, PaginatedResponse


class InvoiceStatus(str, Enum):
    """Invoice status."""
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    VOID = "void"


class InvoiceResponse(BaseSchema):
    """Schema for invoice response."""
    id: int = Field(..., description="Invoice ID")
    organization_id: int = Field(..., description="Organization ID")
    invoice_number: str = Field(..., description="Invoice number (e.g., INV-2024-001)")
    period_start: date = Field(..., description="Billing period start date")
    period_end: date = Field(..., description="Billing period end date")
    total_amount: float = Field(..., ge=0, description="Total invoice amount")
    currency: str = Field(..., description="Currency code (ISO 4217)")
    status: InvoiceStatus = Field(..., description="Invoice status")
    stripe_invoice_id: Optional[str] = Field(None, description="Stripe invoice ID")
    stripe_payment_intent_id: Optional[str] = Field(None, description="Stripe payment intent ID")
    due_at: Optional[datetime] = Field(None, description="Invoice due date")
    paid_at: Optional[datetime] = Field(None, description="When invoice was paid")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    subtotal: float = Field(..., description="Subtotal (sum of line items)")
    tax_amount: float = Field(..., description="Tax amount")
    grand_total: float = Field(..., description="Grand total (subtotal + tax)")
    
    @validator('invoice_number')
    def validate_invoice_number(cls, v):
        """Validate invoice number format."""
        pattern = r'^INV-\d{4}-\d{3,}$'
        if not re.match(pattern, v):
            raise ValueError('Invoice number must be in format INV-YYYY-NNN')
        return v
    
    @validator('currency')
    def validate_currency(cls, v):
        """Validate currency code."""
        if len(v) != 3 or not v.isalpha():
            raise ValueError('Currency code must be 3 letters (ISO 4217)')
        return v.upper()


class LineItemResponse(BaseSchema):
    """Schema for invoice line item response."""
    id: int = Field(..., description="Line item ID")
    invoice_id: int = Field(..., description="Invoice ID")
    description: str = Field(..., description="Line item description")
    quantity: float = Field(..., ge=0, description="Quantity")
    unit_price: float = Field(..., ge=0, description="Price per unit")
    total_amount: float = Field(..., ge=0, description="Total amount (quantity × unit_price)")
    usage_record_ids: List[int] = Field(default=[], description="Usage record IDs included")


class InvoiceWithLineItemsResponse(InvoiceResponse):
    """Invoice response with line items."""
    line_items: List[LineItemResponse] = Field(default=[], description="Line items")


class PaymentIntentCreate(BaseSchema):
    """Schema for creating a payment intent."""
    invoice_id: int = Field(..., description="Invoice ID to pay")
    payment_method_id: Optional[str] = Field(None, description="Payment method ID (if saving)")
    save_payment_method: bool = Field(default=False, description="Whether to save payment method for future use")


class PaymentMethodResponse(BaseSchema):
    """Schema for payment method response."""
    id: str = Field(..., description="Payment method ID")
    type: str = Field(..., description="Payment method type (card, etc.)")
    last4: Optional[str] = Field(None, description="Last 4 digits (for cards)")
    brand: Optional[str] = Field(None, description="Card brand")
    exp_month: Optional[int] = Field(None, description="Expiration month")
    exp_year: Optional[int] = Field(None, description="Expiration year")
    is_default: bool = Field(default=False, description="Whether this is the default payment method")


class SubscriptionCreate(BaseSchema):
    """Schema for creating a subscription."""
    plan_tier: str = Field(..., description="Plan tier (pro, enterprise)")
    payment_method_id: Optional[str] = Field(None, description="Payment method ID (if not using default)")
    quantity: int = Field(default=1, ge=1, description="Number of seats/users")


class SubscriptionResponse(BaseSchema):
    """Schema for subscription response."""
    id: str = Field(..., description="Subscription ID")
    organization_id: int = Field(..., description="Organization ID")
    plan_tier: str = Field(..., description="Plan tier")
    status: str = Field(..., description="Subscription status")
    current_period_start: datetime = Field(..., description="Current period start")
    current_period_end: datetime = Field(..., description="Current period end")
    cancel_at_period_end: bool = Field(..., description="Whether subscription cancels at period end")
    quantity: int = Field(..., description="Number of seats")
    amount: float = Field(..., description="Amount per period")
    currency: str = Field(..., description="Currency")
    stripe_subscription_id: Optional[str] = Field(None, description="Stripe subscription ID")


class CreditPurchaseCreate(BaseSchema):
    """Schema for purchasing credits."""
    amount: float = Field(..., gt=0, description="Amount to purchase (in currency)")
    currency: str = Field(default="USD", description="Currency code")
    payment_method_id: Optional[str] = Field(None, description="Payment method ID")


class CreditBalanceResponse(BaseSchema):
    """Schema for credit balance response."""
    total_credits: float = Field(..., ge=0, description="Total credits available")
    used_credits_month: float = Field(..., ge=0, description="Credits used this month")
    remaining_credits_month: float = Field(..., description="Remaining credits this month")
    monthly_limit: float = Field(..., description="Monthly credit limit")
    estimated_cost_month: float = Field(..., description="Estimated cost this month (in currency)")


class InvoiceListResponse(PaginatedResponse[InvoiceResponse]):
    """Paginated response for invoice list."""
    pass


class PaymentMethodListResponse(BaseSchema):
    """Response for payment method list."""
    payment_methods: List[PaymentMethodResponse] = Field(..., description="List of payment methods")
    default_payment_method_id: Optional[str] = Field(None, description="Default payment method ID")


# Import date/datetime after class definitions to avoid circular import
from datetime import datetime, date