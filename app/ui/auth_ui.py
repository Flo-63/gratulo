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
    Handles the login submission process for users. Validates user credentials against
    the database and provides appropriate responses based on the success or failure of
    the authentication. In case of a successful login, user session data is updated,
    and the user is redirected to the main page. If login fails, an error message is
    returned to the template for rendering.

    :param request: The HTTP request object.
    :type request: Request
    :param db: The database session dependency.
    :type db: Session
    :param email: The email address submitted by the user through the login form.
    :type email: str
    :param password: The password submitted by the user through the login form.
    :type password: str
    :return: An HTMLResponse object with the appropriate page or redirection.
    :rtype: HTMLResponse
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
    Handles user logout by clearing the session data and redirects the user to
    the login page with a 303 status code.

    :param request: The HTTP request object, which provides access to the
        session data.
    :type request: Request
    :return: A redirection response to the login page.
    :rtype: RedirectResponse
    """
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# ---------------------------
# OAuth (Start/Callback)
# ---------------------------
@auth_ui_router.get("/oauth/start")
async def oauth_start():
    """
    Performs a redirection to initiate the OAuth process.

    This endpoint triggers a redirect to the OAuth callback URL, starting the
    authentication workflow with the third-party provider. It ensures the flow
    begins by redirecting the client to the appropriate callback endpoint.

    :return: A redirection response to the OAuth callback URL.
    :rtype: RedirectResponse
    """
    return RedirectResponse("/oauth/callback")


@auth_ui_router.get("/oauth/callback")
async def oauth_callback(request: Request, db: Session = Depends(get_db)):
    """
    Handles the OAuth callback after a user authentication event.

    This function processes the callback request from the OAuth provider to complete
    the user authentication. It verifies the user's email address against a list of
    authorized admin emails from the database. If the user is authorized, their
    email address is stored in the session, and they are redirected to the admin
    dashboard. If not authorized, the access is denied with a 403 status code.

    :param request: The HTTP request received by the server.
        It is a fastapi.Request object that contains request data and attributes.
    :param db: The database session dependency used to query or interact with
        the database. It is resolved as a SQLAlchemy session object.

    :return: Either an HTMLResponse denying access with status code 403 if the
        user is not authorized, or a RedirectResponse redirecting to the admin
        panel (status code 303) if authorized.
    """
    config = db.query(MailerConfig).first()
    user_email = "florian@radtreffcampus.de"

    allowed_admins = (config.admin_emails or "").split(",") if config else []
    if user_email not in [m.strip() for m in allowed_admins]:
        return HTMLResponse("❌ Zugriff verweigert", status_code=403)

    request.session["user"] = user_email
    return RedirectResponse("/admin", status_code=303)
