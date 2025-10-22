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


from fastapi import APIRouter, Request, Depends
from fastapi_limiter.depends import RateLimiter
from fastapi.responses import HTMLResponse, RedirectResponse

from fastapi import Form

from sqlalchemy.orm import Session
from app.core.deps import jinja_templates, context
from app.core.database import get_db
from app.core.models import MailerConfig, AdminUser
from app.services.auth_service import verify_login, make_user, verify_2fa_token
from app.core.constants import INITIAL_ADMIN_USER, INITIAL_PASSWORD

auth_ui_router = APIRouter(include_in_schema=False)


@auth_ui_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    """
    Handles rendering of the login page based on the authentication configuration.

    This function determines the authentication method using either an environment-based
    login or configurations retrieved from the database. If no configuration is found, it
    falls back to default values. The rendered login page is returned via a Jinja2 template.

    Args:
        request (Request): The HTTP request object.
        db (Session, optional): The database session dependency.

    Returns:
        HTMLResponse: The rendered login page with the appropriate context.
    """

    config = db.query(MailerConfig).first()

    if INITIAL_ADMIN_USER and INITIAL_PASSWORD:
        # 1) ENV-Login aktiv
        auth_method = "email"
        using_env_login = True

    elif config:
        # 2) DB ist vorhanden – Authentifizierungsmethode aus DB verwenden
        if config.auth_method in ("email", "oauth"):
            auth_method = config.auth_method
            using_env_login = False
        else:
            # Fallback, falls jemand Mist in die DB schreibt
            auth_method = "email"
            using_env_login = False

    else:
        # 3) Kein ENV und keine Config → keine Methode konfiguriert
        auth_method = None
        using_env_login = False

    return jinja_templates.TemplateResponse(
        "login.html",
        context(
            request,
            auth_method=auth_method,
            using_env_login=using_env_login,
            error_message=None,
        ),
    )


@auth_ui_router.post("/login", dependencies=[Depends(RateLimiter(times=5, seconds=600))])
async def login_submit(
    request: Request,
    db: Session = Depends(get_db),
    email: str = Form(None),
    password: str = Form(None),
):
    """
    Handles the login request, performing user authentication based on email
    and password. If the login is successful, the function either initiates
    a 2FA process if enabled or logs in the user directly. In case of failure,
    an error message is displayed to the user.

    Args:
        request (Request): FastAPI Request object.
        db (Session): Database session injected using dependency injection.
        email (str): Email address submitted through the login form.
        password (str): Password submitted through the login form.

    Returns:
        RedirectResponse: Redirects to the 2FA verification page if 2FA is
        enabled for the user, or to the homepage upon successful login.
        Otherwise, returns a TemplateResponse to render the login page with
        an error message on login failure.
    """
    config = db.query(MailerConfig).first()

    # Prüfen mit zentraler Funktion
    success, error = verify_login(db, email, password)

    if success:
        # Benutzer aus DB laden
        db_user = db.query(AdminUser).filter(AdminUser.username == email).first()

        # Wenn 2FA aktiv → Zwischenstufe
        if db_user and db_user.is_2fa_enabled:
            request.session["pending_2fa_user"] = db_user.username
            return RedirectResponse("/2fa-verify", status_code=303)

        # sonst normaler Login
        request.session["user"] = make_user(email, is_admin=True)
        return RedirectResponse("/", status_code=303)

    # Fehlerfall -> Fehlermeldung an Template
    else:
        auth_method = (
            "email" if (INITIAL_ADMIN_USER and INITIAL_PASSWORD)
            else (config.auth_method if config and config.auth_method else "oauth")
        )
        return jinja_templates.TemplateResponse(
            "login.html",
            context(request,
                auth_method=auth_method,
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
    Handles the user logout by clearing the session and redirecting to the login page.

    Args:
        request (Request): The HTTP request object.

    Returns:
        RedirectResponse: A response object that redirects the user to the login page.
    """
    request.session.clear()
    return RedirectResponse("/login", status_code=303)

# ---------------------------
# OAuth (Start/Callback)
# ---------------------------
@auth_ui_router.get("/oauth/start")
async def oauth_start():
    """
    Handles the initiation of OAuth authentication and redirects to the callback URL.

    Returns:
        RedirectResponse: A redirection response to the OAuth callback URL.
    """
    return RedirectResponse("/oauth/callback")


@auth_ui_router.get("/oauth/callback")
async def oauth_callback(request: Request, db: Session = Depends(get_db)):
    """
    Handles the OAuth callback for user authentication and authorization.

    This function processes the OAuth callback, performing user email validation
    against a stored list of allowed admin emails. If the email is not found in
    the allowed list, access will be denied. Otherwise, the user session is
    established, and the user is redirected to the admin panel.

    Args:
        request (Request): The incoming HTTP request containing session data.
        db (Session): The database session for querying stored configuration data.

    Returns:
        Response: An HTML response denying access with a 403 status code if the
        user email is not authorized, or a redirect response to the admin panel
        with a 303 status code upon successful authentication.
    """
    config = db.query(MailerConfig).first()
    user_email = "florian@radtreffcampus.de"

    allowed_admins = (config.admin_emails or "").split(",") if config else []
    if user_email not in [m.strip() for m in allowed_admins]:
        return HTMLResponse("❌ Zugriff verweigert", status_code=403)

    request.session["user"] = user_email
    return RedirectResponse("/admin", status_code=303)


# ---------------------------
# Zwei-Faktor-Authentifizierung
# ---------------------------

@auth_ui_router.get("/2fa-verify")
async def two_factor_form(request: Request):
    """
    Handles requests for the Two-Factor Authentication (2FA) verification form.

    This endpoint serves the 2FA verification page when a user is in the process of
    logging in and is required to complete 2FA verification. If no pending 2FA user information
    is found in the session, the request is redirected to the login page.

    Args:
        request: The HTTP request object containing session information and other
            request details.

    Returns:
        Either a template response rendering the 2FA verification page with
        necessary context or a redirect response to the login page if no pending
        2FA user is found.
    """
    pending_user = request.session.get("pending_2fa_user")
    if not pending_user:
        return RedirectResponse("/login", status_code=303)

    return jinja_templates.TemplateResponse(
        "2fa_verify.html",
        context(request, username=pending_user, error=None),
    )


@auth_ui_router.post("/2fa-verify")
async def two_factor_verify(
    request: Request,
    token: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Handles the two-factor authentication (2FA) verification process for a user.

    Once a 2FA token is submitted via a form, this endpoint verifies the token against
    the stored user data. If the verification is successful, the user session is updated
    with the necessary credentials and authentication status. Unsuccessful attempts will
    redirect users back to the verification page with an appropriate error message.

    Args:
        request (Request): The HTTP request object containing session data and form data.
        token (str): The token provided by the user for two-factor authentication.
        db (Session): The database session dependency used to query and interact with
            the database.

    Returns:
        RedirectResponse: Redirects to the login page if the user is not pending 2FA or
            verification fails. Redirects to the dashboard/root page upon successful
            verification.
    """
    pending_user = request.session.get("pending_2fa_user")
    if not pending_user:
        return RedirectResponse("/login", status_code=303)

    user = db.query(AdminUser).filter(AdminUser.username == pending_user).first()
    if not user or not verify_2fa_token(user, token):
        return jinja_templates.TemplateResponse(
            "2fa_verify.html",
            context(request, username=pending_user, error="❌ Ungültiger Code oder abgelaufen."),
            status_code=401,
        )

    # Erfolgreich
    request.session.pop("pending_2fa_user", None)
    request.session["user"] = make_user(user.username, is_admin=True)
    request.session["2fa_valid"] = True

    return RedirectResponse("/", status_code=303)
