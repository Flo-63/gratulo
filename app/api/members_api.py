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
    Sucht Mitglieder anhand von Vorname, Nachname oder E-Mail-Adresse.
    Optional können auch gelöschte Mitglieder einbezogen werden.

    :param query: Suchbegriff (mindestens 2 Zeichen)
    :param include_deleted: True, um auch gelöschte Mitglieder einzuschließen
    :param db: Datenbanksession
    :return: Liste der gefundenen Mitglieder
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
    Retrieve a list of members based on the `deleted` filter.

    This endpoint allows the retrieval of member records based on their deletion status.
    The `deleted` parameter determines whether to return all members, only deleted members,
    or only active members.

    :param deleted: A string filter to specify which members to retrieve. Possible
                    values are 'true', 'false', or 'all'.
                    Default is 'false', which retrieves only active members.
    :param db: The database session dependency used for interacting with the database.
    :return: A list of member records matching the specified deletion filter.
    """
    if deleted == "all":
        members = member_service.list_members(db, include_deleted=True)
    elif deleted == "true":
        members = member_service.list_deleted_members(db)
    else:
        members = member_service.list_active_members(db)

    logger.debug(f"🧩 DEBUG list_members: deleted={deleted}, count={len(members)}")
    return members



@members_api_router.get("/{member_id}", response_model=schemas.MemberResponse)
def get_member(member_id: int, db: Session = Depends(database.get_db)):
    """
    Retrieves a member by their ID from the database.

    This function handles GET requests to fetch the information of a specific
    member based on their unique member ID. If the member does not exist, it
    raises an HTTP 404 error with a relevant message.

    :param member_id: The unique identifier of the member to retrieve.
    :type member_id: int
    :param db: The database session dependency injected by FastAPI.
    :type db: Session
    :return: The member data retrieved based on the given member ID.
    :rtype: schemas.MemberResponse

    :raises HTTPException: If the member is not found in the database, an error
        with status code 404 is raised.
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
    Creates a new member in the database.

    This function allows the creation of a new member with the provided data.
    It uses the `member_service.save_member` method to persist the member's details to
    the database. If the member is successfully created, it logs the operation.

    :param member: Data required to create a new member, including first name,
        last name, gender, email, birthdate, membership start date, and group ID.
    :type member: schemas.MemberCreate
    :param db: Database session dependency used to interact with the persistence layer.
    :type db: Session
    :return: The created member object, if successful.
    :rtype: schemas.MemberResponse
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
    Updates an existing member's information based on the provided identifier and update data.
    This function retrieves the member from the database using the `member_id`, checks if the member
    exists and is not marked as deleted. It then applies the updated information from `member_update`
    object by selectively overriding fields that are provided, leaving others unchanged. After saving
    the changes, the updated member record is retrieved and returned.

    :param member_id: The unique identifier of the member to be updated.
    :type member_id: int
    :param member_update: An object containing the new data to update for the member.
    :type member_update: schemas.MemberUpdate
    :param db: The database session dependency used for database operations.
    :type db: Session
    :return: The updated member object reflecting the applied changes.
    :rtype: schemas.MemberResponse

    :raises HTTPException: If no member with the provided identifier is found or if the member has
        been marked as deleted.
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
    logger.info(f"✏️ Mitglied aktualisiert (ID {member_id})")
    audit_logger.info(f"UPDATE member_id={member_id}, fields={list(data.keys())}")
    return updated


@members_api_router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(member_id: int, db: Session = Depends(database.get_db)):
    """
    Deletes a member by setting its `is_deleted` attribute to True and marking the
    timestamp for deletion. The operation is logged for auditing purposes.

    :param member_id: Identifier of the member to be deleted.
    :type member_id: int
    :param db: Database session dependency.
    :type db: Session
    :return: None
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
    Restores a deleted member identified by its member ID. If the member is not found
    or is not in a deleted state, an HTTP 404 exception is raised. Upon successful
    restoration, logs the action for both general and audit purposes and returns the
    restored member data.

    :param member_id: The unique identifier of the member to be restored.
    :type member_id: int
    :param db: Database session dependency.
    :return: The restored member as a response model.
    :rtype: schemas.MemberResponse

    :raises HTTPException: If the member with the given ID is not found or is not deleted.
    """
    member = member_service.restore_member(db, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Mitglied nicht gefunden oder nicht gelöscht")

    logger.info(f"♻️ Mitglied wiederhergestellt (ID {member.id})")
    audit_logger.info(f"RESTORE member_id={member.id}")
    return member

@members_api_router.delete("/{member_id}/wipe", status_code=status.HTTP_204_NO_CONTENT)
def wipe_member(
    member_id: int,
    force: bool = Query(False, description="Erzwingt vollständiges Löschen auch bei aktiven Mitgliedern"),
    db: Session = Depends(database.get_db),
):
    """
    Deletes a member permanently from the database. If the member is still active, the operation
    can only be forced by setting `force` to True. This endpoint logs both a warning and an
    audit log entry when successful.

    :param member_id: The unique identifier for the member to be deleted.
    :type member_id: int
    :param force: Specifies whether to force the deletion even for active members.
    :type force: bool
    :param db: The database session dependency.
    :type db: Session
    :return: None

    :raises HTTPException: If the member is active and the `force` parameter is not set to True.
    """
    success = member_service.wipe_member(db, member_id, force=force)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Mitglied ist noch aktiv – zum endgültigen Löschen 'force=true' angeben.",
        )

    logger.warning(f"🧨 Mitglied dauerhaft gelöscht (ID {member_id}, force={force})")
    audit_logger.info(f"WIPE member_id={member_id} force={force}")
    return None

