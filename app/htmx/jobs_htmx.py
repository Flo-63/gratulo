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

from datetime import timezone

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import jinja_templates, context
from app.core.auth import require_admin
from app.core import models
from app.core.constants import LOCAL_TZ
from app.helpers.cron_helper import cron_to_human
from app.services.job_service import save_job


jobs_htmx_router = APIRouter(
    prefix="/htmx/jobs",
    include_in_schema=False,
    dependencies=[Depends(require_admin)],
)


@jobs_htmx_router.get("/list", response_class=HTMLResponse)
def jobs_list(request: Request, db: Session = Depends(get_db)):
    """
    Fetches and displays a list of mailer jobs from the database. The jobs are ordered
    by their creation time in descending order. Each job's details are processed to
    enhance the representation (e.g., converting cron expressions to human-readable
    format, adjusting timestamps to local timezone), and the enriched data is used
    to render an HTML template for displaying the list.

    Args:
        request (Request): The HTTP request object.
        db (Session): The database session dependency used to query the database.

    Returns:
        HTMLResponse: Renders a template with the list of jobs and their enriched
        details.
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
    template_id: str = Form(...),  # kommt als String
    mode: str = Form(...),
    once_at: str | None = Form(None),
    selection: str | None = Form(None),
    group_id: int | None = Form(None),
    interval_type: str | None = Form(None),
    time: str | None = Form(None),
    weekday: str | None = Form(None),
    monthday: str | None = Form(None),
):
    """Handles the creation or update of a job entity and saves it to the database.

    This endpoint processes the form data submitted through an HTML form and performs
    necessary validations, including validating the provided template ID and group
    selection. If no group is explicitly provided, it defaults to a pre-defined group.
    Upon successful validation, the job entity is saved to the database.

    Raises:
        HTTPException: If the template ID is invalid or no valid group is found.
        HTTPException: Returns with a status code 400 when validations fail.
        HTTPException: Generated if Group cannot be resolved or retrieved.

    Args:
        request (Request): The incoming HTTP request object.
        db (Session): The database session dependency injection for ORM operations.
        id (int | None): The ID of the job to update; None if creating a new job.
        name (str): The name of the job.
        subject (str | None): The subject line for the job; optional.
        template_id (str): The ID of the template associated with the job, as a string.
        mode (str): The mode of the job, such as 'once' or 'recurring'.
        once_at (str | None): The specific timestamp for a one-time job creation, optional.
        selection (str | None): Additional job selection parameter, optional.
        group_id (int | None): The group ID associated with the job, optional.
        interval_type (str | None): Type of interval, such as 'weekly' or 'monthly', optional.
        time (str | None): The time of the job execution, optional.
        weekday (str | None): The day of the week for execution, optional.
        monthday (str | None): The day of the month for execution, optional.

    Returns:
        Response: A response object with status code 200 and optional redirect headers.
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
    Deletes a job with the given job ID and updates the job list rendered in the
    template. The function handles deletion of a job entry in the database, and it then fetches
    all remaining jobs from the database to update the response.

    Args:
        job_id (int): ID of the job to be deleted.
        request (Request): FastAPI request object.
        db (Session): Database session dependency instance for executing queries.

    Returns:
        HTMLResponse: Rendered HTML template with the updated list of jobs.

    Raises:
        HTTPException: If the job with the specified ID does not exist in the database.
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
    Fetch and display logs for a specific job.

    This endpoint retrieves the logs related to a specific job identified by its job ID.
    It queries the database to obtain job logs limited to the most recent 50 entries.
    The logs are processed to ensure proper time zone handling before being displayed,
    and the information is returned as an HTML response.

    Args:
        job_id (int): The unique identifier of the job for which logs are being requested.
        request (Request): The HTTP request object to pass into the template context.
        db (Session): The database session dependency to use for database queries.

    Returns:
        HTMLResponse: An HTML response rendering the job logs modal.
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
    """Deletes the logs associated with a specific job.

    This function deletes all log entries related to a given job by its `job_id`
    from the database. If the specified job does not exist, it raises an HTTP 404
    error. After deleting the logs, it re-renders the modal with an empty log list.

    Args:
        job_id (int): The ID of the job whose logs are to be deleted.
        request (Request): The HTTP request object containing request details.
        db (Session): The database session used for querying and updating records.

    Returns:
        HTMLResponse: A rendered HTML response for the updated modal with an empty
        log list.

    Raises:
        HTTPException: If the job with the given `job_id` is not found, an
        exception with a 404 status code is raised.
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
