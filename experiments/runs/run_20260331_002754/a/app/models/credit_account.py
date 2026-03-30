"""app/models/credit_account.py — Credit account model for billing.

exports: CreditAccount, CreditTransaction
used_by: billing service → credit management, usage service → credit deduction
rules:   credits must be non-negative; transactions must be atomic; balance calculated from transactions
agent:   DataEngineer | 2024-11-06 | implemented credit accounting model
         message: "ensure credit balance calculation uses materialized view for performance"
"""

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Numeric,
    Boolean,
    Index,
    Enum as SQLEnum,
    CheckConstraint,
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

from app.models.base import Base, TimestampMixin


class TransactionType(str, Enum):
    """Credit transaction types."""
    PURCHASE = "purchase"
    USAGE = "usage"
    REFUND = "refund"
    BONUS = "bonus"
    ADJUSTMENT = "adjustment"
    EXPIRE = "expire"


class CreditAccount(Base, TimestampMixin):
    """Credit account for an organization.
    
    Rules:
        Each organization has exactly one credit account
        Credits are purchased via Stripe or granted as bonuses
        Credits expire after 12 months (FIFO)
        Negative credits not allowed (enforced via constraint)
    """
    
    __tablename__ = "credit_accounts"
    
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Unique credit account identifier",
    )
    
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        doc="Organization this account belongs to",
    )
    
    balance = Column(
        Numeric(12, 4),
        default=0,
        nullable=False,
        doc="Current credit balance (non-negative)",
    )
    
    lifetime_credits_purchased = Column(
        Numeric(12, 4),
        default=0,
        nullable=False,
        doc="Total credits purchased over account lifetime",
    )
    
    lifetime_credits_used = Column(
        Numeric(12, 4),
        default=0,
        nullable=False,
        doc="Total credits used over account lifetime",
    )
    
    last_purchase_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When credits were last purchased",
    )
    
    # Relationships
    organization = relationship(
        "Organization",
        back_populates="credit_account",
        lazy="selectin",
        doc="Organization that owns this credit account",
    )
    
    transactions = relationship(
        "CreditTransaction",
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="CreditTransaction.created_at.desc()",
        doc="Credit transactions for this account",
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint("balance >= 0", name="ck_credit_balance_non_negative"),
        Index("ix_credit_accounts_org_id", organization_id),
    )
    
    @validates("balance")
    def validate_balance(self, key: str, balance: float) -> float:
        """Validate balance is non-negative.
        
        Args:
            key: Field name
            balance: Balance to validate
            
        Returns:
            float: Validated balance
            
        Raises:
            ValueError: If balance is negative
        """
        if balance < 0:
            raise ValueError("Credit balance cannot be negative")
        return balance
    
    @property
    def available_credits(self) -> float:
        """Get available credits (balance minus any holds).
        
        Returns:
            float: Available credits
        """
        # TODO: Implement credit holds for pending transactions
        return float(self.balance)
    
    @property
    def is_low(self) -> bool:
        """Check if credit balance is low.
        
        Returns:
            bool: True if balance is below threshold
        """
        # Low threshold: less than 1000 credits or 10% of lifetime purchased
        threshold = min(1000, float(self.lifetime_credits_purchased) * 0.1)
        return float(self.balance) < threshold
    
    def can_deduct(self, amount: float) -> bool:
        """Check if specified amount can be deducted.
        
        Args:
            amount: Amount to deduct
            
        Returns:
            bool: True if amount can be deducted
        """
        return amount >= 0 and float(self.balance) >= amount
    
    def __repr__(self) -> str:
        """String representation of credit account."""
        return f"<CreditAccount(id={self.id}, org={self.organization_id}, balance={self.balance})>"


class CreditTransaction(Base, TimestampMixin):
    """Individual credit transaction for audit trail.
    
    Rules:
        Each transaction has a unique reference ID
        Credits expire 12 months after purchase (FIFO)
        All transactions are immutable once created
    """
    
    __tablename__ = "credit_transactions"
    
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Unique transaction identifier",
    )
    
    account_id = Column(
        Integer,
        ForeignKey("credit_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Credit account this transaction belongs to",
    )
    
    reference_id = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        doc="Unique reference ID (e.g., stripe_charge_id or usage_id)",
    )
    
    transaction_type = Column(
        SQLEnum(TransactionType),
        nullable=False,
        doc="Type of transaction",
    )
    
    amount = Column(
        Numeric(12, 4),
        nullable=False,
        doc="Amount of credits (positive for additions, negative for deductions)",
    )
    
    description = Column(
        Text,
        nullable=True,
        doc="Transaction description",
    )
    
    metadata = Column(
        # Using String instead of JSON for PostgreSQL JSONB compatibility
        String,
        nullable=True,
        doc="Additional metadata (Stripe charge ID, usage details, etc.)",
    )
    
    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When these credits expire (null for non-expiring credits)",
    )
    
    is_expired = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether credits have expired",
    )
    
    # Relationships
    account = relationship(
        "CreditAccount",
        back_populates="transactions",
        lazy="selectin",
        doc="Credit account for this transaction",
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_credit_transactions_account_type", account_id, transaction_type),
        Index("ix_credit_transactions_expires_at", expires_at),
        Index("ix_credit_transactions_reference_id", reference_id, unique=True),
        Index("ix_credit_transactions_created_at", created_at),
    )
    
    @validates("amount")
    def validate_amount(self, key: str, amount: float) -> float:
        """Validate transaction amount.
        
        Args:
            key: Field name
            amount: Amount to validate
            
        Returns:
            float: Validated amount
            
        Note:
            Amount can be positive (credit addition) or negative (credit deduction)
        """
        if amount == 0:
            raise ValueError("Transaction amount cannot be zero")
        return amount
    
    @property
    def is_credit(self) -> bool:
        """Check if transaction adds credits.
        
        Returns:
            bool: True if amount > 0
        """
        return float(self.amount) > 0
    
    @property
    is_debit = property(lambda self: float(self.amount) < 0)
    
    def mark_expired(self) -> None:
        """Mark transaction as expired."""
        self.is_expired = True
    
    def __repr__(self) -> str:
        """String representation of credit transaction."""
        return f"<CreditTransaction(id={self.id}, account={self.account_id}, type={self.transaction_type}, amount={self.amount})>"