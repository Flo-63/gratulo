"""
===============================================================================
Project   : gratulo
Module    : app/htmx/templates_htmx.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides HTTP endpoints for managing templates.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""


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
    Handles the route to retrieve and render the list of templates. The function
    interacts with the service layer to get the templates data from the database
    and then renders the data into an HTML template using Jinja.

    Args:
        request (Request): The incoming HTTP request object containing metadata
            and other request-related information.
        db (Session): The database session used to query the templates.

    Returns:
        TemplateResponse: A response generated using Jinja to render the
        "partials/templates_list.html" template with the provided context data.
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
    Saves a template to the database with provided details. If the `id` is not
    provided or empty, a new template is created; otherwise, an existing template
    with the given `id` is updated. Once saved, redirects to the `/templates`
    route.

    Args:
        request (Request): The incoming HTTP request object.
        db (Session): Database session dependency.
        id (str | None): The identifier of the template to be updated, or None for
            creating a new template.
        name (str): The name of the template.
        content_html (str): The HTML content of the template.

    Returns:
        Response: HTTP response with a status code of 204 and a redirect header
        to the `/templates` route.
    """
    template_id = int(id) if id and id.strip() else None
    template_service.save_template(db, template_id, name, content_html)
    return Response(status_code=204, headers={"HX-Redirect": "/templates"})


@templates_htmx_router.delete("/{template_id}", response_class=Response)
def delete_template(template_id: int, db: Session = Depends(get_db)):
    """
    Deletes a specified template from the database.

    This endpoint allows the removal of a template based on its unique identifier.
    Upon successful deletion, the server responds with a 204 No Content status and
    redirects the user to the templates list.

    Args:
        template_id (int): The unique identifier of the template to be deleted.
        db (Session): The database session dependency for performing database
            operations.

    Returns:
        Response: An HTTP response with a 204 No Content status and an
            "HX-Redirect" header pointing to "/templates".
    """
    template_service.delete_template(db, template_id)
    return Response(status_code=204, headers={"HX-Redirect": "/templates"})


@templates_htmx_router.get("/list-images", response_class=JSONResponse)
def list_images():
    """
    Lists image files from the upload directory and returns their URLs as a JSON response.

    This function retrieves all image files from the specified upload directory, filters
    them based on supported image formats, and sorts them by their last modified time
    in descending order. The URLs of the image files are then returned as a JSON response.

    Raises:
        FileNotFoundError: If the upload directory does not exist.

    Returns:
        JSONResponse: A JSON response containing a list of URLs for the retrieved image files.
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
    Handles image upload and saves the file to the specified directory while ensuring
    that the filename does not collide with existing files in the directory.

    Args:
        file: The image file uploaded by the user.

    Returns:
        dict: A dictionary containing the file location as a key-value pair.
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
