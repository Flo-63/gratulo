from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.core.deps import jinja_templates, context
from app.core import database, models
from app.core.auth import require_admin
from app.services import member_service, group_service

members_ui_router = APIRouter(prefix="/members",include_in_schema=False)

@members_ui_router.get("", response_class=HTMLResponse)
async def members_page(request: Request, db: Session = Depends(database.get_db)):
    """
    Handles the rendering of the members page. Uses Jinja2 templates to render the
    page with the required context. Retrieves the last imported metadata from the
    database to include it in the rendered page.

    :param request: HTTP request object containing request-specific information
        such as headers, URL parameters, and other metadata.
    :type request: Request
    :param db: Dependency-injected database session used to query the metadata
        table for import information.
    :return: Rendered HTML response displaying the members page, including
        last imported metadata if available.
    :rtype: HTMLResponse
    """
    # ImportMeta holen (kann None sein, wenn noch nie importiert)
    meta = db.query(models.ImportMeta).first()
    return jinja_templates.TemplateResponse(
        "members.html",
        context(request, last_imported=meta.last_imported if meta else None)
    )

@members_ui_router.get("/list", response_class=HTMLResponse)
async def members_list(request: Request, db: Session = Depends(database.get_db)):
    """
    Fetch and display the list of members using the centralized service layer.
    """
    members = member_service.list_members(db)
    return jinja_templates.TemplateResponse(
        "partials/members_list.html",
        context(request, members=members)
    )

@members_ui_router.get("/new", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def new_member_page(request: Request, db: Session = Depends(database.get_db)):
    """
    Handles the HTTP GET request for rendering the member editor page in the
    admin panel. The response is generated with the specified Jinja2 template,
    using the provided request context.

    :param request: The incoming HTTP request object.
    :type request: Request
    :return: An HTML response rendered from the member editor template.
    :rtype: HTMLResponse
    """
    groups = group_service.list_groups(db)
    return jinja_templates.TemplateResponse("member_editor.html", context(request, member=None,  GROUPS=groups))

@members_ui_router.get("/{member_id}/edit", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def edit_member_page(request: Request, member_id: int, db: Session = Depends(database.get_db)):
    """
    Handles the request to display the member edit page.

    This endpoint renders the HTML page to edit the details of a specific member
    identified by their unique ID. The provided member ID is validated and fetched
    from the database. If the member is not found, an error is raised.

    :param request: The request object containing details about the incoming request.
    :type request: Request
    :param member_id: The unique identifier for the member to edit.
    :type member_id: int
    :param db: The database session dependency used for executing database queries.
    :type db: Session
    :return: The rendered HTML page for editing the member.
    :rtype: HTMLResponse
    :raises HTTPException: If the member with the specified ID is not found.
    """
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Mitglied nicht gefunden")
    groups = group_service.list_groups(db)
    return jinja_templates.TemplateResponse("member_editor.html", context(request, member=member,  GROUPS=groups))

@members_ui_router.get("/groups", response_class=HTMLResponse)
async def groups_list(request: Request, db: Session = Depends(database.get_db)):
    groups = group_service.list_groups(db)
    return jinja_templates.TemplateResponse(
        "partials/groups_list.html",
        context(request, groups=groups)
    )
