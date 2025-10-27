"""
===============================================================================
Project   : gratulo
Module    : app/services/job_service.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides services for managing mail jobs.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""



from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError


from app.core import models
from app.helpers.cron_helper import build_cron
from app.services.scheduler import register_job
from app.core.constants import LABELS_DISPLAY, LOCAL_TZ, SYSTEM_GROUP_ID_ALL


from datetime import datetime, timezone

def save_job(
    db: Session,
    id: int | None,
    name: str,
    subject: str | None,
    template_id: int,
    round_template_id: str | None,
    mode: str,                       # "once" | "regular"
    once_at: str | None,             # "%Y-%m-%dT%H:%M"
    selection: str | None,           # "date1" | "date2" | "birthdate" | "entry" | "all" | "list"
    interval_type: str | None,       # "daily" | "weekly" | "monthly"
    time: str | None,                # "HH:MM"
    weekday: str | None,             # "0".."6"
    monthday: str | None,            # "1".."28"
    group_id: int | None = None,
    bcc_address: str | None = None,
) -> models.MailerJob:

    name_clean = (name or "").strip()
    if not name_clean:
        raise HTTPException(status_code=400, detail="Name darf nicht leer sein")

    # --- Eindeutigkeit prüfen ---
    q = db.query(models.MailerJob).filter(models.MailerJob.name == name_clean)
    if id:
        q = q.filter(models.MailerJob.id != id)
    if q.first():
        raise HTTPException(status_code=400, detail=f"Job-Name '{name_clean}' ist bereits vergeben")

    # --- Laden oder Neu anlegen ---
    job = db.query(models.MailerJob).get(id) if id else models.MailerJob()
    if id and not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")

    job.name = name_clean
    job.subject = (subject or "").strip() if subject else None
    job.template_id = template_id
    job.round_template_id = round_template_id
    job.bcc_address = (bcc_address or "").strip() or None

    # --- Gruppe prüfen ---
    if group_id == "all":
        # Spezialfall "Alle Gruppen" (Systemgruppe)
        if selection != "all":
            raise HTTPException(
                status_code=400,
                detail="Die Auswahl 'Alle Gruppen' ist nur bei Selektion 'Alle Mitglieder' erlaubt."
            )
        job.group_id = SYSTEM_GROUP_ID_ALL
        group = None  # Kein echtes Group-Objekt nötig
    else:
        # Normale Gruppe
        if group_id:
            try:
                group_id_int = int(group_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Ungültige Gruppen-ID")

            group = db.query(models.Group).filter(models.Group.id == group_id_int).first()
        else:
            from app.services import group_service
            group = group_service.get_default_group(db)

        if not group:
            raise HTTPException(status_code=400, detail="Keine gültige Gruppe gefunden")

        job.group_id = group.id


    # --- Modus: einmalig oder regelmäßig ---
    if mode == "once":
        if not once_at:
            raise HTTPException(status_code=400, detail="Zeitpunkt (Einmalig) fehlt")

        parsed_once_at = None
        for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
            try:
                parsed_once_at = datetime.strptime(once_at, fmt)
                break
            except ValueError:
                continue

        if not parsed_once_at:
            raise HTTPException(status_code=400, detail=f"Ungültiges Datum/Zeit-Format: {once_at}")

        # 🕓 Lokale Zeitzone anfügen, falls keine vorhanden
        if parsed_once_at.tzinfo is None:
            parsed_once_at = parsed_once_at.replace(tzinfo=LOCAL_TZ)

        # 🌍 In UTC speichern, damit Scheduler + DB konsistent sind
        parsed_once_at_utc = parsed_once_at.astimezone(timezone.utc)

        # 🔹 einmaliger Job: kein CRON, keine Wiederholung
        job.once_at = parsed_once_at_utc
        job.cron = None
        job.selection = selection


    elif mode == "regular":
        # ---------------------------------------------------------------
        # 🔍 NEUE & ALTE SELEKTIONEN akzeptieren ("date1"/"birthdate")
        # ---------------------------------------------------------------
        legacy_to_new = {"birthdate": "date1", "entry": "date2"}
        selection_mapped = legacy_to_new.get(selection, selection)

        valid_selections = ("date1", "date2", "all", "list")
        if selection_mapped not in valid_selections:
            raise HTTPException(
                status_code=400,
                detail=f"Selektion ungültig ({'|'.join(valid_selections)})"
            )

        # 🔹 Prüfe doppelte Selektionen für gleiche Gruppe (egal ob alt oder neu)
        if selection_mapped in ("date1", "date2"):
            q = db.query(models.MailerJob).filter(
                models.MailerJob.selection.in_(["date1", "birthdate"]) if selection_mapped == "date1"
                else models.MailerJob.selection.in_(["date2", "entry"]),
                models.MailerJob.group_id == group.id,
            )
            if id:
                q = q.filter(models.MailerJob.id != id)
            if q.first():
                # 🔸 Menschlich lesbares Label einfügen
                selection_label = LABELS_DISPLAY.get(selection_mapped, selection_mapped)
                raise HTTPException(
                    status_code=400,
                    detail=f"Es existiert bereits ein Job mit der Selektion '{selection_label}' für Gruppe '{group.name}'",
                )

        cron_expr = build_cron(interval_type or "", time or "", weekday, monthday)
        job.cron = cron_expr
        job.selection = selection_mapped
        job.once_at = None

    else:
        raise HTTPException(status_code=400, detail="Ausführungsrhythmus ungültig (once|regular)")

    # --- Speichern ---
    db.add(job)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Job konnte nicht gespeichert werden (DB-Constraint verletzt: {str(e.orig)})",
        )

    db.refresh(job)
    register_job(job)
    return job

