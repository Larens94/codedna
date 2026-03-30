"""invoices.py — Invoice generation and management.

exports: generate_invoice_pdf, create_invoice, get_invoice_details
used_by: billing.py router, webhook handlers, admin interface
rules:   must generate professional PDF invoices; must include all required legal info
agent:   DataEngineer | 2024-01-15 | created PDF invoice generation with reportlab
         message: "implement multi-language invoice support and tax calculations"
"""

import logging
import io
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from agenthub.db.models import Invoice, CreditAccount, User
from agenthub.config import settings

logger = logging.getLogger(__name__)


class InvoiceGenerator:
    """Generate professional PDF invoices."""
    
    @staticmethod
    def generate_invoice_pdf(
        invoice_id: str,
        db: Session,
        include_company_info: bool = True
    ) -> Tuple[Optional[bytes], Optional[str]]:
        """Generate PDF invoice.
        
        Args:
            invoice_id: Invoice public ID
            db: Database session
            include_company_info: Whether to include company header/footer
            
        Returns:
            Tuple of (pdf_bytes, error_message)
        """
        try:
            # Get invoice data
            invoice = db.query(Invoice).filter(Invoice.public_id == invoice_id).first()
            if not invoice:
                return None, "Invoice not found"
            
            # Get related data
            credit_account = db.query(CreditAccount).filter(
                CreditAccount.id == invoice.credit_account_id
            ).first()
            
            if not credit_account:
                return None, "Credit account not found"
            
            user = db.query(User).filter(User.id == credit_account.user_id).first()
            if not user:
                return None, "User not found"
            
            # Create PDF
            buffer = io.BytesIO()
            
            # Choose page size based on locale
            page_size = A4  # Use A4 for international, letter for US
            
            doc = SimpleDocTemplate(
                buffer,
                pagesize=page_size,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            
            # Build story (content)
            story = []
            styles = getSampleStyleSheet()
            
            # Add custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                textColor=colors.HexColor('#2c3e50')
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=12,
                textColor=colors.HexColor('#34495e')
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=6
            )
            
            # Company header (optional)
            if include_company_info:
                story.append(Paragraph(settings.APP_NAME, title_style))
                story.append(Paragraph("Professional AI Agent Platform", styles['Normal']))
                story.append(Spacer(1, 20))
            
            # Invoice title
            story.append(Paragraph(f"INVOICE #{invoice.public_id}", title_style))
            story.append(Spacer(1, 10))
            
            # Invoice details table
            invoice_data = [
                ["Invoice Date:", invoice.created_at.strftime("%B %d, %Y")],
                ["Invoice Number:", str(invoice.public_id)],
                ["Status:", invoice.status.upper()],
                ["Payment Method:", invoice.payment_method or "Not specified"],
            ]
            
            if invoice.paid_at:
                invoice_data.append(["Paid Date:", invoice.paid_at.strftime("%B %d, %Y")])
            
            invoice_table = Table(invoice_data, colWidths=[2*inch, 3*inch])
            invoice_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            story.append(invoice_table)
            story.append(Spacer(1, 20))
            
            # Billing information
            story.append(Paragraph("BILLING INFORMATION", heading_style))
            
            billing_data = [
                ["Bill To:", f"{user.full_name or 'Customer'}<br/>{user.email}"],
            ]
            
            billing_table = Table(billing_data, colWidths=[2*inch, 3*inch])
            billing_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            story.append(billing_table)
            story.append(Spacer(1, 20))
            
            # Line items table
            story.append(Paragraph("INVOICE DETAILS", heading_style))
            
            line_items = [
                ["Description", "Quantity", "Unit Price", "Amount"],
                [
                    f"AI Agent Credits - {invoice.credits_added} credits",
                    "1",
                    f"{invoice.currency} {invoice.amount:.2f}",
                    f"{invoice.currency} {invoice.amount:.2f}"
                ]
            ]
            
            line_items_table = Table(line_items, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
            line_items_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('LINEABOVE', (0, 0), (-1, 0), 1, colors.black),
                ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
                ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8f9fa')),
            ]))
            
            story.append(line_items_table)
            story.append(Spacer(1, 20))
            
            # Totals
            subtotal = invoice.amount
            tax_rate = Decimal('0.00')  # Would come from tax configuration
            tax_amount = subtotal * tax_rate
            total = subtotal + tax_amount
            
            totals_data = [
                ["Subtotal:", f"{invoice.currency} {subtotal:.2f}"],
                ["Tax ({:.0%}):".format(tax_rate), f"{invoice.currency} {tax_amount:.2f}"],
                ["Total:", f"<b>{invoice.currency} {total:.2f}</b>"],
            ]
            
            totals_table = Table(totals_data, colWidths=[4*inch, 2*inch])
            totals_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
            ]))
            
            story.append(totals_table)
            story.append(Spacer(1, 30))
            
            # Payment instructions
            if invoice.status == 'pending':
                story.append(Paragraph("PAYMENT INSTRUCTIONS", heading_style))
                story.append(Paragraph(
                    "Please make payment within 30 days of invoice date. "
                    "You can pay online through our secure payment portal.",
                    normal_style
                ))
                story.append(Spacer(1, 10))
            
            # Terms and conditions
            story.append(Paragraph("TERMS & CONDITIONS", heading_style))
            story.append(Paragraph(
                "1. All payments are due within 30 days of invoice date.<br/>"
                "2. Late payments may be subject to a 1.5% monthly interest charge.<br/>"
                "3. Credits are non-refundable and non-transferable.<br/>"
                "4. Unused credits expire according to your plan's terms.<br/>"
                "5. All amounts are in USD unless otherwise specified.",
                normal_style
            ))
            
            # Footer
            story.append(Spacer(1, 40))
            story.append(Paragraph(
                "Thank you for your business!<br/>"
                f"{settings.APP_NAME} - Professional AI Agent Platform<br/>"
                "support@agenthub.ai | https://agenthub.ai",
                ParagraphStyle(
                    'Footer',
                    parent=styles['Normal'],
                    fontSize=9,
                    textColor=colors.gray,
                    alignment=1  # Center aligned
                )
            ))
            
            # Build PDF
            doc.build(story)
            
            # Get PDF bytes
            pdf_bytes = buffer.getvalue()
            buffer.close()
            
            logger.info(f"Generated PDF invoice for {invoice_id}")
            return pdf_bytes, None
            
        except Exception as e:
            logger.error(f"Error generating invoice PDF: {e}")
            return None, str(e)
    
    @staticmethod
    def create_invoice(
        db: Session,
        credit_account_id: int,
        amount: float,
        currency: str,
        credits_added: float,
        description: str,
        payment_method: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[Invoice], Optional[str]]:
        """Create a new invoice record.
        
        Args:
            db: Database session
            credit_account_id: Credit account ID
            amount: Invoice amount
            currency: Currency code
            credits_added: Credits to add to account
            description: Invoice description
            payment_method: Payment method used
            metadata: Additional invoice metadata
            
        Returns:
            Tuple of (invoice_object, error_message)
        """
        try:
            import uuid
            
            # Validate amount
            if amount <= 0:
                return None, "Amount must be positive"
            
            if credits_added <= 0:
                return None, "Credits added must be positive"
            
            # Create invoice
            invoice = Invoice(
                public_id=str(uuid.uuid4()),
                credit_account_id=credit_account_id,
                amount=amount,
                currency=currency,
                status='draft',
                credits_added=credits_added,
                payment_method=payment_method,
                metadata={
                    'description': description,
                    'created_at': datetime.utcnow().isoformat(),
                    **(metadata or {})
                }
            )
            
            db.add(invoice)
            db.commit()
            db.refresh(invoice)
            
            logger.info(f"Created invoice {invoice.public_id} for account {credit_account_id}")
            return invoice, None
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating invoice: {e}")
            return None, str(e)
    
    @staticmethod
    def get_invoice_details(
        invoice_id: str,
        db: Session
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Get detailed invoice information.
        
        Args:
            invoice_id: Invoice public ID
            db: Database session
            
        Returns:
            Tuple of (invoice_details, error_message)
        """
        try:
            invoice = db.query(Invoice).filter(Invoice.public_id == invoice_id).first()
            if not invoice:
                return None, "Invoice not found"
            
            # Get related data
            credit_account = db.query(CreditAccount).filter(
                CreditAccount.id == invoice.credit_account_id
            ).first()
            
            user = db.query(User).filter(User.id == credit_account.user_id).first() if credit_account else None
            
            # Build detailed response
            details = {
                'invoice': {
                    'id': invoice.id,
                    'public_id': str(invoice.public_id),
                    'amount': invoice.amount,
                    'currency': invoice.currency,
                    'status': invoice.status,
                    'credits_added': invoice.credits_added,
                    'payment_method': invoice.payment_method,
                    'payment_id': invoice.payment_id,
                    'metadata': invoice.metadata,
                    'created_at': invoice.created_at,
                    'paid_at': invoice.paid_at,
                },
                'credit_account': {
                    'id': credit_account.id if credit_account else None,
                    'balance': credit_account.balance if credit_account else None,
                    'currency': credit_account.currency if credit_account else None,
                },
                'user': {
                    'id': user.id if user else None,
                    'email': user.email if user else None,
                    'full_name': user.full_name if user else None,
                } if user else None
            }
            
            return details, None
            
        except Exception as e:
            logger.error(f"Error getting invoice details: {e}")
            return None, str(e)
    
    @staticmethod
    def update_invoice_status(
        db: Session,
        invoice_id: str,
        status: str,
        payment_id: Optional[str] = None,
        metadata_updates: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """Update invoice status.
        
        Args:
            db: Database session
            invoice_id: Invoice public ID
            status: New status
            payment_id: Payment ID (if applicable)
            metadata_updates: Metadata updates
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            invoice = db.query(Invoice).filter(Invoice.public_id == invoice_id).first()
            if not invoice:
                return False, "Invoice not found"
            
            # Validate status transition
            valid_transitions = {
                'draft': ['pending', 'failed'],
                'pending': ['paid', 'failed'],
                'paid': ['refunded'],
                'failed': ['pending'],
                'refunded': []
            }
            
            if status not in valid_transitions.get(invoice.status, []):
                return False, f"Invalid status transition from {invoice.status} to {status}"
            
            # Update invoice
            invoice.status = status
            
            if payment_id:
                invoice.payment_id = payment_id
            
            if status == 'paid':
                invoice.paid_at = datetime.utcnow()
            
            if metadata_updates:
                invoice.metadata = {**(invoice.metadata or {}), **metadata_updates}
            
            db.commit()
            
            logger.info(f"Updated invoice {invoice_id} status to {status}")
            return True, None
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating invoice status: {e}")
            return False, str(e)


# Convenience functions
def generate_invoice_pdf(
    invoice_id: str,
    db: Session,
    include_company_info: bool = True
) -> Tuple[Optional[bytes], Optional[str]]:
    """Generate PDF invoice."""
    return InvoiceGenerator.generate_invoice_pdf(invoice_id, db, include_company_info)


def create_invoice(
    db: Session,
    credit_account_id: int,
    amount: float,
    currency: str,
    credits_added: float,
    description: str,
    payment_method: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Tuple[Optional[Invoice], Optional[str]]:
    """Create a new invoice."""
    return InvoiceGenerator.create_invoice(
        db, credit_account_id, amount, currency, credits_added,
        description, payment_method, metadata
    )


def get_invoice_details(
    invoice_id: str,
    db: Session
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Get invoice details."""
    return InvoiceGenerator.get_invoice_details(invoice_id, db)