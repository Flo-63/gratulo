"""
===============================================================================
Project   : gratulo
Module    : mail_queue.py
Created   : 15.10.2025
Author    : Florian
Purpose   : [Describe the purpose of this module briefly.]

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

import redis
from app.core.constants import (
    REDIS_URL,
    RATE_LIMIT_MAILS,
    RATE_LIMIT_WINDOW,
)
from app.helpers.mailer import send_mail
from app.helpers.security_helper import anonymize
from app.core.database import SessionLocal
from app.core.models import MailerConfig
from app.core.constants import MAIL_QUEUE_INTERVAL_SECONDS, RATE_LIMIT_WINDOW


logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Redis connection
# -----------------------------------------------------------------------------
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

MAIL_QUEUE_KEY = "mailer:queue"
MAIL_LOG_KEY = "mailer:log"

# -----------------------------------------------------------------------------
# Enqueue Mail
# -----------------------------------------------------------------------------
def enqueue_mail(to_address: str, subject: str, body: str, config_id: Optional[int] = None, bcc_address: Optional[str] = None,):
    """
    Enqueues an email message into a Redis-based mail queue for asynchronous sending.

    This function prepares the email payload with the provided data and pushes it
    to the mail queue for processing. The queued email data includes details such
    as recipient address, subject, body content, optional BCC address, and
    configuration ID, along with the current timestamp at which the email was
    queued.

    Args:
        to_address (str): The email address of the primary recipient.
        subject (str): The subject of the email.
        body (str): The content of the email body.
        config_id (Optional[int]): Optional configuration ID related to the email
            settings or account to use for sending the email.
        bcc_address (Optional[str]): Optional BCC recipient email address.
    """
    payload = {
        "to": to_address,
        "subject": subject,
        "body": body,
        "bcc": bcc_address,
        "config_id": config_id,
        "queued_at": datetime.utcnow().isoformat(),
    }

    redis_client.rpush(MAIL_QUEUE_KEY, json.dumps(payload))
    logger.info(f"[MailQueue] Queued mail to {anonymize(to_address)} ({subject[:40]}...)")

# -----------------------------------------------------------------------------
# Process Queue
# -----------------------------------------------------------------------------
def process_mail_queue(max_batch: int = 40):
    """
    Processes the mail queue to send pending emails in batches.

    This function retrieves pending email jobs from a Redis queue, processes them
    in batches, and sends the emails using the configured mailer setup. If the mailer
    configuration is not available or an error occurs during the process, the function
    handles errors gracefully and logs the necessary information. Unprocessed or failed
    emails are requeued for later attempts.

    Args:
        max_batch (int): The maximum number of emails to process in a single batch. Defaults
            to 40.

    Raises:
        Exception: Catches and logs any exceptions that may occur during email sending.
    """
    pending = redis_client.llen(MAIL_QUEUE_KEY)

    # --- immer next_run_at setzen, auch wenn keine Mail gesendet wird
    next_run_at = (datetime.utcnow() + timedelta(seconds=MAIL_QUEUE_INTERVAL_SECONDS)).isoformat()
    redis_client.set("mailer:next_run_at", next_run_at)

    if pending == 0:
        logger.debug("[MailQueue] No mails in queue.")
        return

    db = SessionLocal()
    try:
        config = db.query(MailerConfig).first()
    finally:
        db.close()

    if not config:
        logger.error("[MailQueue] ❌ Keine Mailer-Konfiguration vorhanden – Versand wird übersprungen.")
        return

    logger.info(f"[MailQueue] Processing up to {max_batch} mails (pending={pending})...")

    for _ in range(min(max_batch, pending)):
        raw = redis_client.lpop(MAIL_QUEUE_KEY)
        if not raw:
            break

        try:
            job = json.loads(raw)
            to_address = job["to"]
            subject = job["subject"]
            body = job["body"]
            bcc = job.get("bcc")

            send_mail(
                config=config,
                to_address=to_address,
                subject=subject,
                body=body,
                bcc_address=bcc,
            )

            _log_success(to_address, subject)

        except Exception as e:
            logger.error(f"[MailQueue] Error sending mail: {e}")
            _log_error(job, str(e))
            # Requeue für späteren Versuch
            redis_client.rpush(MAIL_QUEUE_KEY, raw)
            time.sleep(2)



# -----------------------------------------------------------------------------
# Logging helpers
# -----------------------------------------------------------------------------
def _log_success(address: str, subject: str, bcc: Optional[str] = None):
    """
    Logs the success of a sent email by recording details in a Redis list.

    This function logs details such as the recipient's anonymized address,
    optional bcc anonymized address, subject of the email, and a timestamp
    indicating when the email was sent. The log is stored in Redis for record-keeping
    and consists of at most 500 recent entries, retaining only the most recent records.

    Args:
        address (str): The recipient's email address to be logged.
        subject (str): The subject of the sent email.
        bcc (Optional[str]): An optional bcc email address to be logged if provided.

    """
    entry = {
        "status": "sent",
        "to_hash": anonymize(address),
        "bcc_hash": anonymize(bcc) if bcc else None,
        "subject": subject,
        "timestamp": datetime.utcnow().isoformat(),
    }
    redis_client.lpush(MAIL_LOG_KEY, json.dumps(entry))
    redis_client.ltrim(MAIL_LOG_KEY, 0, 500)  # keep last 500

def _log_error(job: dict, error_msg: str):
    """
    Logs an error entry for a given job to the Redis mail log.

    This function anonymizes sensitive details from the job dictionary and stores
    the error information in a Redis list under the mail log key. It also ensures
    that the list does not grow beyond the specified limit.

    Args:
        job (dict): Dictionary containing details of the job such as "to", "bcc",
            and "subject".
        error_msg (str): Error message to be logged with the job details.
    """
    entry = {
        "status": "error",
        "to_hash": anonymize(job.get("to")),
        "bcc_hash": anonymize(job.get("bcc")) if job.get("bcc") else None,
        "subject": job.get("subject"),
        "error": error_msg,
        "timestamp": datetime.utcnow().isoformat(),
    }
    redis_client.lpush(MAIL_LOG_KEY, json.dumps(entry))
    redis_client.ltrim(MAIL_LOG_KEY, 0, 500)

# -----------------------------------------------------------------------------
# utility
# -----------------------------------------------------------------------------
def get_queue_status() -> dict:
    """
    Gets the current status of the mail queue.

    This function accesses the Redis mailing queue and log to determine the pending
    queued mails, the last sent email's timestamp, rate limit details, and the time
    until the next scheduled run. If any error occurs during this process, a
    fallback status is provided with default values.

    Returns:
        dict: A dictionary containing the following keys:
            - queued (int): Count of pending mails in the mailing queue.
            - rate_limit_remaining (int): Remaining allowed mails for the current
              rate limit window.
            - last_sent (Optional[str]): Timestamp of the last successfully sent
              email. None if unavailable.
            - next_run_in (int): Seconds remaining until the next scheduled run.
              Defaults to the rate limit window if calculation fails.
            - error (Optional[str]): Description of the error if one occurs. None
              if the operation succeeds.
    """
    try:
        pending = redis_client.llen(MAIL_QUEUE_KEY)
        last_log_raw = redis_client.lindex(MAIL_LOG_KEY, 0)

        # Extract info from the latest log entry (optional)
        last_sent = None
        if last_log_raw:
            try:
                entry = json.loads(last_log_raw)
                if entry.get("status") == "sent":
                    last_sent = entry.get("timestamp")
            except Exception:
                pass

        # Dynamische Berechnung des nächsten Laufs
        next_run_in = 0
        try:
            next_run_raw = redis_client.get("mailer:next_run_at")
            if next_run_raw:
                diff = datetime.fromisoformat(next_run_raw) - datetime.utcnow()
                next_run_in = max(int(diff.total_seconds()), 0)
        except Exception:
            next_run_in = RATE_LIMIT_WINDOW  # fallback

        return {
            "queued": pending,
            "rate_limit_remaining": RATE_LIMIT_MAILS,
            "last_sent": last_sent,
            "next_run_in": next_run_in,
        }

    except Exception as e:
        logger.error(f"[MailQueue] Error reading queue status: {e}")
        return {
            "queued": 0,
            "rate_limit_remaining": 0,
            "last_sent": None,
            "next_run_in": 0,
            "error": str(e),
        }


