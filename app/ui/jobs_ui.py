"""
===============================================================================
Project   : gratulo
Module    : app/ui/jobs_ui.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides UI endpoints for managing jobs
    for managing jobs.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""


from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.deps import jinja_templates, context
from app.core.constants import LABELS_DISPLAY
from app.core import database, models
from app.core.auth import require_admin
from app.services import group_service

jobs_ui_router = APIRouter(prefix="/jobs", include_in_schema=False, dependencies=[Depends(require_admin)])


@jobs_ui_router.get("", response_class=HTMLResponse)
async def jobs_page(request: Request, db: Session = Depends(database.get_db)):
    """
    Handles the rendering of the jobs page by querying the database for all
    available jobs and providing them to the template for display.

    Args:
        request (Request): The incoming HTTP request object.
        db (Session): The database session dependency provided via `Depends`.

    Returns:
        HTMLResponse: Rendered HTML page showing all available jobs.
    """
    jobs = db.query(models.MailerJob).all()
    return jinja_templates.TemplateResponse(
        "jobs.html",
        context(request, jobs=jobs)
    )


@jobs_ui_router.get("/new", response_class=HTMLResponse)
async def new_job_page(request: Request, db: Session = Depends(database.get_db)):
    """
    Handles HTTP GET request to render the new job page.

    This function serves the new job creation page by querying the necessary data
    such as templates, groups, and allowed selections from the database. It uses
    Jinja2 templates for rendering the HTML response.

    Args:
        request (Request): The incoming HTTP request object.
        db (Session): The database session dependency.

    Returns:
        HTMLResponse: The rendered HTML response containing the new job creation page.
    """
    templates = db.query(models.Template).all()
    groups = group_service.list_groups(db)

    # Dynamisch erlaubte Selektionen prüfen
    valid_selections = ["date1", "date2"]
    used_selections = (
        db.query(models.MailerJob.selection)
        .filter(models.MailerJob.selection.in_(valid_selections))
        .all()
    )
    used_selections = [s[0] for s in used_selections]

    return jinja_templates.TemplateResponse(
        "job_editor.html",
        context(
            request,
            job=None,
            templates=templates,
            used_selections=used_selections,
            groups=groups,
            labels=LABELS_DISPLAY,
        ),
    )

@jobs_ui_router.get("/{job_id}/edit", response_class=HTMLResponse)
async def edit_job_page(request: Request, job_id: int, db: Session = Depends(database.get_db)):
    """
    Handles the rendering of the job editing page for the given job ID. Fetches the
    job details, templates, and selection data required to edit a job configuration.

    Args:
        request (Request): The HTTP request object.
        job_id (int): The unique identifier of the job to be edited.
        db (Session): The database session used to fetch job data.

    Returns:
        HTMLResponse: A rendered HTML response for the job editor template.

    Raises:
        HTTPException: If the job with the given job ID is not found in the database.
    """
    job = db.query(models.MailerJob).filter(models.MailerJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")

    templates = db.query(models.Template).all()
    groups = group_service.list_groups(db)

    valid_selections = ["date1", "date2"]
    used_selections = (
        db.query(models.MailerJob.selection)
        .filter(models.MailerJob.selection.in_(valid_selections))
        .all()
    )
    used_selections = [s[0] for s in used_selections]

    return jinja_templates.TemplateResponse(
        "job_editor.html",
        context(
            request,
            job=job,
            templates=templates,
            used_selections=used_selections,
            groups=groups,
            labels=LABELS_DISPLAY,
        ),
    )
