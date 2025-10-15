"""
===============================================================================
Project   : gratulo
Module    : app/htmx/admin_users_htmx.py
Created   : 2025-10-15
Author    : Florian
Purpose   : This module provides endpoints and functionality for managing admin users via HTMX.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""


from fastapi import APIRouter, Depends, Request, Form, HTTPException
from sqlalchemy.orm import Session
from starlette.responses import HTMLResponse
from datetime import datetime
from passlib.hash import bcrypt

from app.core.database import get_db
from app.core.models import AdminUser
from app.services.auth_service import (
    generate_2fa_secret,
    generate_qr_code_uri,
    generate_qr_code_base64,
    verify_2fa_token,
)


from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="frontend/templates")

admin_users_router = APIRouter(prefix="/mailer-config/admin-users", tags=["Admin Users (HTMX)"])

# -----------------------------------------------------------------------------
# Helper
# -----------------------------------------------------------------------------
def render_admin_list(request: Request, db: Session):
    """
    Renders the admin user list template with the list of admin users retrieved
    from the database. The admin users are sorted in ascending order of their usernames.

    Args:
        request (Request): HTTP request object containing information about the
            incoming request.
        db (Session): Database session object used to execute database queries.

    Returns:
        TemplateResponse: Rendered HTML template for the admin user list.
    """
    users = db.query(AdminUser).order_by(AdminUser.username).all()
    return templates.TemplateResponse(
        "partials/admin_user_list.html",
        {"request": request, "users": users}
    )

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@admin_users_router.get("", response_class=HTMLResponse)
def list_admin_users(request: Request, db: Session = Depends(get_db)):
    """
    Handles the HTTP GET request to retrieve and render the list of admin users.

    This endpoint fetches data from the database and renders a template to display the
    list of admin users.

    Args:
        request: The incoming HTTP request object.
        db: The database session dependency.

    Returns:
        HTMLResponse: A rendered HTML response displaying the list of admin users.
    """
    return render_admin_list(request, db)


@admin_users_router.get("/new", response_class=HTMLResponse)
def new_admin_user(request: Request):
    """
    Handles the request to render the new admin user creation page.

    Args:
        request (Request): The incoming HTTP request object.

    Returns:
        HTMLResponse: A rendered HTML response containing the admin user editor
        template.
    """
    return templates.TemplateResponse(
        "partials/admin_user_editor.html",
        {"request": request, "user": None}
    )


@admin_users_router.get("/{user_id}/edit", response_class=HTMLResponse)
def edit_admin_user(request: Request, user_id: int, db: Session = Depends(get_db)):
    """
    Handles the retrieval and rendering of the admin user editor page. This function is an
    endpoint for displaying the edit UI for an admin user with the provided user ID if such
    user exists. Otherwise, it responds with a 404 HTTP error.

    Args:
        request (Request): The incoming HTTP request object. This contains metadata about
            the request, such as headers and query parameters.
        user_id (int): The unique identifier of the admin user to be loaded for editing.
        db (Session): The database session dependency used for querying the database.

    Returns:
        HTMLResponse: An HTML response rendered by the template, containing the admin user
        editor page.

    Raises:
        HTTPException: If no admin user exists with the given user_id, an HTTP 404 error is
            raised.
    """
    user = db.query(AdminUser).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Admin user not found")
    return templates.TemplateResponse(
        "partials/admin_user_editor.html",
        {"request": request, "user": user}
    )


@admin_users_router.post("/save", response_class=HTMLResponse)
def save_admin_user(
    request: Request,
    db: Session = Depends(get_db),
    user_id: int = Form(None),
    username: str = Form(...),
    password: str = Form(""),
    is_active: bool = Form(False),
    is_2fa_enabled: bool = Form(False),
):
    """
    Saves or updates an admin user in the database and handles 2-factor authentication (2FA) setup.

    This function processes a form to save or update an admin user in the database. It includes functionality
    to hash the password if provided, toggle the active state and 2FA status, and manage 2FA secret generation
    with a QR code setup if enabled and not previously configured. If updating an existing user, it validates
    that the user exists in the database before proceeding.

    Args:
        request: The HTTP request object.
        db: The database session dependency.
        user_id: The ID of the admin user to update. If None, a new user will be created.
        username: The username of the admin user.
        password: The unencrypted password for the admin user. Defaults to an empty string.
        is_active: A boolean indicating if the admin user is active. Defaults to False.
        is_2fa_enabled: A boolean indicating if two-factor authentication is enabled for the admin user.
            Defaults to False.

    Returns:
        Depending on the state of 2FA setup, either renders a 2FA QR code setup template or renders the admin
        user list view.

    Raises:
        HTTPException: If the provided user_id does not correspond to an existing admin user in the database.
    """
    if user_id:
        user = db.query(AdminUser).get(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Admin user not found")
        user.username = username.strip()
        if password:
            user.password_hash = bcrypt.hash(password)
        user.is_active = is_active
        user.is_2fa_enabled = is_2fa_enabled
        user.last_login_at = user.last_login_at  # no change here
    else:
        user = AdminUser(
            username=username.strip(),
            password_hash=bcrypt.hash(password) if password else "",
            is_active=is_active,
            is_2fa_enabled=is_2fa_enabled,
            created_at=datetime.utcnow(),
        )
        db.add(user)

    db.commit()
    db.refresh(user)

    # Wenn 2FA aktiviert wurde, aber kein Secret existiert -> QR-Code anzeigen
    if user.is_2fa_enabled and not user.totp_secret:
        secret = generate_2fa_secret(user, db)
        uri = generate_qr_code_uri(user, issuer_name="Gratulo")
        qr_b64 = generate_qr_code_base64(uri)
        return templates.TemplateResponse(
            "partials/2fa_setup.html",
            {"request": request, "user": user, "qr_b64": qr_b64},
        )

    return render_admin_list(request, db)


@admin_users_router.delete("/{user_id}", response_class=HTMLResponse)
def delete_admin_user(request: Request, user_id: int, db: Session = Depends(get_db)):
    """
    Deletes an admin user by their unique ID.

    This endpoint allows for the deletion of a specific admin user from the
    database. If the user is not found, an HTTP 404 error is raised. After
    successful deletion, the updated admin user list is rendered.

    Args:
        request (Request): The HTTP request object.
        user_id (int): The unique identifier of the admin user to be deleted.
        db (Session): Database session dependency.

    Returns:
        HTMLResponse: An HTML response containing the rendered admin user list.

    Raises:
        HTTPException: If the admin user with the specified ID is not found.
    """
    user = db.query(AdminUser).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Admin user not found")

    db.delete(user)
    db.commit()
    return render_admin_list(request, db)

@admin_users_router.post("/{user_id}/2fa-verify", response_class=HTMLResponse)
def verify_2fa_code(
    request: Request,
    user_id: int,
    token: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Handles the verification of a 2FA code for an admin user. Users provide a 2FA token
    that is checked against the stored 2FA configuration for the user.

    If the 2FA token verification fails, a QR code for configuring 2FA is regenerated,
    and an appropriate response is provided. On successful verification, the function
    returns a rendered admin list.

    Args:
        request (Request): The HTTP request object containing metadata about the request.
        user_id (int): The unique identifier for the admin user attempting to verify 2FA.
        token (str, Form): The 2FA token submitted by the user for verification.
        db (Session): The database session dependency used to query and interact with the database.

    Returns:
        HTMLResponse: The response containing either the 2FA configuration page with an error message
        or the admin list page upon successful 2FA verification.

    Raises:
        HTTPException: Raised with status code 404 if the admin user with the given user_id is not found.
    """
    user = db.query(AdminUser).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Admin user not found")

    if not verify_2fa_token(user, token):
        uri = generate_qr_code_uri(user, issuer_name="Gratulo")
        qr_b64 = generate_qr_code_base64(uri)
        return templates.TemplateResponse(
            "partials/2fa_setup.html",
            {"request": request, "user": user, "qr_b64": qr_b64, "error": "❌ Ungültiger Code."},
            status_code=401,
        )

    # Erfolgreich: Flag bleibt, zurück zur Liste
    return render_admin_list(request, db)

@admin_users_router.post("/{user_id}/disable-2fa", response_class=HTMLResponse)
def disable_2fa(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Disables two-factor authentication (2FA) for a specific admin user. This includes
    deactivating the 2FA flag and deleting the TOTP secret for the user. After disabling
    2FA, the admin user list is updated and rendered.

    Args:
        request (Request): The HTTP request object.
        user_id (int): The unique identifier of the admin user whose 2FA should be disabled.
        db (Session): The database session dependency for querying and updating data.

    Raises:
        HTTPException: If the specified admin user is not found in the database.

    Returns:
        HTMLResponse: The updated list of admin users after 2FA is disabled for the specified user.
    """
    user = db.query(AdminUser).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Admin user not found")

    # 2FA wirklich deaktivieren: Flag aus und Secret löschen
    user.is_2fa_enabled = False
    user.totp_secret = None
    db.add(user)
    db.commit()
    db.refresh(user)

    # Liste aktualisieren
    return render_admin_list(request, db)