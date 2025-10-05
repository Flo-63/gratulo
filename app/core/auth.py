from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.models import MailerConfig
from app.core.constants import INITIAL_ADMIN_USER

def require_admin(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Checks if the requesting user has administrator privileges. Depending on the
    authentication configuration, it verifies the user's rights and enforces various
    restrictions. If the user is not authorized, appropriate HTTP exceptions are
    raised. This function is commonly used to control access to sensitive operations
    or resources requiring administrative permissions.

    :param request: The incoming HTTP Request object containing session information
                    about the current user.
    :type request: fastapi.Request

    :param db: Database session object for querying the MailerConfig and other
               persisted data.
    :type db: sqlalchemy.orm.Session

    :return: A dictionary object representing the user data if the user is an
             authorized administrator.
    :rtype: dict
    """
    user = request.session.get("user")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
            detail="Nicht eingeloggt",
        )

    config = db.query(MailerConfig).first()

    # 🟦 Initial-Admin darf immer rein
    if INITIAL_ADMIN_USER and user["email"] == INITIAL_ADMIN_USER.lower():
        return user

    if not config:
        raise HTTPException(status_code=403, detail="Keine Konfiguration gefunden")

    # OAuth-Adminprüfung
    if config.auth_method == "oauth":
        allowed_admins = [m.strip().lower() for m in (config.admin_emails or "").split(",") if m.strip()]
        if user["email"] not in allowed_admins:
            raise HTTPException(status_code=403, detail="Keine Adminrechte")

    # Email-Auth: Admin-Flag muss stimmen
    if not user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Keine Adminrechte")

    return user


