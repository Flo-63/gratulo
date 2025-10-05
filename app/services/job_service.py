from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core import models
from app.helpers.cron_helper import build_cron
from app.services.scheduler import register_job


def save_job(
    db: Session,
    id: int | None,
    name: str,
    subject: str | None,
    template_id: int,
    mode: str,                       # "once" | "regular"
    once_at: str | None,             # "%Y-%m-%dT%H:%M"
    selection: str | None,           # "birthdate" | "entry" | "all" | "list"
    interval_type: str | None,       # "daily" | "weekly" | "monthly"
    time: str | None,                # "HH:MM"
    weekday: str | None,             # "0".."6"
    monthday: str | None,            # "1".."28"
    group_id: int | None = None,
) -> models.MailerJob:
    """
    Saves or updates a mailer job in the database and registers it with the scheduler.

    This function manages the creation or update of a mailer job based on the provided
    parameters. Depending on the mode (one-time or regular), it validates inputs
    and constructs the appropriate cron expressions or schedules. It ensures that
    jobs are unique for a specific selection and group combination and registers
    the saved job with the scheduler.

    :param db: Database session used for querying and committing changes.
    :type db: Session
    :param id: The ID of the job (if updating an existing job), or None for a new job.
    :type id: int | None
    :param name: The unique name of the job. Cannot be empty.
    :type name: str
    :param subject: The subject of the emails to be sent by the job. Optional.
    :type subject: str | None
    :param template_id: The ID of the email template to be used by the job.
    :type template_id: int
    :param mode: The mode of the job execution. Either "once" for a one-time job,
        or "regular" for recurring jobs.
    :type mode: str
    :param once_at: The date and time of execution for one-time jobs in the format
        "%Y-%m-%dT%H:%M". Not applicable for regular jobs.
    :type once_at: str | None
    :param selection: Selection criteria for the job. Can be "birthdate", "entry",
        "all", or "list". Must conform to these values for regular jobs.
    :type selection: str | None
    :param interval_type: Specifies the interval type for recurring jobs: "daily",
        "weekly", or "monthly". Not applicable for one-time jobs.
    :type interval_type: str | None
    :param time: The time of day in "HH:MM" format for recurring jobs. Not
        applicable for one-time jobs.
    :type time: str | None
    :param weekday: Day of the week for weekly jobs. Represented as a string value
        in the range "0" (Monday) to "6" (Sunday). Optional for other cases.
    :type weekday: str | None
    :param monthday: Day of the month for monthly jobs. Represented as a string
        value in the range "1" to "28". Optional for other cases.
    :type monthday: str | None
    :param group_name: The name of the group this job is associated with. Defaults
        to "standard".
    :type group_name: str
    :return: The saved mailer job instance after successful database insertion or
        update.
    :rtype: models.MailerJob
    """
    name_clean = (name or "").strip()
    if not name_clean:
        raise HTTPException(status_code=400, detail="Name darf nicht leer sein")

    # Name muss unique sein (freundliche Vorprüfung)
    q = db.query(models.MailerJob).filter(models.MailerJob.name == name_clean)
    if id:
        q = q.filter(models.MailerJob.id != id)
    if q.first():
        raise HTTPException(status_code=400, detail=f"Job-Name '{name_clean}' ist bereits vergeben")

    # Laden oder neu anlegen
    job = db.query(models.MailerJob).get(id) if id else models.MailerJob()
    if id and not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")

    job.name = name_clean
    job.subject = (subject or "").strip() if subject else None
    job.template_id = template_id

    # --- Gruppe prüfen ---

    if group_id:
        group = db.query(models.Group).filter(models.Group.id == group_id).first()
    else:
        from app.services import group_service
        group = group_service.get_default_group(db)

    if not group:
        raise HTTPException(status_code=400, detail="Keine gültige Gruppe gefunden")
    job.group_id = group.id

    # --- Modus ---

    if mode == "once":
        if not once_at:
            raise HTTPException(status_code=400, detail="Zeitpunkt (Einmalig) fehlt")
        try:
            job.once_at = datetime.strptime(once_at, "%Y-%m-%dT%H:%M")
        except ValueError:
            raise HTTPException(status_code=400, detail="Ungültiges Datum/Zeit-Format (Einmalig)")

        # Bei einmaligen Jobs erlaubst du "all" (und später "list")
        job.selection = selection if selection in ("all", "list") else None
        job.cron = None

    elif mode == "regular":
        # Nur birthdatey/entry/all/list zulässig
        if selection not in ("birthdate", "entry", "all", "list"):
            raise HTTPException(status_code=400, detail="Selektion ungültig (birthdate|entry|all|list)")

        # Exklusivität: pro (selection, group) nur 1 Job
        if selection in ("birthdate", "entry"):
            q = db.query(models.MailerJob).filter(
                models.MailerJob.selection == selection,
                models.MailerJob.group_id == group.id
            )
            if id:
                q = q.filter(models.MailerJob.id != id)
            if q.first():
                raise HTTPException(
                    status_code=400,
                    detail=f"Es existiert bereits ein Job mit der Selektion '{selection}' für Gruppe '{group.name}'"
                )
        cron_expr = build_cron(interval_type or "", time or "", weekday, monthday)
        job.cron = cron_expr
        job.selection = selection
        job.once_at = None

    else:
        raise HTTPException(status_code=400, detail="Ausführungsrhythmus ungültig (once|regular)")

    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Job konnte nicht gespeichert werden (DB-Constraint verletzt).")

    db.refresh(job)

    # Nach erfolgreichem Speichern im Scheduler (re-)registrieren
    register_job(job)

    return job

