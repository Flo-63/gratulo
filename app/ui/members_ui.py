"""
===============================================================================
Project   : gratulo
Module    : app/ui/members_ui.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides the UI for managing members.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""



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
    Handles the rendering of the members page.

    Given the incoming request, the function queries the database for an import meta
    record, which stores metadata about the last import operation. It uses this
    information to render the members page with the appropriate context.

    Args:
        request (Request): The HTTP request object.
        db (Session): Database session, injected as a dependency.

    Returns:
        HTMLResponse: Renders the HTML template for the members page with necessary
        context.
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
    Handles the endpoint to display the list of members. Retrieves members from
    the database and renders the appropriate HTML template with the list of
    members included in the context.

    Args:
        request (Request): Incoming HTTP request.
        db (Session): Database session dependency.

    Returns:
        HTMLResponse: Rendered HTML response with the members list.
    """
    members = member_service.list_members(db)
    return jinja_templates.TemplateResponse(
        "partials/members_list.html",
        context(request, members=members)
    )

@members_ui_router.get("/new", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def new_member_page(request: Request, db: Session = Depends(database.get_db)):
    """
    Handles the creation of a new member page.

    This endpoint serves a webpage for creating a new member profile.
    It generates a page using `jinja_templates` and populates the
    context with necessary data for creating a new member.

    Args:
        request: The incoming HTTP request object.
        db: Database session dependency retrieved from the application context.

    Returns:
        HTMLResponse: A rendered HTML page generated using the Jinja2 template
        engine.
    """
    groups = group_service.list_groups(db)
    return jinja_templates.TemplateResponse("member_editor.html", context(request, member=None,  GROUPS=groups))

@members_ui_router.get("/{member_id}/edit", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def edit_member_page(request: Request, member_id: int, db: Session = Depends(database.get_db)):
    """Handles the request to render the member editing page for a specific member.

    This function is responsible for fetching the details of a member from
    the database and rendering the member editing page. It retrieves the
    list of groups from the database and populates the page with the
    relevant data. If the specified member is not found, an HTTPException
    with a 404 status code is raised.

    Args:
        request (Request): The HTTP request object.
        member_id (int): The unique identifier of the member to be edited.
        db (Session): The database session for executing queries.

    Returns:
        TemplateResponse: The rendered HTML response for the member editing page.

    Raises:
        HTTPException: If the member with the specified ID is not found.
    """
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Mitglied nicht gefunden")
    groups = group_service.list_groups(db)
    return jinja_templates.TemplateResponse("member_editor.html", context(request, member=member,  GROUPS=groups))

@members_ui_router.get("/groups", response_class=HTMLResponse)
async def groups_list(request: Request, db: Session = Depends(database.get_db)):
    """
    Fetches and returns a rendered HTML response containing a list of groups.

    This endpoint interacts with the database to retrieve group information
    and renders the groups list using a specified Jinja2 template.

    Args:
        request: The HTTP request object, containing metadata about the client request.
        db: A database session dependency, used to interact with the database.

    Returns:
        HTMLResponse: A rendered HTML response containing the groups list.
    """
    groups = group_service.list_groups(db)
    return jinja_templates.TemplateResponse(
        "partials/groups_list.html",
        context(request, groups=groups)
    )
