"""Invoice generator for creating PDF invoices."""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, BinaryIO
from decimal import Decimal
from io import BytesIO

from sqlalchemy.orm import Session

from app.models.subscription import Invoice, BillingAccount, User
from app.models.credit import CreditTransaction

logger = logging.getLogger(__name__)


class InvoiceGeneratorError(Exception):
    """Base exception for invoice generator errors."""
    pass


class InvoiceGenerator:
    """Invoice generator for creating PDF invoices."""
    
    def __init__(self, db_session: Session):
        """Initialize invoice generator.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
    
    def generate_invoice_pdf(self, invoice_id: int) -> Optional[BytesIO]:
        """Generate PDF for invoice.
        
        Args:
            invoice_id: Invoice ID
            
        Returns:
            BytesIO buffer containing PDF, or None if failed
        """
        try:
            invoice = self.db.query(Invoice).get(invoice_id)
            if not invoice:
                raise InvoiceGeneratorError(f"Invoice {invoice_id} not found")
            
            # Get billing account and user
            billing_account = invoice.billing_account
            user = billing_account.user if billing_account else None
            
            # Generate simple invoice
            pdf_buffer = self._create_pdf(invoice, billing_account, user)
            
            logger.info(f"Generated PDF for invoice {invoice_id}")
            return pdf_buffer
            
        except Exception as e:
            logger.error(f"Failed to generate invoice PDF for invoice {invoice_id}: {e}")
            return None
    
    def generate_credit_transaction_receipt(self, transaction_id: int) -> Optional[BytesIO]:
        """Generate receipt PDF for credit transaction.
        
        Args:
            transaction_id: CreditTransaction ID
            
        Returns:
            BytesIO buffer containing PDF receipt
        """
        try:
            transaction = self.db.query(CreditTransaction).get(transaction_id)
            if not transaction:
                raise InvoiceGeneratorError(f"Transaction {transaction_id} not found")
            
            credit_account = transaction.credit_account
            user = credit_account.user if credit_account else None
            
            # Generate receipt
            pdf_buffer = self._create_receipt(transaction, user)
            
            logger.info(f"Generated receipt for transaction {transaction_id}")
            return pdf_buffer
            
        except Exception as e:
            logger.error(f"Failed to generate receipt for transaction {transaction_id}: {e}")
            return None
    
    def _create_pdf(self, invoice: Invoice, billing_account: BillingAccount, user: User) -> BytesIO:
        """Create PDF for invoice.
        
        Args:
            invoice: Invoice instance
            billing_account: BillingAccount instance
            user: User instance
            
        Returns:
            BytesIO buffer containing PDF
        """
        # TODO: Implement actual PDF generation using ReportLab, WeasyPrint, or similar
        # For now, return a placeholder
        
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        
        # Add header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(1 * inch, 10.5 * inch, "INVOICE")
        
        # Invoice details
        c.setFont("Helvetica", 10)
        c.drawString(1 * inch, 10 * inch, f"Invoice #: {invoice.invoice_number}")
        c.drawString(1 * inch, 9.75 * inch, f"Date: {invoice.invoice_date.strftime('%Y-%m-%d')}")
        if invoice.due_date:
            c.drawString(1 * inch, 9.5 * inch, f"Due Date: {invoice.due_date.strftime('%Y-%m-%d')}")
        
        # Bill to
        c.drawString(1 * inch, 9 * inch, "Bill To:")
        c.drawString(1.5 * inch, 8.75 * inch, f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username)
        c.drawString(1.5 * inch, 8.5 * inch, user.email)
        
        if billing_account:
            if billing_account.company_name:
                c.drawString(1.5 * inch, 8.25 * inch, billing_account.company_name)
            if billing_account.address_line1:
                c.drawString(1.5 * inch, 8 * inch, billing_account.address_line1)
            if billing_account.address_line2:
                c.drawString(1.5 * inch, 7.75 * inch, billing_account.address_line2)
            if billing_account.city and billing_account.state:
                c.drawString(1.5 * inch, 7.5 * inch, f"{billing_account.city}, {billing_account.state} {billing_account.postal_code}")
        
        # Invoice items
        c.drawString(1 * inch, 7 * inch, "Description")
        c.drawString(5 * inch, 7 * inch, "Amount")
        
        c.line(1 * inch, 6.9 * inch, 7.5 * inch, 6.9 * inch)
        
        y = 6.7 * inch
        c.drawString(1 * inch, y, invoice.description or "Service")
        c.drawString(5 * inch, y, f"${invoice.amount_usd:,.2f}")
        
        if invoice.tax_usd and invoice.tax_usd > 0:
            y -= 0.25 * inch
            c.drawString(1 * inch, y, "Tax")
            c.drawString(5 * inch, y, f"${invoice.tax_usd:,.2f}")
        
        y -= 0.5 * inch
        c.line(1 * inch, y, 7.5 * inch, y)
        
        y -= 0.25 * inch
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1 * inch, y, "TOTAL")
        c.drawString(5 * inch, y, f"${invoice.total_usd:,.2f}")
        
        # Footer
        c.setFont("Helvetica", 8)
        c.drawString(1 * inch, 0.5 * inch, "Thank you for your business!")
        c.drawString(1 * inch, 0.25 * inch, "Generated by AgentHub")
        
        c.save()
        buffer.seek(0)
        return buffer
    
    def _create_receipt(self, transaction: CreditTransaction, user: User) -> BytesIO:
        """Create PDF receipt for credit transaction.
        
        Args:
            transaction: CreditTransaction instance
            user: User instance
            
        Returns:
            BytesIO buffer containing PDF receipt
        """
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        
        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(1 * inch, 10.5 * inch, "RECEIPT")
        
        # Receipt details
        c.setFont("Helvetica", 10)
        c.drawString(1 * inch, 10 * inch, f"Receipt #: CR{transaction.id:08d}")
        c.drawString(1 * inch, 9.75 * inch, f"Date: {transaction.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Customer info
        c.drawString(1 * inch, 9.25 * inch, "Customer:")
        c.drawString(1.5 * inch, 9 * inch, f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username)
        c.drawString(1.5 * inch, 8.75 * inch, user.email)
        
        # Transaction details
        c.drawString(1 * inch, 8.25 * inch, "Transaction Type:")
        c.drawString(2.5 * inch, 8.25 * inch, transaction.transaction_type.value.replace('_', ' ').title())
        
        c.drawString(1 * inch, 8 * inch, "Amount:")
        amount_text = f"{transaction.amount:+,.2f} credits"
        c.drawString(2.5 * inch, 8 * inch, amount_text)
        
        c.drawString(1 * inch, 7.75 * inch, "Description:")
        c.drawString(2.5 * inch, 7.75 * inch, transaction.description or "")
        
        c.drawString(1 * inch, 7.5 * inch, "Balance After:")
        c.drawString(2.5 * inch, 7.5 * inch, f"{transaction.balance_after:,.2f} credits")
        
        if transaction.stripe_payment_intent_id:
            c.drawString(1 * inch, 7.25 * inch, "Payment ID:")
            c.drawString(2.5 * inch, 7.25 * inch, transaction.stripe_payment_intent_id[:20] + "...")
        
        # Footer
        c.setFont("Helvetica", 8)
        c.drawString(1 * inch, 0.5 * inch, "Thank you for using AgentHub!")
        c.drawString(1 * inch, 0.25 * inch, "This is an automated receipt. Please keep for your records.")
        
        c.save()
        buffer.seek(0)
        return buffer
    
    def create_invoice_from_credit_purchase(
        self,
        user_id: int,
        amount_usd: Decimal,
        credits: int,
        description: str = "Credit Purchase",
        organization_id: Optional[int] = None,
    ) -> Optional[Invoice]:
        """Create invoice for credit purchase.
        
        Args:
            user_id: User ID
            amount_usd: Amount in USD
            credits: Number of credits purchased
            description: Invoice description
            organization_id: Optional organization ID
            
        Returns:
            Invoice instance or None if failed
        """
        try:
            # Get user and billing account
            user = self.db.query(User).get(user_id)
            if not user:
                raise InvoiceGeneratorError(f"User {user_id} not found")
            
            billing_account = user.billing_account
            if not billing_account:
                # Create billing account if doesn't exist
                billing_account = BillingAccount(
                    user_id=user_id,
                    balance_usd=Decimal('0.00'),
                    currency='USD',
                )
                self.db.add(billing_account)
                self.db.commit()
                self.db.refresh(billing_account)
            
            # Generate invoice number
            invoice_number = self._generate_invoice_number()
            
            # Create invoice
            invoice = Invoice(
                billing_account_id=billing_account.id,
                invoice_number=invoice_number,
                status='draft',
                amount_usd=amount_usd,
                total_usd=amount_usd,
                currency='USD',
                invoice_date=datetime.utcnow().date(),
                due_date=datetime.utcnow().date(),
                description=f"{description}: {credits} credits",
                metadata={
                    'credits': credits,
                    'organization_id': organization_id,
                    'type': 'credit_purchase',
                }
            )
            
            self.db.add(invoice)
            self.db.commit()
            
            logger.info(f"Created invoice {invoice_number} for credit purchase by user {user_id}")
            return invoice
            
        except Exception as e:
            logger.error(f"Failed to create invoice for credit purchase: {e}")
            self.db.rollback()
            return None
    
    def _generate_invoice_number(self) -> str:
        """Generate unique invoice number.
        
        Returns:
            Invoice number string
        """
        # Format: INV-YYYYMMDD-XXXXX
        date_part = datetime.utcnow().strftime("%Y%m%d")
        
        # Get count of invoices today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        count = self.db.query(Invoice).filter(
            Invoice.created_at >= today_start
        ).count()
        
        sequence = count + 1
        return f"INV-{date_part}-{sequence:05d}"