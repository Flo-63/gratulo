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
    Renders the login page with the correct authentication method.
    Determines whether .env-based login (INITIAL_ADMIN_USER) or OAuth is active.
    """

    config = db.query(MailerConfig).first()

    if INITIAL_ADMIN_USER and INITIAL_PASSWORD:
        auth_method = "email"
        using_env_login = True
    elif config and config.auth_method == "oauth":
        auth_method = "oauth"
        using_env_login = False
    else:
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
    Handles login submission for the admin area. Validates credentials, processes authentication steps such
    as Two-Factor Authentication (2FA) if enabled, and manages user sessions. Redirects the user to the
    appropriate page based on the state of the login (successful login, pending 2FA, or failure).

    Args:
        request (Request): The incoming HTTP request object containing session and form data.
        db (Session): The database session used for querying and persisting data.
        email (str): The email address submitted via the login form.
        password (str): The password submitted via the login form.

    Returns:
        RedirectResponse: Redirects to the homepage on successful login or to the 2FA verification page
        if 2FA is enabled. On login failure, returns a rendered login page with an error message.

    Raises:
        None: Does not explicitly raise any exception.
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
    Logs out the user by clearing the session and redirects to the login page.

    This endpoint is used to log out the current user by clearing their session
    data. After the session is cleared, the user is redirected to the login page.

    Args:
        request: The incoming HTTP request object containing session information.

    Returns:
        RedirectResponse: A response object to redirect the user to the login
        page with a 303 status code.
    """
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# ---------------------------
# OAuth (Start/Callback)
# ---------------------------
@auth_ui_router.get("/oauth/start")
async def oauth_start():
    """
    Handles the start of the OAuth process by redirecting to the OAuth callback URL.

    Returns:
        RedirectResponse: A response object that redirects the user to the
        "/oauth/callback" endpoint.
    """
    return RedirectResponse("/oauth/callback")


@auth_ui_router.get("/oauth/callback")
async def oauth_callback(request: Request, db: Session = Depends(get_db)):
    """
    Handles OAuth callback for user authentication and authorization.

    This endpoint processes the callback from an OAuth provider and validates the
    user's email against the allowed admin emails configured in the database. If
    the email is not authorized, access is denied with a 403 status. Otherwise,
    the user's email is stored in the session, and they are redirected to the
    admin page.

    Args:
        request (Request): The incoming HTTP request object, used to manage the
            session and extract request-specific information.
        db (Session): SQLAlchemy session dependency for database access.

    Returns:
        HTMLResponse: An HTML response denying access with a 403 status if the
            user's email is not authorized.
        RedirectResponse: A redirection response to the admin page with a 303
            status if the user is successfully authenticated and authorized.
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
    Handles rendering the two-factor authentication verification form.

    The endpoint is responsible for serving the Two-Factor Authentication (2FA)
    verification page. It retrieves the pending user from the session. If no
    pending user is found, the user will be redirected to the login page. This
    endpoint leverages a Jinja2 template to render the 2FA verification form
    with the pending user's username passed in the context.

    Args:
        request (Request): The HTTP request object carrying session and other
        data for the current user.

    Returns:
        TemplateResponse: Renders the 2FA verification HTML page if the session
        includes a pending 2FA user.
        RedirectResponse: Redirects to the login page if no pending 2FA user
        exists in the session.
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
    Handles the Two-Factor Authentication (2FA) verification process for admin users. This
    endpoint is triggered after the user submits their 2FA token for verification. It ensures
    the validity of the token for the user associated with the current session. Upon successful
    verification, the user session is updated to reflect authentication and redirects to the main
    page. In case of failure, the user is redirected back to the 2FA verification form with an
    error message.

    Args:
        request (Request): The HTTP request object containing session data.
        token (str): The 2FA token provided by the user.
        db (Session): The database session dependency for querying user data.

    Returns:
        RedirectResponse: A redirection to the main page upon success or re-rendering of
        the 2FA verification form upon failure.
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
