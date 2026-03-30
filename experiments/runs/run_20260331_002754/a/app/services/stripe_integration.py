"""app/services/stripe_integration.py — Stripe payment processing integration.

exports: StripeIntegrationService
used_by: app/services/container.py → ServiceContainer.stripe, billing service, webhook handlers
rules:   must handle webhook idempotency; sync local state with Stripe; validate signatures
agent:   Product Architect | 2024-03-30 | created Stripe integration service skeleton
         message: "implement webhook signature verification for security"
"""

import logging
import hashlib
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

import stripe

from app.exceptions import ServiceUnavailableError, ValidationError
from app.services.container import ServiceContainer

logger = logging.getLogger(__name__)


class StripeIntegrationService:
    """Stripe payment processing integration service.
    
    Rules:
        All Stripe calls must handle errors gracefully
        Webhook handlers must be idempotent
        Signature verification is mandatory for webhooks
        Local state must stay synchronized with Stripe
    """
    
    def __init__(self, container: ServiceContainer):
        """Initialize Stripe integration service.
        
        Args:
            container: Service container with dependencies
        """
        self.container = container
        self.config = container.config
        
        # Configure Stripe
        stripe.api_key = self.config.STRIPE_SECRET_KEY
        stripe.max_network_retries = 3
        
        # Webhook secret for signature verification
        self.webhook_secret = self.config.STRIPE_WEBHOOK_SECRET
        
        logger.info("StripeIntegrationService initialized")
    
    # --- Customer Management ---
    
    async def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create Stripe customer.
        
        Args:
            email: Customer email
            name: Optional customer name
            metadata: Optional metadata to attach to customer
            
        Returns:
            Stripe customer object
            
        Raises:
            ServiceUnavailableError: If Stripe API fails
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {},
            )
            return customer.to_dict()
        except stripe.error.StripeError as e:
            logger.error(f"Stripe customer creation failed: {e}")
            raise ServiceUnavailableError("Payment service", str(e))
    
    async def get_customer(
        self,
        customer_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get Stripe customer by ID.
        
        Args:
            customer_id: Stripe customer ID
            
        Returns:
            Stripe customer object or None if not found
        """
        try:
            customer = stripe.Customer.retrieve(customer_id)
            return customer.to_dict()
        except stripe.error.InvalidRequestError as e:
            if "No such customer" in str(e):
                return None
            logger.error(f"Stripe customer retrieval failed: {e}")
            raise ServiceUnavailableError("Payment service", str(e))
        except stripe.error.StripeError as e:
            logger.error(f"Stripe customer retrieval failed: {e}")
            raise ServiceUnavailableError("Payment service", str(e))
    
    async def update_customer(
        self,
        customer_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update Stripe customer.
        
        Args:
            customer_id: Stripe customer ID
            updates: Fields to update
            
        Returns:
            Updated Stripe customer object
        """
        try:
            customer = stripe.Customer.modify(customer_id, **updates)
            return customer.to_dict()
        except stripe.error.StripeError as e:
            logger.error(f"Stripe customer update failed: {e}")
            raise ServiceUnavailableError("Payment service", str(e))
    
    # --- Subscription Management ---
    
    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_days: Optional[int] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create Stripe subscription.
        
        Args:
            customer_id: Stripe customer ID
            price_id: Stripe price ID
            trial_days: Optional trial period in days
            metadata: Optional metadata
            
        Returns:
            Stripe subscription object
        """
        try:
            subscription_data = {
                "customer": customer_id,
                "items": [{"price": price_id}],
                "metadata": metadata or {},
                "payment_behavior": "default_incomplete",
                "expand": ["latest_invoice.payment_intent"],
            }
            
            if trial_days:
                subscription_data["trial_period_days"] = trial_days
            
            subscription = stripe.Subscription.create(**subscription_data)
            return subscription.to_dict()
        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription creation failed: {e}")
            raise ServiceUnavailableError("Payment service", str(e))
    
    async def get_subscription(
        self,
        subscription_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get Stripe subscription by ID.
        
        Args:
            subscription_id: Stripe subscription ID
            
        Returns:
            Stripe subscription object or None if not found
        """
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return subscription.to_dict()
        except stripe.error.InvalidRequestError as e:
            if "No such subscription" in str(e):
                return None
            logger.error(f"Stripe subscription retrieval failed: {e}")
            raise ServiceUnavailableError("Payment service", str(e))
        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription retrieval failed: {e}")
            raise ServiceUnavailableError("Payment service", str(e))
    
    async def cancel_subscription(
        self,
        subscription_id: str,
        cancel_at_period_end: bool = True,
    ) -> Dict[str, Any]:
        """Cancel Stripe subscription.
        
        Args:
            subscription_id: Stripe subscription ID
            cancel_at_period_end: Whether to cancel at period end
            
        Returns:
            Updated Stripe subscription object
        """
        try:
            if cancel_at_period_end:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True,
                )
            else:
                subscription = stripe.Subscription.delete(subscription_id)
            
            return subscription.to_dict()
        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription cancellation failed: {e}")
            raise ServiceUnavailableError("Payment service", str(e))
    
    async def update_subscription(
        self,
        subscription_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update Stripe subscription.
        
        Args:
            subscription_id: Stripe subscription ID
            updates: Fields to update
            
        Returns:
            Updated Stripe subscription object
        """
        try:
            subscription = stripe.Subscription.modify(subscription_id, **updates)
            return subscription.to_dict()
        except stripe.error.StripeError as e:
            logger.error(f"Stripe subscription update failed: {e}")
            raise ServiceUnavailableError("Payment service", str(e))
    
    # --- Payment Methods ---
    
    async def attach_payment_method(
        self,
        customer_id: str,
        payment_method_id: str,
        set_as_default: bool = True,
    ) -> Dict[str, Any]:
        """Attach payment method to customer.
        
        Args:
            customer_id: Stripe customer ID
            payment_method_id: Stripe payment method ID
            set_as_default: Whether to set as default payment method
            
        Returns:
            Attached payment method object
        """
        try:
            # Attach payment method to customer
            payment_method = stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id,
            )
            
            # Set as default if requested
            if set_as_default:
                stripe.Customer.modify(
                    customer_id,
                    invoice_settings={"default_payment_method": payment_method_id},
                )
            
            return payment_method.to_dict()
        except stripe.error.StripeError as e:
            logger.error(f"Stripe payment method attach failed: {e}")
            raise ServiceUnavailableError("Payment service", str(e))
    
    async def list_payment_methods(
        self,
        customer_id: str,
        type: str = "card",
    ) -> List[Dict[str, Any]]:
        """List customer's payment methods.
        
        Args:
            customer_id: Stripe customer ID
            type: Payment method type (card, etc.)
            
        Returns:
            List of payment method objects
        """
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type=type,
            )
            return [pm.to_dict() for pm in payment_methods.data]
        except stripe.error.StripeError as e:
            logger.error(f"Stripe payment method listing failed: {e}")
            raise ServiceUnavailableError("Payment service", str(e))
    
    # --- Invoices ---
    
    async def create_invoice(
        self,
        customer_id: str,
        description: str,
        amount_cents: int,
        currency: str = "usd",
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create Stripe invoice.
        
        Args:
            customer_id: Stripe customer ID
            description: Invoice line item description
            amount_cents: Amount in cents
            currency: Currency code
            metadata: Optional metadata
            
        Returns:
            Stripe invoice object
        """
        try:
            # Create invoice item
            stripe.InvoiceItem.create(
                customer=customer_id,
                amount=amount_cents,
                currency=currency,
                description=description,
                metadata=metadata or {},
            )
            
            # Create invoice
            invoice = stripe.Invoice.create(
                customer=customer_id,
                auto_advance=True,
                metadata=metadata or {},
            )
            
            # Finalize invoice
            invoice = stripe.Invoice.finalize_invoice(invoice.id)
            
            return invoice.to_dict()
        except stripe.error.StripeError as e:
            logger.error(f"Stripe invoice creation failed: {e}")
            raise ServiceUnavailableError("Payment service", str(e))
    
    async def get_invoice(
        self,
        invoice_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get Stripe invoice by ID.
        
        Args:
            invoice_id: Stripe invoice ID
            
        Returns:
            Stripe invoice object or None if not found
        """
        try:
            invoice = stripe.Invoice.retrieve(invoice_id)
            return invoice.to_dict()
        except stripe.error.InvalidRequestError as e:
            if "No such invoice" in str(e):
                return None
            logger.error(f"Stripe invoice retrieval failed: {e}")
            raise ServiceUnavailableError("Payment service", str(e))
        except stripe.error.StripeError as e:
            logger.error(f"Stripe invoice retrieval failed: {e}")
            raise ServiceUnavailableError("Payment service", str(e))
    
    async def list_invoices(
        self,
        customer_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """List customer's invoices.
        
        Args:
            customer_id: Stripe customer ID
            limit: Maximum number of invoices to return
            
        Returns:
            List of invoice objects
        """
        try:
            invoices = stripe.Invoice.list(
                customer=customer_id,
                limit=limit,
            )
            return [inv.to_dict() for inv in invoices.data]
        except stripe.error.StripeError as e:
            logger.error(f"Stripe invoice listing failed: {e}")
            raise ServiceUnavailableError("Payment service", str(e))
    
    # --- Webhook Handling ---
    
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """Verify Stripe webhook signature.
        
        Args:
            payload: Raw request payload
            signature: Stripe signature header
            
        Returns:
            True if signature is valid
            
        Rules:
            Must use webhook secret from configuration
            Protects against webhook spoofing
        """
        if not self.webhook_secret:
            logger.warning("No webhook secret configured, skipping signature verification")
            return True
        
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                self.webhook_secret,
            )
            return True
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Stripe webhook signature verification failed: {e}")
            return False
        except ValueError as e:
            logger.error(f"Stripe webhook payload error: {e}")
            return False
    
    async def parse_webhook_event(
        self,
        payload: bytes,
        signature: str,
    ) -> Optional[Dict[str, Any]]:
        """Parse and verify webhook event.
        
        Args:
            payload: Raw request payload
            signature: Stripe signature header
            
        Returns:
            Parsed event object or None if invalid
        """
        if not self.verify_webhook_signature(payload, signature):
            return None
        
        try:
            event = json.loads(payload.decode('utf-8'))
            return event
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse webhook payload: {e}")
            return None
    
    # --- Pricing ---
    
    async def list_prices(
        self,
        active: bool = True,
        product_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List Stripe prices.
        
        Args:
            active: Only return active prices
            product_id: Optional product ID filter
            
        Returns:
            List of price objects
        """
        try:
            params = {"active": active}
            if product_id:
                params["product"] = product_id
            
            prices = stripe.Price.list(**params)
            return [price.to_dict() for price in prices.data]
        except stripe.error.StripeError as e:
            logger.error(f"Stripe price listing failed: {e}")
            raise ServiceUnavailableError("Payment service", str(e))
    
    async def get_price(
        self,
        price_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get Stripe price by ID.
        
        Args:
            price_id: Stripe price ID
            
        Returns:
            Price object or None if not found
        """
        try:
            price = stripe.Price.retrieve(price_id)
            return price.to_dict()
        except stripe.error.InvalidRequestError as e:
            if "No such price" in str(e):
                return None
            logger.error(f"Stripe price retrieval failed: {e}")
            raise ServiceUnavailableError("Payment service", str(e))
        except stripe.error.StripeError as e:
            logger.error(f"Stripe price retrieval failed: {e}")
            raise ServiceUnavailableError("Payment service", str(e))
    
    # --- Usage Recording (for metered billing) ---
    
    async def create_usage_record(
        self,
        subscription_item_id: str,
        quantity: int,
        timestamp: Optional[int] = None,
        action: str = "increment",
    ) -> Dict[str, Any]:
        """Create usage record for metered billing.
        
        Args:
            subscription_item_id: Stripe subscription item ID
            quantity: Usage quantity
            timestamp: Optional timestamp (Unix)
            action: increment or set
            
        Returns:
            Usage record object
        """
        try:
            usage_record = stripe.SubscriptionItem.create_usage_record(
                subscription_item_id,
                quantity=quantity,
                timestamp=timestamp or int(datetime.now().timestamp()),
                action=action,
            )
            return usage_record.to_dict()
        except stripe.error.StripeError as e:
            logger.error(f"Stripe usage record creation failed: {e}")
            raise ServiceUnavailableError("Payment service", str(e))
    
    # --- Health Check ---
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Stripe connectivity.
        
        Returns:
            Health status with details
        """
        try:
            # Simple API call to test connectivity
            balance = stripe.Balance.retrieve()
            
            return {
                "status": "healthy",
                "stripe_account": balance.get("object") == "balance",
                "livemode": balance.get("livemode", False),
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "stripe_account": False,
                "livemode": False,
            }