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


from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.deps import jinja_templates, context
from app.core.database import get_db
from app.core.models import MailerConfig
from app.core.constants import INITIAL_ADMIN_USER, INITIAL_PASSWORD

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


# ---------------------------
# Login-Seite
# ---------------------------
@main_ui_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    """
    Handles the rendering of the login page and determines the authentication method to
    be used based on environment variables or database configuration.

    Args:
        request (Request): The current HTTP request object.
        db (Session): A database session object, provided via dependency injection.

    Returns:
        HTMLResponse: The rendered HTML template for the login page. If no valid
        authentication method is configured, an error page is displayed with a
        status code of 400.
    """
    config = db.query(MailerConfig).first()
    using_env_login = False

    # 1. Prüfen: ENV hat Vorrang (nur wenn beide nicht leer sind)
    if INITIAL_ADMIN_USER and INITIAL_PASSWORD:
        auth_method = "email"
        using_env_login = True
        print("Verwende ENV-basierte Login-Daten (auth_method=email)")
    # 2. Sonst DB-Konfiguration nutzen
    elif config and config.auth_method:
        auth_method = config.auth_method
        print(f"Verwende DB-Konfiguration (auth_method={auth_method})")
    else:
        auth_method = None
        print("❌ Keine Auth-Methode gefunden (ENV & DB leer)")

    # 3. Wenn nichts da → Fehler
    if not auth_method:
        print("Zeige Fehlermeldung an Benutzer")
        return jinja_templates.TemplateResponse(
            "login.html",
            context(request, error_message="❌ Keine Authentisierungsmethode konfiguriert."),
            status_code=400,
        )

    # 4. Erfolgreiches Rendern
    print(f" Login-Seite wird angezeigt mit auth_method={auth_method}, using_env_login={using_env_login}")
    return jinja_templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "auth_method": auth_method,
            "using_env_login": using_env_login,
        },
    )

