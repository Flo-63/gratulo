"""
===============================================================================
Project   : gratulo
Module    : app/htmx/jobs_htmx.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides HTMX endpoints for managing jobs.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""


from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from datetime import timezone, datetime
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.core.deps import jinja_templates, context
from app.core.auth import require_admin
from app.core import models
from app.core.constants import MAIL_QUEUE_INTERVAL_SECONDS, RATE_LIMIT_WINDOW, SYSTEM_GROUP_ID_ALL, LOCAL_TZ
from app.helpers.cron_helper import cron_to_human
from app.services.job_service import save_job
from app.services.mail_queue import get_queue_status
from app.services.scheduler import get_scheduler


jobs_htmx_router = APIRouter(
    prefix="/htmx/jobs",
    include_in_schema=False,
    dependencies=[Depends(require_admin)],
)


@jobs_htmx_router.get("/list", response_class=HTMLResponse)
def jobs_list(request: Request, db: Session = Depends(get_db)):
    """
    Fetches and renders a list of mailer jobs, sorted by creation date in descending order.
    Adds human-readable cron expressions and resolves group names correctly, including
    the special system group 'Alle Gruppen'.
    """

    # Lade alle Jobs inkl. verknüpfter Gruppen (Vermeidung von Lazy Loading)
    jobs = (
        db.query(models.MailerJob)
        .options(joinedload(models.MailerJob.group))
        .order_by(models.MailerJob.created_at.desc())
        .all()
    )

    # Ergänze menschenlesbare Cron-Strings + Gruppenbezeichnung
    for j in jobs:
        j.cron_human = cron_to_human(j.cron) if j.cron else None

        # Fallback für Systemgruppe
        if j.group_id == SYSTEM_GROUP_ID_ALL:
            j.group_name = "Alle Gruppen"
        elif j.group:
            j.group_name = j.group.name
        else:
            j.group_name = None

    # Übergib ORM-Objekte ans Template
    return jinja_templates.TemplateResponse(
        "partials/jobs_list.html",
        context(request, jobs=jobs, local_tz=LOCAL_TZ)
    )





@jobs_htmx_router.post("", response_class=Response)
async def save_job_endpoint(
    request: Request,
    db: Session = Depends(get_db),

    id: int | None = Form(None),
    name: str = Form(...),
    subject: str | None = Form(None),
    bcc_address: str | None = Form(None),
    template_id: str = Form(...),
    round_template_id: str | None = Form(None),
    mode: str = Form(...),
    once_at: str | None = Form(None),
    selection: str | None = Form(None),
    group_id: str | None = Form(None),
    interval_type: str | None = Form(None),
    time: str | None = Form(None),
    weekday: str | None = Form(None),
    monthday: str | None = Form(None),
):
    """
    Handles the creation or update of a job configuration. Validates input data,
    checks for valid templates, and ensures that a suitable group is assigned.
    Updates selection compatibility, validates selections, saves the job into the
    database, and provides an appropriate response for the client.

    Args:
        request (Request): The HTTP request object.
        db (Session): The database session dependency.
        id (int | None): The ID of the job to be updated, or None for a new job.
        name (str): The name of the job, required.
        subject (str | None): The subject line for the job, optional.
        bcc_address (str | None): The email address for blind carbon copy, optional.
        template_id (str): The ID of the email template, required.
        round_template_id (str | None): The ID of the round template, optional.
        mode (str): The operational mode of the job, required.
        once_at (str | None): A specific timestamp for the job execution, optional.
        selection (str | None): The segment of users to be selected for the job, optional.
        group_id (int | None): The ID of the associated group for the job, optional.
        interval_type (str | None): The interval type for periodic jobs, optional.
        time (str | None): Time of the day for the job if periodic, optional.
        weekday (str | None): The day of the week for weekly recurring jobs, optional.
        monthday (str | None): The day of the month for monthly recurring jobs, optional.

    Raises:
        HTTPException: If template_id is invalid.
        HTTPException: If no valid group is found.
        HTTPException: If the selection is invalid.

    Returns:
        Response: A redirect response with status code 200 upon successful creation or update.
    """

    # 🧩 Validierung Template
    if not template_id or not template_id.isdigit():
        raise HTTPException(status_code=400, detail="Bitte ein gültiges Template auswählen")

    # 🧩 Gruppe prüfen
    if group_id == "all":
        # Spezialfall: "Alle Gruppen" (Systemgruppe)
        if selection != "all":
            raise HTTPException(
                status_code=400,
                detail="Die Auswahl 'Alle Gruppen' ist nur bei Selektion 'Alle Mitglieder' erlaubt."
            )
        resolved_group_id = "all"
    else:
        group = db.query(models.Group).filter(models.Group.id == group_id).first() if group_id else None
        if not group:
            from app.services import group_service
            group = group_service.get_default_group(db)
        if not group:
            raise HTTPException(status_code=400, detail="Keine gültige Gruppe gefunden")

        resolved_group_id = group.id

    # 🧠 MIGRATION / VALIDIERUNG DER SELECTION
    # Abwärtskompatibilität: alte Werte ("birthdate", "entry") auf neue ummappen
    if selection in ("birthdate", "date1_birthdate"):
        selection = "date1"
    elif selection in ("entry", "date2_entry"):
        selection = "date2"

    # Gültige Werte prüfen
    valid_selections = ["all", "date1", "date2"]
    if selection not in valid_selections:
        raise HTTPException(status_code=400, detail=f"Ungültige Selektion: {selection}")

    # 🧩 Job speichern
    save_job(
        db=db,
        id=id,
        name=name,
        subject=subject,
        template_id=int(template_id),
        round_template_id=int(round_template_id) if round_template_id else None,
        mode=mode,
        once_at=once_at,
        selection=selection,   # <-- Jetzt dynamisch (date1/date2)
        interval_type=interval_type,
        time=time,
        weekday=weekday,
        monthday=monthday,
        group_id=resolved_group_id,
        bcc_address=bcc_address,
    )

    # 🧭 Antwort mit Redirect
    return Response(status_code=200, headers={"HX-Redirect": "/jobs"})



@jobs_htmx_router.delete("/{job_id}", response_class=HTMLResponse)
def delete_job(job_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Deletes a job entry by its ID and updates the job list displayed
    to the user. If the specified job does not exist, an HTTP 404
    exception is raised. The updated list includes human-readable
    representations of job schedules and timestamps.

    Args:
        job_id (int): The ID of the job to be deleted.
        request (Request): The HTTP request object.
        db (Session): The database session, acquired through dependency
            injection.

    Raises:
        HTTPException: Raised with status code 404 if the job with the
            specified ID is not found.

    Returns:
        TemplateResponse: Rendered HTML template with the updated job list.
    """
    job = db.query(models.MailerJob).filter(models.MailerJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")

    db.delete(job)
    db.commit()

    jobs = db.query(models.MailerJob).order_by(models.MailerJob.created_at.desc()).all()
    for j in jobs:
        j.cron_human = cron_to_human(j.cron) if j.cron else None

    return jinja_templates.TemplateResponse(
        "partials/jobs_list.html",
        context(request, jobs=jobs, local_tz=LOCAL_TZ)
    )


@jobs_htmx_router.get("/{job_id}/logs", response_class=HTMLResponse)
def job_logs(job_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Fetches and displays logs for a specific mailer job.

    This endpoint retrieves the logs associated with a specified mailer job ID.
    The logs are fetched from the database, ordered by execution time in
    descending order, and limited to the latest 50 entries. The logs'
    execution times are converted to a local timezone if they are in UTC.

    Args:
        job_id (int): The ID of the mailer job for which logs are to be fetched.
        request (Request): The incoming HTTP request object.
        db (Session): The database session dependency.

    Returns:
        HTMLResponse: A rendered template containing the logs for the specified job.
    """
    job = db.query(models.MailerJob).filter(models.MailerJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")

    logs = (
        db.query(models.MailerJobLog)
        .filter(models.MailerJobLog.job_id == job_id)
        .order_by(models.MailerJobLog.executed_at.desc())
        .limit(50)
        .all()
    )

    for log in logs:
        if log.executed_at and log.executed_at.tzinfo is None:
            log.executed_at = log.executed_at.replace(tzinfo=timezone.utc).astimezone(LOCAL_TZ)

    return jinja_templates.TemplateResponse(
        "partials/job_logs_modal.html",
        context(request, job=job, logs=logs, local_tz=LOCAL_TZ)
    )

@jobs_htmx_router.delete("/{job_id}/logs", response_class=HTMLResponse)
def delete_job_logs(job_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Deletes all logs associated with a specific mailer job. The handler renders and
    returns an updated modal without any logs for the selected job.

    Args:
        job_id (int): The ID of the mailer job whose logs are to be deleted.
        request (Request): The HTTP request object containing metadata and context.
        db (Session): The SQLAlchemy database session dependency for querying or
            updating the database.

    Returns:
        HTMLResponse: Rendered HTML content for the updated job logs modal, with
            an empty log list.

    Raises:
        HTTPException: If the specified mailer job does not exist in the database.
    """
    job = db.query(models.MailerJob).filter(models.MailerJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")

    db.query(models.MailerJobLog).filter(models.MailerJobLog.job_id == job_id).delete()
    db.commit()

    # Modal neu rendern (mit leerer Log-Liste)
    return jinja_templates.TemplateResponse(
        "partials/job_logs_modal.html",
        context(request, job=job, logs=[], local_tz=LOCAL_TZ)
    )
# ---------------------------------------------------------------------------
# Mailer Queue Status
# ---------------------------------------------------------------------------

@jobs_htmx_router.get("/queue-status", response_class=HTMLResponse)
def queue_status(request: Request):
    """
    Returns the current queue status as an HTML response.

    This endpoint retrieves the current status of the queue, including the number
    of queued items, remaining rate limit, time until the next run, and the last
    sent event time. The response is formatted as an HTML snippet, ready to be
    used for dynamic updates on the frontend.

    Args:
        request (Request): The request object representing the HTTP request.

    Returns:
        str: An HTML response containing the formatted queue status.
    """
    status = get_queue_status()
    return f"""
    <div id='queue-status' class='bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm text-gray-700 flex justify-between items-center'>
        <div class='flex items-center gap-3'>
            <span>📨 <strong>{status['queued']}</strong> in Queue</span>
            <span>🚀 <strong>{status['rate_limit_remaining']}</strong> frei</span>
            <span>⏱️ Nächster Lauf: {status.get('next_run_in', '?')} s</span>
        </div>
        <div class='text-gray-500 text-xs'>
            Letzter Versand: {status.get('last_sent', '-') or '-'}
        </div>
    </div>
    """


@jobs_htmx_router.get("/job-status", response_class=HTMLResponse)
def job_status(request: Request):
    scheduler = get_scheduler()
    status = get_queue_status() or {}
    status.setdefault("queued", 0)
    status.setdefault("next_run_in", 0)
    status.setdefault("rate_limit_window", RATE_LIMIT_WINDOW)

    # 🔧 Localize 'last_sent' if present
    last_sent = status.get("last_sent")
    if last_sent:
        try:
            if isinstance(last_sent, str):
                dt = datetime.fromisoformat(last_sent.replace("Z", "+00:00"))
            elif isinstance(last_sent, datetime):
                dt = last_sent
            else:
                dt = None

            if dt:
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                status["last_sent_local"] = dt.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")
            else:
                status["last_sent_local"] = "-"
        except Exception:
            status["last_sent_local"] = "-"
    else:
        status["last_sent_local"] = "-"

    # Scheduler-Status
    job = scheduler.get_job("mail_queue_worker")
    next_run = job.next_run_time if job else None
    tz = getattr(scheduler, "timezone", ZoneInfo("UTC"))
    now = datetime.now(tz)

    next_run_in = 0
    if next_run:
        delta = (next_run - now).total_seconds()
        next_run_in = max(0, int(delta))

    return jinja_templates.TemplateResponse(
        "partials/job_status.html",
        context(
            request,
            status={**status, "next_run_in": next_run_in},
            rate_limit_window=RATE_LIMIT_WINDOW,
            mail_queue_interval=MAIL_QUEUE_INTERVAL_SECONDS,
        )
    )



