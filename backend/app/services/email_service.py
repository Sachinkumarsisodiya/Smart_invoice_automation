import smtplib
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict, Any, Optional
from decimal import Decimal

from app.config import settings
from app.core.logging import logger


class EmailProvider(ABC):
    @abstractmethod
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send an email to a recipient. Returns True if successful, raises Exception otherwise."""
        pass


class ConsoleMockEmailProvider(EmailProvider):
    """Zero-dependency local development and testing email provider."""
    sent_emails: List[Dict[str, Any]] = []

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        payload = {
            "to": to_email,
            "subject": subject,
            "html_content": html_content,
            "text_content": text_content,
            "from": f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
        }
        self.sent_emails.append(payload)
        logger.info(f"[MockEmail] Dispatched email to '{to_email}' with subject: '{subject}'")
        return True

    @classmethod
    def clear_sent_emails(cls):
        cls.sent_emails.clear()


class SMTPEmailProvider(EmailProvider):
    """Production-grade SMTP email provider with TLS support."""

    def __init__(
        self,
        host: str = settings.SMTP_HOST,
        port: int = settings.SMTP_PORT,
        user: str = settings.SMTP_USER,
        password: str = settings.SMTP_PASSWORD,
        tls: bool = settings.SMTP_TLS,
        from_email: str = settings.EMAILS_FROM_EMAIL,
        from_name: str = settings.EMAILS_FROM_NAME
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.tls = tls
        self.from_email = from_email
        self.from_name = from_name

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        if not self.host:
            raise ValueError("SMTP host is not configured.")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.from_name} <{self.from_email}>"
        msg["To"] = to_email

        if text_content:
            msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        try:
            with smtplib.SMTP(self.host, self.port, timeout=15) as server:
                if self.tls:
                    server.starttls()
                if self.user and self.password:
                    server.login(self.user, self.password)
                server.sendmail(self.from_email, [to_email], msg.as_string())
            logger.info(f"[SMTPEmail] Sent email to '{to_email}' via {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"[SMTPEmail] Failed to send email to '{to_email}': {str(e)}")
            raise e


class EmailTemplateService:
    @staticmethod
    def render_payment_reminder(
        invoice_number: str,
        vendor_name: str,
        remaining_amount: Decimal,
        currency: str,
        due_date_str: str,
        days_left: int
    ) -> tuple[str, str]:
        """Renders HTML and Text templates for upcoming payment reminders."""
        if days_left == 0:
            urgency_text = "is due TODAY"
            badge_color = "#dc2626"
        elif days_left == 1:
            urgency_text = "is due TOMORROW"
            badge_color = "#ea580c"
        else:
            urgency_text = f"is due in {days_left} days"
            badge_color = "#2563eb"

        text_content = f"""SmartInvoice Payment Reminder

Invoice: #{invoice_number}
Supplier: {vendor_name}
Outstanding Balance: {currency} {remaining_amount:,.2f}
Due Date: {due_date_str} ({urgency_text})

Please ensure settlement is scheduled before the due date.
"""

        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }}
    .card {{ max-width: 540px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
    .header {{ font-size: 20px; font-weight: bold; color: #0f172a; margin-bottom: 8px; }}
    .badge {{ display: inline-block; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 600; color: #ffffff; background: {badge_color}; }}
    .details {{ background: #f8fafc; border-radius: 8px; padding: 16px; margin: 20px 0; }}
    .row {{ display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; }}
    .row:last-child {{ margin-bottom: 0; }}
    .label {{ color: #64748b; }}
    .value {{ font-weight: 600; color: #0f172a; }}
    .amount {{ font-size: 24px; font-weight: 800; color: #0f172a; margin: 12px 0; }}
    .footer {{ font-size: 12px; color: #94a3b8; text-align: center; margin-top: 24px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="badge">Payment Reminder</div>
    <div class="header" style="margin-top: 12px;">Invoice #{invoice_number} {urgency_text}</div>
    <p style="font-size: 14px; color: #475569; margin: 0;">This is an automated notification regarding an upcoming vendor settlement liability.</p>
    
    <div class="details">
      <div class="row">
        <span class="label">Vendor / Supplier:</span>
        <span class="value">{vendor_name}</span>
      </div>
      <div class="row">
        <span class="label">Due Date:</span>
        <span class="value">{due_date_str}</span>
      </div>
      <div class="row">
        <span class="label">Outstanding Amount:</span>
        <span class="value">{currency} {remaining_amount:,.2f}</span>
      </div>
    </div>

    <p style="font-size: 13px; color: #64748b; line-height: 1.5;">
      To record a payment or review line item breakdowns, please log into your SmartInvoice portal.
    </p>

    <div class="footer">
      Sent automatically by SmartInvoice Automation Engine.
    </div>
  </div>
</body>
</html>"""
        return html_content, text_content

    @staticmethod
    def render_overdue_notice(
        invoice_number: str,
        vendor_name: str,
        remaining_amount: Decimal,
        currency: str,
        due_date_str: str,
        days_overdue: int
    ) -> tuple[str, str]:
        """Renders HTML and Text templates for overdue invoice alerts."""
        text_content = f"""SmartInvoice OVERDUE Notice

Invoice: #{invoice_number}
Supplier: {vendor_name}
Outstanding Balance: {currency} {remaining_amount:,.2f}
Due Date: {due_date_str} ({days_overdue} days past due)

Immediate attention is required to settle this overdue liability.
"""

        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #fff1f2; margin: 0; padding: 24px; color: #1e293b; }}
    .card {{ max-width: 540px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #fecdd3; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
    .header {{ font-size: 20px; font-weight: bold; color: #9f1239; margin-bottom: 8px; }}
    .badge {{ display: inline-block; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 600; color: #ffffff; background: #e11d48; }}
    .details {{ background: #fff1f2; border-radius: 8px; padding: 16px; margin: 20px 0; border: 1px solid #ffe4e6; }}
    .row {{ display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; }}
    .row:last-child {{ margin-bottom: 0; }}
    .label {{ color: #881337; }}
    .value {{ font-weight: 700; color: #9f1239; }}
    .footer {{ font-size: 12px; color: #94a3b8; text-align: center; margin-top: 24px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="badge">Action Required: Overdue</div>
    <div class="header" style="margin-top: 12px;">Invoice #{invoice_number} is {days_overdue} Days Overdue</div>
    <p style="font-size: 14px; color: #475569; margin: 0;">An unpaid invoice has exceeded its agreed credit terms.</p>
    
    <div class="details">
      <div class="row">
        <span class="label">Vendor / Supplier:</span>
        <span class="value">{vendor_name}</span>
      </div>
      <div class="row">
        <span class="label">Original Due Date:</span>
        <span class="value">{due_date_str}</span>
      </div>
      <div class="row">
        <span class="label">Pending Balance:</span>
        <span class="value">{currency} {remaining_amount:,.2f}</span>
      </div>
    </div>

    <p style="font-size: 13px; color: #64748b; line-height: 1.5;">
      Please record the settlement reference or contact the vendor to reconcile outstanding payments.
    </p>

    <div class="footer">
      SmartInvoice Accounts Payable Automation
    </div>
  </div>
</body>
</html>"""
        return html_content, text_content


def get_email_provider() -> EmailProvider:
    """Factory creating the configured email provider."""
    provider_type = settings.EMAIL_PROVIDER.lower().strip()
    if provider_type == "smtp":
        return SMTPEmailProvider()
    return ConsoleMockEmailProvider()
