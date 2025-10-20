"""
===============================================================================
Project   : gratulo
Module    : app/ui/main_ui.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides the main user interface routes and functionality
            for the Gratulo application.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""


from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from app.core.deps import jinja_templates, context
from app.core.auth import require_admin


main_ui_router = APIRouter(include_in_schema=False)


# ---------------------------
# Root -> Login wenn nicht eingeloggt
# ---------------------------
@main_ui_router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """
    Handles the root route of the application.

    Checks if the user is logged in by verifying the presence of the "user"
    key in the session. If the user is not logged in, redirects them to
    the login page. If the user is logged in, redirects them to the admin
    page.

    Args:
        request (Request): The incoming HTTP request.

    Returns:
        RedirectResponse: A redirect to the login page if the user is not
            logged in, or a redirect to the admin page if the user is
            authenticated.
    """
    if "user" not in request.session:
        return RedirectResponse("/login", status_code=303)
    return RedirectResponse("/admin", status_code=303)


# ---------------------------
# Admin-Seite
# ---------------------------
@main_ui_router.get("/admin", response_class=HTMLResponse)
async def admin(request: Request):
    """
    Handles the admin page endpoint.

    This asynchronous function serves as the route handler for the admin page. It first
    checks if the user is authenticated by verifying the presence of the "user" key
    in the session of the incoming request. If the user is not authenticated, it
    redirects them to the login page. Otherwise, it renders the "admin.html" template
    using Jinja2.

    Args:
        request (Request): The incoming HTTP request object, which contains session
            data and other relevant information.

    Returns:
        RedirectResponse: Redirects unauthenticated users to the login page with
            a status code of 303.
        TemplateResponse: Renders the "admin.html" page for authenticated users.
    """
    if "user" not in request.session:
        return RedirectResponse("/login", status_code=303)
    return jinja_templates.TemplateResponse("admin.html", context(request))


