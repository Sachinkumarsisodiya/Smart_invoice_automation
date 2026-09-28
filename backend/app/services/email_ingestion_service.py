import io
import os
import imaplib
import email
import hashlib
from email.header import decode_header
from typing import List, Dict, Any, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import UploadFile

from app.config import settings
from app.core.logging import logger
from app.models.user import User, UserRole
from app.models.invoice import Invoice
from app.models.notification import Notification, NotificationType
from app.services.invoice_service import InvoiceService
from app.services.extraction_service import ExtractionService


class EmailIngestionService:
    """Automated IMAP Email Ingestion Service for SmartInvoice.
    Connects to email servers (e.g., Gmail via SSL), scans for emails with invoice attachments,
    and ingests them into the processing pipeline.
    """

    @classmethod
    def _decode_header_str(cls, header_val: Optional[str]) -> str:
        if not header_val:
            return ""
        decoded_parts = decode_header(header_val)
        result = []
        for text, encoding in decoded_parts:
            if isinstance(text, bytes):
                try:
                    result.append(text.decode(encoding or "utf-8", errors="ignore"))
                except Exception:
                    result.append(text.decode("latin1", errors="ignore"))
            else:
                result.append(str(text))
        return "".join(result)

    @classmethod
    async def sync_mailbox(cls, db: Session, user: Optional[User] = None) -> Dict[str, Any]:
        """Connects to IMAP server, checks for emails with attachments,
        processes new invoices, and stores them in SmartInvoice.
        """
        if not settings.IMAP_ENABLED:
            return {
                "success": False,
                "message": "IMAP email ingestion is currently disabled in configuration.",
                "fetched_count": 0,
                "invoices": [],
                "errors": []
            }

        if not settings.IMAP_USER or not settings.IMAP_PASSWORD:
            return {
                "success": False,
                "message": "IMAP credentials not configured. Please set IMAP_USER and IMAP_PASSWORD (Google App Password) in .env.",
                "fetched_count": 0,
                "invoices": [],
                "errors": []
            }

        target_user = user
        if not target_user:
            target_user = (
                db.query(User).filter(User.email == settings.IMAP_USER).first()
                or db.query(User).filter(User.role == UserRole.ADMIN).first()
            )

        if not target_user:
            return {
                "success": False,
                "message": "No admin user found to assign ingested invoices.",
                "fetched_count": 0,
                "invoices": [],
                "errors": []
            }

        mail = None
        processed_invoices: List[Dict[str, Any]] = []
        errors: List[str] = []

        try:
            logger.info(f"Connecting to IMAP server {settings.IMAP_HOST}:{settings.IMAP_PORT} as {settings.IMAP_USER}...")
            
            if settings.IMAP_USE_SSL:
                mail = imaplib.IMAP4_SSL(settings.IMAP_HOST, settings.IMAP_PORT)
            else:
                mail = imaplib.IMAP4(settings.IMAP_HOST, settings.IMAP_PORT)

            mail.login(settings.IMAP_USER, settings.IMAP_PASSWORD)
            mail.select(settings.IMAP_FOLDER)

            # 1. Search UNSEEN first
            status, messages = mail.search(None, "UNSEEN")
            email_ids = messages[0].split() if (status == "OK" and messages and messages[0]) else []

            # 2. If no UNSEEN messages, inspect recent messages from ALL to ensure no read attachment was missed
            if not email_ids:
                status, all_messages = mail.search(None, "ALL")
                if status == "OK" and all_messages and all_messages[0]:
                    all_ids = all_messages[0].split()
                    # Inspect the latest 20 emails
                    email_ids = all_ids[-20:]

            if not email_ids:
                return {
                    "success": True,
                    "message": f"No new invoice attachments found in {settings.IMAP_USER}.",
                    "fetched_count": 0,
                    "invoices": [],
                    "errors": []
                }

            logger.info(f"Inspecting {len(email_ids)} emails for invoice attachments...")
            allowed_extensions = {".pdf", ".png", ".jpg", ".jpeg"}

            for e_id in reversed(email_ids):
                try:
                    res, msg_data = mail.fetch(e_id, "(RFC822)")
                    if res != "OK" or not msg_data or not msg_data[0]:
                        continue

                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    subject = cls._decode_header_str(msg.get("Subject"))
                    sender = cls._decode_header_str(msg.get("From"))

                    for part in msg.walk():
                        filename = part.get_filename() or part.get_param("name")

                        if filename:
                            filename = cls._decode_header_str(filename)
                            ext = os.path.splitext(filename)[1].lower()

                            if ext in allowed_extensions:
                                payload = part.get_payload(decode=True)
                                if not payload:
                                    continue

                                # Check duplicate by payload hash to prevent double ingestion
                                sha256_hash = hashlib.sha256(payload).hexdigest()
                                existing = db.query(Invoice).filter(Invoice.document_hash == sha256_hash).first()
                                if existing:
                                    logger.info(f"Skipping attachment {filename} - already ingested as invoice #{existing.invoice_number}")
                                    continue

                                file_obj = io.BytesIO(payload)
                                upload_file = UploadFile(
                                    file=file_obj,
                                    filename=filename,
                                    headers={"content-type": part.get_content_type() or "application/pdf"}
                                )

                                try:
                                    # 1. Handle invoice upload
                                    invoice, _ = InvoiceService.handle_upload(
                                        file=upload_file,
                                        db=db,
                                        current_user=target_user
                                    )

                                    # 2. Trigger async extraction pipeline directly
                                    extracted_invoice = await ExtractionService.process_invoice_extraction(
                                        db=db,
                                        invoice_id=invoice.id,
                                        current_user=target_user
                                    )

                                    confidence = getattr(extracted_invoice, 'extraction_confidence', 0) or 0
                                    is_flagged = extracted_invoice.extraction_status in ("FAILED", "MANUAL") or extracted_invoice.total_amount <= Decimal("0.00")

                                    # 3. Create Notification
                                    notif = Notification(
                                        user_id=target_user.id,
                                        title="⚠️ Invoice Flagged for Review" if is_flagged else "New Verified Invoice Ingested",
                                        message=f"Invoice #{extracted_invoice.invoice_number} from '{sender}' (Total: INR {extracted_invoice.total_amount}). Extracted with confidence {confidence}%.",
                                        type=NotificationType.WARNING if is_flagged else NotificationType.SUCCESS,
                                        is_read=False
                                    )
                                    db.add(notif)
                                    db.commit()

                                    processed_invoices.append({
                                        "invoice_id": str(extracted_invoice.id),
                                        "invoice_number": extracted_invoice.invoice_number,
                                        "filename": filename,
                                        "sender": sender,
                                        "subject": subject,
                                        "confidence_score": str(confidence)
                                    })
                                    logger.info(f"Successfully ingested email invoice #{extracted_invoice.invoice_number} from {sender}")

                                except Exception as upload_err:
                                    db.rollback()
                                    err_msg = f"Failed to ingest attachment {filename}: {str(upload_err)}"
                                    logger.error(err_msg)
                                    errors.append(err_msg)

                    if settings.IMAP_MARK_SEEN:
                        try:
                            mail.store(e_id, "+FLAGS", "\\Seen")
                        except Exception:
                            pass

                except Exception as msg_err:
                    err_msg = f"Error processing message ID {e_id}: {str(msg_err)}"
                    logger.error(err_msg)
                    errors.append(err_msg)

            count = len(processed_invoices)
            msg_str = (
                f"Synced {count} new invoice{'s' if count != 1 else ''} from {settings.IMAP_USER}."
                if count > 0
                else f"Mailbox {settings.IMAP_USER} is up to date (0 new invoices found)."
            )

            return {
                "success": True,
                "message": msg_str,
                "fetched_count": count,
                "invoices": processed_invoices,
                "errors": errors
            }

        except imaplib.IMAP4.error as imap_err:
            err_msg = f"IMAP Authentication error for {settings.IMAP_USER}: {str(imap_err)}"
            logger.error(err_msg)
            return {
                "success": False,
                "message": err_msg + " (Tip: Ensure you generated a 16-character Google App Password in Security settings)",
                "fetched_count": 0,
                "invoices": [],
                "errors": [err_msg]
            }
        except Exception as ex:
            err_msg = f"Unexpected error syncing mailbox: {str(ex)}"
            logger.error(err_msg)
            return {
                "success": False,
                "message": err_msg,
                "fetched_count": 0,
                "invoices": [],
                "errors": [err_msg]
            }
        finally:
            if mail:
                try:
                    mail.close()
                except Exception:
                    pass
                try:
                    mail.logout()
                except Exception:
                    pass

