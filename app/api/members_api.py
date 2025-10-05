"""
===============================================================================
Project   : gratulo
Module    : app/api/members_api.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides endpoints for managing members via API

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""



from fastapi import APIRouter, Depends, HTTPException, Query,status
from sqlalchemy.orm import Session
from datetime import datetime
from app.core import schemas, database
from app.api.auth_api import require_service_auth
from app.core.logging import get_audit_logger
from app.services import member_service
from app.core.database import get_db
import logging

logger = logging.getLogger("uvicorn")
audit_logger = get_audit_logger()

members_api_router = APIRouter(
    prefix="/api/members",
    dependencies=[Depends(require_service_auth)],
    responses={404: {"description": "Mitglied nicht gefunden"}},
)


@members_api_router.get("/search", response_model=list[schemas.MemberResponse])
def search_members(
    query: str = Query(..., min_length=2, description="Suche nach Vorname, Nachname oder E-Mail"),
    include_deleted: bool = Query(
        False, description="Falls true, werden auch gelöschte Mitglieder in die Suche einbezogen"
    ),
    db: Session = Depends(database.get_db),
):
    """
    Searches for members by query.

    This function searches for members based on the provided query, which can match
    first name, last name, or email. Optionally, it can include deleted members in
    the search results.

    Args:
        query: The search term for filtering members; minimum length is 2
            characters, and it matches first name, last name, or email.
        include_deleted: Specifies whether to include deleted members in the
            search results (default is False).
        db: The database session dependency for querying.

    Returns:
        A list of members matching the search criteria.

    Raises:
        HTTPException: If no matching members are found.
    """
    results = member_service.search_members(db, query, include_deleted)
    if not results:
        raise HTTPException(status_code=404, detail="Keine Mitglieder gefunden.")
    return results


@members_api_router.get("/", response_model=list[schemas.MemberResponse], operation_id="create_member_rest")
def list_members(
    deleted: str = Query("false", regex="^(true|false|all)$", description="Filter: 'true', 'false' oder 'all'"),
    db: Session = Depends(database.get_db),
):
    """
    Handles the retrieval of members with filtering options for deleted status.

    This function allows clients to retrieve a list of members with optional
    filtering for their deletion status. The available filters include 'true'
    (for deleted members), 'false' (for active members), or 'all' (for both
    active and deleted members). The members data is pulled from the database
    and returned in the response.

    Args:
        deleted (str): Indicates the type of members to retrieve. Accepts one
            of the following values:
            - 'true': Retrieve only deleted members.
            - 'false': Retrieve only active members.
            - 'all': Retrieve all members, regardless of deletion status.
        db (Session): The database session dependency used to query the member
            data.

    Returns:
        list[schemas.MemberResponse]: A list of member data conforming to the
            MemberResponse schema.
    """
    if deleted == "all":
        members = member_service.list_members(db, include_deleted=True)
    elif deleted == "true":
        members = member_service.list_deleted_members(db)
    else:
        members = member_service.list_active_members(db)

    logger.debug(f"DEBUG list_members: deleted={deleted}, count={len(members)}")
    return members



@members_api_router.get("/{member_id}", response_model=schemas.MemberResponse)
def get_member(member_id: int, db: Session = Depends(database.get_db)):
    """
    Fetch a member's details by their unique identifier.

    This endpoint retrieves the information of a specific member by their ID
    from the database. If the member does not exist, a 404 HTTP exception is raised.

    Args:
        member_id (int): The unique identifier of the member to retrieve.
        db (Session): The database session dependency.

    Raises:
        HTTPException: If the member with the given ID is not found.

    Returns:
        schemas.MemberResponse: The response model containing member details.
    """
    member = member_service.get_member_api(db, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Mitglied nicht gefunden")
    return member


@members_api_router.post(
    "/", response_model=schemas.MemberResponse, status_code=status.HTTP_201_CREATED
)
@members_api_router.post("/", response_model=schemas.MemberResponse)
def create_member(member: schemas.MemberCreate, db: Session = Depends(get_db)):
    """
    Creates a new member in the database and logs the creation if successful.

    This function takes in a member creation payload and inserts it into the database
    using the provided database session. Logging occurs upon successful member creation.

    Args:
        member (schemas.MemberCreate): The member creation payload containing details
            like firstname, lastname, gender, email, birthdate, member_since, and group_id.
        db (Session): The database session dependency to interact with the database.

    Returns:
        schemas.MemberResponse: The response model of the created member containing their details.
    """
    new_member = member_service.save_member(
        db=db,
        id=None,
        firstname=member.firstname,
        lastname=member.lastname,
        gender=member.gender,
        email=member.email,
        birthdate=member.birthdate,
        member_since=member.member_since,
        group_id=member.group_id,
    )

    # Nur loggen, wenn erfolgreich gespeichert
    if new_member and new_member.id:
        logger.info(f"👤 Neues Mitglied angelegt (ID {new_member.id})")

    return new_member



@members_api_router.put("/{member_id}", response_model=schemas.MemberResponse)
def update_member(member_id: int, member_update: schemas.MemberUpdate, db: Session = Depends(database.get_db)):
    """
    Updates an existing member in the database with the provided details. If the member
    does not exist or is marked as deleted, a 404 HTTP error will be raised. The operation
    logs audit information about the update and fields affected.

    Args:
        member_id (int): Unique identifier of the member to be updated.
        member_update (schemas.MemberUpdate): Object containing the updated data for
            the member. Fields not included will retain their previous values.
        db (Session): Database session dependency.

    Returns:
        schemas.MemberResponse: The updated member record.

    Raises:
        HTTPException: If the member does not exist or is marked as deleted.
    """
    member = member_service.get_member(db, member_id)
    if not member or member.is_deleted:
        raise HTTPException(status_code=404, detail="Mitglied nicht gefunden")

    data = member_update.dict(exclude_unset=True)
    member_service.save_member(
        db=db,
        id=member_id,
        firstname=data.get("firstname", member.firstname),
        lastname=data.get("lastname", member.lastname),
        gender=data.get("gender", member.gender),
        email=data.get("email", member.email),
        birthdate=str(data.get("birthdate", member.birthdate or "")),
        member_since=str(data.get("member_since", member.member_since or "")),
        group_id=data.get("group_id", member.group_id),
    )

    updated = member_service.get_member(db, member_id)
    logger.info(f"Mitglied aktualisiert (ID {member_id})")
    audit_logger.info(f"UPDATE member_id={member_id}, fields={list(data.keys())}")
    return updated


@members_api_router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(member_id: int, db: Session = Depends(database.get_db)):
    """
    Deletes a member by setting its status as deleted and marking the deletion
    time in the database. This operation is idempotent and only marks
    existing active members as deleted.

    Args:
        member_id (int): Unique identifier of the member to delete.
        db (Session): Database session used to query and update member records.

    Raises:
        HTTPException: Raised with a 404 status code if the member does not exist
            or is already marked as deleted.
    """
    member = member_service.get_member(db, member_id)
    if not member or member.is_deleted:
        raise HTTPException(status_code=404, detail="Mitglied nicht gefunden")

    member.is_deleted = True
    member.deleted_at = datetime.utcnow()

    db.commit()
    logger.warning(f"Mitglied zur Löschung markiert (ID {member.id})")
    audit_logger.info(f"DELETE member_id={member.id}")
    return None


@members_api_router.post("/{member_id}/restore", response_model=schemas.MemberResponse)
def restore_member(member_id: int, db: Session = Depends(database.get_db)):
    """
    Restores a logically deleted member by its unique identifier.

    This endpoint allows the restoration of a previously deleted member. If the
    member does not exist, or has not been deleted, an exception will be raised.
    Upon successful restoration, informational logs for general and audit purposes
    are generated.

    Args:
        member_id (int): The unique identifier of the member to restore.
        db (Session): The database session dependency used to perform the
            restoration.

    Raises:
        HTTPException: Raised when the member is not found or has not been logically
            deleted.

    Returns:
        schemas.MemberResponse: The restored member data in the specified response
            model format.
    """
    member = member_service.restore_member(db, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Mitglied nicht gefunden oder nicht gelöscht")

    logger.info(f"Mitglied wiederhergestellt (ID {member.id})")
    audit_logger.info(f"RESTORE member_id={member.id}")
    return member

@members_api_router.delete("/{member_id}/wipe", status_code=status.HTTP_204_NO_CONTENT)
def wipe_member(
    member_id: int,
    force: bool = Query(False, description="Erzwingt vollständiges Löschen auch bei aktiven Mitgliedern"),
    db: Session = Depends(database.get_db),
):
    """
    Deletes a member permanently from the database. If the member is still active, deletion is blocked
    unless the `force` parameter is explicitly set to `True`. Requires an active database session.

    Args:
        member_id (int): Unique identifier of the member to delete.
        force (bool): If set to `True`, forces deletion even if the member is active.
        db (Session): Active SQLAlchemy session connected to the database.

    Raises:
        HTTPException: If the member is still active and `force` is not set to `True`.

    Returns:
        None: Indicates successful deletion of the member.
    """
    success = member_service.wipe_member(db, member_id, force=force)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Mitglied ist noch aktiv – zum endgültigen Löschen 'force=true' angeben.",
        )

    logger.warning(f"Mitglied dauerhaft gelöscht (ID {member_id}, force={force})")
    audit_logger.info(f"WIPE member_id={member_id} force={force}")
    return None

