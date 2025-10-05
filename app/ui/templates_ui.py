from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from starlette.responses import HTMLResponse
from app.core.database import get_db
from app.core.deps import jinja_templates, context
from app.services import template_service

templates_ui_router = APIRouter(prefix="/templates", include_in_schema=False)


@templates_ui_router.get("", response_class=HTMLResponse)
async def templates_page(request: Request, db: Session = Depends(get_db)):
    """
    Handles requests to render the templates page and fetches the templates
    from the database for display. The templates are processed with the
    Jinja 2 template engine and returned as an HTML response.

    :param request: The HTTP request object.
    :type request: Request
    :param db: The database session dependency.
    :type db: Session
    :return: Rendered HTML response of the templates page.
    :rtype: HTMLResponse
    """
    templates = template_service.get_templates(db)
    return jinja_templates.TemplateResponse(
        "templates.html",
        context(request, templates=templates)
    )


@templates_ui_router.get("/new", response_class=HTMLResponse)
async def new_template_page(request: Request):
    """
    Handles the request to render the new template editor page.

    :param request: Request object containing client request data
    :return: An HTML response rendering the template editor page
    """
    return jinja_templates.TemplateResponse(
        "template_editor.html",
        context(request, template=None)
    )


@templates_ui_router.get("/{template_id}/edit", response_class=HTMLResponse)
async def edit_template_page(request: Request, template_id: int, db: Session = Depends(get_db)):
    """
    Retrieve and render the HTML editor page for a specific template.

    This endpoint fetches a template based on the provided template ID from the
    database, and then renders the template editor page using the retrieved
    template data.

    :param request: The HTTP request object, providing details about the current
        HTTP request context, such as headers, path, and method.
    :type request: Request
    :param template_id: The identification number of the template to retrieve and
        edit.
    :type template_id: int
    :param db: A database session used to interact with persistence storage.
    :type db: Session, optional
    :return: An HTML response displaying the template editor page populated with
        the data of the specified template.
    :rtype: HTMLResponse

    :raises HTTPException: If the specified template is not found (404).
    """
    template = template_service.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template nicht gefunden")

    return jinja_templates.TemplateResponse(
        "template_editor.html",
        context(request, template=template)
    )
