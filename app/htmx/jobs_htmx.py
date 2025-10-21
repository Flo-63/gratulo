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

from app.core.database import get_db
from app.core.deps import jinja_templates, context
from app.core.auth import require_admin
from app.core import models
from app.core.constants import LOCAL_TZ
from app.helpers.cron_helper import cron_to_human
from app.services.job_service import save_job
from app.services.mail_queue import get_queue_status
from app.core.constants import MAIL_QUEUE_INTERVAL_SECONDS, RATE_LIMIT_WINDOW
from app.services.scheduler import get_scheduler


jobs_htmx_router = APIRouter(
    prefix="/htmx/jobs",
    include_in_schema=False,
    dependencies=[Depends(require_admin)],
)


@jobs_htmx_router.get("/list", response_class=HTMLResponse)
def jobs_list(request: Request, db: Session = Depends(get_db)):
    """
    Fetches and displays the list of mailer jobs in a human-readable format. It retrieves job data
    from the database, processes it to include necessary details such as timestamps formatted to the
    local timezone, human-readable cron expressions, and other job attributes. The processed data is
    rendered using an HTML template.

    Args:
        request (Request): The HTTP request object.
        db (Session): The database session dependency for executing queries.

    Returns:
        HTMLResponse: Rendered HTML template containing the list of mailer jobs with processed attributes.
    """

    jobs = db.query(models.MailerJob).order_by(models.MailerJob.created_at.desc()).all()

    jobs_with_human = []
    for j in jobs:
        jobs_with_human.append({
            "id": j.id,
            "subject": j.subject,
            "name": j.name,
            "selection": j.selection,
            "group_id": j.group_id,
            "group_name": j.group.name if j.group else None,
            "cron": j.cron,
            "cron_human": cron_to_human(j.cron) if j.cron else None,
            "once_at": j.once_at.astimezone(LOCAL_TZ) if j.once_at else None,
            "created_at": j.created_at.astimezone(LOCAL_TZ) if j.created_at else None,
            "updated_at": j.updated_at.astimezone(LOCAL_TZ) if j.updated_at else None,
            "template": j.template,
            "round_template": j.round_template,  # 🔹 Falls du sie in der Tabelle brauchst
            "bcc_address": j.bcc_address,        # ✅ NEU: BCC-Adresse an Template übergeben
        })

    return jinja_templates.TemplateResponse(
        "partials/jobs_list.html",
        context(request, jobs=jobs_with_human, local_tz=LOCAL_TZ)
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
    group_id: int | None = Form(None),
    interval_type: str | None = Form(None),
    time: str | None = Form(None),
    weekday: str | None = Form(None),
    monthday: str | None = Form(None),
):
    """
    Handles the creation or update of a job through an HTTP POST request. The endpoint validates input
    data, retrieves or creates a group if necessary, and passes the processed information to the save_job
    function to persist the job into the database.

    Args:
        request: The HTTP request object.
        db: The database session dependency.
        id: The ID of the job (used for updates). Defaults to None.
        name: The name of the job. This is a required field.
        subject: The subject for the job e-mails. Optional and defaults to None.
        bcc_address: The BCC address for the job e-mails. Optional and defaults to None.
        template_id: The ID of the template to associate with the job. This is a required field and must
            be a valid ID.
        round_template_id: The ID of the round template (if any). Optional and defaults to None.
        mode: The mode for the job (e.g., scheduling mode). This is a required field.
        once_at: The specific date-time value for one-time execution of the job. Optional and defaults
            to None.
        selection: The selection criteria or configuration for the job. Optional and defaults to None.
        group_id: The ID of the group. If not provided, a default group is retrieved or created.
            Defaults to None.
        interval_type: The type of interval used for scheduling the job. Optional and defaults to None.
        time: The specific time for scheduling the job. Optional and defaults to None.
        weekday: The weekday for scheduling the job (if applicable). Optional and defaults to None.
        monthday: The day of the month for scheduling (if applicable). Optional and defaults to None.

    Raises:
        HTTPException: Raised with status code 400 for invalid input (such as missing template ID or
            invalid group).
    """

    # Validierung Template
    if not template_id or not template_id.isdigit():
        raise HTTPException(status_code=400, detail="Bitte ein gültiges Template auswählen")

    group = db.query(models.Group).filter(models.Group.id == group_id).first() if group_id else None
    if not group:
        from app.services import group_service
        group = group_service.get_default_group(db)

    if not group:
        raise HTTPException(status_code=400, detail="Keine gültige Gruppe gefunden")

    save_job(
        db=db,
        id=id,
        name=name,
        subject=subject,
        template_id=int(template_id),
        round_template_id=int(round_template_id) if round_template_id else None,
        mode=mode,
        once_at=once_at,
        selection=selection,
        interval_type=interval_type,
        time=time,
        weekday=weekday,
        monthday=monthday,
        group_id=group.id,
        bcc_address=bcc_address,
    )

    # 200 statt 204, damit HX-Redirect zuverlässig funktioniert
    return Response(status_code=200, headers={"HX-Redirect": "/jobs"})


@jobs_htmx_router.delete("/{job_id}", response_class=HTMLResponse)
def delete_job(job_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Deletes a specific job from the database by its ID and returns the updated jobs list.
    If the job with the given ID does not exist, raises an HTTP 404 error.

    Args:
        job_id (int): The unique identifier of the job to delete.
        request (Request): The incoming HTTP request object.
        db (Session): The database session dependency.

    Returns:
        HTMLResponse: An updated template response containing the list of remaining jobs.
    """
    job = db.query(models.MailerJob).filter(models.MailerJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")

    db.delete(job)
    db.commit()

    jobs = db.query(models.MailerJob).order_by(models.MailerJob.created_at.desc()).all()

    jobs_with_human = []
    for j in jobs:
        jobs_with_human.append({
            "id": j.id,
            "name": j.name,
            "selection": j.selection,
            "group_id": j.group_id,
            "group_name":j.group.name if j.group else None,
            "cron": j.cron,
            "cron_human": cron_to_human(j.cron) if j.cron else None,
            "once_at": j.once_at.astimezone(LOCAL_TZ) if j.once_at else None,
            "created_at": j.created_at.astimezone(LOCAL_TZ) if j.created_at else None,
            "updated_at": j.updated_at.astimezone(LOCAL_TZ) if j.updated_at else None,
            "template": j.template,
        })

    return jinja_templates.TemplateResponse(
        "partials/jobs_list.html",
        context(request, jobs=jobs_with_human, local_tz=LOCAL_TZ)
    )


@jobs_htmx_router.get("/{job_id}/logs", response_class=HTMLResponse)
def job_logs(job_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Fetch and render the logs of a specific mailer job.

    This function retrieves the logs of a specific mailer job identified by the provided
    job ID from the database. The logs are ordered by execution time in descending order
    and limited to the most recent 50 entries. It then converts any naive datetime objects
    to timezone-aware ones using a local timezone. Finally, it renders the logs in an
    HTML response using a Jinja2 template.

    Args:
        job_id (int): The identifier of the mailer job whose logs are to be fetched.
        request (Request): The HTTP request object.
        db (Session): The database session dependency.

    Returns:
        HTMLResponse: An HTML response rendering the job logs and related information.

    Raises:
        HTTPException: Raised with status code 404 if the specified mailer job is not found.
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
    Deletes all logs associated with a specific job, provided by its job_id. If the job
    identified by the provided job_id does not exist, it raises an HTTPException with
    status 404.

    Args:
        job_id (int): The identifier of the job whose logs need to be deleted.
        request (Request): The current HTTP request instance.
        db (Session): The database session to interact with the database.

    Raises:
        HTTPException: Raised with status code 404 if the job specified by job_id is not
            found in the database.

    Returns:
        HTMLResponse: A response rendering the updated modal with an empty log list.
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
    Fetches and displays the current status of the queue, including the number of
    messages in the queue, rate limit remaining, next run timing, and the last
    dispatch timestamp.

    Args:
        request: The current HTTP request.

    Returns:
        str: HTML content displaying the queue status information.
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
    """
    Retrieves and displays the current job status, including queue details and the next
    run time for scheduled jobs.

    Args:
        request (Request): The HTTP request object required to render the template.

    Returns:
        HTMLResponse: Rendered HTML response displaying job status details.
    """

    scheduler = get_scheduler()
    status = get_queue_status() or {}
    status.setdefault("queued", 0)
    status.setdefault("next_run_in", 0)
    status.setdefault("rate_limit_window", RATE_LIMIT_WINDOW)

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



