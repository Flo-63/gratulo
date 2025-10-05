from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from email_validator import validate_email, EmailNotValidError

from app.core.database import get_db
from app.core.models import MailerConfig
from app.core.deps import jinja_templates, context
from app.helpers.security_helper import set_password
mailer_config_ui_router = APIRouter(include_in_schema=False)


@mailer_config_ui_router.get("/mailer-config")
def mailer_config_ui(request: Request, db: Session = Depends(get_db)):
    config = db.query(MailerConfig).first()
    return jinja_templates.TemplateResponse(
        "mailer_config.html",
        context(request, config=config)
    )


@mailer_config_ui_router.post("/mailer-config")
def mailer_config_save(
    request: Request,
    smtp_host: str = Form(...),
    smtp_port: int = Form(...),
    smtp_user: str = Form(...),
    smtp_password: str = Form(""),
    use_tls: bool = Form(False),
    from_address: str = Form(...),
    auth_method: str = Form("email"),
    login_email: str = Form(""),
    login_password: str = Form(""),
    oauth_client_id: str = Form(""),
    oauth_client_secret: str = Form(""),
    oauth_provider_url: str = Form(""),
    oauth_redirect_uri: str = Form(""),
    admin_emails: str = Form(""),
    db: Session = Depends(get_db),
):
    error_message = None

    # --- Validierungen ---
    if smtp_port not in [25, 465, 587]:
        error_message = "Ungültiger SMTP-Port (erlaubt: 25, 465, 587)."

    try:
        validate_email(from_address)
    except EmailNotValidError:
        error_message = "Die Absenderadresse ist ungültig."

    if auth_method not in ["email", "oauth"]:
        error_message = "Ungültige Authentifizierungsmethode."

    if auth_method == "email":
        if login_email:
            try:
                validate_email(login_email)
            except EmailNotValidError:
                error_message = "Login-E-Mail ist ungültig."

    if auth_method == "oauth":
        if not oauth_client_id or not oauth_client_secret:
            error_message = "OAuth-Client ID und Secret müssen angegeben werden."
        elif not oauth_provider_url.startswith("http"):
            error_message = "Ungültige OAuth Provider-URL."
        elif not oauth_redirect_uri.startswith("http"):
            error_message = "Ungültige Redirect-URI."

        if admin_emails:
            for addr in [e.strip() for e in admin_emails.split(",") if e.strip()]:
                try:
                    validate_email(addr)
                except EmailNotValidError:
                    error_message = f"Ungültige Admin-E-Mail: {addr}"

    # --- Falls Fehler, zurück ins Template ---
    if error_message:
        config = db.query(MailerConfig).first()
        return jinja_templates.TemplateResponse(
            "mailer_config.html",
            context(request, config=config, error_message=error_message),
            status_code=400
        )

    # --- Speichern ---
    config = db.query(MailerConfig).first()
    if not config:
        config = MailerConfig()

    config.smtp_host = smtp_host
    config.smtp_port = smtp_port
    config.smtp_user = smtp_user
    if smtp_password:
        config.smtp_password = smtp_password
    config.use_tls = use_tls
    config.from_address = from_address

    config.auth_method = auth_method
    config.login_email = login_email if auth_method == "email" else None
    if login_password and auth_method == "email":
        config.login_password = set_password(login_password)

    config.oauth_client_id = oauth_client_id if auth_method == "oauth" else None
    config.oauth_client_secret = oauth_client_secret if auth_method == "oauth" else None
    config.oauth_provider_url = oauth_provider_url if auth_method == "oauth" else None
    config.oauth_redirect_uri = oauth_redirect_uri if auth_method == "oauth" else None
    config.admin_emails = admin_emails if auth_method == "oauth" else None

    db.add(config)
    db.commit()

    return RedirectResponse(url="/admin", status_code=303)
