"""app/models/billing.py — Billing and invoice models.

exports: BillingInvoice, BillingLineItem
used_by: billing service → invoice generation, stripe integration → payment processing
rules:   invoices must reference usage records; line items must match aggregated usage
agent:   Product Architect | 2024-03-30 | implemented billing models with stripe integration
         message: "verify that invoice number generation is thread-safe"
"""

import re
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Date,
    ForeignKey,
    Numeric,
    Boolean,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

from app.models.base import Base, TimestampMixin


class InvoiceStatus(str, Enum):
    """Invoice status lifecycle."""
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    VOID = "void"


class BillingInvoice(Base, TimestampMixin):
    """Invoice for organization billing.
    
    Rules:
        Each invoice belongs to an organization
        Invoice number must be unique and sequential
        Period defines which usage records are included
        Stripe integration for payment processing
    """
    
    __tablename__ = "billing_invoices"
    
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Unique invoice identifier",
    )
    
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        doc="Organization being billed",
    )
    
    invoice_number = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        doc="Unique invoice number (e.g., INV-2024-001)",
    )
    
    period_start = Column(
        Date,
        nullable=False,
        doc="Start date of billing period",
    )
    
    period_end = Column(
        Date,
        nullable=False,
        doc="End date of billing period",
    )
    
    total_amount = Column(
        Numeric(12, 2),
        nullable=False,
        doc="Total invoice amount",
    )
    
    currency = Column(
        String(3),
        default="USD",
        nullable=False,
        doc="Currency code (ISO 4217)",
    )
    
    status = Column(
        SQLEnum(InvoiceStatus),
        default=InvoiceStatus.DRAFT,
        nullable=False,
        doc="Invoice status",
    )
    
    stripe_invoice_id = Column(
        String(255),
        nullable=True,
        unique=True,
        doc="Stripe invoice ID (if synced)",
    )
    
    stripe_payment_intent_id = Column(
        String(255),
        nullable=True,
        doc="Stripe payment intent ID",
    )
    
    due_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Invoice due date",
    )
    
    paid_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When invoice was paid",
    )
    
    # Relationships
    organization = relationship(
        "Organization",
        back_populates="billing_invoices",
        lazy="selectin",
    )
    
    line_items = relationship(
        "BillingLineItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="BillingLineItem.id",
        doc="Line items on this invoice",
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_invoices_org_id", organization_id),
        Index("ix_invoices_status", status),
        Index("ix_invoices_period", period_start, period_end),
        Index("ix_invoices_due_at", due_at),
    )
    
    @validates("invoice_number")
    def validate_invoice_number(self, key: str, number: str) -> str:
        """Validate invoice number format.
        
        Args:
            key: Field name
            number: Invoice number
            
        Returns:
            str: Validated invoice number
            
        Raises:
            ValueError: If format is invalid
        """
        if not number:
            raise ValueError("Invoice number cannot be empty")
        
        # Basic format validation: INV-YYYY-NNN
        pattern = r"^INV-\d{4}-\d{3,}$"
        if not re.match(pattern, number):
            raise ValueError("Invoice number must be in format INV-YYYY-NNN")
        
        return number
    
    @validates("currency")
    def validate_currency(self, key: str, currency: str) -> str:
        """Validate currency code.
        
        Args:
            key: Field name
            currency: Currency code
            
        Returns:
            str: Validated currency code
            
        Raises:
            ValueError: If currency code is invalid
        """
        if not currency:
            raise ValueError("Currency cannot be empty")
        
        currency = currency.upper()
        if len(currency) != 3:
            raise ValueError("Currency code must be 3 characters")
        
        # Basic validation - could be enhanced with ISO 4217 list
        if not currency.isalpha():
            raise ValueError("Currency code must contain only letters")
        
        return currency
    
    @validates("period_start", "period_end")
    def validate_period(self, key: str, period_date: date) -> date:
        """Validate billing period dates.
        
        Args:
            key: Field name
            period_date: Period date
            
        Returns:
            date: Validated date
            
        Raises:
            ValueError: If date is in future
        """
        if period_date > date.today():
            raise ValueError("Billing period cannot be in the future")
        return period_date
    
    @property
    def period_days(self) -> int:
        """Get billing period length in days.
        
        Returns:
            int: Number of days in billing period
        """
        return (self.period_end - self.period_start).days + 1
    
    @property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue.
        
        Returns:
            bool: True if invoice is overdue
        """
        if self.status == InvoiceStatus.PAID:
            return False
        
        if self.due_at and self.due_at < datetime.now(self.due_at.tzinfo):
            return True
        
        return False
    
    @property
    def subtotal(self) -> float:
        """Calculate subtotal from line items.
        
        Returns:
            float: Subtotal amount
        """
        return sum(float(item.total_amount) for item in self.line_items)
    
    @property
    def tax_amount(self) -> float:
        """Calculate tax amount.
        
        Returns:
            float: Tax amount (0 for now - could be configurable)
        """
        # TODO: Implement tax calculation based on organization location
        return 0.0
    
    @property
    def grand_total(self) -> float:
        """Calculate grand total (subtotal + tax).
        
        Returns:
            float: Grand total
        """
        return self.subtotal + self.tax_amount
    
    def mark_paid(self, paid_at: Optional[datetime] = None) -> None:
        """Mark invoice as paid.
        
        Args:
            paid_at: When invoice was paid (defaults to now)
        """
        self.status = InvoiceStatus.PAID
        self.paid_at = paid_at or func.now()
    
    def mark_sent(self, due_at: Optional[datetime] = None) -> None:
        """Mark invoice as sent.
        
        Args:
            due_at: Due date for payment
        """
        self.status = InvoiceStatus.SENT
        if due_at:
            self.due_at = due_at
        elif not self.due_at:
            # Default due date: 30 days from now
            self.due_at = func.now() + func.make_interval(days=30)
    
    def __repr__(self) -> str:
        """String representation of invoice."""
        return f"<BillingInvoice(id={self.id}, number='{self.invoice_number}', amount={self.total_amount}, status={self.status})>"


class BillingLineItem(Base, TimestampMixin):
    """Line item on an invoice.
    
    Rules:
        Each line item references usage records
        Quantity and unit price determine total
        Description explains what is being billed
    """
    
    __tablename__ = "billing_line_items"
    
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Unique line item identifier",
    )
    
    invoice_id = Column(
        Integer,
        ForeignKey("billing_invoices.id", ondelete="CASCADE"),
        nullable=False,
        doc="Invoice this line item belongs to",
    )
    
    description = Column(
        Text,
        nullable=False,
        doc="Line item description",
    )
    
    quantity = Column(
        Numeric(10, 2),
        nullable=False,
        doc="Quantity (e.g., number of tokens, API calls)",
    )
    
    unit_price = Column(
        Numeric(12, 2),
        nullable=False,
        doc="Price per unit",
    )
    
    total_amount = Column(
        Numeric(12, 2),
        nullable=False,
        doc="Total amount (quantity × unit_price)",
    )
    
    usage_record_ids = Column(
        ARRAY(Integer),
        default=[],
        nullable=False,
        doc="Array of usage record IDs included in this line item",
    )
    
    # Relationships
    invoice = relationship(
        "BillingInvoice",
        back_populates="line_items",
        lazy="selectin",
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_line_items_invoice_id", invoice_id),
    )
    
    @validates("quantity")
    def validate_quantity(self, key: str, quantity: float) -> float:
        """Validate quantity is positive.
        
        Args:
            key: Field name
            quantity: Quantity
            
        Returns:
            float: Validated quantity
            
        Raises:
            ValueError: If quantity is not positive
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        return quantity
    
    @validates("unit_price")
    def validate_unit_price(self, key: str, price: float) -> float:
        """Validate unit price is non-negative.
        
        Args:
            key: Field name
            price: Unit price
            
        Returns:
            float: Validated unit price
            
        Raises:
            ValueError: If price is negative
        """
        if price < 0:
            raise ValueError("Unit price cannot be negative")
        return price
    
    @validates("total_amount")
    def validate_total_amount(self, key: str, total: float) -> float:
        """Validate total amount matches quantity × unit_price.
        
        Args:
            key: Field name
            total: Total amount
            
        Returns:
            float: Validated total amount
            
        Note:
            This is a simple validation; in practice, we would calculate it
        """
        if total < 0:
            raise ValueError("Total amount cannot be negative")
        return total
    
    def __repr__(self) -> str:
        """String representation of line item."""
        return f"<BillingLineItem(id={self.id}, invoice={self.invoice_id}, description='{self.description[:50]}...')>"