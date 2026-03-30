"""Stripe integration for payment processing."""

import logging
import stripe
from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.models.credit import CreditPlan, CreditTransactionType
from app.models.audit_log import AuditLog, AuditAction, AuditSeverity
from app.billing.credit_engine import CreditEngine

logger = logging.getLogger(__name__)


class StripeIntegrationError(Exception):
    """Base exception for Stripe integration errors."""
    pass


class StripeIntegration:
    """Stripe integration for payment processing."""
    
    def __init__(self, db_session: Session):
        """Initialize Stripe integration.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.credit_engine = CreditEngine(db_session)
        
        # Configure Stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    
    def create_customer(self, user: User, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create Stripe customer for user.
        
        Args:
            user: User instance
            metadata: Additional metadata
            
        Returns:
            Stripe customer ID
        """
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username,
                metadata={
                    'user_id': str(user.id),
                    'username': user.username,
                    **(metadata or {}),
                }
            )
            
            # Update user with Stripe customer ID
            # Note: This should be stored in user model or billing account
            # For now, we'll store in audit log
            
            AuditLog.log(
                action=AuditAction.SUBSCRIPTION_CREATE,
                description=f"Created Stripe customer: {customer.id}",
                user_id=user.id,
                resource_type='user',
                resource_id=user.id,
                metadata={
                    'stripe_customer_id': customer.id,
                    'customer_email': customer.email,
                }
            )
            
            logger.info(f"Created Stripe customer {customer.id} for user {user.id}")
            return customer.id
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer for user {user.id}: {e}")
            raise StripeIntegrationError(f"Stripe error: {e}")
    
    def create_checkout_session(
        self,
        user_id: int,
        credit_plan_id: Optional[int] = None,
        amount_usd: Optional[Decimal] = None,
        credits: Optional[int] = None,
        success_url: str = "http://localhost:3000/billing/success",
        cancel_url: str = "http://localhost:3000/billing/cancel",
        organization_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create Stripe checkout session for credit purchase.
        
        Args:
            user_id: User ID
            credit_plan_id: Credit plan ID (optional)
            amount_usd: Amount in USD (optional if credit_plan_id provided)
            credits: Number of credits (optional)
            success_url: Success redirect URL
            cancel_url: Cancel redirect URL
            organization_id: Optional organization ID
            
        Returns:
            Checkout session data
            
        Raises:
            StripeIntegrationError: If Stripe operation fails
            ValueError: If invalid parameters
        """
        try:
            user = self.db.query(User).get(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Get or create Stripe customer
            customer_id = self.get_customer_id(user)
            
            line_items = []
            metadata = {
                'user_id': str(user_id),
                'purchase_type': 'credits',
            }
            
            if credit_plan_id:
                # Purchase specific credit plan
                credit_plan = self.db.query(CreditPlan).get(credit_plan_id)
                if not credit_plan or not credit_plan.is_active:
                    raise ValueError(f"Credit plan {credit_plan_id} not found or inactive")
                
                if not credit_plan.stripe_price_id:
                    raise StripeIntegrationError(f"Credit plan {credit_plan_id} has no Stripe price ID")
                
                line_items.append({
                    'price': credit_plan.stripe_price_id,
                    'quantity': 1,
                })
                
                metadata.update({
                    'credit_plan_id': str(credit_plan_id),
                    'credits': str(credit_plan.credits),
                    'expires_in_days': str(credit_plan.expires_in_days) if credit_plan.expires_in_days else '',
                })
                
                amount_usd = credit_plan.price_usd
                credits = credit_plan.credits
                
            elif amount_usd and credits:
                # Custom amount purchase
                # Create a Stripe Price on the fly
                price = stripe.Price.create(
                    unit_amount=int(amount_usd * 100),  # Convert to cents
                    currency='usd',
                    product_data={
                        'name': f'{credits} Credits',
                        'description': f'Purchase of {credits} credits',
                    },
                    metadata={
                        'credits': str(credits),
                        'user_id': str(user_id),
                    }
                )
                
                line_items.append({
                    'price': price.id,
                    'quantity': 1,
                })
                
                metadata.update({
                    'credits': str(credits),
                    'custom_amount': 'true',
                })
                
            else:
                raise ValueError("Either credit_plan_id or both amount_usd and credits must be provided")
            
            if organization_id:
                metadata['organization_id'] = str(organization_id)
            
            # Create checkout session
            checkout_session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url=f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=cancel_url,
                metadata=metadata,
                customer_update={
                    'address': 'auto',
                },
                billing_address_collection='required',
            )
            
            # Log audit trail
            AuditLog.log(
                action=AuditAction.SUBSCRIPTION_CREATE,
                description=f"Created checkout session for {credits} credits (${amount_usd})",
                user_id=user_id,
                organization_id=organization_id,
                resource_type='credit_purchase',
                metadata={
                    'checkout_session_id': checkout_session.id,
                    'amount_usd': float(amount_usd) if amount_usd else 0.0,
                    'credits': int(credits) if credits else 0,
                    'credit_plan_id': credit_plan_id,
                    'stripe_customer_id': customer_id,
                }
            )
            
            logger.info(f"Created checkout session {checkout_session.id} for user {user_id}")
            
            return {
                'session_id': checkout_session.id,
                'url': checkout_session.url,
                'amount_usd': float(amount_usd) if amount_usd else 0.0,
                'credits': int(credits) if credits else 0,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session for user {user_id}: {e}")
            raise StripeIntegrationError(f"Stripe error: {e}")
    
    def get_customer_id(self, user: User) -> str:
        """Get or create Stripe customer ID for user.
        
        Args:
            user: User instance
            
        Returns:
            Stripe customer ID
        """
        # TODO: Store Stripe customer ID in user model or billing account
        # For now, we'll search for existing customer by email
        try:
            customers = stripe.Customer.list(email=user.email, limit=1)
            if customers.data:
                return customers.data[0].id
        except stripe.error.StripeError:
            pass
        
        # Create new customer
        return self.create_customer(user)
    
    def handle_webhook_event(self, payload: bytes, sig_header: str) -> Dict[str, Any]:
        """Handle Stripe webhook event.
        
        Args:
            payload: Raw webhook payload
            sig_header: Stripe signature header
            
        Returns:
            Webhook handling result
            
        Raises:
            StripeIntegrationError: If webhook validation fails
        """
        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
        except ValueError as e:
            logger.error(f"Invalid Stripe webhook payload: {e}")
            raise StripeIntegrationError(f"Invalid payload: {e}")
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid Stripe webhook signature: {e}")
            raise StripeIntegrationError(f"Invalid signature: {e}")
        
        # Handle event
        event_type = event['type']
        event_data = event['data']['object']
        
        logger.info(f"Processing Stripe webhook event: {event_type}")
        
        # Handle different event types
        if event_type == 'checkout.session.completed':
            return self._handle_checkout_session_completed(event_data)
        elif event_type == 'payment_intent.succeeded':
            return self._handle_payment_intent_succeeded(event_data)
        elif event_type == 'payment_intent.payment_failed':
            return self._handle_payment_intent_failed(event_data)
        elif event_type == 'invoice.paid':
            return self._handle_invoice_paid(event_data)
        elif event_type == 'invoice.payment_failed':
            return self._handle_invoice_payment_failed(event_data)
        else:
            logger.info(f"Ignoring unhandled Stripe event type: {event_type}")
            return {'status': 'ignored', 'event_type': event_type}
    
    def _handle_checkout_session_completed(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle checkout.session.completed webhook event.
        
        Args:
            session: Stripe session object
            
        Returns:
            Processing result
        """
        try:
            # Extract metadata
            metadata = session.get('metadata', {})
            user_id = int(metadata.get('user_id', 0))
            organization_id = int(metadata.get('organization_id', 0)) if metadata.get('organization_id') else None
            credit_plan_id = int(metadata.get('credit_plan_id', 0)) if metadata.get('credit_plan_id') else None
            credits = int(metadata.get('credits', 0))
            
            if not user_id or not credits:
                logger.error(f"Invalid metadata in checkout session: {metadata}")
                return {'status': 'error', 'reason': 'invalid_metadata'}
            
            # Calculate credits from amount if not provided
            if not credits and session.get('amount_total'):
                amount_usd = session['amount_total'] / 100  # Convert cents to USD
                credits = int(amount_usd * 100)  # 1 credit = $0.01
            
            # Get expiration days from credit plan
            expires_in_days = None
            if credit_plan_id:
                credit_plan = self.db.query(CreditPlan).get(credit_plan_id)
                if credit_plan:
                    expires_in_days = credit_plan.expires_in_days
            
            # Add credits to user account
            transaction = self.credit_engine.add(
                user_id=user_id,
                amount=Decimal(str(credits)),
                transaction_type=CreditTransactionType.PURCHASE,
                reference_id=session.get('id'),
                reference_type='stripe_checkout_session',
                description=f"Credit purchase via Stripe: {credits} credits",
                organization_id=organization_id,
                expires_in_days=expires_in_days,
                stripe_payment_intent_id=session.get('payment_intent'),
            )
            
            # Update transaction with Stripe details
            if transaction:
                transaction.stripe_payment_intent_id = session.get('payment_intent')
                self.db.commit()
            
            logger.info(f"Added {credits} credits to user {user_id} from Stripe checkout session {session['id']}")
            
            return {
                'status': 'success',
                'user_id': user_id,
                'credits': credits,
                'transaction_id': transaction.id if transaction else None,
            }
            
        except Exception as e:
            logger.error(f"Failed to handle checkout.session.completed: {e}")
            return {'status': 'error', 'reason': str(e)}
    
    def _handle_payment_intent_succeeded(self, payment_intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle payment_intent.succeeded webhook event.
        
        Args:
            payment_intent: Stripe payment intent object
            
        Returns:
            Processing result
        """
        # Payment intent success is already handled by checkout.session.completed
        # but we log it for audit purposes
        logger.info(f"Payment intent {payment_intent['id']} succeeded")
        
        AuditLog.log(
            action=AuditAction.INVOICE_PAY,
            description=f"Payment intent succeeded: {payment_intent['id']}",
            metadata={
                'payment_intent_id': payment_intent['id'],
                'amount': payment_intent.get('amount'),
                'currency': payment_intent.get('currency'),
                'customer': payment_intent.get('customer'),
            }
        )
        
        return {'status': 'success'}
    
    def _handle_payment_intent_failed(self, payment_intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle payment_intent.payment_failed webhook event.
        
        Args:
            payment_intent: Stripe payment intent object
            
        Returns:
            Processing result
        """
        logger.warning(f"Payment intent {payment_intent['id']} failed: {payment_intent.get('last_payment_error', {})}")
        
        AuditLog.log(
            action=AuditAction.INVOICE_PAY,
            description=f"Payment intent failed: {payment_intent['id']}",
            severity=AuditSeverity.HIGH,
            metadata={
                'payment_intent_id': payment_intent['id'],
                'error': payment_intent.get('last_payment_error', {}),
                'amount': payment_intent.get('amount'),
                'customer': payment_intent.get('customer'),
            }
        )
        
        return {'status': 'success'}
    
    def _handle_invoice_paid(self, invoice: Dict[str, Any]) -> Dict[str, Any]:
        """Handle invoice.paid webhook event.
        
        Args:
            invoice: Stripe invoice object
            
        Returns:
            Processing result
        """
        # Handle subscription invoice payment
        # This would trigger subscription activation
        logger.info(f"Invoice {invoice['id']} paid for subscription {invoice.get('subscription')}")
        
        # TODO: Update subscription status in database
        
        return {'status': 'success'}
    
    def _handle_invoice_payment_failed(self, invoice: Dict[str, Any]) -> Dict[str, Any]:
        """Handle invoice.payment_failed webhook event.
        
        Args:
            invoice: Stripe invoice object
            
        Returns:
            Processing result
        """
        logger.warning(f"Invoice {invoice['id']} payment failed for subscription {invoice.get('subscription')}")
        
        # TODO: Update subscription status to past_due
        
        return {'status': 'success'}
    
    def create_subscription_checkout(
        self,
        user_id: int,
        plan_type: str,
        billing_cycle: str = 'monthly',
        success_url: str = "http://localhost:3000/billing/success",
        cancel_url: str = "http://localhost:3000/billing/cancel",
    ) -> Dict[str, Any]:
        """Create Stripe checkout session for subscription.
        
        Args:
            user_id: User ID
            plan_type: Plan type (free, basic, pro, team, enterprise)
            billing_cycle: Billing cycle (monthly, yearly)
            success_url: Success redirect URL
            cancel_url: Cancel redirect URL
            
        Returns:
            Checkout session data
        """
        # TODO: Implement subscription checkout
        # This would involve:
        # 1. Getting Stripe price ID for the plan
        # 2. Creating checkout session in subscription mode
        # 3. Setting up webhook for subscription events
        
        raise NotImplementedError("Subscription checkout not yet implemented")
    
    def get_payment_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's payment history from Stripe.
        
        Args:
            user_id: User ID
            limit: Maximum number of payments to return
            
        Returns:
            List of payment records
        """
        try:
            user = self.db.query(User).get(user_id)
            if not user:
                return []
            
            customer_id = self.get_customer_id(user)
            if not customer_id:
                return []
            
            # Get payment intents for customer
            payment_intents = stripe.PaymentIntent.list(
                customer=customer_id,
                limit=limit,
            )
            
            payments = []
            for pi in payment_intents.data:
                payments.append({
                    'id': pi.id,
                    'amount': pi.amount / 100,  # Convert cents to USD
                    'currency': pi.currency,
                    'status': pi.status,
                    'created': datetime.fromtimestamp(pi.created).isoformat(),
                    'description': pi.description,
                    'metadata': pi.metadata,
                })
            
            return payments
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get payment history for user {user_id}: {e}")
            return []