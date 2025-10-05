import os
from pathlib import Path
from fastapi import APIRouter, Depends, Form, Request, Response, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import jinja_templates, context, UPLOADS_DIR
from app.services import template_service

templates_htmx_router = APIRouter(prefix="/htmx/templates", include_in_schema=False)

# Upload-Verzeichnis konfigurieren
UPLOAD_DIR =  str(UPLOADS_DIR)
os.makedirs(UPLOAD_DIR, exist_ok=True)


@templates_htmx_router.get("/list")
def templates_list(request: Request, db: Session = Depends(get_db)):
    """
    Fetches the list of templates and renders the templates list HTML
    partial using Jinja templates. Integrates with the database for
    data retrieval and handles the HTTP request.

    :param request: HTTP request object containing metadata and
        request information
    :type request: Request
    :param db: Database session instance for retrieving templates
    :type db: Session
    :return: Rendered HTML response containing the templates list
    :rtype: TemplateResponse
    """
    templates = template_service.get_templates(db)
    return jinja_templates.TemplateResponse(
        "partials/templates_list.html",
        context(request, templates=templates)
    )


@templates_htmx_router.post("", response_class=Response)
@templates_htmx_router.post("/", response_class=Response)
def save_template(
    request: Request,
    db: Session = Depends(get_db),
    id: str | None = Form(None),
    name: str = Form(...),
    content_html: str = Form(""),
):
    """
    Handles the saving of a template through an HTTP POST request. This functionality
    allows saving or updating templates identified by their ID and associated with a
    name and HTML content. The operation is backed by a database session and ensures
    a proper response with an HTTP status code and redirection headers.

    :param request: The incoming HTTP request object.
    :type request: Request
    :param db: The database session dependency for executing operations.
    :type db: Session
    :param id: The optional identifier of the template to be updated. If not provided,
        a new template creation is assumed.
    :type id: str | None
    :param name: The name of the template to be saved. This is a required parameter.
    :type name: str
    :param content_html: The HTML content of the template. Defaults to an empty string
        if not provided.
    :type content_html: str
    :return: A Response object with status code 204 and redirection headers.
    :rtype: Response
    """
    template_id = int(id) if id and id.strip() else None
    template_service.save_template(db, template_id, name, content_html)
    return Response(status_code=204, headers={"HX-Redirect": "/templates"})


@templates_htmx_router.delete("/{template_id}", response_class=Response)
def delete_template(template_id: int, db: Session = Depends(get_db)):
    """
    Deletes a template with a specified ID from the database. This operation
    is permanent and cannot be undone. Upon successful deletion, the response
    will redirect the user to the `/templates` page.

    :param template_id: The ID of the template to delete.
    :type template_id: int
    :param db: The database session to use for performing the delete operation.
    :type db: Session
    :return: A response indicating the deletion status with a redirect header.
    :rtype: Response
    """
    template_service.delete_template(db, template_id)
    return Response(status_code=204, headers={"HX-Redirect": "/templates"})


# =========================
#  NEUE ENDPOINTS
# =========================

from fastapi.responses import JSONResponse

@templates_htmx_router.get("/list-images", response_class=JSONResponse)
def list_images():
    """
    List all images from the upload directory that match supported file types.

    The function fetches all files from the UPLOAD_DIR directory, filters out
    non-image files and unsupported formats, sorts them by their modification
    time in descending order, and returns only the URLs of the image files.

    :return: A JSONResponse containing a list of URLs of the image files.
    :rtype: JSONResponse
    """
    try:
        paths = [Path(UPLOAD_DIR) / f for f in os.listdir(UPLOAD_DIR)]
    except FileNotFoundError:
        paths = []

    # Nur Bilddateien berücksichtigen
    images = [
        (p.stat().st_mtime, f"/uploads/{p.name}")
        for p in paths
        if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".webp")
    ]

    # Nach Änderungszeit sortieren, neueste zuerst
    images.sort(key=lambda x: x[0], reverse=True)

    # Nur die URLs zurückgeben
    return JSONResponse(content=[url for _, url in images])


@templates_htmx_router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """
    Upload an image to the server. This function handles the file upload process, ensures
    that the uploaded file's name does not collide with existing files, saves the file
    to the server, and returns the location of the uploaded file.

    :param file: The image file to be uploaded.
    :type file: UploadFile

    :return: A JSON response with the location of the uploaded file.
    :rtype: dict
    """
    filename = file.filename
    save_path = os.path.join(UPLOAD_DIR, filename)

    # Sicherstellen, dass der Dateiname nicht kollidiert
    base, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(save_path):
        filename = f"{base}_{counter}{ext}"
        save_path = os.path.join(UPLOAD_DIR, filename)
        counter += 1

    with open(save_path, "wb") as buffer:
        buffer.write(await file.read())

    return {"location": f"/uploads/{filename}"}
