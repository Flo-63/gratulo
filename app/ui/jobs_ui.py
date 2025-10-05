from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.deps import jinja_templates, context
from app.core import database, models
from app.core.auth import require_admin
from app.services import group_service


jobs_ui_router = APIRouter(prefix="/jobs", include_in_schema=False, dependencies=[Depends(require_admin)])


@jobs_ui_router.get("", response_class=HTMLResponse)
async def jobs_page(request: Request, db: Session = Depends(database.get_db)):
    """
    Handles the HTTP GET request for the jobs page. Fetches all mailer job entries
    from the database and renders them into the 'jobs.html' template.

    :param request: The HTTP request object.
    :type request: Request
    :param db: The database session dependency injected via FastAPI's dependency
        injection system.
    :type db: Session
    :return: An HTML response containing the rendered 'jobs.html' template populated
        with the list of mailer jobs.
    :rtype: HTMLResponse
    """
    jobs = db.query(models.MailerJob).all()
    return jinja_templates.TemplateResponse(
        "jobs.html",
        context(request, jobs=jobs)
    )


@jobs_ui_router.get("/new", response_class=HTMLResponse)
async def new_job_page(request: Request, db: Session = Depends(database.get_db)):
    """
    Handles the GET request for the "/new" endpoint and renders the `job_editor.html`
    template. The method retrieves required data, such as all templates and the
    specific selections in use, and passes these values to the template rendering context.

    :param request: The incoming HTTP request to the endpoint.
    :type request: Request
    :param db: Dependency-injected database session for database operations.
    :type db: Session
    :return: Rendered HTML response for the job editor page.
    :rtype: HTMLResponse
    """
    templates = db.query(models.Template).all()

    # Nur die belegten Selektionen "birthdate" und "entry" abfragen
    used_selections = (
        db.query(models.MailerJob.selection)
        .filter(models.MailerJob.selection.in_(["birthdate", "entry"]))
        .all()
    )
    used_selections = [s[0] for s in used_selections]

    groups = group_service.list_groups(db)

    return jinja_templates.TemplateResponse(
        "job_editor.html",
        context(request, job=None, templates=templates, used_selections=used_selections, groups=groups)
    )

@jobs_ui_router.get("/{job_id}/edit", response_class=HTMLResponse)
async def edit_job_page(request: Request, job_id: int, db: Session = Depends(database.get_db)):
    """
    Fetches the job editing page for a specific job identified by ``job_id``. Retrieves the job details,
    available templates, and the selections that are in use for the job ("birthdate" and "entry" only).
    Returns an HTML response rendering the job editor page with the relevant data.

    :param request: The HTTP request object passed to the route handler.
                    Type: ``Request``
    :param job_id: The unique identifier of the job to be fetched.
                   Type: ``int``
    :param db: The database session dependency used to query the necessary data.
               Type: ``Session``
    :return: An HTML response rendering the job editor page with the job information, template data,
             and filters for used selections.
             Type: ``HTMLResponse``
    :raises HTTPException: Raised with status code 404 if no job with the provided ``job_id`` is found.
    """
    job = db.query(models.MailerJob).filter(models.MailerJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")

    templates = db.query(models.Template).all()

    # Nur die belegten Selektionen "birthdate" und "entry" abfragen
    used_selections = (
        db.query(models.MailerJob.selection)
        .filter(models.MailerJob.selection.in_(["birthdate", "entry"]))
        .all()
    )
    used_selections = [s[0] for s in used_selections]

    groups = group_service.list_groups(db)

    return jinja_templates.TemplateResponse(
        "job_editor.html",
        context(request, job=job, templates=templates, used_selections=used_selections, groups=groups)
    )
