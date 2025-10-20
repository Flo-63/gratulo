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
    Fetches and renders a list of jobs in a human-readable format.

    This function queries the database for all mailer jobs, orders them by the creation time
    in descending order, converts certain fields (such as cron schedules and timestamps) into
    more human-readable formats, and then uses a Jinja2 template to render and return the result.

    Args:
        request: The HTTP request object.
        db: The database session provided by FastAPI dependency injection.

    Returns:
        HTMLResponse: Rendered HTML content displaying the list of jobs.
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
    Handles saving of a job based on provided form data and validates input parameters. Ensures association
    with a valid group and performs required database operations. Returns a response upon successful
    completion.

    Args:
        request: The inbound HTTP request object.
        db: Database session dependency.
        id: Optional job ID to identify an existing job for update.
        name: Name of the job; required form field.
        subject: Optional subject of the job.
        template_id: Template identifier as a form field; required field and validated as an integer.
        mode: Mode of the job (e.g., scheduling type); required form field.
        once_at: Optional string form field for one-time schedule.
        selection: Optional string for selection criteria.
        group_id: Optional group ID for assigning the job to a specific group.
        interval_type: Optional interval type for scheduling, if applicable.
        time: Optional time string for scheduling.
        weekday: Optional weekday string for scheduling weekly intervals.
        monthday: Optional monthday string for scheduling monthly intervals.

    Raises:
        HTTPException: If template_id is invalid or not provided.
        HTTPException: If no valid group is found or specified.

    Returns:
        Response: An HTTP 200 response with a redirect header for successful operation.
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
    )

    # 200 statt 204, damit HX-Redirect zuverlässig funktioniert
    return Response(status_code=200, headers={"HX-Redirect": "/jobs"})


@jobs_htmx_router.delete("/{job_id}", response_class=HTMLResponse)
def delete_job(job_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Deletes a specific job by its ID and returns a response with updated job data.

    This function retrieves a job using its unique ID. If the job is found, it deletes it
    from the database, commits changes, and retrieves the list of all remaining jobs. The
    jobs are formatted for a user-friendly display, including attributes such as the human-readable
    cron string and timezone-aware timestamps. The resulting job list is then rendered using
    a template response.

    Args:
        job_id (int): ID of the job to delete.
        request (Request): An incoming HTTP request object.
        db (Session): Database session dependency injected using FastAPI's Depends.

    Raises:
        HTTPException: Raised when a job with the given ID is not found, with a 404 status code.

    Returns:
        HTMLResponse: A rendered HTML response containing the updated list of jobs.
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
    Retrieve and display job logs.

    This function handles HTTP GET requests to fetch a specific job's logs by its job ID.
    It retrieves the job details and associated logs from the database, formats their
    timestamps to account for correct timezone information, and renders an HTML response
    using a Jinja2 template.

    Args:
        job_id (int): The ID of the job for which logs are to be retrieved.
        request (Request): The HTTP request object.
        db (Session): The SQLAlchemy database session dependency.

    Raises:
        HTTPException: If the job with the given job_id does not exist in the database.

    Returns:
        HTMLResponse: Rendered HTML content containing the job logs, displayed using a
        Jinja2 template.
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
    Deletes the logs associated with the specified job ID and returns a refreshed
    HTML modal with an empty log list for the corresponding job.

    This endpoint removes all logs for a specific job from the database and
    renders an updated template to reflect the deletion.

    Args:
        job_id (int): The unique identifier of the job for which logs need to be
            deleted.
        request (Request): The HTTP request instance.
        db (Session): The database session dependency used to interact with the
            database.

    Raises:
        HTTPException: If the job with the specified job ID is not found in the
            database.

    Returns:
        HTMLResponse: The rendered HTML template response for the modal with an
            empty job log list.
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
    Fetches and renders the current status of the queue including the number of queued items,
    remaining rate limit, time until the next run, and the time of the last dispatch.

    Args:
        request (Request): The incoming HTTP request object.

    Returns:
        str: A formatted HTML string representing the current queue status.
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
    Retrieves and renders the current status of a job queue, including the number of jobs
    queued, the rate limit window, and the interval until the next scheduled job execution.

    This endpoint returns an HTML response with information about mail queue scheduling
    and rate limiting. The job queue status is fetched from the queue manager, and the time
    remaining until the next scheduled job run is calculated. The retrieved data is rendered
    into a template for display.

    Args:
        request (Request): The HTTP request object.

    Returns:
        HTMLResponse: Rendered HTML of the job status page.
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



