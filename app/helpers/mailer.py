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
from redis import Redis
from app.core.constants import REDIS_URL
from app.core.models import MailerConfig
from app.core.deps import UPLOADS_DIR, STATIC_DIR
from app.core.rate_limiter import wait_for_slot
from app.helpers.security_helper import mask_email

redis_client = Redis.from_url(REDIS_URL, decode_responses=True)

logger = logging.getLogger(__name__)

# Regex: suche Bilder aus uploads und static (auch absolute URLs)
CID_PATTERN = re.compile(
    r'<img[^>]+src="(?:https?://[^/]+)?(/(?:uploads|static)/[^"]+)"',
    re.IGNORECASE
)


def prepare_template_for_mail(body: str, msg: MIMEMultipart) -> str:
    """
    Prepares an HTML email body by embedding inline images as content IDs (CIDs) and wrapping
    the email content in standard HTML email formatting. The function parses paths to inline
    images from the email body and attaches them to the provided email message object.

    Args:
        body (str): The HTML content of the email containing paths to inline images.
        msg (MIMEMultipart): The email message object to which the inline images will be attached.

    Returns:
        str: The formatted email body with inline images replaced by their corresponding CIDs.
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
    Sends an email with the specified parameters using the provided mailer
    configuration.

    This function supports sending HTML emails with inline images and also ensures
    rate limiting for mail dispatch. The email can be sent using either TLS or SSL
    as defined in the mailer configuration.

    Args:
        config (MailerConfig): Configuration object containing SMTP details and
            authentication credentials.
        to_address (str): Recipient email address.
        subject (str): Subject of the email.
        body (str): HTML content of the email body.

    Raises:
        RuntimeError: If the mailer configuration is missing.
        Exception: For any error encountered during the email-sending process.
    """

    if not config:
        raise RuntimeError("❌ Keine Mailer-Konfiguration vorhanden.")

    #  Rate Limiter prüfen
    wait_for_slot("mailer", limit=40, window=60)

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

        logger.info(f"✅ Mail erfolgreich an {mask_email(to_address)} gesendet (Betreff: {subject})")

    except Exception as e:
        logger.exception(f"❌ Fehler beim Senden der Mail an {mask_email(to_address)}: {e}")
        raise

