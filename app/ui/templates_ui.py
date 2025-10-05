"""
===============================================================================
Project   : gratulo
Module    : app/ui/templates_ui.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides UI endpoints for managing templates.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""


from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from starlette.responses import HTMLResponse
from app.core.database import get_db
from app.core.deps import jinja_templates, context
from app.services import template_service

templates_ui_router = APIRouter(prefix="/templates", include_in_schema=False)


@templates_ui_router.get("", response_class=HTMLResponse)
async def templates_page(request: Request, db: Session = Depends(get_db)):
    """
    Handles the HTTP GET request for the templates page and renders the templates.html view.

    This function retrieves a list of templates from the database using the provided
    template_service. The retrieved templates are then passed to the Jinja2 template
    renderer to generate the HTML response that is returned to the client.

    Args:
        request (Request): The HTTP request object containing context and metadata for
            the incoming request.
        db (Session): The database session dependency injected to facilitate database
            operations.

    Returns:
        HTMLResponse: A rendered HTML response containing the templates page.
    """
    templates = template_service.get_templates(db)
    return jinja_templates.TemplateResponse(
        "templates.html",
        context(request, templates=templates)
    )


@templates_ui_router.get("/new", response_class=HTMLResponse)
async def new_template_page(request: Request):
    """
    Handles the `/new` endpoint and renders the `template_editor.html` page.

    This function generates an HTML response using the Jinja2 template engine.
    It is mapped to the `/new` route and is designed to display the template
    editor interface.

    Args:
        request: The HTTP request object.

    Returns:
        HTMLResponse: A response containing the rendered HTML content for
        the template editor page.
    """
    return jinja_templates.TemplateResponse(
        "template_editor.html",
        context(request, template=None)
    )


@templates_ui_router.get("/{template_id}/edit", response_class=HTMLResponse)
async def edit_template_page(request: Request, template_id: int, db: Session = Depends(get_db)):
    """
    Handles the display of the template editor page for editing a specific template.

    This function retrieves the template from the database using the provided
    template ID and renders the template editor page. If the template is not
    found, an HTTP 404 exception is raised.

    Args:
        request (Request): The HTTP request object containing metadata about the
            request.
        template_id (int): The ID of the template to be edited.
        db (Session): Database session dependency used to query the
            database.

    Raises:
        HTTPException: If the template with the given ID is not found, a 404 HTTP
            exception is raised.

    Returns:
        HTMLResponse: Renders and returns the template editor HTML page.
    """
    template = template_service.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template nicht gefunden")

    return jinja_templates.TemplateResponse(
        "template_editor.html",
        context(request, template=template)
    )
