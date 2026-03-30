"""billing.py — Billing and credit management API.

exports: router
used_by: main.py
rules:   must handle currency conversion; must be idempotent for payment processing
agent:   BackendEngineer | 2024-01-15 | implemented billing with Stripe integration
         message: "implement Stripe/PayPal integration with webhook handling"
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Header, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
import stripe
import uuid
from datetime import datetime

from agenthub.db.session import get_db
from agenthub.db.models import User, CreditAccount, Invoice, AuditLog
from agenthub.auth.dependencies import get_current_user
from agenthub.schemas.billing import CreditPurchase, InvoiceResponse, TransactionResponse, StripeWebhook
from agenthub.config import settings

router = APIRouter()

# Initialize Stripe
if settings.STRIPE_SECRET_KEY:
    stripe.api_key = settings.STRIPE_SECRET_KEY


@router.get("/balance")
async def get_credit_balance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's credit balance.
    
    Rules:   must return balance with currency; must include pending transactions
    """
    credit_account = db.query(CreditAccount).filter(
        CreditAccount.user_id == current_user.id
    ).first()
    
    if not credit_account:
        # Create credit account if it doesn't exist
        credit_account = CreditAccount(user_id=current_user.id, balance=0.0, currency="USD")
        db.add(credit_account)
        db.commit()
        db.refresh(credit_account)
    
    # Get pending invoices
    pending_invoices = db.query(Invoice).filter(
        Invoice.credit_account_id == credit_account.id,
        Invoice.status.in_(["draft", "pending"])
    ).all()
    
    pending_amount = sum(invoice.amount for invoice in pending_invoices)
    
    return {
        "balance": credit_account.balance,
        "currency": credit_account.currency,
        "pending_amount": pending_amount,
        "available_balance": credit_account.balance - pending_amount,
        "account_id": credit_account.id
    }


@router.get("/transactions", response_model=List[TransactionResponse])
async def get_transaction_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
    type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """Get credit transaction history.
    
    Rules:   must support pagination; must include agent runs and purchases
    """
    # This is a simplified implementation
    # In production, you would have a separate Transaction model
    # For now, we'll combine invoices and agent runs
    
    transactions = []
    
    # Get credit account
    credit_account = db.query(CreditAccount).filter(
        CreditAccount.user_id == current_user.id
    ).first()
    
    if not credit_account:
        return []
    
    # Get invoices (purchases)
    invoice_query = db.query(Invoice).filter(
        Invoice.credit_account_id == credit_account.id
    )
    
    if type == "purchase":
        invoice_query = invoice_query.filter(Invoice.status == "paid")
    
    if start_date:
        invoice_query = invoice_query.filter(Invoice.created_at >= start_date)
    if end_date:
        invoice_query = invoice_query.filter(Invoice.created_at <= end_date)
    
    invoices = invoice_query.order_by(desc(Invoice.created_at))\
                           .offset(offset)\
                           .limit(limit)\
                           .all()
    
    for invoice in invoices:
        transactions.append({
            "id": invoice.id,
            "type": "purchase",
            "amount": invoice.credits_added,
            "balance_before": 0,  # Would need to calculate from history
            "balance_after": 0,   # Would need to calculate from history
            "description": f"Credit purchase - {invoice.amount} {invoice.currency}",
            "reference_id": str(invoice.public_id),
            "metadata": invoice.metadata,
            "created_at": invoice.created_at
        })
    
    # Note: Agent run transactions would come from a separate table
    # For now, we're only showing purchase transactions
    
    return transactions


@router.post("/purchase", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def purchase_credits(
    purchase_data: CreditPurchase,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Purchase credits using payment gateway.
    
    Rules:   must create invoice before payment; must handle webhook callbacks
    """
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Stripe integration is not configured"
        )
    
    # Get or create credit account
    credit_account = db.query(CreditAccount).filter(
        CreditAccount.user_id == current_user.id
    ).first()
    
    if not credit_account:
        credit_account = CreditAccount(user_id=current_user.id, balance=0.0, currency="USD")
        db.add(credit_account)
        db.commit()
        db.refresh(credit_account)
    
    # Calculate credits to add (using exchange rate)
    credits_to_add = purchase_data.amount * settings.CREDIT_EXCHANGE_RATE
    
    # Create invoice record
    invoice = Invoice(
        public_id=str(uuid.uuid4()),
        credit_account_id=credit_account.id,
        amount=purchase_data.amount,
        currency=purchase_data.currency,
        status="draft",
        credits_added=credits_to_add,
        metadata={
            "payment_method": "stripe",
            "user_id": current_user.id,
            "user_email": current_user.email
        }
    )
    
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    
    try:
        # Create Stripe payment intent
        payment_intent = stripe.PaymentIntent.create(
            amount=int(purchase_data.amount * 100),  # Convert to cents
            currency=purchase_data.currency.lower(),
            payment_method=purchase_data.payment_method_id,
            confirmation_method="manual",
            confirm=True,
            metadata={
                "invoice_id": str(invoice.public_id),
                "user_id": str(current_user.public_id),
                "credits": str(credits_to_add)
            },
            return_url=f"https://yourapp.com/billing/success?invoice={invoice.public_id}",
            receipt_email=current_user.email,
        )
        
        # Update invoice with payment details
        invoice.status = "pending"
        invoice.payment_method = "stripe"
        invoice.payment_id = payment_intent.id
        db.commit()
        
        # Create audit log
        audit_log = AuditLog(
            user_id=current_user.id,
            action="credit_purchase",
            resource_type="invoice",
            resource_id=str(invoice.public_id),
            details={
                "amount": purchase_data.amount,
                "currency": purchase_data.currency,
                "credits_added": credits_to_add,
                "stripe_payment_intent": payment_intent.id
            }
        )
        db.add(audit_log)
        db.commit()
        
        # Return client secret for frontend confirmation
        return {
            **invoice.__dict__,
            "client_secret": payment_intent.client_secret
        }
        
    except stripe.error.StripeError as e:
        # Update invoice status to failed
        invoice.status = "failed"
        invoice.metadata["error"] = str(e)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Payment failed: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process payment: {str(e)}"
        )


@router.get("/invoices", response_model=List[InvoiceResponse])
async def list_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """List user's invoices.
    
    Rules:   must filter by status; must include payment details
    """
    # Get credit account
    credit_account = db.query(CreditAccount).filter(
        CreditAccount.user_id == current_user.id
    ).first()
    
    if not credit_account:
        return []
    
    # Build query
    query = db.query(Invoice).filter(
        Invoice.credit_account_id == credit_account.id
    )
    
    if status:
        query = query.filter(Invoice.status == status)
    
    invoices = query.order_by(desc(Invoice.created_at))\
                   .offset(offset)\
                   .limit(limit)\
                   .all()
    
    return invoices


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get invoice details.
    
    Rules:   must verify user owns the invoice; must include line items
    """
    # Find invoice
    invoice = db.query(Invoice).filter(Invoice.public_id == invoice_id).first()
    
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Verify ownership
    credit_account = db.query(CreditAccount).filter(
        CreditAccount.id == invoice.credit_account_id,
        CreditAccount.user_id == current_user.id
    ).first()
    
    if not credit_account:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this invoice"
        )
    
    return invoice


@router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    stripe_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Handle Stripe webhook events.
    
    Rules:   must verify webhook signature; must handle event idempotency
    """
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Stripe webhook secret is not configured"
        )
    
    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature"
        )
    
    try:
        # Get request body
        body = await request.body()
        
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload=body,
            sig_header=stripe_signature,
            secret=settings.STRIPE_WEBHOOK_SECRET
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payload: {str(e)}"
        )
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid signature: {str(e)}"
        )
    
    # Handle different event types
    event_type = event["type"]
    event_data = event["data"]["object"]
    
    if event_type == "payment_intent.succeeded":
        await handle_payment_success(event_data, db, background_tasks)
    elif event_type == "payment_intent.payment_failed":
        await handle_payment_failure(event_data, db)
    elif event_type == "charge.refunded":
        await handle_refund(event_data, db)
    
    # Create audit log for webhook
    audit_log = AuditLog(
        user_id=None,  # System event
        action="stripe_webhook",
        resource_type="webhook",
        resource_id=event["id"],
        details={
            "type": event_type,
            "livemode": event["livemode"],
            "created": event["created"]
        }
    )
    db.add(audit_log)
    db.commit()
    
    return {"status": "success"}


async def handle_payment_success(payment_intent: dict, db: Session, background_tasks: BackgroundTasks):
    """Handle successful payment."""
    invoice_id = payment_intent.get("metadata", {}).get("invoice_id")
    
    if not invoice_id:
        return
    
    # Find invoice
    invoice = db.query(Invoice).filter(Invoice.public_id == invoice_id).first()
    if not invoice:
        return
    
    # Update invoice status
    invoice.status = "paid"
    invoice.paid_at = datetime.utcnow()
    invoice.payment_id = payment_intent["id"]
    
    # Add credits to user's account
    credit_account = db.query(CreditAccount).filter(
        CreditAccount.id == invoice.credit_account_id
    ).first()
    
    if credit_account:
        credit_account.balance += invoice.credits_added
    
    db.commit()
    
    # Send receipt email in background
    # background_tasks.add_task(send_receipt_email, invoice)


async def handle_payment_failure(payment_intent: dict, db: Session):
    """Handle failed payment."""
    invoice_id = payment_intent.get("metadata", {}).get("invoice_id")
    
    if not invoice_id:
        return
    
    # Find invoice
    invoice = db.query(Invoice).filter(Invoice.public_id == invoice_id).first()
    if not invoice:
        return
    
    # Update invoice status
    invoice.status = "failed"
    invoice.metadata["failure_reason"] = payment_intent.get("last_payment_error", {}).get("message", "Unknown")
    
    db.commit()


async def handle_refund(charge: dict, db: Session):
    """Handle refund."""
    payment_intent_id = charge.get("payment_intent")
    
    if not payment_intent_id:
        return
    
    # Find invoice by payment intent ID
    invoice = db.query(Invoice).filter(Invoice.payment_id == payment_intent_id).first()
    if not invoice:
        return
    
    # Update invoice status
    invoice.status = "refunded"
    
    # Deduct credits from user's account
    credit_account = db.query(CreditAccount).filter(
        CreditAccount.id == invoice.credit_account_id
    ).first()
    
    if credit_account:
        credit_account.balance -= invoice.credits_added
        if credit_account.balance < 0:
            credit_account.balance = 0  # Prevent negative balance
    
    db.commit()


@router.get("/pricing")
async def get_pricing_info():
    """Get credit pricing information."""
    return {
        "credit_exchange_rate": settings.CREDIT_EXCHANGE_RATE,
        "currency": "USD",
        "pricing_tiers": [
            {"credits": 100, "price": 10.00, "price_per_credit": 0.10},
            {"credits": 500, "price": 45.00, "price_per_credit": 0.09},
            {"credits": 1000, "price": 80.00, "price_per_credit": 0.08},
            {"credits": 5000, "price": 350.00, "price_per_credit": 0.07},
            {"credits": 10000, "price": 600.00, "price_per_credit": 0.06},
        ],
        "supported_currencies": ["USD", "EUR", "GBP"],
        "payment_methods": ["stripe"]  # Could add "paypal", "crypto" etc.
    }