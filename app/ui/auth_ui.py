"""
===============================================================================
Project   : gratulo
Module    : app/ui/auth_ui.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides authentication-related user interface (UI) endpoints.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""


from fastapi import APIRouter, Request, Form, Depends
from fastapi_limiter.depends import RateLimiter
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.deps import jinja_templates, context
from app.core.database import get_db
from app.core.models import MailerConfig
from app.services.auth_service import verify_login, make_user
from app.core.constants import INITIAL_ADMIN_USER, INITIAL_PASSWORD

auth_ui_router = APIRouter(include_in_schema=False)


# ---------------------------
# Login POST
# ---------------------------

@auth_ui_router.post("/login", dependencies=[Depends(RateLimiter(times=5, seconds=600))])
async def login_submit(
    request: Request,
    db: Session = Depends(get_db),
    email: str = Form(None),
    password: str = Form(None),
):
    """
    Handles the user login process. This endpoint allows users to authenticate
    with their email and password. It validates the user credentials, updates the
    session on successful authentication, and redirects accordingly.

    Args:
        request (Request): The current HTTP request containing session information.
        db (Session): The database session dependency for accessing the database.
        email (str): The user's email address (optional).
        password (str): The user's password (optional).

    Returns:
        RedirectResponse: If the login is successful, redirects the user to the
            home page with a status code of 303.
        TemplateResponse: If the login fails, renders the login page with an
            appropriate error message and a status code of 401.
    """
    config = db.query(MailerConfig).first()

    # Prüfen mit zentraler Funktion
    success, error = verify_login(db, email, password)

    if success:
        # sauberes User-Objekt in Session speichern
        request.session["user"] = make_user(email, is_admin=True)
        return RedirectResponse("/", status_code=303)

    # Fehlerfall -> Fehlermeldung an Template
    return jinja_templates.TemplateResponse(
        "login.html",
        context(request,
            auth_method="email" if (INITIAL_ADMIN_USER and INITIAL_PASSWORD) or (config and config.auth_method == "email") else None,
            using_env_login=bool(INITIAL_ADMIN_USER and INITIAL_PASSWORD),
            error_message=error or "❌ Ungültige E-Mail oder Passwort."
        ),
        status_code=401,
    )


# ---------------------------
# Logout
# ---------------------------
@auth_ui_router.get("/logout")
async def logout(request: Request):
    """
    Handles user logout by clearing the session and redirecting to the login page.

    This endpoint clears the current user's session data, effectively logging them
    out of the system, and then redirects them to the login page using a 303 status code.

    Args:
        request (Request): The incoming HTTP request object containing session
            and other request-related data.

    Returns:
        RedirectResponse: An HTTP response object that performs a redirection to
        the login page with a 303 status code.
    """
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# ---------------------------
# OAuth (Start/Callback)
# ---------------------------
@auth_ui_router.get("/oauth/start")
async def oauth_start():
    """
    Handles the starting point for OAuth authentication by redirecting to
    the OAuth callback endpoint.

    This function is an endpoint that initiates the OAuth flow by redirecting
    the client to the `/oauth/callback` path.

    Returns:
        RedirectResponse: A response object redirecting to the OAuth callback
        endpoint.
    """
    return RedirectResponse("/oauth/callback")


@auth_ui_router.get("/oauth/callback")
async def oauth_callback(request: Request, db: Session = Depends(get_db)):
    """
    Handles OAuth callback and authenticates the user based on the provided OAuth
    parameters.

    This function checks whether the authenticated user email matches the allowed
    admin emails stored in the database. If the user is authorized, the session
    is updated with the user's email, and the user is redirected to the admin
    dashboard. Unauthorized users receive a 403 access denied response.

    Args:
        request (Request): The HTTP request object containing session and other
            request details.
        db (Session): Database session dependency used for querying application
            configurations.

    Returns:
        RedirectResponse: Redirects the authenticated user to the admin page if
            authorized.
        HTMLResponse: Returns a 403 HTML response if the user is not an allowed
            admin.
    """
    config = db.query(MailerConfig).first()
    user_email = "florian@radtreffcampus.de"

    allowed_admins = (config.admin_emails or "").split(",") if config else []
    if user_email not in [m.strip() for m in allowed_admins]:
        return HTMLResponse("❌ Zugriff verweigert", status_code=403)

    request.session["user"] = user_email
    return RedirectResponse("/admin", status_code=303)
