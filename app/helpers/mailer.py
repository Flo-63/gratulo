"""
===============================================================================
Project   : gratulo
Module    : app/helpers/mailer.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides helper functions for sending emails.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""


import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import logging
import os
import re
from sqlalchemy.sql import extract

from app.core.models import MailerConfig
from app.core.deps import UPLOADS_DIR, STATIC_DIR

logger = logging.getLogger(__name__)

# Regex: suche Bilder aus uploads und static (auch absolute URLs)
CID_PATTERN = re.compile(
    r'<img[^>]+src="(?:https?://[^/]+)?(/(?:uploads|static)/[^"]+)"',
    re.IGNORECASE
)


def prepare_template_for_mail(body: str, msg: MIMEMultipart) -> str:
    """
    Prepares and formats the email body into an HTML template with inline images.

    This function identifies any image paths in the provided email body and attaches
    these images as inline attachments to the email message. The function modifies
    the email body to reference the attached images using content IDs. Images can
    be loaded from specified directories for uploads, static files, or the current
    working directory. If an image file is not found, the function logs a warning
    and continues processing other images.

    Args:
        body (str): The email body potentially containing image paths to embed.
        msg (MIMEMultipart): The email message object to which inline images will be attached.

    Returns:
        str: The formatted HTML email body where image paths are replaced with
             content IDs referring to the inline attachments.
    """
    matches = CID_PATTERN.findall(body)

    for path in matches:
        filename = os.path.basename(path)

        if path.startswith("/uploads/"):
            full_path = os.path.join(UPLOADS_DIR, path[len("/uploads/"):].lstrip("/"))
        elif path.startswith("/static/"):
            full_path = os.path.join(STATIC_DIR, path[len("/static/"):].lstrip("/"))
        else:
            full_path = os.path.join(os.getcwd(), path.lstrip("/"))

        if not os.path.exists(full_path):
            logger.warning(f"⚠️ Bild {filename} nicht gefunden ({full_path})")
            continue

        try:
            with open(full_path, "rb") as f:
                img = MIMEImage(f.read())
                # 💡 Unterschiedliche Prefixes für Uploads und Static erlauben saubere IDs
                cid = path.lstrip("/").replace("/", "_")
                img.add_header("Content-ID", f"<{cid}>")
                msg.attach(img)
                logger.debug(f"📎 Inline-Bild {filename} eingebettet.")

            # Ersetze sowohl Upload- als auch Static-Pfade durch cid:
            pattern = re.compile(
                rf"(?:https?://[^/]+)?{re.escape(path)}",
                re.IGNORECASE
            )
            body = pattern.sub(f"cid:{cid}", body)

        except Exception as e:
            logger.exception(f"❌ Fehler beim Einbetten von {filename}: {e}")

    wrapped = f"""
    <!DOCTYPE html>
    <html>
      <body style="margin:0; padding:0;">
        <table align="center" border="0" cellpadding="0" cellspacing="0" width="600">
          <tr>
            <td style="padding:20px; font-family:Arial, sans-serif; font-size:14px; line-height:20px;">
              {body}
            </td>
          </tr>
        </table>
      </body>
    </html>
    """


    return wrapped


def send_mail(config: MailerConfig, to_address: str, subject: str, body: str) -> None:
    """
    Sends an email using the provided SMTP configuration and details. Supports both
    TLS and SSL for secure connections. The email content can include HTML with
    inline images.

    Args:
        config (MailerConfig): SMTP configuration with server details and credentials.
        to_address (str): Recipient's email address.
        subject (str): Subject of the email.
        body (str): HTML body content of the email.

    Raises:
        RuntimeError: If the email configuration is not provided.
        Exception: For any unforeseen issues during the email sending process.
    """

    if not config:
        raise RuntimeError("❌ Keine Mailer-Konfiguration vorhanden.")

    # multipart/related erlaubt HTML + Bilder
    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = config.from_address
    msg["To"] = to_address

    # multipart/alternative für Text+HTML-Body
    msg_alternative = MIMEMultipart("alternative")
    msg.attach(msg_alternative)

    # HTML vorbereiten (mit inline Bildern und Wrapper)
    html_out = prepare_template_for_mail(body, msg)

    html_part = MIMEText(html_out, "html", "utf-8")
    msg_alternative.attach(html_part)

    try:
        context = ssl.create_default_context()

        if config.use_tls:
            logger.debug(f"Verbinde per STARTTLS mit {config.smtp_host}:{config.smtp_port}")
            with smtplib.SMTP(config.smtp_host, config.smtp_port) as server:
                server.starttls(context=context)
                if config.smtp_user and config.smtp_password:
                    server.login(config.smtp_user, config.smtp_password)
                server.send_message(msg)
        else:
            logger.debug(f"📡 Verbinde ohne TLS mit {config.smtp_host}:{config.smtp_port}")
            with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port, context=context) as server:
                if config.smtp_user and config.smtp_password:
                    server.login(config.smtp_user, config.smtp_password)
                server.send_message(msg)

        logger.info(f"✅ Mail erfolgreich an {to_address} gesendet (Betreff: {subject})")

    except Exception as e:
        logger.exception(f"❌ Fehler beim Senden der Mail an {to_address}: {e}")
        raise
