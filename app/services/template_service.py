from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.core import models


def get_templates(db: Session):
    """
    Fetches and returns all template records from the database, ordered by their name
    in ascending order.

    :param db: Database session required to query the template records.
    :type db: Session
    :return: A list of templates ordered alphabetically by their name.
    :rtype: List[Template]
    """
    return db.query(models.Template).order_by(models.Template.name.asc()).all()


def get_template(db: Session, template_id: int):
    """
    Retrieves a specific template from the database based on the provided template ID.

    The function queries the database to find a template that matches the given template ID.
    If the template is not found, it raises an exception with a 404 status code and an error
    message indicating that the template was not found.

    :param db: Database session used for querying.
    :param template_id: The unique identifier of the template to retrieve.
    :return: The template object if found.
    :rtype: models.Template, optional
    :raises HTTPException: If no template is found with the given ID.
    """
    template = db.query(models.Template).filter(models.Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template nicht gefunden")
    return template


def save_template(db: Session, id: int | None, name: str, content_html: str):
    """
    Save or update a template in the database. If an `id` is provided, the existing template with the given `id`
    is updated. Otherwise, a new template is created. The `name` of the template must be unique. If the template
    name is empty or already exists, an `HTTPException` with status code 400 is raised.

    :param db: Database session object used for querying and committing changes.
    :type db: Session
    :param id: The unique identifier of the template to update. If None, a new template is created.
    :type id: int | None
    :param name: The name of the template. It must be unique and cannot be empty.
    :type name: str
    :param content_html: The HTML content of the template.
    :type content_html: str
    :return: The saved or updated template object.
    :rtype: models.Template
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
    Delete a specific template from the database by its ID.

    This function removes a template identified by its unique ID from the
    provided database session. After successfully deleting the template, the
    changes are committed to the database.

    :param db: The database session used for querying and modifying the templates.
    :type db: Session
    :param template_id: The unique identifier of the template to be deleted.
    :type template_id: int
    :return: None
    """
    template = get_template(db, template_id)
    db.delete(template)
    db.commit()
