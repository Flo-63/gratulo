"""
===============================================================================
Project   : gratulo
Module    : app/services/mailer_service.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides services related to mailer operations.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

# app/services/mailer_service.py
import logging
import time
from datetime import date, datetime, timezone
from sqlalchemy import extract
from sqlalchemy.orm import Session

from app.core import models
from app.core.models import MailerConfig, MailerJobLog
from app.services.mail_queue import enqueue_mail
from app.helpers.placeholders import resolve_placeholders
from app.helpers.security_helper import anonymize, mask_email

logger = logging.getLogger(__name__)


def execute_job_by_id(job_id: int, logical: date | None = None):
    """
    Executes a mailer job for the specified job ID and logical date.

    This function initiates a database session, determines the logical date if not
    provided, logs the execution process, and invokes the mailer job. Logs errors
    if the execution process fails and ensures the database session is closed
    after execution.

    Args:
        job_id (int): The unique identifier of the job to be executed.
        logical (date | None): The logical date for executing the job. If None,
            the current date will be used.
    """
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        logical = logical or date.today()
        logger.info(f"▶️ Starte Mailer-Job {job_id} für {logical.isoformat()}")
        run_mailer_job(db, job_id, logical)
        logger.info(f"✅ Mailer-Job {job_id} beendet")
    except Exception:
        logger.exception(f"❌ Fehler beim Ausführen des Mailer-Jobs {job_id}")
    finally:
        db.close()


def run_mailer_job(db: Session, job_id: int, logical: date) -> None:
    """
    Executes a mailer job based on the given job ID and logical date, sending emails to
    determined recipients using the specified templates, and logs the execution details
    and results in the database.

    This function queries the database to locate the mailer job and associated template
    using the given job ID. If the template or mailer configuration is missing, or if no
    recipients can be resolved, the function logs appropriate information and terminates.
    For valid jobs with recipients, it attempts to send emails, tracks success and failures,
    computes execution duration, and updates the database with the results.

    Args:
        db (Session): Database session for querying and committing database changes.
        job_id (int): Identifier of the mailer job to be executed.
        logical (date): Logical date associated with the mail execution.
    """
    job = db.query(models.MailerJob).filter(models.MailerJob.id == job_id).first()
    if not job:
        logger.warning(f"[MailerService] Job {job_id} nicht gefunden")
        log_entry = MailerJobLog(
            job_id=job_id,
            executed_at=datetime.now(timezone.utc),
            logical_date=logical,
            status="job_not_found",
            mails_sent=0,
            errors_count=0,
            duration_ms=0,
            details="Job nicht gefunden"
        )
        db.add(log_entry)
        db.commit()
        return

    template = job.template
    if not template:
        logger.warning(f"[MailerService] Job {job.id} hat kein Template")
        log_entry = MailerJobLog(
            job_id=job.id,
            executed_at=datetime.now(timezone.utc),
            logical_date=logical,
            status="no_template",
            mails_sent=0,
            errors_count=0,
            duration_ms=0,
            details="Kein Template vorhanden"
        )
        db.add(log_entry)
        db.commit()
        return

    # ✅ MailerConfig laden
    config = db.query(MailerConfig).first()
    if not config:
        logger.error("❌ Keine Mailer-Konfiguration gefunden.")
        log_entry = MailerJobLog(
            job_id=job.id,
            executed_at=datetime.now(timezone.utc),
            logical_date=logical,
            status="no_config",
            mails_sent=0,
            errors_count=0,
            duration_ms=0,
            details="Keine Mailer-Konfiguration gefunden"
        )
        db.add(log_entry)
        db.commit()
        return

    # Empfänger bestimmen
    recipients = list(_resolve_recipients(db, job, logical))

    # Fallback-Logik bleibt unverändert
    if not recipients and job.group and not job.group.is_default:
        fallback_job = (
            db.query(models.MailerJob)
            .join(models.Group)
            .filter(
                models.MailerJob.selection == job.selection,
                models.Group.is_default == True,
            )
            .first()
        )
        if fallback_job:
            logger.info(f"[MailerService] Fallback auf Standard-Gruppe für Job {job.id} ({job.group.name})")
            job = fallback_job
            template = job.template
            recipients = list(_resolve_recipients(db, job, logical))

    if not recipients:
        logger.info(
            f"[MailerService] Keine Empfänger für Job {job.id} ({job.name}, Gruppe {job.group.name}) am {logical.isoformat()}."
        )
        log_entry = MailerJobLog(
            job_id=job.id,
            executed_at=datetime.now(timezone.utc),
            logical_date=logical,
            status="no_recipients",
            mails_sent=0,
            errors_count=0,
            duration_ms=0,
            details="Keine Empfänger gefunden"
        )
        db.add(log_entry)
        db.commit()
        return

    logger.info(
        f"[MailerService] {len(recipients)} Empfänger für Job {job.id} "
        f"({job.name}, Gruppe {job.group.name}) gefunden."
    )

    subject_fallback = job.name
    mails_sent = 0
    errors = 0
    failed_recipients = []
    start_time = time.perf_counter()

    for member in recipients:
        try:
            html_out = resolve_placeholders(template.content_html, member)
            subject = (job.subject or subject_fallback).strip()

            enqueue_mail(to_address=member.email, subject=subject, body=html_out)
            mails_sent += 1
            logger.info(f"[MailerService] Mail an {mask_email(member.email)} in Queue gestellt.")

        except Exception:
            errors += 1
            failed_recipients.append(member.email)
            logger.exception(f"[MailerService] ❌ Fehler beim Senden an {mask_email(member.email)}")


    duration = int((time.perf_counter() - start_time) * 1000)

    # 📓 Logeintrag in DB
    if errors == 0:
        status = "ok"
    elif mails_sent > 0:
        status = "partial_error"
    else:
        status = "error"

    details = f"{mails_sent} gesendet, {errors} Fehler"
    if failed_recipients:
        details += (
            f" (Fehler bei: "
            f"{', '.join(anonymize(r) for r in failed_recipients[:5])}"
            f"{'...' if len(failed_recipients) > 5 else ''})"
        )

    log_entry = MailerJobLog(
        job_id=job.id,
        executed_at=datetime.now(timezone.utc),
        logical_date=logical,
        status=status,
        mails_sent=mails_sent,
        errors_count=errors,
        duration_ms=duration,
        details=details,
    )
    db.add(log_entry)
    db.commit()



def _resolve_recipients(db: Session, job: models.MailerJob, logical: date):
    """
    Resolves a list of recipients for a given mailer job based on selection criteria
    and group associations.

    This function determines the intended recipients for a given mailer job,
    taking into account selection rules like "all", "birthdate", or "entry" while
    respecting group-specific logic. For the default group, members are processed
    differently than those from other groups, which are checked for conflicts with
    existing jobs.

    Args:
        db (Session): The database session used to query for members and jobs.
        job (models.MailerJob): The mailer job specifying criteria for recipient
            selection.
        logical (date): The logical reference date used for filtering based on
            "birthdate" or "entry" selection criteria.

    Returns:
        list: A list of member entities matching the selection criteria for the
        specified mailer job.
    """

    def apply_selection(query):
        """Filtert Query nach job.selection."""
        if job.selection == "all":
            return query.all()

        if job.selection == "birthdate":
            return query.filter(
                models.Member.birthdate != None,
                extract("month", models.Member.birthdate) == logical.month,
                extract("day", models.Member.birthdate) == logical.day,
            ).all()

        if job.selection == "entry":
            return query.filter(
                models.Member.member_since != None,
                extract("month", models.Member.member_since) == logical.month,
                extract("day", models.Member.member_since) == logical.day,
            ).all()

        logger.warning(f"[MailerService] Unbekannte Selektion '{job.selection}' für Job {job.id}")
        return []

    # ---------------------------
    # Fall A: Gruppe nicht default
    # ---------------------------
    if job.group and not job.group.is_default:
        q = db.query(models.Member).filter(models.Member.group_id == job.group_id)
        return apply_selection(q)

    # ---------------------------
    # Fall B: Gruppe == standard
    # ---------------------------
    recipients = []

    # 1) Alle Mitglieder der Default-Gruppe
    std_q = db.query(models.Member).join(models.Group).filter(models.Group.is_default == True)
    recipients.extend(apply_selection(std_q))

    # 2) Mitglieder anderer Gruppen ohne eigenen Job
    other_groups = db.query(models.Group).filter(models.Group.is_default == False).all()

    for grp in other_groups:
        has_job = (
            db.query(models.MailerJob)
            .filter(
                models.MailerJob.selection == job.selection,
                models.MailerJob.group_id == grp.id,
            )
            .first()
        )
        if not has_job:
            q = db.query(models.Member).filter(models.Member.group_id == grp.id)
            recipients.extend(apply_selection(q))

    return recipients

