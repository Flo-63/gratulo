"""
===============================================================================
Project   : gratulo
Module    : app/services/template_service.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides services for managing templates.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""


from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.core import models


def get_templates(db: Session):
    """
    Fetches and returns all templates from the database, ordered by their names
    in ascending order.

    Args:
        db (Session): An active SQLAlchemy database session.

    Returns:
        list: A list of Template objects retrieved from the database, ordered
        by their names in ascending order.
    """
    return db.query(models.Template).order_by(models.Template.name.asc()).all()


def get_template(db: Session, template_id: int):
    """
    Retrieves a template from the database by its ID.

    This function queries the database to find a template with the given ID. If
    no template is found, it raises an HTTPException with a 404 status code.

    Args:
        db (Session): The database session used for querying.
        template_id (int): The ID of the template to retrieve.

    Returns:
        Template: The template object matching the provided ID, if found.

    Raises:
        HTTPException: If no template is found with the provided ID, raises an
        exception with a 404 status and an error message.
    """
    template = db.query(models.Template).filter(models.Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template nicht gefunden")
    return template


def save_template(db: Session, id: int | None, name: str, content_html: str):
    """
    Saves a template to the database. If an ID is provided, it updates the existing template.
    Otherwise, it creates a new template. The function ensures the template name is unique.

    Args:
        db (Session): SQLAlchemy database session used to perform database operations.
        id (int | None): ID of the template to update. If None, a new template will be created.
        name (str): Name of the template. The name must be non-empty and unique.
        content_html (str): HTML content of the template. If not provided, an empty string
            will be used.

    Raises:
        HTTPException: Raised with a status code 400 if the name is empty or if the
            given name is already in use by another template.

    Returns:
        models.Template: The saved or updated template object.
    """
    name_clean = (name or "").strip()
    if not name_clean:
        raise HTTPException(status_code=400, detail="Name darf nicht leer sein")

    # Name-Unique prüfen
    q = db.query(models.Template).filter(models.Template.name == name_clean)
    if id:
        q = q.filter(models.Template.id != id)
    if q.first():
        raise HTTPException(status_code=400, detail=f"Template-Name '{name_clean}' ist bereits vergeben")

    template = db.query(models.Template).filter(models.Template.id == id).first() if id else models.Template()

    template.name = name_clean
    template.content_html = content_html or ""

    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def delete_template(db: Session, template_id: int):
    """
    Deletes a template from the database.

    This function retrieves a template using its ID, deletes it, and commits the changes
    to the database.

    Args:
        db: Database session object used to interact with the database.
        template_id: Unique identifier of the template to be deleted.
    """
    template = get_template(db, template_id)
    db.delete(template)
    db.commit()
