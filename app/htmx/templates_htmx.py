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


import io
import json
import os
import re
from pathlib import Path
from fastapi import APIRouter, Depends, Form, Request, Response, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from PIL import Image, UnidentifiedImageError

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.core.auth import require_admin
from app.core.deps import jinja_templates, context, UPLOADS_DIR
from app.services import template_service

templates_htmx_router = APIRouter(
    prefix="/htmx/templates",
    include_in_schema=False,
    dependencies=[Depends(require_admin)],
)

# Upload-Verzeichnis konfigurieren
UPLOAD_DIR =  str(UPLOADS_DIR)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Upload-Härtung: maximale Größe und erlaubte Bildformate.
# Die Endung wird aus dem *erkannten* Format abgeleitet (nicht aus dem
# Client-Dateinamen), damit nichts als text/html o. Ä. ausgeliefert werden kann.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_IMAGE_FORMATS = {
    "PNG": ".png",
    "JPEG": ".jpg",
    "GIF": ".gif",
    "WEBP": ".webp",
}


@templates_htmx_router.get("/list")
def templates_list(request: Request, db: Session = Depends(get_db)):
    """
    Handles the route to retrieve and display the list of templates.

    This function fetches a list of templates from the database by invoking the
    template_service and renders an HTML response using Jinja templates.

    Args:
        request (Request): The HTTP request object from the client.
        db (Session): The database session dependency provided by FastAPI.

    Returns:
        TemplateResponse: The rendered HTML response containing the list of templates.
    """
    templates = template_service.get_templates(db)
    ctx = context(request, templates=templates)
    return jinja_templates.TemplateResponse(
        request=request,
        name="partials/templates_list.html",
        context=ctx
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
    Handles the saving of a template submitted via an HTTP POST request. This method
    processes form data containing template details (id, name, and content_html),
    handles saving the template into the database, and returns an appropriate
    response. If the operation is successful, it redirects the user to the templates
    overview.

    Args:
        request: The incoming HTTP request object.
        db: Database session dependency.
        id: The unique identifier of the template, optionally provided.
        name: The name of the template. This field is required.
        content_html: The HTML content of the template. Defaults to an empty string.

    Returns:
        A Response object with no content and an HTTP status code of 204. Redirects
        the user to the "/templates" route using the HX-Redirect header.
    """
    template_id = int(id) if id and id.strip() else None
    template_service.save_template(db, template_id, name, content_html)
    return Response(status_code=204, headers={"HX-Redirect": "/templates"})


@templates_htmx_router.delete("/{template_id}", response_class=Response)
def delete_template(template_id: int, db: Session = Depends(get_db)):
    """
    Deletes a template specified by its ID. Upon successful deletion, it triggers a client-side redirection to the
    templates page. If the template is currently in use by any job(s), it sends a notification to the client,
    indicating that the template cannot be deleted.

    Args:
        template_id (int): The unique identifier of the template to delete.
        db (Session): The database session instance for performing database operations.

    Returns:
        Response or HTMLResponse: A Response with HTTP status code 204 upon successful deletion. If the template cannot
        be deleted due to integrity constraints, returns an HTMLResponse with inline JavaScript to display a notification.

    Raises:
        IntegrityError: Raised when there are integrity constraints preventing the deletion of the template.
    """
    try:
        template_service.delete_template(db, template_id)
        return Response(status_code=204, headers={"HX-Redirect": "/templates"})

    except IntegrityError:
        db.rollback()

        # CSP-safe notification: no inline script. htmx dispatches the HX-Trigger
        # event, which the "notify" listener turns into a toast + reload.
        trigger = json.dumps({
            "notify": {
                "message": "Template ist noch in Job(s) in Benutzung. Bitte erst Jobs bearbeiten!",
                "type": "error",
                "reload": True,
            }
        })
        return Response(status_code=200, headers={"HX-Trigger": trigger, "HX-Reswap": "none"})

@templates_htmx_router.get("/list-images", response_class=JSONResponse)
def list_images():
    """
    Retrieve a sorted list of image URLs from the upload directory.

    This function retrieves all image files from the specified upload directory, filters out files that
    do not correspond to valid image formats, and sorts them by their last modification time in descending
    order. The resulting list of image URLs is returned as a JSON response.

    Raises:
        FileNotFoundError: If the upload directory does not exist, an empty list is returned.

    Returns:
        JSONResponse: A JSON response containing a list of image URLs sorted by modification time
        in descending order.
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
    Uploads an image file to the server after strict validation.

    The upload is rejected unless the raw bytes decode as a real image in an
    allowed format (PNG, JPEG, GIF, WEBP). The stored filename is sanitized and
    its extension is derived from the *detected* image format — never from the
    client-supplied name — so a caller cannot control the served content type or
    escape the upload directory via path traversal. The size is capped and the
    resolved path is confirmed to stay inside the upload directory.

    Args:
        file (UploadFile): The uploaded image file.

    Returns:
        dict: A dictionary containing the file's location as a relative URL under
        the 'location' key.

    Raises:
        HTTPException: If the file is empty, too large, not a valid image, or of
        an unsupported format.
    """
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Leere Datei")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Datei zu groß (max. 5 MB)")

    # Inhalt als echtes Bild validieren (blockt HTML/Skript/Polyglot-Uploads)
    try:
        with Image.open(io.BytesIO(data)) as img:
            img_format = (img.format or "").upper()
            img.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail="Keine gültige Bilddatei")

    if img_format not in ALLOWED_IMAGE_FORMATS:
        raise HTTPException(
            status_code=400,
            detail="Nicht unterstütztes Bildformat (erlaubt: PNG, JPEG, GIF, WEBP)",
        )

    # Endung aus dem erkannten Format erzwingen, nie aus dem Client-Namen
    ext = ALLOWED_IMAGE_FORMATS[img_format]

    # Dateinamen säubern: nur Basename, nur unbedenkliche Zeichen, keine "..".
    raw_base = os.path.splitext(os.path.basename(file.filename or "upload"))[0]
    safe_base = re.sub(r"[^A-Za-z0-9._-]", "_", raw_base).strip("._") or "upload"

    filename = f"{safe_base}{ext}"
    save_path = os.path.join(UPLOAD_DIR, filename)

    # Namenskollisionen auflösen
    counter = 1
    while os.path.exists(save_path):
        filename = f"{safe_base}_{counter}{ext}"
        save_path = os.path.join(UPLOAD_DIR, filename)
        counter += 1

    # Defense in depth: sicherstellen, dass der Zielpfad im Upload-Ordner bleibt
    upload_root = os.path.realpath(UPLOAD_DIR)
    if os.path.commonpath([upload_root, os.path.realpath(save_path)]) != upload_root:
        raise HTTPException(status_code=400, detail="Ungültiger Dateiname")

    with open(save_path, "wb") as buffer:
        buffer.write(data)

    return {"location": f"/uploads/{filename}"}
