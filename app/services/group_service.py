"""
===============================================================================
Project   : gratulo
Module    : app/services/group_service.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides functions for managing groups for UI and API Endpoints

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""



from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import update

from app.core import models


def list_groups(db: Session) -> list[models.Group]:
    """
    Fetches and returns a list of all groups from the database, sorted by the group's name.

    Args:
        db (Session): The database session used to interact with the database.

    Returns:
        list[models.Group]: A list of group instances, ordered by their name.
    """
    return db.query(models.Group).order_by(models.Group.name).all()

def get_default_group(db: Session) -> models.Group | None:
    """
    Fetches the default group from the database.

    This function queries the database for a group marked as the default group
    and returns it. If no such group exists, it returns None.

    Args:
        db (Session): SQLAlchemy session object for database interaction.

    Returns:
        models.Group | None: The default group if found, otherwise None.
    """
    return db.query(models.Group).filter_by(is_default=True).first()

def get_group(db: Session, group_id: int) -> models.Group:
    """
    Retrieve a specific group by its ID from the database.

    This function queries the database to find and return a group object
    corresponding to the provided group ID. If the group is not found, an
    HTTPException is raised with a 404 status code.

    Args:
        db: Database session used for querying.
        group_id: Unique identifier of the group to retrieve.

    Returns:
        The group object corresponding to the specified ID.

    Raises:
        HTTPException: If no group is found with the given ID, raises an
        exception with 404 status.
    """
    g = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Gruppe nicht gefunden")
    return g


def create_group(
    db: Session,
    name: str,
    is_default: bool = False,
    *,
    logger=None,
    audit_logger=None
) -> models.Group:
    """
    Creates a new group in the database, ensuring proper validations and default group
    behavior. Logs the creation via provided loggers if applicable.

    Args:
        db (Session): The database session used to create the group.
        name (str): The name of the group to be created. Must not be empty or only whitespace.
        is_default (bool, optional): Indicates if the new group should be the default group.
            If True, updates all other groups to non-default. Defaults to False.
        logger (Optional): Optional logger to log informational messages about the group
            creation. Defaults to None.
        audit_logger (Optional): Optional logger to log audit trail messages for the group
            creation. Defaults to None.

    Raises:
        HTTPException: If the group name is empty or already exists in the database.

    Returns:
        models.Group: The newly created group object.
    """
    name_clean = (name or "").strip()
    if not name_clean:
        raise HTTPException(status_code=400, detail="Gruppenname darf nicht leer sein")

    if db.query(models.Group).filter(models.Group.name == name_clean).first():
        raise HTTPException(status_code=400, detail=f"Gruppe '{name_clean}' existiert bereits")

    if is_default:
        db.query(models.Group).update({models.Group.is_default: False})

    g = models.Group(name=name_clean, is_default=is_default)
    db.add(g)
    db.commit()
    db.refresh(g)

    ensure_default_exists(db)

    if logger:
        logger.info(f"👥 Gruppe erstellt: {g.name} (ID={g.id}, default={g.is_default})")
    if audit_logger:
        audit_logger.info(f"CREATE group_id={g.id}, default={g.is_default}")

    return g



def update_group(db: Session, group_id: int, name: str, is_default: bool = False) -> models.Group:
    """
    Updates an existing group in the database with the provided details. It ensures
    unique group names, trims leading and trailing spaces from the name, and optionally
    sets the group as the default one. If the group is marked as default, all other
    groups are updated to not be the default. Lastly, it ensures that at least one
    default group exists after the update.

    Args:
        db (Session): The database session used to query and update data.
        group_id (int): The unique identifier of the group to be updated.
        name (str): The new name for the group. It cannot be empty or a duplicate of
            another group's name.
        is_default (bool, optional): Indicates whether the group should be marked as
            the default group. Defaults to False.

    Returns:
        models.Group: The updated group object.

    Raises:
        HTTPException: If the provided name is empty or already exists in another group.
    """
    g = get_group(db, group_id)

    name_clean = (name or "").strip()
    if not name_clean:
        raise HTTPException(status_code=400, detail="Gruppenname darf nicht leer sein")

    if db.query(models.Group).filter(models.Group.name == name_clean, models.Group.id != group_id).first():
        raise HTTPException(status_code=400, detail=f"Gruppe '{name_clean}' existiert bereits")

    g.name = name_clean

    if is_default:
        # alle anderen zurücksetzen
        db.query(models.Group).update({models.Group.is_default: False})
        g.is_default = True

    db.commit()
    db.refresh(g)

    ensure_default_exists(db)
    return g


def delete_group(db: Session, group_id: int) -> None:
    """
    Deletes a specific group by its ID from the database. If the deleted group
    was marked as a default group, ensures another default group exists.

    Args:
        db: Database session for the current operation.
        group_id: Unique identifier of the group to be deleted.

    """
    g = get_group(db, group_id)
    was_default = g.is_default

    db.delete(g)
    db.commit()

    # immer eine Defaultgruppe garantieren
    if was_default:
        ensure_default_exists(db)


def ensure_default_exists(db: Session) -> models.Group:
    """Ensures that a default group exists in the database.

    This function checks for the existence of a group marked as default in the database.
    If a default group exists, it is returned. If no default exists but other groups are
    present, it marks the first group as the default. If no groups are present at all,
    a new default group is created, added to the database, and then returned.

    Args:
        db (Session): The SQLAlchemy session used for database operations.

    Returns:
        models.Group: The default group that exists or was created/updated.
    """
    default_group = db.query(models.Group).filter(models.Group.is_default == True).first()
    if default_group:
        return default_group

    g = db.query(models.Group).order_by(models.Group.id).first()
    if g:
        g.is_default = True
        db.commit()
        return g

    # noch gar keine Gruppen → eine Standardgruppe erstellen
    g = models.Group(name="Standard", is_default=True)
    db.add(g)
    db.commit()
    db.refresh(g)
    return g
