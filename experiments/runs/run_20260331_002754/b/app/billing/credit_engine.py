"""Credit engine for managing user credits and enforcing limits."""

import logging
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.credit import (
    CreditAccount, CreditTransaction, CreditTransactionType, CreditPlan
)
from app.models.user import User
from app.models.organization import Organization
from app.models.audit_log import AuditLog, AuditAction, AuditSeverity

logger = logging.getLogger(__name__)


class CreditEngineError(Exception):
    """Base exception for credit engine errors."""
    pass


class InsufficientCreditsError(CreditEngineError):
    """Raised when user has insufficient credits."""
    pass


class CreditLimitExceededError(CreditEngineError):
    """Raised when credit limit would be exceeded."""
    pass


class CreditEngine:
    """Engine for managing user credits and enforcing limits."""
    
    def __init__(self, db_session: Session):
        """Initialize credit engine.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
    
    def get_account(self, user_id: int, organization_id: Optional[int] = None) -> CreditAccount:
        """Get or create credit account for user/organization.
        
        Args:
            user_id: User ID
            organization_id: Optional organization ID
            
        Returns:
            CreditAccount instance
        """
        account = self.db.query(CreditAccount).filter_by(
            user_id=user_id,
            organization_id=organization_id,
        ).first()
        
        if not account:
            account = CreditAccount(
                user_id=user_id,
                organization_id=organization_id,
                balance=Decimal('0.00'),
                credit_limit=Decimal('0.00'),
            )
            self.db.add(account)
            self.db.commit()
            logger.info(f"Created credit account for user {user_id}, org {organization_id}")
        
        return account
    
    def get_balance(self, user_id: int, organization_id: Optional[int] = None) -> Decimal:
        """Get current credit balance.
        
        Args:
            user_id: User ID
            organization_id: Optional organization ID
            
        Returns:
            Current balance in credits
        """
        account = self.get_account(user_id, organization_id)
        return account.balance
    
    def get_available_balance(self, user_id: int, organization_id: Optional[int] = None) -> Decimal:
        """Get available credit balance (balance + credit limit).
        
        Args:
            user_id: User ID
            organization_id: Optional organization ID
            
        Returns:
            Available credits
        """
        account = self.get_account(user_id, organization_id)
        return account.available_balance()
    
    def deduct(
        self,
        user_id: int,
        amount: Decimal,
        transaction_type: CreditTransactionType,
        reference_id: Optional[int] = None,
        reference_type: Optional[str] = None,
        description: Optional[str] = None,
        organization_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> CreditTransaction:
        """Deduct credits from user account.
        
        Args:
            user_id: User ID
            amount: Amount to deduct (positive)
            transaction_type: Type of transaction
            reference_id: ID of related entity
            reference_type: Type of reference
            description: Transaction description
            organization_id: Optional organization ID
            ip_address: IP address for audit log
            user_agent: User agent for audit log
            
        Returns:
            CreditTransaction instance
            
        Raises:
            InsufficientCreditsError: If insufficient credits
            CreditLimitExceededError: If credit limit would be exceeded
        """
        if amount <= 0:
            raise ValueError("Deduction amount must be positive")
        
        account = self.get_account(user_id, organization_id)
        
        # Check if user has sufficient credits
        if not account.has_sufficient_credits(amount):
            raise InsufficientCreditsError(
                f"Insufficient credits: {account.balance} available, {amount} required"
            )
        
        # Perform deduction
        success = account.deduct(
            amount=amount,
            transaction_type=transaction_type,
            reference_id=reference_id,
            description=description,
        )
        
        if not success:
            raise CreditEngineError("Failed to deduct credits")
        
        # Get the created transaction
        transaction = self.db.query(CreditTransaction).filter_by(
            credit_account_id=account.id,
            reference_id=reference_id,
            transaction_type=transaction_type,
        ).order_by(CreditTransaction.created_at.desc()).first()
        
        if transaction:
            transaction.reference_type = reference_type
        
        # Create audit log
        AuditLog.log(
            action=AuditAction.CREDIT_DEDUCT,
            description=f"Deducted {amount} credits: {description or transaction_type.value}",
            user_id=user_id,
            organization_id=organization_id,
            resource_type='credit_account',
            resource_id=account.id,
            severity=AuditSeverity.LOW,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                'amount': float(amount),
                'transaction_type': transaction_type.value,
                'reference_id': reference_id,
                'reference_type': reference_type,
                'balance_before': float(account.balance + amount),  # Balance before deduction
                'balance_after': float(account.balance),
            }
        )
        
        self.db.commit()
        logger.info(f"Deducted {amount} credits from user {user_id}, org {organization_id}")
        
        return transaction
    
    def add(
        self,
        user_id: int,
        amount: Decimal,
        transaction_type: CreditTransactionType,
        reference_id: Optional[int] = None,
        reference_type: Optional[str] = None,
        description: Optional[str] = None,
        organization_id: Optional[int] = None,
        expires_in_days: Optional[int] = None,
        stripe_payment_intent_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> CreditTransaction:
        """Add credits to user account.
        
        Args:
            user_id: User ID
            amount: Amount to add (positive)
            transaction_type: Type of transaction
            reference_id: ID of related entity
            reference_type: Type of reference
            description: Transaction description
            organization_id: Optional organization ID
            expires_in_days: Days until credits expire
            stripe_payment_intent_id: Stripe payment intent ID
            ip_address: IP address for audit log
            user_agent: User agent for audit log
            
        Returns:
            CreditTransaction instance
        """
        if amount <= 0:
            raise ValueError("Addition amount must be positive")
        
        account = self.get_account(user_id, organization_id)
        
        # Calculate expiration date
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Perform addition
        account.add(
            amount=amount,
            transaction_type=transaction_type,
            reference_id=reference_id,
            description=description,
        )
        
        # Get the created transaction
        transaction = self.db.query(CreditTransaction).filter_by(
            credit_account_id=account.id,
            reference_id=reference_id,
            transaction_type=transaction_type,
        ).order_by(CreditTransaction.created_at.desc()).first()
        
        if transaction:
            transaction.reference_type = reference_type
            transaction.expires_at = expires_at
            transaction.stripe_payment_intent_id = stripe_payment_intent_id
        
        # Create audit log
        AuditLog.log(
            action=AuditAction.CREDIT_ADD,
            description=f"Added {amount} credits: {description or transaction_type.value}",
            user_id=user_id,
            organization_id=organization_id,
            resource_type='credit_account',
            resource_id=account.id,
            severity=AuditSeverity.LOW,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={
                'amount': float(amount),
                'transaction_type': transaction_type.value,
                'reference_id': reference_id,
                'reference_type': reference_type,
                'expires_in_days': expires_in_days,
                'stripe_payment_intent_id': stripe_payment_intent_id,
                'balance_before': float(account.balance - amount),  # Balance before addition
                'balance_after': float(account.balance),
            }
        )
        
        self.db.commit()
        logger.info(f"Added {amount} credits to user {user_id}, org {organization_id}")
        
        return transaction
    
    def refund(
        self,
        user_id: int,
        amount: Decimal,
        original_transaction_id: Optional[int] = None,
        description: Optional[str] = None,
        organization_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> CreditTransaction:
        """Refund credits to user account.
        
        Args:
            user_id: User ID
            amount: Amount to refund (positive)
            original_transaction_id: ID of original transaction being refunded
            description: Refund description
            organization_id: Optional organization ID
            ip_address: IP address for audit log
            user_agent: User agent for audit log
            
        Returns:
            CreditTransaction instance
        """
        return self.add(
            user_id=user_id,
            amount=amount,
            transaction_type=CreditTransactionType.REFUND,
            reference_id=original_transaction_id,
            reference_type='credit_transaction',
            description=description or f"Refund of {amount} credits",
            organization_id=organization_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    
    def enforce_cap(self, user_id: int, organization_id: Optional[int] = None) -> bool:
        """Enforce credit cap (prevent negative balance beyond limit).
        
        Args:
            user_id: User ID
            organization_id: Optional organization ID
            
        Returns:
            True if cap is enforced, False if over limit
        """
        account = self.get_account(user_id, organization_id)
        
        # Check if balance is below negative credit limit
        if account.balance < -account.credit_limit:
            # Cap at limit
            account.balance = -account.credit_limit
            self.db.commit()
            logger.warning(f"Enforced credit cap for user {user_id}, org {organization_id}")
            return True
        
        return True
    
    def get_transaction_history(
        self,
        user_id: int,
        organization_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[list, int]:
        """Get transaction history for account.
        
        Args:
            user_id: User ID
            organization_id: Optional organization ID
            limit: Maximum number of transactions to return
            offset: Offset for pagination
            
        Returns:
            Tuple of (transactions list, total count)
        """
        account = self.get_account(user_id, organization_id)
        
        query = self.db.query(CreditTransaction).filter_by(
            credit_account_id=account.id,
        ).order_by(CreditTransaction.created_at.desc())
        
        total = query.count()
        transactions = query.offset(offset).limit(limit).all()
        
        return [t.to_dict() for t in transactions], total
    
    def expire_credits(self, user_id: int, organization_id: Optional[int] = None) -> Decimal:
        """Expire credits that have passed their expiration date.
        
        Args:
            user_id: User ID
            organization_id: Optional organization ID
            
        Returns:
            Amount of credits expired
        """
        account = self.get_account(user_id, organization_id)
        expired_amount = account.expire_credits()
        
        if expired_amount > 0:
            self.db.commit()
            logger.info(f"Expired {expired_amount} credits for user {user_id}, org {organization_id}")
        
        return expired_amount
    
    def get_credit_plans(self, active_only: bool = True) -> list:
        """Get available credit plans.
        
        Args:
            active_only: Whether to return only active plans
            
        Returns:
            List of credit plans
        """
        query = self.db.query(CreditPlan)
        if active_only:
            query = query.filter_by(is_active=True)
        
        plans = query.order_by(CreditPlan.price_usd).all()
        return [plan.to_dict() for plan in plans]
    
    def calculate_cost_in_credits(self, cost_usd: Decimal) -> int:
        """Convert USD cost to credits (1 credit = $0.01).
        
        Args:
            cost_usd: Cost in USD
            
        Returns:
            Cost in credits (rounded up)
        """
        # Convert to cents and round up
        cents = cost_usd * 100
        credits = int(cents.to_integral_value(rounding='ROUND_UP'))
        return max(credits, 1)  # Minimum 1 credit