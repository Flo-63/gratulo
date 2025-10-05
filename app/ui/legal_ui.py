"""
===============================================================================
Project   : gratulo
Module    : app/ui/legal_ui.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides UI endpoints to present legal information

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""



from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.deps import jinja_templates, context

legal_ui_router = APIRouter(
    prefix="/legal",
    tags=["Legal"],
    include_in_schema=False
)

@legal_ui_router.get("/license", response_class=HTMLResponse)
def show_license(request: Request):
    """
    Handles the rendering of the license page for the legal user interface.

    This function is executed when the route "/license" is accessed, and it
    returns an HTML response rendering the "legal/license.html" template
    with the specified page title provided in the context.

    Args:
        request (Request): The incoming HTTP request object containing
            metadata about the client request.

    Returns:
        TemplateResponse: An HTTP response containing the rendered HTML
            template for the license page.
    """
    return jinja_templates.TemplateResponse(
        "legal/license.html",
        context(request, page_title="Lizenzbedingungen")
    )

@legal_ui_router.get("/privacy", response_class=HTMLResponse)
def show_privacy(request: Request):
    """
    Handles rendering of the privacy policy page.

    Args:
        request (Request): The request object containing HTTP request details.

    Returns:
        HTMLResponse: The rendered HTML response for the privacy policy page.
    """
    return jinja_templates.TemplateResponse(
        "legal/privacy.html",
        context(request, page_title="Datenschutzerklärung")
    )

@legal_ui_router.get("/terms", response_class=HTMLResponse)
def show_terms(request: Request):
    """
    Handles a GET request to show the terms and conditions page.

    This function renders the terms and conditions page using a Jinja2 template
    and includes the page title as part of the context.

    Args:
        request (Request): The incoming HTTP request object.

    Returns:
        HTMLResponse: A rendered HTML response for the terms and conditions page.
    """
    return jinja_templates.TemplateResponse(
        "legal/terms.html",
        context(request, page_title="Nutzungsbedingungen")
    )
