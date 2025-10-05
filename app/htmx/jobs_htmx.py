# app/htmx/jobs_htmx.py
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
    Fetches the list of mailer jobs from the database, formats the data for human-readable
    use, and renders an HTML response using a Jinja2 template.

    :param request: An instance of the Request object provided by Starlette that contains
        metadata about the HTTP request being processed.
    :param db: A database session object injected via FastAPI's dependency injection,
        providing access to query and interact with the application's database.
    :return: An HTMLResponse containing the rendered template with job data, enriched
        with human-readable information and formatted according to the given template.
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
    """
    Handles the job saving process by validating the input parameters and invoking the save job
    functionality. Ensures correct template validation and response to the client. It also manages
    asynchronous form data retrieval alongside mapping the data within the designated job save logic.

    :param request: FastAPI Request object for accessing HTTP request information.
    :param db: SQLAlchemy session dependency for interacting with the database.
    :param id: Optional job identifier as an integer to update an existing job, or create a new one
        if not provided.
    :param name: Name of the job as a string, mandatory parameter.
    :param template_id: Template identifier as a string, must be numeric. This is a required parameter.
    :param mode: Mode of the job as string, required for defining the job's functional state.
    :param once_at: Optional string representing the time for one-time execution if in one-time mode.
    :param selection: Optional string specifying a custom selection depending on mode or job type.
    :param group_name: Name of the job group as a string, defaults to "standard" if not explicitly
        defined.
    :param interval_type: Optional string defining the type of interval for the job's repetitive nature.
    :param time: Optional string for setting time-specific repeating jobs.
    :param weekday: Optional string for setting specific days of the week for repeating jobs.
    :param monthday: Optional string for setting specific days of the month for repeating jobs.
    :return: Response with HTTP 200 status code along with HX-Redirect header to redirect to
        the "/jobs" route.
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
    Deletes a mailer job by its job ID. If the job is found, it is removed from the
    database and the list of remaining jobs is returned. The jobs list includes
    human-readable cron schedules and timezone-aware timestamps for better
    understanding.

    :param job_id: The ID of the mailer job to delete
    :type job_id: int
    :param request: The FastAPI request object
    :type request: Request
    :param db: The database session to interact with
    :type db: Session
    :return: The updated list of jobs rendered in an HTML template
    :rtype: Response

    :raises HTTPException: If the job with the given `job_id` is not found, a 404
        error is raised
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
    Handles the retrieval and rendering of job logs from the database. The function looks up the job
    specified by its ID and fetches a limited number of logs associated with the job, ordered by the
    execution timestamp in descending order. If the job is not found, an exception is raised. For
    logs with missing timezone information, their timestamps are converted to a local timezone.

    :param job_id: The unique identifier of the job whose logs are to be fetched.
    :param request: The current request object.
    :param db: The database session dependency.
    :return: An `HTMLResponse` containing the rendered job logs template.
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

    print(f"Fetched {len(logs)} logs for job {job_id}")

    for l in logs:
        print(l.id, l.executed_at, l.status, l.mails_sent, l.errors_count, l.details)

    return jinja_templates.TemplateResponse(
        "partials/job_logs_modal.html",
        context(request, job=job, logs=logs, local_tz=LOCAL_TZ)
    )
@jobs_htmx_router.delete("/{job_id}/logs", response_class=HTMLResponse)
def delete_job_logs(job_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Deletes logs of a specific mailer job from the database.

    This function handles deletion of all associated logs for the provided job
    based on the given job ID. If the job with the specified ID is not found,
    an HTTP 404 error is raised. After deletion, it returns a re-rendered modal
    template with an updated, empty log list.

    :param job_id: ID of the job for which logs are to be deleted.
    :type job_id: int
    :param request: The request instance for the action.
    :type request: Request
    :param db: The database session dependency injected using `Depends`.
    :type db: Session
    :return: A rendered template response containing the updated job logs modal.
    :rtype: HTMLResponse
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
