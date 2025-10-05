# app/htmx/members_htmx.py
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
    Builds a context dictionary for use in a given request context.

    This function retrieves a list of groups from the database using the group service
    and constructs a context dictionary, combining the request data, retrieved groups,
    and any additional keyword arguments provided.

    :param request: The HTTP request object.
    :type request: Request
    :param db: The database session used for retrieving the groups.
    :type db: Session
    :param extra: Additional keyword arguments to include in the context dictionary.
    :type extra: dict
    :return: A dictionary containing the request object, groups, and any additional data.
    :rtype: dict
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
    errors = []

    # 🧩 UI-Logik bleibt vollständig erhalten (Alter, Format, UX)
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

    # 🧩 Template-Fehleranzeige (unverändert)
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

    # 🧩 Speicherung mit zentraler Service-Funktion
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

    # 🧩 Fehlerhafte Speicherung → UI bleibt unverändert
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
    Handles the import and validation of members from a CSV file.

    This function receives a file uploaded via a POST request and attempts
    to parse the file as a CSV. If successful, the parsed data (rows) are
    used as context for rendering a template. This process allows validation
    and preview of the imported members data before any further actions are
    performed.

    :param request: The incoming HTTP request.
    :type request: Request
    :param file: The file uploaded by the client, expected to be a CSV file.
    :type file: UploadFile
    :return: An HTML response rendering the preview of the members data.
    :rtype: HTMLResponse
    """
    rows = parse_csv(file)
    return jinja_templates.TemplateResponse("partials/members_import_preview.html", context(request, db=db, rows=rows))


@members_htmx_router.post("/import-commit")
async def import_members_commit(request: Request, db: Session = Depends(database.get_db)):
    """
    Handles the POST request for importing and committing member data. This function
    parses, validates, and processes the incoming data, ensuring all required fields
    are present. If validation errors exist, it responds with the appropriate error
    message within the preview template. If the data passes validation, it saves the
    information to the database and returns a redirect response.

    :param request: The incoming HTTP request containing the form data to be processed.
                    Form data includes rows of information about members.
                    Type: Request
    :param db: The database session utilized for committing the validated member data.
               Dependency injected via FastAPI's Depends.
               Type: Session
    :return: If validation errors exist, returns a Jinja2 template response with the
             error details and the submitted rows. If validation is successful, the
             function commits the data to the database and returns a 204 No Content
             response with a redirect header.
    :rtype: Union[TemplateResponse, Response]
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
    Handles the POST request for importing and revalidating member data. Parses and
    processes incoming form data to construct normalized rows and validates them
    before rendering a preview template with the processed data.

    :param request: The HTTP request object containing form data for processing.
    :type request: Request

    :return: TemplateResponse containing a preview of the validated member data.
    :rtype: TemplateResponse
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
    g = group_service.update_group(db, group_id=group_id, name=name.strip(), is_default=is_default)
    groups = group_service.list_groups(db)
    return jinja_templates.TemplateResponse(
        "partials/groups_list.html",
        context(request, db=db, groups=groups),
    )

# ==========================================================
# 🧩 Mitgliederliste (HTMX-kompatibel, mit Filter)
# ==========================================================
@members_htmx_router.get("/list", response_class=HTMLResponse)
def list_members_htmx(
    request: Request,
    deleted: str = "false",  # Werte: "true", "false", "all"
    db: Session = Depends(database.get_db),
):
    """
    Gibt eine HTML-Teilansicht (Partial) mit der Mitgliederliste zurück.
    Unterstützt Filter für aktive, gelöschte oder alle Mitglieder.
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
    Markiert ein Mitglied als gelöscht (Soft Delete).
    """
    deleted_member = member_service.soft_delete_member(db, member_id)
    if not deleted_member:
        raise HTTPException(status_code=404, detail="Mitglied nicht gefunden")

    members = member_service.list_active_members(db)
    return jinja_templates.TemplateResponse(
        "partials/members_list.html",
        context(request, db=db, members=members),
    )

@members_htmx_router.post("/{member_id}/restore", response_class=HTMLResponse)
def restore_member_htmx(member_id: int, request: Request, db: Session = Depends(database.get_db)):
    """
    Stellt ein zuvor soft-gelöschtes Mitglied wieder her.
    """
    restored = member_service.restore_member(db, member_id)
    if not restored:
        raise HTTPException(status_code=404, detail="Mitglied nicht gefunden oder nicht gelöscht")

    members = member_service.list_members(db, include_deleted=True)
    return jinja_templates.TemplateResponse(
        "partials/members_list.html",
        context(request, db=db, members=members),
    )


@members_htmx_router.delete("/{member_id}/wipe", response_class=HTMLResponse)
def wipe_member_htmx(member_id: int, request: Request, db: Session = Depends(database.get_db)):
    """
    Löscht ein Mitglied dauerhaft aus der Datenbank.
    """
    success = member_service.wipe_member(db, member_id, force=True)
    if not success:
        raise HTTPException(status_code=404, detail="Mitglied nicht gefunden oder konnte nicht gelöscht werden")

    members = member_service.list_members(db, include_deleted=True)
    return jinja_templates.TemplateResponse(
        "partials/members_list.html",
        context(request, db=db, members=members),
    )
