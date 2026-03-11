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
    Executes a mailer job by its ID with an optional logical date. This function ensures
    the database session is handled properly, logs the start and completion of the job,
    and logs any exceptions encountered during execution.

    Args:
        job_id (int): The ID of the mailer job to execute.
        logical (date | None): The logical execution date of the mailer job. Defaults
            to the current date if not provided.
    """
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        logical = logical or date.today()
        logger.debug(f"▶️ Starte Mailer-Job {job_id} für {logical.isoformat()}")
        run_mailer_job(db, job_id, logical)
        logger.debug(f"✅ Mailer-Job {job_id} beendet")
    except Exception as e:
        logger.error(f"❌ Fehler beim Ausführen des Mailer-Jobs {job_id}: {type(e).__name__}")
        logger.debug(f"❌ Exception Details für Job {job_id}: {str(e)}", exc_info=True)
    finally:
        db.close()

def run_mailer_job(db: Session, job_id: int, logical: date) -> None:
    """
    Executes a mailer job by fetching relevant configuration, resolving recipients, and processing
    emails for each recipient based on the specified template or fallback logic. Logs the execution
    results, errors, and duration accordingly.

    Args:
        db (Session): The database session used for querying and updating the mailer job, configuration,
            and recipient information, as well as persisting log entries.
        job_id (int): The identifier of the mailer job to be executed.
        logical (date): The logical date used during the execution, typically representing the target
            date for which emails are being sent.

    Raises:
        Exception: If any errors occur while processing individual recipients during the email sending
            workflow. These errors are internally logged and do not interrupt the processing of
            subsequent recipients.
    """
    job = db.query(models.MailerJob).filter(models.MailerJob.id == job_id).first()
    if not job:
        logger.error(f"❌ [MailerService] Job {job_id} nicht gefunden")
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
        logger.error(f"❌ [MailerService] Job {job.id} ({job.name}) hat kein Template")
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
        logger.error(f"❌ [MailerService] Keine Mailer-Konfiguration gefunden - Job {job.id} abgebrochen")
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
            logger.debug(f"[MailerService] Fallback auf Standard-Gruppe für Job {job.id} ({job.group.name})")
            job = fallback_job
            template = job.template
            recipients = list(_resolve_recipients(db, job, logical))

    if not recipients:
        logger.debug(
            f"[MailerService] Keine Empfänger für Job {job.id} ({job.name}) am {logical.isoformat()}"
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

    logger.debug(
        f"[MailerService] {len(recipients)} Empfänger für Job {job.id} ({job.name}) gefunden"
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


        except Exception as e:
            errors += 1
            failed_recipients.append(member.email)
            logger.warning(f"⚠️ [MailerService] Fehler bei Mail-Versand an {mask_email(member.email)}: {type(e).__name__}")
            logger.debug(f"❌ [MailerService] Details: Template {tmpl_to_use.name}, Exception: {str(e)}", exc_info=True)


    duration = int((time.perf_counter() - start_time) * 1000)

    # 📓 Logeintrag in DB
    if errors == 0:
        status = "ok"
        logger.info(f"✅ [MailerService] Job {job.id} ({job.name}): {mails_sent} Mails versendet")
        logger.debug(f"[MailerService] Job {job.id} Dauer: {duration}ms")
    elif mails_sent > 0:
        status = "partial_error"
        logger.warning(f"⚠️ [MailerService] Job {job.id} ({job.name}): {mails_sent} Mails versendet, {errors} Fehler")
        logger.debug(f"[MailerService] Job {job.id} Dauer: {duration}ms")
    else:
        status = "error"
        logger.error(f"❌ [MailerService] Job {job.id} ({job.name}): Fehlgeschlagen - 0 Mails versendet, {errors} Fehler")

    details = f"{mails_sent} gesendet, {errors} Fehler"
    if failed_recipients:
        details += (
            f" (Fehler bei: "
            f"{', '.join(anonymize(r) for r in failed_recipients[:5])}"
            f"{'...' if len(failed_recipients) > 5 else ''})"
        )
        logger.debug(f"[MailerService] Job {job.id} fehlgeschlagene Empfänger: {', '.join(anonymize(r) for r in failed_recipients)}")

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
    logger.debug(f"[MailerService] Job {job.id}: DB-Log geschrieben (Status: {status})")

def _select_template(job, member, logical):
    """
    Select and process a template based on the specified job, member, and logical input.

    This function maps specific selection keys to member attributes, determines the type of label
    to be applied (ANNIVERSARY or EVENT), calculates anniversaries, or processes specific events
    based on the job's criteria. If applicable, it returns a special round-anniversary template.
    Otherwise, a default template with context data is returned.

    Args:
        job: The job object containing template, selection, and other relevant information.
        member: The member object with attributes used for mapping and processing.
        logical: A logical date or time reference used for anniversary calculations or other operations.

    Returns:
        A tuple containing:
        - The selected template or round-anniversary template (if conditions are met).
        - A string describing the selected template (if applicable, e.g., round anniversary).
        - A context dictionary with additional metadata such as years or event date.
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
    Calculates the age of a person based on their birthdate and a reference date.

    This function is used to determine the difference in years between the provided
    birthdate and the reference date. It adjusts the age calculation if the
    reference date occurs before the person's birthday in the same year.

    Args:
        birthdate (date): The birthdate of the person for whom age is being calculated.
        ref_date (date): The reference date used to calculate the age.

    Returns:
        int: The calculated age in full years.
    """
    return ref_date.year - birthdate.year - (
        (ref_date.month, ref_date.day) < (birthdate.month, birthdate.day)
    )

def _calculate_membership_years(entry_date: date, ref_date: date) -> int:
    """
    Calculates the number of full membership years between entry_date and ref_date.

    This function determines the full years of membership between the entry date and
    the reference date, considering if the anniversary has passed in the current year.

    Args:
        entry_date: The date the membership started.
        ref_date: The reference date for calculating the membership duration.

    Returns:
        int: The number of full membership years.
    """
    return ref_date.year - entry_date.year - (
        (ref_date.month, ref_date.day) < (entry_date.month, entry_date.day)
    )

def _resolve_recipients(db: Session, job: models.MailerJob, logical: date):
    """
    Resolves recipients for a mailing job based on the provided criteria.

    The function determines the list of recipients for a mailing job, depending
    on the job's selection type, associated group, and logical date. It supports
    various scenarios, such as selecting all members, filtering members based
    on specific criteria like anniversaries or events, and handling group-based
    recipients.

    Args:
        db (Session): Database session used for querying members and groups.
        job (models.MailerJob): Details of the mailing job containing
            selection criteria and group information.
        logical (date): A logical date used for filtering members (e.g.,
            anniversaries or events).

    Returns:
        List[models.Member]: List of members who match the criteria of the
            mailing job.
    """

    # 🟩 Sonderfall: "Alle Mitglieder"
    if job.selection == "all":
        # SYSTEM-GRUPPE → wirklich alle Mitglieder
        if job.group_id == SYSTEM_GROUP_ID_ALL:
            logger.info(
                f"[MailerService] Job {job.id}: SYSTEM_GROUP_ID_ALL → sende an ALLE Mitglieder aller Gruppen."
            )
            return db.query(models.Member).all()

        # Bestimmte Gruppe → nur Mitglieder dieser Gruppe
        if job.group_id:
            group_name = job.group.name if job.group else f"ID {job.group_id}"
            logger.info(
                f"[MailerService] Job {job.id}: 'Alle Mitglieder' in Gruppe {group_name}."
            )
            return (
                db.query(models.Member)
                .filter(models.Member.group_id == job.group_id)
                .all()
            )

        # Fallback: keine Gruppe gesetzt
        logger.warning(f"[MailerService] Job {job.id}: Keine Gruppe gesetzt → keine Empfänger.")
        return []

    # 🟨 Mapping für Selektionen (z. B. Geburtstag, Eintritt, Jubiläum)
    field_map = {
        "date1": "birthdate",
        "date2": "member_since",
    }

    if job.selection not in field_map:
        logger.warning(f"[MailerService] Unbekannte Selektion '{job.selection}' für Job {job.id}")
        return []

    field_name = field_map[job.selection]
    field = getattr(models.Member, field_name, None)

    if not field:
        logger.warning(f"[MailerService] Feld {field_name} existiert nicht im Member-Modell.")
        return []

    label_type = LABELS.get(f"{job.selection}_type", "ANNIVERSARY").upper()

    # Funktion für wiederverwendbare Filterung
    def apply_selection(query):
        """Filtert Query nach label_type (ANNIVERSARY oder EVENT)."""
        if label_type == "ANNIVERSARY":
            return query.filter(
                field.isnot(None),
                extract("month", field) == logical.month,
                extract("day", field) == logical.day,
            ).all()

        elif label_type == "EVENT":
            freq_months = int(LABELS.get(f"{job.selection}_frequency_months", 12))
            target_year, target_month, target_day = logical.year, logical.month, logical.day

            return query.filter(
                field.isnot(None),
                extract("year", field) * 12 + extract("month", field) + freq_months ==
                target_year * 12 + target_month,
                extract("day", field) == target_day
            ).all()

        return []

    # 🟦 Fall 1: Systemgruppe → alle Mitglieder aller Gruppen
    if job.group_id == SYSTEM_GROUP_ID_ALL:
        logger.info(
            f"[MailerService] Job {job.id}: SYSTEM_GROUP_ID_ALL aktiv → sende an alle Gruppen."
        )
        q = db.query(models.Member)
        return apply_selection(q)

    # 🟧 Fall 2: Spezifische Gruppe
    if job.group:
        q = db.query(models.Member).filter(models.Member.group_id == job.group_id)
        logger.info(
            f"[MailerService] Job {job.id}: Wende Selektion '{job.selection}' auf Gruppe {job.group.name} an."
        )
        return apply_selection(q)

    # 🟥 Fall 3: Standard-Gruppe → erweitert um Gruppen ohne eigenen Job
    recipients = []

    # 1️⃣ Mitglieder der Default-Gruppe
    std_q = db.query(models.Member).join(models.Group).filter(models.Group.is_default == True)
    recipients.extend(apply_selection(std_q))

    # 2️⃣ Mitglieder anderer Gruppen ohne eigenen Job
    other_groups = db.query(models.Group).filter(models.Group.is_default == False).all()
    for grp in other_groups:
        has_job = (
            db.query(models.MailerJob)
            .filter(models.MailerJob.selection == job.selection, models.MailerJob.group_id == grp.id)
            .first()
        )
        if not has_job:
            q = db.query(models.Member).filter(models.Member.group_id == grp.id)
            recipients.extend(apply_selection(q))

    return recipients




