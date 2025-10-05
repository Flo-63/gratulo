"""
===============================================================================
Project   : gratulo
Module    : app/api/groups_api.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides endpoints for managing groups via API.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""


from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core import schemas, database
from app.api.auth_api import require_service_auth
from app.services import group_service
from app.core.logging import get_audit_logger
import logging

logger = logging.getLogger("uvicorn")
audit_logger = get_audit_logger()

groups_api_router = APIRouter(
    prefix="/api/groups",
    dependencies=[Depends(require_service_auth)],
    responses={404: {"description": "Gruppe nicht gefunden"}},
)


@groups_api_router.get("/", response_model=list[schemas.GroupResponse])
def list_groups(db: Session = Depends(database.get_db)):
    """
    Retrieves a list of all groups.

    Args:
        db (Session): The database session dependency.

    Returns:
        list[schemas.GroupResponse]: A list of group response objects.
    """
    groups = group_service.list_groups(db)
    return groups


@groups_api_router.post("/", response_model=schemas.GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(group: schemas.GroupCreate, db: Session = Depends(database.get_db)):
    """
    Creates a new group in the database.

    This endpoint allows for the creation of a new group with specified
    attributes. The method utilizes the `group_service` to handle
    the business logic for group creation, including required logging
    and auditing actions.

    Args:
        group (schemas.GroupCreate): An instance of `GroupCreate` schema
            containing the details for the new group such as the group
            name and whether it is a default group.
        db (Session): Database session dependency that facilitates interaction
            with the database.

    Returns:
        schemas.GroupResponse: The newly created group represented as an instance
            of `GroupResponse` schema.
    """
    g = group_service.create_group(
        db,
        name=group.name,
        is_default=group.is_default,
        logger=logger,
        audit_logger=audit_logger,
    )
    return g


@groups_api_router.put("/{group_id}", response_model=schemas.GroupResponse)
def update_group(group_id: int, group: schemas.GroupUpdate, db: Session = Depends(database.get_db)):
    """
    Updates an existing group by its ID with new details provided in the request.
    Logs the changes and audit trails for system monitoring and tracking.

    Args:
        group_id (int): ID of the group to be updated.
        group (schemas.GroupUpdate): Object containing the fields to update for the
            group, including name and is_default.
        db (Session): Database session dependency used for database operations.

    Returns:
        schemas.GroupResponse: Updated group information in the response model.
    """
    g = group_service.update_group(db, group_id, group.name, group.is_default)
    logger.info(f"Gruppe aktualisiert: ID {g.id} → {g.name} (default={g.is_default})")
    audit_logger.info(f"UPDATE group_id={g.id}, default={g.is_default}")
    return g


@groups_api_router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(group_id: int, db: Session = Depends(database.get_db)):
    """
    Deletes a group from the database and logs the action. If the group is a default
    group, it will annotate the log with the details.

    Args:
        group_id (int): ID of the group to be deleted.
        db (Session): Database session dependency.

    Returns:
        None
    """
    group = group_service.get_group(db, group_id)
    group_name = group.name
    is_default = group.is_default

    group_service.delete_group(db, group_id)

    logger.warning(f"Gruppe gelöscht: {group_name} (ID {group_id}, default={is_default})")
    audit_logger.info(f"DELETE group_id={group_id}, was_default={is_default}")
    return None
