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
from app.core import database, models
from app.core.auth import require_admin
from app.services import group_service

jobs_ui_router = APIRouter(prefix="/jobs", include_in_schema=False, dependencies=[Depends(require_admin)])


@jobs_ui_router.get("", response_class=HTMLResponse)
async def jobs_page(request: Request, db: Session = Depends(database.get_db)):
    """
    Handles the retrieval and rendering of the jobs page.

    This function is responsible for fetching all jobs stored in the database
    and rendering them into the "jobs.html" template. It is designed to be an
    async endpoint for use with an HTTP GET request. The `HTMLResponse` is used
    to provide an HTML page back to the user.

    Args:
        request (Request): The incoming HTTP request.
        db (Session): A database session dependency, used to query the required data.

    Returns:
        TemplateResponse: The response rendered from the "jobs.html" template, including
        the queried list of jobs.
    """
    jobs = db.query(models.MailerJob).all()
    return jinja_templates.TemplateResponse(
        "jobs.html",
        context(request, jobs=jobs)
    )


@jobs_ui_router.get("/new", response_class=HTMLResponse)
async def new_job_page(request: Request, db: Session = Depends(database.get_db)):
    """
    Handles the request to render the new job creation page. This endpoint generates
    an HTML page that allows users to create a new job, providing context data such
    as available templates, used selections, and groups.

    Args:
        request (Request): The HTTP request object containing metadata about the request.
        db (Session): The database session dependency used to query the database.

    Returns:
        HTMLResponse: The rendered HTML page with the context data necessary for
        creating a new job.
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
    Handles rendering the job editing page for a specific job ID.

    This function retrieves the job details, available templates, used selections,
    and groups from the database. It then renders an HTML response using the
    specified template and context data.

    Args:
        request (Request): The incoming HTTP request object.
        job_id (int): The unique identifier of the job to be edited.
        db (Session): The database session dependency.

    Returns:
        HTMLResponse: The rendered HTML response containing the job editing page.

    Raises:
        HTTPException: Raised if the specified job ID does not exist in the database.
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
