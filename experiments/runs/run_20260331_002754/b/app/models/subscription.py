"""Subscription and billing models for AgentHub."""

from datetime import datetime, timedelta
from typing import Optional
from decimal import Decimal
import enum

from sqlalchemy import Column, Integer, String, Text, Enum, DateTime, ForeignKey, Numeric, Boolean, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app import db


class PlanType(enum.Enum):
    """Subscription plan type enumeration."""
    
    FREE = 'free'
    BASIC = 'basic'
    PRO = 'pro'
    TEAM = 'team'
    ENTERPRISE = 'enterprise'


class Plan(db.Model):
    """Subscription plan model.
    
    Attributes:
        id: Primary key
        name: Plan name
        type: Plan type
        description: Plan description
        price_monthly_usd: Monthly price in USD
        price_yearly_usd: Yearly price in USD
        max_agents: Maximum number of agents allowed
        max_runs_per_day: Maximum runs per day
        max_team_members: Maximum team members
        features: List of features (JSON)
        is_active: Whether plan is available
        created_at: Creation timestamp
        updated_at: Last update timestamp
        subscriptions: Subscriptions using this plan
    """
    
    __tablename__ = 'plans'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    type = Column(Enum(PlanType), nullable=False, unique=True)
    description = Column(Text)
    price_monthly_usd = Column(Numeric(10, 2), default=Decimal('0.00'), nullable=False)
    price_yearly_usd = Column(Numeric(10, 2), default=Decimal('0.00'), nullable=False)
    max_agents = Column(Integer, default=1)
    max_runs_per_day = Column(Integer, default=10)
    max_team_members = Column(Integer, default=1)
    features = Column(Text)  # JSON array of features
    is_active = Column(Boolean, default=True)
    stripe_price_id_monthly = Column(String(100))
    stripe_price_id_yearly = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscriptions = relationship('Subscription', back_populates='plan', cascade='all, delete-orphan')
    
    def get_features(self) -> list:
        """Parse features as JSON list.
        
        Returns:
            List of features
        """
        import json
        if self.features:
            return json.loads(self.features)
        return []
    
    def to_dict(self) -> dict:
        """Convert plan to dictionary representation.
        
        Returns:
            Dictionary representation of plan
        """
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type.value if self.type else None,
            'description': self.description,
            'price_monthly_usd': float(self.price_monthly_usd) if self.price_monthly_usd else 0.0,
            'price_yearly_usd': float(self.price_yearly_usd) if self.price_yearly_usd else 0.0,
            'max_agents': self.max_agents,
            'max_runs_per_day': self.max_runs_per_day,
            'max_team_members': self.max_team_members,
            'features': self.get_features(),
            'is_active': self.is_active,
            'stripe_price_id_monthly': self.stripe_price_id_monthly,
            'stripe_price_id_yearly': self.stripe_price_id_yearly,
        }
    
    def __repr__(self) -> str:
        return f'<Plan {self.name} ({self.type.value})>'


class SubscriptionStatus(enum.Enum):
    """Subscription status enumeration."""
    
    ACTIVE = 'active'
    TRIALING = 'trialing'
    PAST_DUE = 'past_due'
    CANCELLED = 'cancelled'
    UNPAID = 'unpaid'
    INCOMPLETE = 'incomplete'
    INCOMPLETE_EXPIRED = 'incomplete_expired'


class BillingCycle(enum.Enum):
    """Billing cycle enumeration."""
    
    MONTHLY = 'monthly'
    YEARLY = 'yearly'


class Subscription(db.Model):
    """User subscription model.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to user
        plan_id: Foreign key to plan
        status: Subscription status
        billing_cycle: Billing cycle (monthly/yearly)
        current_period_start: Current billing period start
        current_period_end: Current billing period end
        cancel_at_period_end: Whether to cancel at period end
        trial_start: Trial period start
        trial_end: Trial period end
        stripe_subscription_id: Stripe subscription ID
        stripe_customer_id: Stripe customer ID
        created_at: Creation timestamp
        updated_at: Last update timestamp
        cancelled_at: When subscription was cancelled
        user: Subscribed user
        plan: Subscription plan
        invoices: Subscription invoices
    """
    
    __tablename__ = 'subscriptions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    plan_id = Column(Integer, ForeignKey('plans.id'), nullable=False)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.INCOMPLETE, nullable=False)
    billing_cycle = Column(Enum(BillingCycle), default=BillingCycle.MONTHLY, nullable=False)
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    cancel_at_period_end = Column(Boolean, default=False)
    trial_start = Column(DateTime)
    trial_end = Column(DateTime)
    stripe_subscription_id = Column(String(100), unique=True)
    stripe_customer_id = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    cancelled_at = Column(DateTime)
    
    # Relationships
    user = relationship('User', back_populates='subscriptions')
    plan = relationship('Plan', back_populates='subscriptions')
    invoices = relationship('Invoice', back_populates='subscription', cascade='all, delete-orphan')
    
    def is_active(self) -> bool:
        """Check if subscription is currently active.
        
        Returns:
            True if subscription is active, False otherwise
        """
        active_statuses = [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]
        return self.status in active_statuses
    
    def is_trialing(self) -> bool:
        """Check if subscription is in trial period.
        
        Returns:
            True if in trial period, False otherwise
        """
        if not self.trial_end:
            return False
        
        now = datetime.utcnow()
        return self.status == SubscriptionStatus.TRIALING and now < self.trial_end
    
    def days_remaining(self) -> Optional[int]:
        """Get days remaining in current period.
        
        Returns:
            Number of days remaining or None if no end date
        """
        if not self.current_period_end:
            return None
        
        now = datetime.utcnow()
        if now > self.current_period_end:
            return 0
        
        delta = self.current_period_end - now
        return delta.days
    
    def to_dict(self, include_details: bool = False) -> dict:
        """Convert subscription to dictionary representation.
        
        Args:
            include_details: Whether to include detailed information
            
        Returns:
            Dictionary representation of subscription
        """
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'plan_id': self.plan_id,
            'status': self.status.value if self.status else None,
            'billing_cycle': self.billing_cycle.value if self.billing_cycle else None,
            'current_period_start': self.current_period_start.isoformat() if self.current_period_start else None,
            'current_period_end': self.current_period_end.isoformat() if self.current_period_end else None,
            'cancel_at_period_end': self.cancel_at_period_end,
            'trial_start': self.trial_start.isoformat() if self.trial_start else None,
            'trial_end': self.trial_end.isoformat() if self.trial_end else None,
            'stripe_subscription_id': self.stripe_subscription_id,
            'stripe_customer_id': self.stripe_customer_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'is_active': self.is_active(),
            'is_trialing': self.is_trialing(),
            'days_remaining': self.days_remaining(),
            'plan': self.plan.to_dict() if self.plan else None,
        }
        
        if include_details:
            data.update({
                'invoices': [invoice.to_dict() for invoice in self.invoices[:10]],  # Limit to 10 recent
            })
        
        return data
    
    def __repr__(self) -> str:
        return f'<Subscription {self.id} ({self.status.value})>'


class BillingAccount(db.Model):
    """Billing account model for user billing information.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to user
        balance_usd: Current balance in USD
        credit_limit_usd: Credit limit in USD
        currency: Currency code (default: USD)
        billing_email: Email for billing notifications
        company_name: Company name for invoices
        tax_id: Tax ID/VAT number
        address_line1: Billing address line 1
        address_line2: Billing address line 2
        city: City
        state: State/Province
        postal_code: Postal code
        country: Country code
        created_at: Creation timestamp
        updated_at: Last update timestamp
        user: Associated user
        invoices: Account invoices
    """
    
    __tablename__ = 'billing_accounts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    balance_usd = Column(Numeric(10, 2), default=Decimal('0.00'), nullable=False)
    credit_limit_usd = Column(Numeric(10, 2), default=Decimal('0.00'))
    currency = Column(String(3), default='USD')
    billing_email = Column(String(255))
    company_name = Column(String(200))
    tax_id = Column(String(100))
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    postal_code = Column(String(20))
    country = Column(String(2))  # ISO 3166-1 alpha-2
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship('User', back_populates='billing_account')
    invoices = relationship('Invoice', back_populates='billing_account', cascade='all, delete-orphan')
    
    def has_credit(self, amount: Decimal) -> bool:
        """Check if account has sufficient credit for amount.
        
        Args:
            amount: Amount to check
            
        Returns:
            True if sufficient credit, False otherwise
        """
        available_credit = self.credit_limit_usd - self.balance_usd
        return amount <= available_credit
    
    def charge(self, amount: Decimal) -> bool:
        """Charge amount to account balance.
        
        Args:
            amount: Amount to charge
            
        Returns:
            True if successful, False if insufficient credit
        """
        if not self.has_credit(amount):
            return False
        
        self.balance_usd += amount
        return True
    
    def credit(self, amount: Decimal) -> None:
        """Credit amount to account balance.
        
        Args:
            amount: Amount to credit
        """
        self.balance_usd -= amount
        if self.balance_usd < 0:
            self.balance_usd = Decimal('0.00')
    
    def to_dict(self) -> dict:
        """Convert billing account to dictionary representation.
        
        Returns:
            Dictionary representation of billing account
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'balance_usd': float(self.balance_usd) if self.balance_usd else 0.0,
            'credit_limit_usd': float(self.credit_limit_usd) if self.credit_limit_usd else 0.0,
            'currency': self.currency,
            'billing_email': self.billing_email,
            'company_name': self.company_name,
            'tax_id': self.tax_id,
            'address_line1': self.address_line1,
            'address_line2': self.address_line2,
            'city': self.city,
            'state': self.state,
            'postal_code': self.postal_code,
            'country': self.country,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f'<BillingAccount User {self.user_id} (Balance: ${self.balance_usd})>'


class InvoiceStatus(enum.Enum):
    """Invoice status enumeration."""
    
    DRAFT = 'draft'
    OPEN = 'open'
    PAID = 'paid'
    VOID = 'void'
    UNCOLLECTIBLE = 'uncollectible'


class Invoice(db.Model):
    """Invoice model for billing.
    
    Attributes:
        id: Primary key
        billing_account_id: Foreign key to billing account
        subscription_id: Foreign key to subscription
        invoice_number: Unique invoice number
        status: Invoice status
        amount_usd: Invoice amount in USD
        tax_usd: Tax amount in USD
        total_usd: Total amount in USD
        currency: Currency code
        invoice_date: Invoice date
        due_date: Due date
        paid_date: When invoice was paid
        stripe_invoice_id: Stripe invoice ID
        stripe_payment_intent_id: Stripe payment intent ID
        description: Invoice description
        metadata: Additional metadata (JSON)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        billing_account: Associated billing account
        subscription: Associated subscription
    """
    
    __tablename__ = 'invoices'
    
    id = Column(Integer, primary_key=True)
    billing_account_id = Column(Integer, ForeignKey('billing_accounts.id', ondelete='CASCADE'), nullable=False)
    subscription_id = Column(Integer, ForeignKey('subscriptions.id', ondelete='SET NULL'))
    invoice_number = Column(String(50), unique=True, nullable=False)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False)
    amount_usd = Column(Numeric(10, 2), default=Decimal('0.00'), nullable=False)
    tax_usd = Column(Numeric(10, 2), default=Decimal('0.00'))
    total_usd = Column(Numeric(10, 2), default=Decimal('0.00'), nullable=False)
    currency = Column(String(3), default='USD')
    invoice_date = Column(Date, default=datetime.utcnow)
    due_date = Column(Date)
    paid_date = Column(DateTime)
    stripe_invoice_id = Column(String(100), unique=True)
    stripe_payment_intent_id = Column(String(100))
    description = Column(Text)
    metadata = Column(Text)  # JSON metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    billing_account = relationship('BillingAccount', back_populates='invoices')
    subscription = relationship('Subscription', back_populates='invoices')
    
    def mark_paid(self, paid_date: Optional[datetime] = None) -> None:
        """Mark invoice as paid.
        
        Args:
            paid_date: When invoice was paid (defaults to now)
        """
        self.status = InvoiceStatus.PAID
        self.paid_date = paid_date or datetime.utcnow()
    
    def mark_void(self) -> None:
        """Mark invoice as void."""
        self.status = InvoiceStatus.VOID
    
    def get_metadata(self) -> dict:
        """Parse metadata as JSON.
        
        Returns:
            Parsed metadata dictionary
        """
        import json
        if self.metadata:
            return json.loads(self.metadata)
        return {}
    
    def to_dict(self) -> dict:
        """Convert invoice to dictionary representation.
        
        Returns:
            Dictionary representation of invoice
        """
        return {
            'id': self.id,
            'billing_account_id': self.billing_account_id,
            'subscription_id': self.subscription_id,
            'invoice_number': self.invoice_number,
            'status': self.status.value if self.status else None,
            'amount_usd': float(self.amount_usd) if self.amount_usd else 0.0,
            'tax_usd': float(self.tax_usd) if self.tax_usd else 0.0,
            'total_usd': float(self.total_usd) if self.total_usd else 0.0,
            'currency': self.currency,
            'invoice_date': self.invoice_date.isoformat() if self.invoice_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'paid_date': self.paid_date.isoformat() if self.paid_date else None,
            'stripe_invoice_id': self.stripe_invoice_id,
            'stripe_payment_intent_id': self.stripe_payment_intent_id,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f'<Invoice {self.invoice_number} (${self.total_usd})>'