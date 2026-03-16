"""services/stripe_service.py -- Stripe payment gateway integration.

Depends on: config.py :: STRIPE_KEY
Exports:
    charge_card(amount_cents, payment_method) -> dict
    refund_charge(charge_id, amount_cents) -> dict
    create_customer(email, name) -> str (customer_id)
    attach_payment_method(customer_id, payment_method_id) -> None
Used by: invoices/invoice_service.py :: collect_payment()

Rules:
  - amount_cents in CENTESIMI INTERI (es. 2900 = 29.00 EUR).
  - Non applicare tax qui: già applicata in invoice_service.py :: issue_invoice().
"""
import stripe
from config import STRIPE_KEY

stripe.api_key = STRIPE_KEY

def charge_card(amount_cents: int, payment_method: str) -> dict:
    intent = stripe.PaymentIntent.create(
        amount=amount_cents,
        currency="eur",
        payment_method=payment_method,
        confirm=True,
    )
    return {"id": intent.id, "status": intent.status}

def refund_charge(charge_id: str, amount_cents: int | None = None) -> dict:
    params = {"charge": charge_id}
    if amount_cents:
        params["amount"] = amount_cents
    refund = stripe.Refund.create(**params)
    return {"id": refund.id, "status": refund.status}

def create_customer(email: str, name: str) -> str:
    customer = stripe.Customer.create(email=email, name=name)
    return customer.id

def attach_payment_method(customer_id: str, payment_method_id: str):
    stripe.PaymentMethod.attach(payment_method_id, customer=customer_id)
