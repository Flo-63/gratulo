from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import update

from app.core import models


def list_groups(db: Session) -> list[models.Group]:
    return db.query(models.Group).order_by(models.Group.name).all()

def get_default_group(db: Session) -> models.Group | None:
    return db.query(models.Group).filter_by(is_default=True).first()

def get_group(db: Session, group_id: int) -> models.Group:
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
    Erstellt eine neue Gruppe. Stellt sicher, dass der Name eindeutig ist und
    eine Default-Gruppe korrekt gesetzt bleibt.
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
    g = get_group(db, group_id)
    was_default = g.is_default

    db.delete(g)
    db.commit()

    # immer eine Defaultgruppe garantieren
    if was_default:
        ensure_default_exists(db)


def ensure_default_exists(db: Session) -> models.Group:
    """
    Garantiert, dass immer genau eine Defaultgruppe existiert.
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
