"""credits.py — Credit engine for managing user balances.

exports: CreditEngine, deduct_credits, refund_credits, get_balance, enforce_cap
used_by: billing.py router, agents/runner.py, scheduler/runner.py
rules:   all operations must be atomic; use SELECT FOR UPDATE for consistency
agent:   DataEngineer | 2024-01-15 | created atomic credit operations with transaction support
         message: "implement credit expiration and renewal policies"
"""

import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, update, func, and_
from sqlalchemy.exc import IntegrityError

from agenthub.db.models import CreditAccount, Invoice, AuditLog
from agenthub.billing.plans import PLANS, get_user_plan

logger = logging.getLogger(__name__)


class CreditEngine:
    """Engine for managing credit operations with atomic transactions."""
    
    @staticmethod
    def deduct_credits(
        db: Session,
        user_id: int,
        amount: float,
        description: str,
        reference_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, float, Optional[str]]:
        """Deduct credits from user's account.
        
        Args:
            db: Database session
            user_id: User ID
            amount: Amount to deduct (must be positive)
            description: Transaction description
            reference_id: Optional reference ID (e.g., agent_run_id)
            metadata: Optional transaction metadata
            
        Returns:
            Tuple of (success, new_balance, error_message)
            
        Rules:
            - Must be atomic with SELECT FOR UPDATE
            - Must check for sufficient balance
            - Must create audit log
        """
        if amount <= 0:
            return False, 0.0, "Amount must be positive"
        
        try:
            # Start transaction
            with db.begin():
                # Lock the credit account for update
                credit_account = db.execute(
                    select(CreditAccount)
                    .where(CreditAccount.user_id == user_id)
                    .with_for_update()
                ).scalar_one_or_none()
                
                if not credit_account:
                    return False, 0.0, "Credit account not found"
                
                # Check if user has sufficient balance
                if credit_account.balance < amount:
                    return False, credit_account.balance, "Insufficient credits"
                
                # Deduct credits
                old_balance = credit_account.balance
                credit_account.balance -= amount
                credit_account.updated_at = datetime.utcnow()
                
                # Create audit log
                audit_log = AuditLog(
                    user_id=user_id,
                    action="credit_deduction",
                    resource_type="credit_account",
                    resource_id=str(credit_account.id),
                    details={
                        "old_balance": old_balance,
                        "amount": amount,
                        "new_balance": credit_account.balance,
                        "description": description,
                        "reference_id": reference_id,
                        "metadata": metadata or {}
                    }
                )
                db.add(audit_log)
                
                logger.info(
                    f"Deducted {amount} credits from user {user_id}. "
                    f"Old balance: {old_balance}, New balance: {credit_account.balance}"
                )
                
                return True, credit_account.balance, None
                
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Integrity error deducting credits: {e}")
            return False, 0.0, "Database integrity error"
        except Exception as e:
            db.rollback()
            logger.error(f"Error deducting credits: {e}")
            return False, 0.0, str(e)
    
    @staticmethod
    def refund_credits(
        db: Session,
        user_id: int,
        amount: float,
        description: str,
        reference_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, float, Optional[str]]:
        """Refund credits to user's account.
        
        Args:
            db: Database session
            user_id: User ID
            amount: Amount to refund (must be positive)
            description: Transaction description
            reference_id: Optional reference ID
            metadata: Optional transaction metadata
            
        Returns:
            Tuple of (success, new_balance, error_message)
        """
        if amount <= 0:
            return False, 0.0, "Amount must be positive"
        
        try:
            with db.begin():
                # Lock the credit account for update
                credit_account = db.execute(
                    select(CreditAccount)
                    .where(CreditAccount.user_id == user_id)
                    .with_for_update()
                ).scalar_one_or_none()
                
                if not credit_account:
                    return False, 0.0, "Credit account not found"
                
                # Add credits
                old_balance = credit_account.balance
                credit_account.balance += amount
                credit_account.updated_at = datetime.utcnow()
                
                # Create audit log
                audit_log = AuditLog(
                    user_id=user_id,
                    action="credit_refund",
                    resource_type="credit_account",
                    resource_id=str(credit_account.id),
                    details={
                        "old_balance": old_balance,
                        "amount": amount,
                        "new_balance": credit_account.balance,
                        "description": description,
                        "reference_id": reference_id,
                        "metadata": metadata or {}
                    }
                )
                db.add(audit_log)
                
                logger.info(
                    f"Refunded {amount} credits to user {user_id}. "
                    f"Old balance: {old_balance}, New balance: {credit_account.balance}"
                )
                
                return True, credit_account.balance, None
                
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Integrity error refunding credits: {e}")
            return False, 0.0, "Database integrity error"
        except Exception as e:
            db.rollback()
            logger.error(f"Error refunding credits: {e}")
            return False, 0.0, str(e)
    
    @staticmethod
    def get_balance(db: Session, user_id: int) -> Tuple[float, str]:
        """Get user's current credit balance.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Tuple of (balance, currency)
        """
        credit_account = db.query(CreditAccount).filter(
            CreditAccount.user_id == user_id
        ).first()
        
        if not credit_account:
            # Create credit account if it doesn't exist
            credit_account = CreditAccount(
                user_id=user_id,
                balance=0.0,
                currency="USD"
            )
            db.add(credit_account)
            db.commit()
            db.refresh(credit_account)
        
        return credit_account.balance, credit_account.currency
    
    @staticmethod
    def enforce_cap(db: Session, user_id: int) -> bool:
        """Enforce credit cap based on user's plan.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            True if user is within credit cap, False otherwise
        """
        credit_account = db.query(CreditAccount).filter(
            CreditAccount.user_id == user_id
        ).first()
        
        if not credit_account:
            return True  # No account yet, so no cap to enforce
        
        # Get user's plan (simplified - in production, you'd have a plan table)
        plan = get_user_plan(db, user_id)
        credit_cap = PLANS[plan]["credit_cap"]
        
        if credit_cap is None:  # Unlimited
            return True
        
        return credit_account.balance <= credit_cap
    
    @staticmethod
    def get_transaction_history(
        db: Session,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> list:
        """Get user's credit transaction history.
        
        Args:
            db: Database session
            user_id: User ID
            limit: Maximum number of transactions
            offset: Pagination offset
            start_date: Filter transactions after this date
            end_date: Filter transactions before this date
            
        Returns:
            List of transaction dictionaries
        """
        # Get credit account
        credit_account = db.query(CreditAccount).filter(
            CreditAccount.user_id == user_id
        ).first()
        
        if not credit_account:
            return []
        
        # Get audit logs for credit transactions
        query = db.query(AuditLog).filter(
            AuditLog.user_id == user_id,
            AuditLog.action.in_(["credit_deduction", "credit_refund", "credit_purchase"])
        )
        
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)
        
        audit_logs = query.order_by(AuditLog.created_at.desc())\
                         .offset(offset)\
                         .limit(limit)\
                         .all()
        
        transactions = []
        for log in audit_logs:
            details = log.details or {}
            transaction_type = "deduction" if log.action == "credit_deduction" else "refund"
            if log.action == "credit_purchase":
                transaction_type = "purchase"
            
            transactions.append({
                "id": log.id,
                "type": transaction_type,
                "amount": details.get("amount", 0),
                "balance_before": details.get("old_balance", 0),
                "balance_after": details.get("new_balance", 0),
                "description": details.get("description", ""),
                "reference_id": details.get("reference_id"),
                "metadata": details.get("metadata", {}),
                "created_at": log.created_at
            })
        
        return transactions
    
    @staticmethod
    def check_credit_expiration(db: Session, user_id: int) -> None:
        """Check and expire old credits based on plan.
        
        Args:
            db: Database session
            user_id: User ID
            
        Note: This should be run as a periodic background job
        """
        # This is a simplified implementation
        # In production, you would track credit expiration dates
        # and expire credits that are older than the plan's validity period
        
        plan = get_user_plan(db, user_id)
        plan_config = PLANS[plan]
        
        if plan_config.get("credit_expiry_days"):
            # Logic to expire old credits would go here
            # For now, this is a placeholder
            pass


# Convenience functions
def deduct_credits(
    db: Session,
    user_id: int,
    amount: float,
    description: str,
    reference_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Tuple[bool, float, Optional[str]]:
    """Convenience function for deducting credits."""
    return CreditEngine.deduct_credits(
        db, user_id, amount, description, reference_id, metadata
    )


def refund_credits(
    db: Session,
    user_id: int,
    amount: float,
    description: str,
    reference_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Tuple[bool, float, Optional[str]]:
    """Convenience function for refunding credits."""
    return CreditEngine.refund_credits(
        db, user_id, amount, description, reference_id, metadata
    )


def get_balance(db: Session, user_id: int) -> Tuple[float, str]:
    """Convenience function for getting balance."""
    return CreditEngine.get_balance(db, user_id)


def enforce_cap(db: Session, user_id: int) -> bool:
    """Convenience function for enforcing credit cap."""
    return CreditEngine.enforce_cap(db, user_id)