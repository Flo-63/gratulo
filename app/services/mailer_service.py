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
from app.core.constants import is_round_birthday, is_round_entry, LABELS, SYSTEM_GROUP_ID_ALL

logger = logging.getLogger(__name__)


def execute_job_by_id(job_id: int, logical: date | None = None):
    """
    Executes a mailer job based on the provided job ID and logical date. This function initializes a
    database session, logs the start of the job, runs the job processing logic, and logs its completion
    or any exception encountered during execution. If no logical date is provided, the current date is used.

    Args:
        job_id (int): The identifier of the mailer job to be executed.
        logical (date | None): The date for job execution logic. Defaults to the current date if not specified.
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
    Executes a mailer job and logs the outcome in the database.

    This function attempts to execute a mailer job identified by `job_id` using the database session `db`.
    It first validates the presence of the mailer job, associated template, and mail configuration.
    If recipients are resolved, it processes them, rendering the email content and sending it out.
    The progress and results (success or errors) of the operation are recorded as a log entry.

    Args:
        db: A database session used for querying and persisting job execution data.
        job_id: The unique identifier of the mailer job to execute.
        logical: The logical execution date of the mailer job, usually used for filtering.

    Raises:
        None

    Returns:
        None
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

    # MailerConfig laden
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
            tmpl_to_use, info, extra_ctx = _select_template(job, member, logical)
            if info:
                logger.debug(f"[MailerService] {info} für {mask_email(member.email)} verwendet.")

            # Context für Platzhalter kombinieren
            html_out = resolve_placeholders(tmpl_to_use.content_html, member, **extra_ctx)

            subject = (job.subject or subject_fallback).strip()
            enqueue_mail(to_address=member.email, subject=subject, body=html_out, bcc_address=job.bcc_address)
            mails_sent += 1


        except Exception:
            errors += 1
            failed_recipients.append(member.email)
            logger.exception(f"[MailerService] Fehler bei {mask_email(member.email)} mit Template {tmpl_to_use.name}")


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

def _select_template(job, member, logical):
    """
    Selects the appropriate template and populates the context for a given job and member selection.

    This function determines the appropriate template to use based on the job's parameters and the
    member's attributes, specifically those mapped by the predefined selection criteria. It supports
    handling anniversaries or events by calculating or retrieving relevant dates and contextual
    information.

    Args:
        job: A job object containing template specifications and selection criteria.
        member: A member object with associated attributes such as dates.
        logical: A logical object providing date and time context.

    Returns:
        tuple: A tuple where the first element is either the original or selected template,
        the second is a textual description of the selection (if applicable),
        and the third is a dictionary with context for the selected template.

    """
    tmpl = job.template
    ctx = {}

    # 🟩 Mapping: date1/date2 → echte Model-Felder
    field_map = {
        "date1": "birthdate",
        "date2": "member_since",
    }

    if job.selection not in field_map:
        return tmpl, None, ctx

    field_name = field_map[job.selection]
    label_type = LABELS.get(f"{job.selection}_type", "ANNIVERSARY").upper()
    field = getattr(member, field_name, None)

    if not field:
        return tmpl, None, ctx

    # Anniversary → jährliche Jubiläen mit Rundenerkennung
    if label_type == "ANNIVERSARY":
        years = logical.year - field.year - (
            (logical.month, logical.day) < (field.month, field.day)
        )
        ctx["years"] = years

        if job.round_template:
            # Verwende Jubiläumsvorlage nur bei runden Jahren
            if is_round_birthday(years) or is_round_entry(years):
                return job.round_template, f"Runde Jubiläumsvorlage ({years} Jahre)", ctx

    # Event → einmalige Ereignisse, kein Jubiläum
    elif label_type == "EVENT":
        ctx["event_date"] = field.strftime("%d.%m.%Y")

    return tmpl, None, ctx

def _calculate_age(birthdate: date, ref_date: date) -> int:
    """
    Calculates the age based on the given birth date and a reference date.

    This function computes the age of a person or entity by comparing the provided
    birth date with the reference date. It accounts for whether the current
    reference date is before or after the birth date in the current year.

    Args:
        birthdate (date): The birth date to calculate the age from.
        ref_date (date): The reference date from which to calculate the age.

    Returns:
        int: The calculated age based on the input dates.
    """
    return ref_date.year - birthdate.year - (
        (ref_date.month, ref_date.day) < (birthdate.month, birthdate.day)
    )

def _calculate_membership_years(entry_date: date, ref_date: date) -> int:
    """
    Calculates the total membership years by determining the difference between
    the reference date and the entry date while accounting for incomplete years.

    Args:
        entry_date (date): The date the membership started.
        ref_date (date): The reference date to calculate the membership years.

    Returns:
        int: The total number of completed membership years.
    """
    return ref_date.year - entry_date.year - (
        (ref_date.month, ref_date.day) < (entry_date.month, entry_date.day)
    )

def _resolve_recipients(db: Session, job: models.MailerJob, logical: date):
    """
    Resolves the recipients for a mailing job based on group and selection criteria.

    This function determines the list of recipients for a mailing job by applying
    group-specific or default group rules. Selection criteria based on the job's
    configuration such as specific date or member-related attributes are dynamically
    applied. Additionally, the function handles cases where some groups do not
    have their own associated mailing jobs.

    Args:
        db (Session): Database session used to query member and group information.
        job (models.MailerJob): The mailing job containing configuration such as selection criteria,
            group information, and other settings.
        logical (date): The logical date that serves as a reference for filtering members,
            anniversaries, or other criteria.

    Returns:
        List[models.Member]: A list of members who fulfill the criteria specified
            by the job configuration.
    """
    def apply_selection(query):
        """Filtert Query dynamisch nach job.selection und Label-Typ."""
        if job.selection == "all":
            return query.all()

        # 🟩 Mapping: date1/date2 auf echte Model-Felder
        field_map = {
            "date1": "birthdate",
            "date2": "member_since",
        }

        if job.selection not in field_map:
            logger.warning(f"[MailerService] Unbekannte Selektion '{job.selection}' für Job {job.id}")
            return []

        field_name = field_map[job.selection]
        label_type = LABELS.get(f"{job.selection}_type", "ANNIVERSARY").upper()
        field = getattr(models.Member, field_name, None)

        if not field:
            logger.warning(f"[MailerService] Feld {field_name} existiert nicht im Member-Modell.")
            return []

        if label_type == "ANNIVERSARY":
            return query.filter(
                field.isnot(None),
                extract("month", field) == logical.month,
                extract("day", field) == logical.day,
            ).all()

        elif label_type == "EVENT":
            # Monatliche / jährliche Erinnerungsfrequenz (z. B. 6, 12, 24)
            freq_months = int(LABELS.get(f"{job.selection}_frequency_months", 12))

            # Wir berechnen alle Mitglieder, deren Datum so alt ist wie freq_months
            target_year = logical.year
            target_month = logical.month
            target_day = logical.day

            return query.filter(
                field.isnot(None),
                extract("year", field) * 12 + extract("month", field) + freq_months ==
                target_year * 12 + target_month,
                extract("day", field) == target_day
            ).all()

        return []

    # ---------------------------
    # Fall 0: "Alle Gruppen" aktiv (group_id is None)
    # ---------------------------
    if job.group is SYSTEM_GROUP_ID_ALL:
        logger.info(f"[MailerService] Job {job.id}: 'Alle Gruppen' aktiviert → sende an alle Gruppen.")
        q = db.query(models.Member)
        return apply_selection(q)


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


