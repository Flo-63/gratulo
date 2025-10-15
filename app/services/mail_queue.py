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
def enqueue_mail(to_address: str, subject: str, body: str, config_id: Optional[int] = None):
    """Queues an email message to be processed asynchronously.

    This function prepares a payload with the email details and enqueues it into
    a Redis queue for further processing. It also logs the queuing operation,
    anonymizing sensitive information for security purposes.

    Args:
        to_address: Recipient's email address.
        subject: Email subject line.
        body: Body content of the email.
        config_id: Optional ID for configuration or additional context.
    """
    payload = {
        "to": to_address,
        "subject": subject,
        "body": body,
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
    Processes the mail queue by sending a limited number of emails from the queue
    and sets the next run time.

    This function checks the number of pending emails in the queue and attempts
    to process up to the specified `max_batch` number of emails. For each email,
    it retrieves the email job details, sends the email, and logs the success or
    failure. If an error occurs, the email is re-queued for a later attempt. The
    function also sets the next scheduled runtime for the mail queue's processing,
    even if no emails are processed.

    Args:
        max_batch (int): The maximum number of emails to process in a single run.
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

            send_mail(
                config=config,
                to_address=to_address,
                subject=subject,
                body=body,
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
def _log_success(address: str, subject: str):
    """
    Logs a successful email delivery to the Redis logging system.

    This function creates a log entry for a successfully sent email, including details
    like the anonymized recipient address, the email subject, and the timestamp of
    the delivery. The entry is pushed into a Redis list and maintains only the latest
    500 log entries in the list.

    Args:
        address (str): The recipient's email address.
        subject (str): The email's subject line.
    """
    entry = {
        "status": "sent",
        "to_hash": anonymize(address),
        "subject": subject,
        "timestamp": datetime.utcnow().isoformat(),
    }
    redis_client.lpush(MAIL_LOG_KEY, json.dumps(entry))
    redis_client.ltrim(MAIL_LOG_KEY, 0, 500)  # keep last 500

def _log_error(job: dict, error_msg: str):
    """
    Logs an error entry to the mail log with job details and error message.

    The function anonymizes sensitive job data before creating a log entry
    and appends this entry to a Redis list. It ensures the log stores only
    the most recent 500 entries.

    Args:
        job (dict): A dictionary containing details of the job which failed.
            Expected keys include "to" and "subject".
        error_msg (str): A description of the error that occurred.
    """
    entry = {
        "status": "error",
        "to_hash": anonymize(job.get("to")),
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
    Retrieves the current status of the mail queue from a Redis database.

    The function communicates with Redis to fetch data about the number of emails
    pending in the queue, details of the last sent email, and the time remaining
    for the next scheduled mail dispatch. If an error occurs during these
    operations, a fallback dictionary containing default values and the error
    message is returned.

    Returns:
        dict: A dictionary containing the status of the mail queue with the
        following keys:
        - "queued" (int): The number of emails currently in the queue.
        - "rate_limit_remaining" (int): The number of emails that can still be sent
          within the current rate limit.
        - "last_sent" (Optional[str]): The timestamp of the most recently sent
          email, if applicable.
        - "next_run_in" (int): The time remaining in seconds until the next
          scheduled mail dispatch.
        - "error" (Optional[str]): An error message, if an exception occurs during
          the operation; otherwise, omitted.
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


