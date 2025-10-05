# app/services/mailer_service.py
import logging
import time
from datetime import date, datetime, timezone
from sqlalchemy import extract
from sqlalchemy.orm import Session

from app.core import models
from app.core.models import MailerConfig, MailerJobLog
from app.helpers.mailer import send_mail
from app.helpers.placeholders import resolve_placeholders

logger = logging.getLogger(__name__)


def execute_job_by_id(job_id: int, logical: date | None = None):
    """
    Executes a mailer job identified by its job ID. This function initializes a database
    session, logs the start and completion of the job, and passes the supplied parameters
    to the `run_mailer_job` function for processing. If any exception occurs during the
    execution, the error is logged without halting the execution of the script. The database
    connection is closed properly under all circumstances.

    :param job_id: Integer representing the unique identifier for the mailer job to execute.
    :type job_id: int

    :param logical: Optional date object specifying the logical date for the job execution.
                    If no date is provided, it defaults to the current date.
                    Accepted type is either `date` or `None`.
    :type logical: date or None

    :return: None
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
    Executes a mailer job by processing recipients, resolving placeholders in templates,
    and sending emails. Logs the operation results, including success, errors, and performance
    metrics, to the database.

    :param db: Database session object used for querying and updating the database
    :param job_id: Identifier of the mailer job to be executed
    :param logical: Logical date associated with the mailer job execution
    :return: None
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

            send_mail(config=config, to_address=member.email, subject=subject, body=html_out)
            mails_sent += 1
            logger.info(f"[MailerService] ✅ Mail an {member.email} gesendet.")
        except Exception:
            errors += 1
            failed_recipients.append(member.email)
            logger.exception(f"[MailerService] ❌ Fehler beim Senden an {member.email}")

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
        details += f" (Fehler bei: {', '.join(failed_recipients[:5])}{'...' if len(failed_recipients) > 5 else ''})"

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
    Resolves recipients for a mailing job based on the selection criteria
    and group configuration in the given job.

    This function determines a set of recipients filtered by the specific
    criteria in the mailing job and logical date, separating members into
    default and non-default groups.

    The implementation handles:
    1. Members of a non-default group (specific job group is provided).
    2. Members of the default group and members of other groups that do not have
       an overlapping job with the same selection criteria.

    :param db: Database session used for querying purposes
    :type db: Session
    :param job: The mailer job containing the selection criteria and group details
    :type job: models.MailerJob
    :param logical: Logical date for filtering recipients, typically corresponding to
                    certain anniversaries or events
    :type logical: date
    :return: A list of Member objects filtered according to the criteria defined in the job
    :rtype: list[models.Member]
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

