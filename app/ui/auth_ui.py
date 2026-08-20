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


import secrets

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.concurrency import run_in_threadpool

from app.core.rate_limit import rate_limit

from fastapi import Form

from sqlalchemy.orm import Session
from app.core.deps import jinja_templates, context
from app.core.database import get_db
from app.core.models import MailerConfig, AdminUser
from app.services.auth_service import verify_login, make_user, verify_2fa_token
from app.services import oauth_service
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
        request=request,
        name="login.html",
        context={
            "auth_method": auth_method,
            "using_env_login": using_env_login,
            "error_message": None,
        }
    )


@auth_ui_router.post("/login", dependencies=[Depends(rate_limit(times=5, seconds=600))])
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
        ctx = context(request,
            auth_method=auth_method,
            using_env_login=bool(INITIAL_ADMIN_USER and INITIAL_PASSWORD),
            error_message=error or "❌ Ungültige E-Mail oder Passwort."
        )
        return jinja_templates.TemplateResponse(
            request=request,
            name="login.html",
            context=ctx,
            status_code=401
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
# OAuth (Start/Callback) – Google OpenID Connect, Authorization Code flow
# ---------------------------
@auth_ui_router.get("/oauth/start")
async def oauth_start(request: Request, db: Session = Depends(get_db)):
    """
    Starts the OAuth login by redirecting the user to the provider.

    Generates a per-request CSRF ``state`` value, stores it in the session, and
    redirects to the provider's authorization endpoint. If OAuth is not
    configured (no client id/secret), the flow is refused instead of silently
    granting access.

    Args:
        request (Request): The incoming HTTP request (session holder).
        db (Session): The database session used to load the mailer config.

    Returns:
        Response: A redirect to the provider, or a 400 page if OAuth is not
        configured.
    """
    config = db.query(MailerConfig).first()
    if not oauth_service.is_configured(config):
        return HTMLResponse("❌ OAuth ist nicht konfiguriert.", status_code=400)

    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    return RedirectResponse(
        oauth_service.build_authorization_url(config, state), status_code=303
    )


@auth_ui_router.get("/oauth/callback")
async def oauth_callback(
    request: Request,
    db: Session = Depends(get_db),
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    """
    Completes the OAuth login: verifies state, exchanges the code, authorizes.

    The provider-supplied ``state`` is compared against the value stored in the
    session (CSRF protection). The authorization code is then exchanged for an
    access token server-to-server, the verified e-mail is read from the
    provider's userinfo endpoint, and access is granted only if that e-mail is
    verified and present on the ``admin_emails`` allow-list.

    Args:
        request (Request): The incoming HTTP request (session holder).
        db (Session): The database session used to load the mailer config.
        code (str | None): The authorization code from the provider.
        state (str | None): The state value echoed back by the provider.
        error (str | None): An error code from the provider, if any.

    Returns:
        Response: A redirect to the admin panel on success, or an error page
        (400/403) on any failure.
    """
    if error:
        return HTMLResponse(f"❌ OAuth-Fehler: {error}", status_code=400)

    # CSRF: the state must match the one we issued in /oauth/start (single use).
    expected_state = request.session.pop("oauth_state", None)
    if not expected_state or not state or not secrets.compare_digest(state, expected_state):
        return HTMLResponse("❌ Ungültiger OAuth-State (CSRF-Schutz).", status_code=400)

    if not code:
        return HTMLResponse("❌ Kein Autorisierungscode erhalten.", status_code=400)

    config = db.query(MailerConfig).first()
    if not oauth_service.is_configured(config):
        return HTMLResponse("❌ OAuth ist nicht konfiguriert.", status_code=400)

    # Blocking HTTP calls to the provider run off the event loop.
    try:
        userinfo = await run_in_threadpool(oauth_service.fetch_userinfo, config, code)
    except oauth_service.OAuthError as e:
        return HTMLResponse(f"❌ OAuth-Anmeldung fehlgeschlagen: {e}", status_code=400)

    email = (userinfo.get("email") or "").strip().lower()
    if not email or not oauth_service.is_email_verified(userinfo):
        return HTMLResponse("❌ E-Mail-Adresse ist nicht verifiziert.", status_code=403)

    if not oauth_service.is_admin_email(config, email):
        return HTMLResponse(
            "❌ Zugriff verweigert: E-Mail ist nicht als Admin hinterlegt.", status_code=403
        )

    # Authenticated by the provider, authorized via the allow-list.
    request.session["user"] = {**make_user(email, is_admin=True), "is_oauth": True}
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

    ctx = context(request, username=pending_user, error=None)
    return jinja_templates.TemplateResponse(
        request=request,
        name="2fa_verify.html",
        context=ctx
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
        ctx = context(request, username=pending_user, error="❌ Ungültiger Code oder abgelaufen.")
        return jinja_templates.TemplateResponse(
            request=request,
            name="2fa_verify.html",
            context=ctx,
            status_code=401
        )

    # Erfolgreich
    request.session.pop("pending_2fa_user", None)
    request.session["user"] = make_user(user.username, is_admin=True)
    request.session["2fa_valid"] = True

    return RedirectResponse("/", status_code=303)
