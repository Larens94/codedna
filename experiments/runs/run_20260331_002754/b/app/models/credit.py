"""Credit system models for tracking user credits."""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Enum, Text, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from decimal import Decimal
import enum

from app import db


class CreditTransactionType(enum.Enum):
    """Credit transaction type enumeration."""
    
    # Add credits
    PURCHASE = 'purchase'  # Purchased via Stripe
    REFUND = 'refund'  # Refund from Stripe
    MANUAL_ADD = 'manual_add'  # Manual addition by admin
    BONUS = 'bonus'  # Bonus credits
    
    # Deduct credits
    AGENT_RUN = 'agent_run'  # Agent execution
    API_CALL = 'api_call'  # API usage
    MEMORY_STORAGE = 'memory_storage'  # Memory storage
    SUBSCRIPTION = 'subscription'  # Subscription payment
    
    # System adjustments
    ADJUSTMENT = 'adjustment'  # Manual adjustment
    EXPIRATION = 'expiration'  # Credit expiration
    TRANSFER = 'transfer'  # Transfer between accounts


class CreditAccount(db.Model):
    """Credit account model for tracking user credits.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to user
        organization_id: Foreign key to organization (for org credits)
        balance: Current credit balance (1 credit = $0.01)
        credit_limit: Maximum credit limit (for billing accounts)
        expires_at: When credits expire (for promotional credits)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        user: Associated user
        organization: Associated organization
        transactions: Credit transactions
    """
    
    __tablename__ = 'credit_accounts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'))
    balance = Column(Numeric(12, 2), default=Decimal('0.00'), nullable=False)  # Credits (1 credit = $0.01)
    credit_limit = Column(Numeric(12, 2), default=Decimal('0.00'))  # Maximum allowed negative balance
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('balance >= -credit_limit', name='check_credit_limit'),
        db.UniqueConstraint('user_id', 'organization_id', name='uq_user_org_credit_account'),
    )
    
    # Indexes
    __table_args__ += (
        db.Index('ix_credit_accounts_user_id', 'user_id'),
        db.Index('ix_credit_accounts_organization_id', 'organization_id'),
        db.Index('ix_credit_accounts_expires_at', 'expires_at'),
    )
    
    # Relationships
    user = relationship('User')
    organization = relationship('Organization')
    transactions = relationship('CreditTransaction', back_populates='credit_account', cascade='all, delete-orphan')
    
    def available_balance(self) -> Decimal:
        """Get available balance (balance + credit limit).
        
        Returns:
            Available credits
        """
        return self.balance + self.credit_limit
    
    def has_sufficient_credits(self, amount: Decimal) -> bool:
        """Check if account has sufficient credits for amount.
        
        Args:
            amount: Amount to check (positive for deduction)
            
        Returns:
            True if sufficient credits, False otherwise
        """
        return self.balance + self.credit_limit >= amount
    
    def deduct(self, amount: Decimal, transaction_type: CreditTransactionType, 
               reference_id: Optional[int] = None, description: Optional[str] = None) -> bool:
        """Deduct credits from account.
        
        Args:
            amount: Amount to deduct (positive)
            transaction_type: Type of transaction
            reference_id: ID of related entity (agent_run_id, invoice_id, etc.)
            description: Transaction description
            
        Returns:
            True if successful, False if insufficient credits
        """
        if not self.has_sufficient_credits(amount):
            return False
        
        self.balance -= amount
        self.updated_at = datetime.utcnow()
        
        # Create transaction record
        transaction = CreditTransaction(
            credit_account_id=self.id,
            amount=-amount,  # Negative for deduction
            transaction_type=transaction_type,
            reference_id=reference_id,
            description=description or f"{transaction_type.value}: {amount} credits deducted",
            balance_after=self.balance,
        )
        db.session.add(transaction)
        
        return True
    
    def add(self, amount: Decimal, transaction_type: CreditTransactionType,
            reference_id: Optional[int] = None, description: Optional[str] = None) -> None:
        """Add credits to account.
        
        Args:
            amount: Amount to add (positive)
            transaction_type: Type of transaction
            reference_id: ID of related entity
            description: Transaction description
        """
        self.balance += amount
        self.updated_at = datetime.utcnow()
        
        # Create transaction record
        transaction = CreditTransaction(
            credit_account_id=self.id,
            amount=amount,  # Positive for addition
            transaction_type=transaction_type,
            reference_id=reference_id,
            description=description or f"{transaction_type.value}: {amount} credits added",
            balance_after=self.balance,
        )
        db.session.add(transaction)
    
    def expire_credits(self) -> Decimal:
        """Expire credits that have passed their expiration date.
        
        Returns:
            Amount of credits expired
        """
        if not self.expires_at or self.expires_at > datetime.utcnow():
            return Decimal('0.00')
        
        # Find expiring transactions
        expiring_transactions = CreditTransaction.query.filter(
            CreditTransaction.credit_account_id == self.id,
            CreditTransaction.amount > 0,
            CreditTransaction.expires_at <= datetime.utcnow(),
            CreditTransaction.expired == False,
        ).all()
        
        expired_total = Decimal('0.00')
        for transaction in expiring_transactions:
            expired_total += transaction.amount
            transaction.expired = True
        
        if expired_total > 0:
            self.balance -= expired_total
            self.updated_at = datetime.utcnow()
            
            # Create expiration transaction
            expiration = CreditTransaction(
                credit_account_id=self.id,
                amount=-expired_total,
                transaction_type=CreditTransactionType.EXPIRATION,
                description=f"Credit expiration: {expired_total} credits expired",
                balance_after=self.balance,
            )
            db.session.add(expiration)
        
        return expired_total
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert credit account to dictionary representation.
        
        Returns:
            Dictionary representation of credit account
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'organization_id': self.organization_id,
            'balance': float(self.balance) if self.balance else 0.0,
            'credit_limit': float(self.credit_limit) if self.credit_limit else 0.0,
            'available_balance': float(self.available_balance()),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'transaction_count': len(self.transactions),
        }
    
    def __repr__(self) -> str:
        return f'<CreditAccount User {self.user_id} (Balance: {self.balance} credits)>'


class CreditTransaction(db.Model):
    """Credit transaction model for tracking all credit changes.
    
    Attributes:
        id: Primary key
        credit_account_id: Foreign key to credit account
        amount: Transaction amount (positive for add, negative for deduct)
        transaction_type: Type of transaction
        reference_id: ID of related entity (agent_run_id, invoice_id, etc.)
        reference_type: Type of reference (agent_run, invoice, etc.)
        description: Transaction description
        balance_after: Balance after this transaction
        expires_at: When these credits expire (for added credits)
        expired: Whether credits have expired
        stripe_payment_intent_id: Stripe payment intent ID (for purchases)
        metadata: Additional metadata (JSON)
        created_at: Creation timestamp
        credit_account: Associated credit account
    """
    
    __tablename__ = 'credit_transactions'
    
    id = Column(Integer, primary_key=True)
    credit_account_id = Column(Integer, ForeignKey('credit_accounts.id', ondelete='CASCADE'), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    transaction_type = Column(Enum(CreditTransactionType), nullable=False)
    reference_id = Column(Integer)
    reference_type = Column(String(50))
    description = Column(Text)
    balance_after = Column(Numeric(12, 2), nullable=False)
    expires_at = Column(DateTime)
    expired = Column(Boolean, default=False)
    stripe_payment_intent_id = Column(String(100))
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes for efficient querying
    __table_args__ = (
        db.Index('ix_credit_transactions_credit_account_id', 'credit_account_id'),
        db.Index('ix_credit_transactions_transaction_type', 'transaction_type'),
        db.Index('ix_credit_transactions_reference', 'reference_type', 'reference_id'),
        db.Index('ix_credit_transactions_created_at', 'created_at'),
        db.Index('ix_credit_transactions_stripe_payment_intent_id', 'stripe_payment_intent_id', unique=True),
    )
    
    # Relationships
    credit_account = relationship('CreditAccount', back_populates='transactions')
    
    def get_metadata_dict(self) -> Dict[str, Any]:
        """Get metadata as dictionary.
        
        Returns:
            Metadata dictionary
        """
        return self.metadata or {}
    
    def is_expired(self) -> bool:
        """Check if transaction credits have expired.
        
        Returns:
            True if expired, False otherwise
        """
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary representation.
        
        Returns:
            Dictionary representation of transaction
        """
        return {
            'id': self.id,
            'credit_account_id': self.credit_account_id,
            'amount': float(self.amount) if self.amount else 0.0,
            'transaction_type': self.transaction_type.value if self.transaction_type else None,
            'reference_id': self.reference_id,
            'reference_type': self.reference_type,
            'description': self.description,
            'balance_after': float(self.balance_after) if self.balance_after else 0.0,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'expired': self.expired,
            'is_expired': self.is_expired(),
            'stripe_payment_intent_id': self.stripe_payment_intent_id,
            'metadata': self.get_metadata_dict(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f'<CreditTransaction {self.id}: {self.amount} ({self.transaction_type.value})>'


class CreditPlan(db.Model):
    """Credit plan model for pre-defined credit packages.
    
    Attributes:
        id: Primary key
        name: Plan name
        description: Plan description
        credits: Number of credits included
        price_usd: Price in USD
        stripe_price_id: Stripe price ID
        is_active: Whether plan is available for purchase
        expires_in_days: When credits expire after purchase (None for no expiration)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    
    __tablename__ = 'credit_plans'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    credits = Column(Numeric(12, 2), nullable=False)
    price_usd = Column(Numeric(10, 2), nullable=False)
    stripe_price_id = Column(String(100), unique=True)
    is_active = Column(Boolean, default=True)
    expires_in_days = Column(Integer)  # Credits expire after X days
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def calculate_expiration_date(self) -> Optional[datetime]:
        """Calculate expiration date for credits purchased now.
        
        Returns:
            Expiration datetime or None if no expiration
        """
        if not self.expires_in_days:
            return None
        
        from datetime import timedelta
        return datetime.utcnow() + timedelta(days=self.expires_in_days)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert credit plan to dictionary representation.
        
        Returns:
            Dictionary representation of credit plan
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'credits': float(self.credits) if self.credits else 0.0,
            'price_usd': float(self.price_usd) if self.price_usd else 0.0,
            'stripe_price_id': self.stripe_price_id,
            'is_active': self.is_active,
            'expires_in_days': self.expires_in_days,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f'<CreditPlan {self.name}: {self.credits} credits for ${self.price_usd}>'