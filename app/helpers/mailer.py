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
import io
from PIL import Image
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
    Prepares an HTML email template by embedding image files as inline attachments and replacing their references
    in the email body with corresponding Content-ID (cid) references.

    Args:
        body (str): The HTML content of the email body containing image references to be embedded.
        msg (MIMEMultipart): The email message object to which the inline images will be attached.

    Returns:
        str: The modified HTML email body wrapped inside a standard structure with inline images referenced by Content-ID.
    """


    matches = CID_PATTERN.findall(body)

    # Set verhindert Duplikate
    for path in set(matches):
        filename = os.path.basename(path)

        # Pfad-Logik wie gehabt
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
            # -----------------------------------------------------------
            # BILD-OPTIMIERUNG
            # -----------------------------------------------------------
            with Image.open(full_path) as img:
                original_format = img.format  # z.B. JPEG, PNG

                # Maximale Breite definieren (z.B. 800px ist für Mails genug)
                max_width = 800

                if img.width > max_width:
                    # Seitenverhältnis berechnen und verkleinern
                    aspect_ratio = img.height / img.width
                    new_height = int(max_width * aspect_ratio)
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                    logger.debug(f"Bild {filename} verkleinert auf {max_width}x{new_height}")

                # Bild in Bytes speichern statt auf Disk
                img_byte_arr = io.BytesIO()

                # Wenn es ein JPEG ist, Qualität leicht senken (spart massiv Platz)
                if original_format == 'JPEG':
                    img.save(img_byte_arr, format=original_format, quality=80, optimize=True)
                else:
                    # PNGs (z.B. Logos mit Transparenz) einfach so speichern
                    img.save(img_byte_arr, format=original_format)

                img_data = img_byte_arr.getvalue()

            # -----------------------------------------------------------
            # MIME-Erstellung mit den optimierten Daten
            # -----------------------------------------------------------
            mime_img = MIMEImage(img_data)

            # 1. CID säubern und RFC-konform machen (@domain)
            base_id = path.lstrip("/").replace("/", "_").replace(" ", "_")
            cid = f"{base_id}@radtreffcampus.de"

            mime_img.add_header("Content-ID", f"<{cid}>")

            # 2. Inline Disposition
            mime_img.add_header("Content-Disposition", "inline", filename=filename)

            msg.attach(mime_img)
            logger.debug(f"📎 Inline-Bild {filename} eingebettet (Größe: {len(img_data) / 1024:.1f} KB).")

            # HTML Pfad ersetzen
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

def send_mail(config: MailerConfig, to_address: str, subject: str, body: str, bcc_address: str | None = None) -> None:
    """
    Sends an email using the specified configuration.

    This function constructs and sends an email using the provided configuration and
    parameters. It handles both plain and HTML email formats and supports sending
    BCC (Blind Carbon Copy) emails, if provided. The function also manages secure
    connections using TLS or SSL based on the configuration settings.

    Args:
        config (MailerConfig): Configuration object containing email sending parameters
            such as SMTP server details, sender address, and authentication credentials.
        to_address (str): The recipient email address.
        subject (str): The subject line of the email.
        body (str): The email message content, which will be embedded as HTML in the email.
        bcc_address (str | None): An optional BCC recipient email address.

    Raises:
        RuntimeError: If the mailer configuration is missing or invalid.
        Exception: For any errors that occur while sending the email.
    """

    if not config:
        raise RuntimeError("❌ Keine Mailer-Konfiguration vorhanden.")

    #  Rate Limiter prüfen
    wait_for_slot("mailer", limit=40, window=60)

    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = config.from_address
    msg["To"] = to_address
    if bcc_address:
        msg["Bcc"] = bcc_address  # 🟩 Header nur zur Info (nicht für SMTP nötig)

    msg_alt = MIMEMultipart("alternative")
    msg.attach(msg_alt)

    html_out = prepare_template_for_mail(body, msg)
    msg_alt.attach(MIMEText(html_out, "html", "utf-8"))

    # SMTP Versand
    try:
        context = ssl.create_default_context()

        recipients = [to_address]
        if bcc_address:
            recipients.append(bcc_address)  # 🟩 Empfänger explizit ergänzen

        if config.use_tls:
            logger.debug(f"📡 Verbinde per STARTTLS mit {config.smtp_host}:{config.smtp_port}")
            with smtplib.SMTP(config.smtp_host, config.smtp_port) as server:
                server.starttls(context=context)
                if (
                        config.smtp_user
                        and config.smtp_password
                        and config.smtp_user not in ("-", "", None)
                        and config.smtp_password not in ("-", "", None)
                ):
                    server.login(config.smtp_user, config.smtp_password)
                server.sendmail(config.from_address, recipients, msg.as_string())
        else:
            logger.debug(f"📡 Verbinde per SSL mit {config.smtp_host}:{config.smtp_port}")
            with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port, context=context) as server:
                if (
                        config.smtp_user
                        and config.smtp_password
                        and config.smtp_user not in ("-", "", None)
                        and config.smtp_password not in ("-", "", None)
                ):
                    server.login(config.smtp_user, config.smtp_password)
                server.sendmail(config.from_address, recipients, msg.as_string())

        logger.info(
            f"✅ Mail erfolgreich an {mask_email(to_address)}"
            f"{' + BCC ' + mask_email(bcc_address) if bcc_address else ''} gesendet (Betreff: {subject})"
        )

    except Exception as e:
        logger.exception(f"❌ Fehler beim Senden der Mail an {mask_email(to_address)}: {e}")
        raise


