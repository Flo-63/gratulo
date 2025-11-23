"""
===============================================================================
Project   : gratulo
Module    : app/htmx/members_htmx.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides HTMX endpoints for managing members.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""


from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session


from app.core import models, database
from app.core.auth import require_admin
from app.core.deps import TEMPLATES_DIR
from app.services import group_service, member_service
from app.services.member_service import parse_csv, commit_members, EXPECTED_FIELDS, validate_rows
from app.helpers.member_helper import parse_date_flexible, parse_member_since

members_htmx_router = APIRouter(
    prefix="/htmx/members",
    tags=["htmx-members"],
    include_in_schema=False,
    dependencies=[Depends(require_admin)],
)

jinja_templates = Jinja2Templates(directory=TEMPLATES_DIR)


def context(request: Request, db: Session, **extra):
    """
    Provides a context dictionary that includes the request, a list of groups,
    and any additional key-value pairs.

    Args:
        request: The incoming HTTP request object.
        db: The database session to fetch the list of groups.
        **extra: Arbitrary additional key-value pairs to include in
            the context.

    Returns:
        dict: A context dictionary containing the request, a list
        of groups, and any additional data.
    """
    groups = group_service.list_groups(db)
    return {"request": request, "GROUPS": groups, **extra}



@members_htmx_router.post("/", response_class=HTMLResponse)
def save_member_htmx(
    request: Request,
    id: str | None = Form(None),
    firstname: str = Form(...),
    lastname: str = Form(...),
    gender: str = Form(...),
    email: str = Form(...),
    birthdate: str | None = Form(None),
    member_since: str | None = Form(None),
    group_id: int | None = Form(None),
    db: Session = Depends(database.get_db),
):
    """
    Handles saving or updating a member's data via an HTMX-based POST request. Performs
    data validation, processes UI-related errors, and interacts with the database for
    member persistence. Returns an HTML response with the necessary changes to update
    the UI dynamically.

    Args:
        request (Request): Represents the incoming HTTP request for rendering templates.
        id (str | None, optional): The ID of the existing member to update. Use None for
            creating a new member.
        firstname (str): The first name of the member.
        lastname (str): The last name of the member.
        gender (str): The gender of the member.
        email (str): The email address of the member.
        birthdate (str | None, optional): The birthdate of the member in the format 'YYYY-MM-DD'.
        member_since (str | None, optional): The membership start date in the format 'YYYY-MM-DD'.
        group_id (int | None, optional): The ID of the group the member belongs to.
        db (Session): The database session used for querying and saving data.

    Returns:
        HTMLResponse: A response containing the rendered HTML template with the
        updated member data and error messages if validation fails.

    Raises:
        None: Errors encountered during validation or database operations are either
        appended to the response or rendered via the HTML template.
    """
    errors = []

    parsed_birthdate = None
    if birthdate:
        try:
            dt = datetime.strptime(birthdate, "%Y-%m-%d").strftime("%d.%m.%Y")
            parsed_birthdate = parse_date_flexible(dt, "Geburtsdatum", 1)
            age = (datetime.now().date() - parsed_birthdate).days // 365
            if age > 105:
                errors.append("Ungültiges Geburtsdatum: älter als 105 Jahre")
            elif age > 80:
                errors.append("Mitglied ist über 80 Jahre alt – bitte prüfen")
        except HTTPException as e:
            errors.append(e.detail)

    parsed_member_since = None
    if member_since:
        try:
            dt = datetime.strptime(member_since, "%Y-%m-%d").strftime("%d.%m.%Y")
            parsed_member_since = parse_member_since(dt, 1)
        except HTTPException as e:
            errors.append(e.detail)

    if "@" not in email or "." not in email.split("@")[-1]:
        errors.append("Ungültige E-Mail-Adresse")

    # Gruppe prüfen (UI-Logik, nicht DB-seitig)
    group = None
    if group_id:
        group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        group = group_service.get_default_group(db)
    if not group:
        errors.append("Keine gültige Gruppe gefunden")

    #  Template-Fehleranzeige
    if errors:
        member_data = {
            "id": id,
            "firstname": firstname,
            "lastname": lastname,
            "gender": gender,
            "email": email,
            "birthdate": birthdate,
            "member_since": member_since,
            "group_id": group_id,
        }
        groups = group_service.list_groups(db)
        return jinja_templates.TemplateResponse(
            "partials/member_editor_partial.html",
            {
                "request": request,
                "member": member_data,
                "errors": errors,
                "GROUPS": groups,
                "htmx": True,
            },
        )

    # Speicherung mit zentraler Service-Funktion
    try:
        member_service.save_member(
            db=db,
            id=int(id) if id else None,
            firstname=firstname,
            lastname=lastname,
            gender=gender,
            email=email,
            birthdate=birthdate,
            member_since=member_since,
            group_id=group.id,
        )

        return Response(status_code=204, headers={"HX-Redirect": "/members"})

    except HTTPException as e:
        db.rollback()
        errors.append(e.detail)

    except Exception as e:
        db.rollback()
        errors.append(f"Fehler beim Speichern: {str(e)}")

    # Fehlerhafte Speicherung
    member_data = {
        "id": id,
        "firstname": firstname,
        "lastname": lastname,
        "gender": gender,
        "email": email,
        "birthdate": birthdate,
        "member_since": member_since,
        "group_id": group_id,
    }
    groups = group_service.list_groups(db)
    return jinja_templates.TemplateResponse(
        "partials/member_editor_partial.html",
        {
            "request": request,
            "member": member_data,
            "errors": errors,
            "GROUPS": groups,
            "htmx": True,
        },
    )


@members_htmx_router.post("/import-validate", response_class=HTMLResponse)
def import_members_validate(request: Request, file: UploadFile = File(...), db: Session = Depends(database.get_db),):
    """
    Handles the member import validation process by parsing the uploaded CSV file
    and rendering a preview of its contents for further review.

    Args:
        request (Request): The HTTP request object representing the incoming
            request, which contains metadata about the client request.
        file (UploadFile): The CSV file uploaded by the user. This file
            contains the data to be parsed and validated.
        db (Session): The database session dependency used for interacting with
            the application's database.

    Returns:
        HTMLResponse: An HTML response that renders the "members_import_preview.html"
        template along with the parsed CSV data for review.
    """
    rows = parse_csv(file)
    validated_rows = validate_rows(rows, db)  # ← VALIDIERUNG HINZUFÜGEN!
    return jinja_templates.TemplateResponse("partials/members_import_preview.html", context(request, db=db, rows=validated_rows))


@members_htmx_router.post("/import-commit")
async def import_members_commit(request: Request, db: Session = Depends(database.get_db)):
    """
    Processes the commit request for importing members by handling the submitted
    form, validating the entries, and saving the members to the database if valid.

    Args:
        request (Request): FastAPI request object to access form data and
            request parameters.
        db (Session): SQLAlchemy database session dependency for interacting
            with the database.

    Returns:
        Response: An HTTP response with status code 204 on successful member import
            or a Jinja template response for handling validation errors or missing
            required fields.
    """
    form = await request.form()

    parsed_rows: dict[int, dict] = {}
    for key, value in form.items():
        if not key.startswith("rows["):
            continue
        try:
            idx_str, field = key.split("][")
            idx = int(idx_str.replace("rows[", ""))
            field = field.rstrip("]")

            if idx not in parsed_rows:
                parsed_rows[idx] = {}
            parsed_rows[idx][field] = value
        except Exception:
            continue

    normalized_rows = []
    for i in sorted(parsed_rows.keys()):
        row = {}
        for field in EXPECTED_FIELDS:
            row[field] = (parsed_rows[i].get(field) or "").strip()
        normalized_rows.append(row)

    validated = validate_rows(normalized_rows, db)

    #  Stoppen, wenn es noch Fehler gibt
    if any(r["_errors"] for r in validated):
        return jinja_templates.TemplateResponse(
            "partials/members_import_preview.html",
            {"request": request, "rows": validated}
        )

    #  Sicherstellen, dass birthdate wirklich gesetzt ist
    for row in validated:
        if not row.get("birthdate"):
            return jinja_templates.TemplateResponse(
                "partials/members_import_preview.html",
                {
                    "request": request,
                    "rows": validated,
                    "error": "Es fehlen Pflichtfelder (Geburtsdatum)."
                }
            )

    # Speichern
    commit_members(db, validated)
    return Response(status_code=204, headers={"HX-Redirect": "/members"})


@members_htmx_router.post("/import-revalidate")
async def import_members_revalidate(
    request: Request,
    db: Session = Depends(database.get_db),   # <-- DB Session einfügen
):
    """
    Processes and validates member data imported in a form, revalidates the content,
    and renders a preview template for review.

    Args:
        request (Request): The HTTP request object containing the form data to process.
        db (Session): Database session dependency to interact with the database.

    Returns:
        HTMLResponse: Renders the "partials/members_import_preview.html" template
        with validated rows for client-side presentation.
    """
    form = await request.form()

    parsed_rows: dict[int, dict] = {}
    for key, value in form.items():
        if not key.startswith("rows["):
            continue
        try:
            idx_str, field = key.split("][")
            idx = int(idx_str.replace("rows[", ""))
            field = field.rstrip("]")

            if idx not in parsed_rows:
                parsed_rows[idx] = {}
            parsed_rows[idx][field] = value
        except Exception:
            continue

    normalized_rows = []
    for i in sorted(parsed_rows.keys()):
        row = {}
        for field in EXPECTED_FIELDS:
            value = (parsed_rows[i].get(field) or "").strip()
            row[field] = value
        normalized_rows.append(row)

    # validate_rows gibt nur die Liste zurück
    validated_rows = validate_rows(normalized_rows,db)

    return jinja_templates.TemplateResponse(
        "partials/members_import_preview.html",
        {
            "request": request,
            "rows": validated_rows,
        }
    )

@members_htmx_router.post("/groups", response_class=HTMLResponse)
def add_group(
    request: Request,
    name: str = Form(...),
    is_default: bool = Form(False),
    db: Session = Depends(database.get_db),
):
    """
    Adds a new group to the database and renders an updated groups list.

    This function handles a POST request to create a new group in the database via the
    'group_service.create_group' method. After creation, it retrieves the updated list of groups
    using 'group_service.list_groups' and renders the groups list template.

    Args:
        request: The HTTP request object.
        name: The name of the group submitted through the form.
        is_default: Indicates whether the new group should be marked as the default.
        db: Database session dependency.
    """
    group_service.create_group(db, name=name.strip(), is_default=is_default)
    groups = group_service.list_groups(db)
    return jinja_templates.TemplateResponse(
        "partials/groups_list.html",
        context(request, db=db, groups=groups),
    )


@members_htmx_router.delete("/groups/{group_id}", response_class=HTMLResponse)
def delete_group(
    group_id: int,
    request: Request,
    db: Session = Depends(database.get_db),
):
    """
    Deletes a group by its ID and updates the group list.

    This endpoint allows a group to be deleted via its unique ID. After deletion,
    the list of groups is updated and rendered using the appropriate HTML template.

    Args:
        group_id (int): The unique identifier of the group to be deleted.
        request (Request): The HTTP request object.
        db (Session): The database session for handling query operations.

    Returns:
        HTMLResponse: A rendered template showing the updated list of groups.
    """
    group_service.delete_group(db, group_id=group_id)
    groups = group_service.list_groups(db)
    return jinja_templates.TemplateResponse(
        "partials/groups_list.html",
        context(request, db=db, groups=groups),
    )


@members_htmx_router.post("/groups/{group_id}", response_class=HTMLResponse)
def update_group(
    group_id: int,
    request: Request,
    name: str = Form(...),
    is_default: bool = Form(False),
    db: Session = Depends(database.get_db),
):
    """
    Updates an existing group with the provided information such as name and
    default status. Utilizes the `group_service` to perform update operations
    in the database and then renders a list of groups using a template.

    Args:
        group_id (int): The ID of the group to update.
        request (Request): The HTTP request object containing metadata about the
            request.
        name (str): The new name for the group, obtained from the form input.
        is_default (bool): A boolean flag to indicate if the group should be set as
            the default group. Defaults to False.
        db (Session): The database session used to execute database operations.

    Returns:
        HTMLResponse: A rendered HTML response containing the updated list of groups.
    """
    g = group_service.update_group(db, group_id=group_id, name=name.strip(), is_default=is_default)
    groups = group_service.list_groups(db)
    return jinja_templates.TemplateResponse(
        "partials/groups_list.html",
        context(request, db=db, groups=groups),
    )

# ==========================================================
#  Mitgliederliste (HTMX-kompatibel, mit Filter)
# ==========================================================

@members_htmx_router.get("/list", response_class=HTMLResponse)
def list_members_htmx(
    request: Request,
    deleted: str = "false",  # Werte: "true", "false", "all"
    db: Session = Depends(database.get_db),
):
    """
    Handles the listing of members based on their deletion status via an HTMX
    compatible endpoint. The response is rendered as HTML using a Jinja2 template.

    Args:
        request (Request): The FastAPI request object.
        deleted (str): Deletion status filter for the members. Accepted values are
            "true" (deleted members), "false" (active members), and "all" (both
            active and deleted members). Default is "false".
        db (Session): SQLAlchemy session dependency, used for database access.

    Returns:
        HTMLResponse: Rendered HTML response containing the member list.
    """
    deleted = (deleted or "").lower().strip()

    if deleted in ("all", "alle"):
        members = member_service.list_members(db, include_deleted=True)
    elif deleted in ("true", "1", "yes", "deleted"):
        members = member_service.list_deleted_members(db)
    else:
        # Default: aktive Mitglieder (nicht gelöscht)
        members = member_service.list_active_members(db)

    return jinja_templates.TemplateResponse(
        "partials/members_list.html",
        context(request, db=db, members=members, deleted=deleted),
    )

@members_htmx_router.delete("/{member_id}", response_class=HTMLResponse)
def soft_delete_member_htmx(member_id: int, request: Request, db: Session = Depends(database.get_db)):
    """
    Soft-deletes a member and returns an updated list of active members.

    This function performs a soft delete operation on a specific member
    based on the given member ID. If the member is successfully soft-deleted,
    it updates the member list and renders the updated list to the client.
    If the member with the given ID cannot be found, an HTTPException with
    status code 404 is raised.

    Args:
        member_id (int): The unique identifier of the member to delete.
        request (Request): The HTTP request instance.
        db (Session): The database session dependency.

    Returns:
        HTMLResponse: Renders the updated member list in an HTML response.
    """
    deleted_member = member_service.soft_delete_member(db, member_id)
    if not deleted_member:
        raise HTTPException(status_code=404, detail="Mitglied nicht gefunden")

    members = member_service.list_active_members(db)
    return jinja_templates.TemplateResponse(
        "partials/members_list.html",
        context(request, db=db, members=members, deleted="false"),
    )

@members_htmx_router.post("/{member_id}/restore", response_class=HTMLResponse)
def restore_member_htmx(member_id: int, request: Request, db: Session = Depends(database.get_db)):
    """
    Restores a deleted member and updates the members list to reflect the changes. If the member
    is not found or not deleted, an HTTPException with status code 404 is raised.

    Args:
        member_id (int): ID of the member to be restored.
        request (Request): The HTTP request object.
        db (Session): Database session dependency.

    Raises:
        HTTPException: If the member is not found or is not in a deleted state.

    Returns:
        HTMLResponse: Rendered HTML response containing the updated members list.
    """
    restored = member_service.restore_member(db, member_id)
    if not restored:
        raise HTTPException(status_code=404, detail="Mitglied nicht gefunden oder nicht gelöscht")

    members = member_service.list_members(db, include_deleted=True)
    return jinja_templates.TemplateResponse(
        "partials/members_list.html",
        context(request, db=db, members=members, deleted="all"),
    )


@members_htmx_router.delete("/{member_id}/wipe", response_class=HTMLResponse)
def wipe_member_htmx(member_id: int, request: Request, db: Session = Depends(database.get_db)):
    """
    Deletes a specific member from the database and updates the list of members.

    This function deletes a member with the specified member ID from the database.
    If the member cannot be located or deleted, a 404 HTTPException is raised. After
    the deletion, the function fetches an updated list of members, including deleted
    ones, and returns a rendered HTML response containing the updated members list.

    Args:
        member_id (int): The unique identifier of the member to be deleted.
        request (Request): The HTTP request object.
        db (Session): The database session dependency for executing database
            operations.

    Returns:
        HTMLResponse: An HTML response containing the updated list of members.

    Raises:
        HTTPException: If the member cannot be found or deleted, an exception with
            a 404 status code is raised.
    """
    success = member_service.wipe_member(db, member_id, force=True)
    if not success:
        raise HTTPException(status_code=404, detail="Mitglied nicht gefunden oder konnte nicht gelöscht werden")

    members = member_service.list_members(db, include_deleted=True)
    return jinja_templates.TemplateResponse(
        "partials/members_list.html",
        context(request, db=db, members=members, deleted="all"),
    )
