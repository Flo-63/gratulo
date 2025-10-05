from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core import models, schemas, database
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
    """Alle Gruppen auslesen."""
    groups = group_service.list_groups(db)
    return groups


@groups_api_router.post("/", response_model=schemas.GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(group: schemas.GroupCreate, db: Session = Depends(database.get_db)):
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
    """Bestehende Gruppe aktualisieren (Name oder Standard wechseln)."""
    g = group_service.update_group(db, group_id, group.name, group.is_default)
    logger.info(f"✏️ Gruppe aktualisiert: ID {g.id} → {g.name} (default={g.is_default})")
    audit_logger.info(f"UPDATE group_id={g.id}, default={g.is_default}")
    return g


@groups_api_router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(group_id: int, db: Session = Depends(database.get_db)):
    """
    Gruppe löschen.
    Achtung: Falls es die Default-Gruppe ist, wird automatisch eine neue gesetzt.
    """
    group = group_service.get_group(db, group_id)
    group_name = group.name
    is_default = group.is_default

    group_service.delete_group(db, group_id)

    logger.warning(f"🗑️ Gruppe gelöscht: {group_name} (ID {group_id}, default={is_default})")
    audit_logger.info(f"DELETE group_id={group_id}, was_default={is_default}")
    return None
