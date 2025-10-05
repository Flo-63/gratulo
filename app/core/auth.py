"""
===============================================================================
Project   : gratulo
Module    : app/core/auth.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides authentication-related functions for the
            Gratulo application.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""



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
    Restricts access to admin resources, ensuring that only authorized admin users can proceed.

    This function checks the session data for a logged-in user and verifies the user's
    admin status through multiple methods, including initial admin checks, OAuth admin
    validation, and email-based admin flag.

    Args:
        request (Request): The incoming HTTP request containing session data.
        db (Session): The database session dependency for querying configuration data.

    Raises:
        HTTPException: Raised with status 303 and redirect to '/login' if no user is logged in.
        HTTPException: Raised with status 403 if no mailer configuration is found in the database.
        HTTPException: Raised with status 403 if the user does not have admin rights based on
            OAuth admin email validation or a missing admin flag in email-based authentication.

    Returns:
        dict: The user dictionary object of the authenticated and authorized admin user.
    """
    user = request.session.get("user")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
            detail="Nicht eingeloggt",
        )

    config = db.query(MailerConfig).first()

    # Initial-Admin darf immer rein
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


