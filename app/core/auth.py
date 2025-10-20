"""
===============================================================================
Project   : gratulo
Module    : app/core/auth.py
Created   : 2025-10-05
Author    : Florian
Purpose   : Provides authentication and admin access control for Gratulo.
===============================================================================
"""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.models import AdminUser
from app.core.constants import INITIAL_ADMIN_USER, INITIAL_PASSWORD
from datetime import datetime, timezone
import bcrypt

def ensure_initial_admin(db: Session):
    """
    Ensures the existence of an initial admin user in the database during the application's
    initial setup phase. If no admin user exists, an informational message is printed to notify
    the user of temporary credentials for initial configuration.

    Args:
        db: Session
            An active SQLAlchemy database session.
    """
    if not (INITIAL_ADMIN_USER and INITIAL_PASSWORD):
        return

    exists = db.query(AdminUser).count() > 0
    if not exists:
        print(
            "[warn] Kein AdminUser in der Datenbank gefunden.\n"
            "       Login über INITIAL_ADMIN_USER/INITIAL_PASSWORD aktiv.\n"
            "       Entfernen Sie diese Werte nach der Erstkonfiguration,\n"
            "       um die Admin-Verwaltung über die Datenbank zu aktivieren."
        )


def require_admin(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Ensure administrative privileges for the user making the request.

    This function verifies the presence of an initial admin, checks if the
    requesting user is logged in, and ensures that the user has active
    administrator privileges in the database. If any of these conditions
    are not met, appropriate HTTPExceptions are raised.

    Args:
        request: The incoming HTTP request object, which includes session
            information about the current user.
        db: A database session used to query the database for user
            authentication and authorization.

    Returns:
        A dictionary containing the admin user's ID, username, and whether
        two-factor authentication is enabled.

    Raises:
        HTTPException: If the user is not logged in, lacks the necessary
            admin rights, or is inactive, appropriate status and detail
            messages are returned.
    """
    # Stelle sicher, dass Initial-Admin vorhanden ist
    ensure_initial_admin(db)

    user = request.session.get("user")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
            detail="Nicht eingeloggt",
        )

    # Suche Benutzer in der Datenbank
    db_user = (
        db.query(AdminUser)
        .filter(AdminUser.username == user.get("username").lower())
        .first()
    )
    username = user.get("username", "").lower()

    if INITIAL_ADMIN_USER and username == INITIAL_ADMIN_USER.lower():
        return {
            "id": None,
            "username": INITIAL_ADMIN_USER,
            "is_env_admin": True,
            "is_2fa_enabled": False,
        }

    # Wenn kein Benutzer oder inaktiv → ablehnen
    if not db_user or not db_user.is_active:
        raise HTTPException(status_code=403, detail="Keine Adminrechte")

    # Adminrechte bestätigt
    return {
        "id": db_user.id,
        "username": db_user.username,
        "is_2fa_enabled": db_user.is_2fa_enabled,
    }
