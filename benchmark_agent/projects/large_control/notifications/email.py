import sendgrid
from sendgrid.helpers.mail import Mail
from config import SENDGRID_KEY

def _send(to: str, subject: str, body: str):
    sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_KEY)
    msg = Mail(from_email="billing@saas.io", to_emails=to,
               subject=subject, html_content=body)
    sg.send(msg)

def send_invoice_email(tenant_id: str, invoice: dict):
    _send(f"billing+{tenant_id}@saas.io",
          f"Fattura #{invoice['id']}",
          f"<p>Importo: {invoice['amount_cents']/100:.2f} EUR</p>")

def send_suspension_notice(email: str, tenant_id: str, reason: str = ""):
    _send(email,
          "Il tuo account è stato sospeso",
          f"<p>Account {tenant_id} sospeso. Motivo: {reason or 'Non specificato'}</p>")

def send_payment_failed(email: str, invoice_id: str):
    _send(email, "Pagamento fallito",
          f"<p>Non è stato possibile processare il pagamento per la fattura {invoice_id}.</p>")

def send_welcome(email: str, tenant_name: str):
    _send(email, f"Benvenuto in SaaS — {tenant_name}",
          f"<p>Ciao {tenant_name}, il tuo account è pronto!</p>")
