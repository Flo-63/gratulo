import csv
from datetime import datetime, date
from io import StringIO
from fastapi import HTTPException, UploadFile
from sqlalchemy import asc, literal, or_, func
from sqlalchemy.orm import Session, joinedload

from app.core import models, schemas
from app.core.constants import CLUB_FOUNDATION_DATE
from app.services import group_service
from app.helpers.member_helper import normalize_date

# Erwartete Standard-Felder (immer auf DB-Spalten-Namen gemappt)
EXPECTED_FIELDS = [
    "email",
    "firstname",
    "lastname",
    "member_since",
    "group_name",
    "birthdate",
    "gender",
]

# Header-Mapping (CSV-Header → interne Keys)
HEADER_MAP = {
    # Email
    "email": "email",
    "e-mail": "email",
    "mail": "email",
    "e mail": "email",

    # Vorname
    "vorname": "firstname",
    "firstname": "firstname",
    "first name": "firstname",

    # Nachname
    "nachname": "lastname",
    "lastname": "lastname",
    "last name": "lastname",
    "familienname": "lastname",

    # Eintrittsdatum
    "eintrittsdatum": "member_since",
    "mitglied seit": "member_since",
    "eintritt": "member_since",
    "member_since": "member_since",
    "entry_date": "member_since",

    # Geburtstag
    "geburtstag": "birthdate",
    "geburtsdatum": "birthdate",
    "birthdate": "birthdate",
    "birthday": "birthdate",
    "date_of_birth": "birthdate",

    # Geschlecht
    "geschlecht": "gender",
    "gender": "gender",
    "sex": "gender",

    # Gruppe
    "group": "group_name",
    "gruppe": "group_name",
    "group_name": "group_name",
}


def parse_csv(file: UploadFile) -> list[dict]:
    """
    Parses a CSV file uploaded by the user and returns a list of dictionaries. The method attempts
    to normalize headers using a predefined mapping and parses the CSV based on detected delimiters.
    It validates rows according to expected fields and ensures that only valid rows are returned.

    :param file: The uploaded CSV file to be parsed. It is expected to be of type UploadFile.
    :return: A list of dictionaries where each dictionary represents a row from the CSV file with
        normalized and validated data.
    :rtype: list[dict]
    :raises HTTPException: If the file cannot be read, the CSV cannot be parsed, or validation fails.
    """
    try:
        decoded = file.file.read().decode("utf-8-sig")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"CSV konnte nicht gelesen werden: {e}")

    for delimiter in [";", ","]:
        file_like = StringIO(decoded)
        reader = csv.DictReader(file_like, delimiter=delimiter)

        if not reader.fieldnames:
            continue

        # Header normalisieren
        normalized_fields = []
        for h in reader.fieldnames:
            if not h:
                continue
            key = h.strip().lower()
            mapped = HEADER_MAP.get(key, key)
            normalized_fields.append(mapped)
        reader.fieldnames = normalized_fields

        rows = []
        for raw_row in reader:
            row = {}
            for field in EXPECTED_FIELDS:
                value = raw_row.get(field, "")
                if value is None:
                    value = ""
                row[field] = str(value).strip()
            if not any(row.values()):
                continue
            rows.append(row)

        if rows:
            return rows

    raise HTTPException(status_code=400, detail="CSV konnte nicht geparst werden – bitte prüfen.")


def validate_rows(rows: list[dict], db: Session) -> list[dict]:
    """
    Validates a list of rows containing user data. Each row is checked for required
    and properly formatted fields, as well as specific business logic such as age
    limitations and group validations. Errors found in the validation process are
    stored in the `_errors` field of each row.

    :param rows: A list of dictionaries representing user data. The dictionaries
        should include the following keys: "firstname", "lastname", "email",
        "birthdete", "member_since", "gender", and "group_name".
    :type rows: list[dict]
    :return: A list of dictionaries, each containing the original row data
        and an additional `_errors` field which includes any validation errors
        for the row.
    :rtype: list[dict]
    """

    validated = []
    today = datetime.now().date()

    groups = group_service.list_groups(db)
    groups_by_name = {g.name.lower(): g for g in groups}
    default_group = group_service.get_default_group(db)

    for row in rows:
        errors = {}

        # --- Pflichtfelder prüfen ---
        if not row.get("firstname"):
            errors["firstname"] = "Vorname fehlt"
        if not row.get("lastname"):
            errors["lastname"] = "Nachname fehlt"

        email = (row.get("email") or "").strip().lower()
        if not email:
            errors["email"] = "E-Mail fehlt"
        elif "@" not in email:
            errors["email"] = "E-Mail ungültig"
        row["email"] = email

        # --- Geburtstag prüfen ---
        birthdate_str = (row.get("birthdate") or "").strip()
        if not birthdate_str:
            errors["birthdate"] = "Geburtstag fehlt"
        else:
            try:
                birth_date = datetime.strptime(birthdate_str, "%d.%m.%Y").date()
                age = (today - birth_date).days // 365
                if age > 105:
                    errors["birthdate"] = "Alter > 105 Jahre"
            except ValueError:
                errors["birthdate"] = "Geburtsdatum ungültig (TT.MM.JJJJ)"

        # --- Eintrittsdatum prüfen ---
        member_since_str = (row.get("member_since") or "").strip()
        if member_since_str:
            try:
                entry_date = datetime.strptime(member_since_str, "%d.%m.%Y").date()
                if entry_date < CLUB_FOUNDATION_DATE:
                    errors["member_since"] = f"Eintritt vor {CLUB_FOUNDATION_DATE.year}"
            except ValueError:
                errors["member_since"] = "Eintrittsdatum ungültig (TT.MM.JJJJ)"

        # --- Geschlecht prüfen ---
        gender = (row.get("gender") or "").lower()
        if gender and gender not in ["m", "w", "d"]:
            errors["gender"] = "Ungültiges Geschlecht (erlaubt: m, w, d)"
        row["gender"] = gender

        # --- Gruppe prüfen ---
        raw_group_name = (row.get("group_name") or "").strip().lower()
        if not raw_group_name:
            if default_group:
                row["group_id"] = default_group.id
                row["group_name"] = default_group.name
            else:
                errors["group_name"] = "Keine Standardgruppe vorhanden"
                row["group_id"] = None
        else:
            group = groups_by_name.get(raw_group_name)
            if group:
                row["group_id"] = group.id
                row["group_name"] = group.name
            else:
                errors["group_name"] = f"Ungültige Gruppe (erlaubt: {', '.join([g.name for g in groups])})"
                row["group_id"] = None

        # Fehler speichern
        row["_errors"] = errors
        validated.append(row)

    return validated

from datetime import datetime, date
from fastapi import HTTPException

from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException

def save_member(
    db: Session,
    id: int | None,
    firstname: str,
    lastname: str,
    gender: str,
    email: str,
    birthdate: str | date | None,
    member_since: str | date | None,
    group_id: int,
):
    try:
        # ... (alle bisherigen Prüfungen & Konvertierungen bleiben)
        group = validate_group(db, group_id)
        validate_unique_email(db, email, id)
        validate_birth_and_membership_dates(birthdate, member_since)

        if id:
            member = db.query(models.Member).filter(models.Member.id == id).first()
            if not member:
                raise HTTPException(status_code=404, detail="Mitglied nicht gefunden.")
        else:
            member = models.Member()
            db.add(member)

        member.firstname = firstname.strip()
        member.lastname = lastname.strip()
        member.gender = gender.strip()
        member.email = email.strip()
        member.birthdate = normalize_date(birthdate)
        member.member_since = normalize_date(member_since)
        member.group_id = group.id
        member.is_deleted = False

        db.commit()
        db.refresh(member)
        return member

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Datenbankfehler: {str(e)}")
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Ungültige Eingabe: {str(e)}")



def commit_members(db: Session, rows: list[dict]) -> None:
    """
    Deletes all current members from the database and commits new members based on
    the provided data. This operation involves associating each member with a valid
    group, creating relationships, and validating specific fields such as dates.

    :param db:
        Database session used to interact with the database.
    :type db: Session
    :param rows:
        List of dictionaries where each dictionary represents a member's details
        including email, firstname, lastname, gender, group_id (optional),
        group_name (optional), member_since (optional), and birthdate (optional).
    :type rows: list[dict]
    :return:
        None
    :rtype: None
    :raises HTTPException:
        Raised with status code 400 if no valid group is found or if an invalid
        birthdate is provided in the input data.
    """
    # 1. Alle bisherigen Mitglieder löschen
    db.query(models.Member).delete()
    db.commit()

    # 2. Neue Mitglieder hinzufügen
    for row in rows:
        # Gruppe auflösen
        group = None
        if "group_id" in row and row["group_id"]:
            group = db.query(models.Group).filter(models.Group.id == row["group_id"]).first()
        if not group and "group_name" in row and row["group_name"]:
            group = db.query(models.Group).filter(models.Group.name == row["group_name"]).first()
        if not group:
            group = group_service.get_default_group(db)
        if not group:
            raise HTTPException(status_code=400, detail="Keine gültige Gruppe vorhanden")

        member = models.Member(
            email=row["email"],
            firstname=row["firstname"],
            lastname=row["lastname"],
            gender=row["gender"],
            member_since=None,
            birthdate=None,
            group=group,  # << jetzt echte Beziehung statt group_name
        )

        if row.get("member_since"):
            try:
                member.member_since = datetime.strptime(row["member_since"], "%d.%m.%Y").date()
            except ValueError:
                pass

        if row.get("birthdate"):
            try:
                member.birthdate = datetime.strptime(row["birthdate"], "%d.%m.%Y").date()
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Ungültiges Geburtsdatum: {row['birthdate']}")

        db.add(member)

    # 3. Commit für alle neuen Mitglieder
    db.commit()


def list_members(db: Session, include_deleted: bool = False):
    query = db.query(models.Member)
    if not include_deleted:
        query = query.filter(models.Member.is_deleted == literal(0))

    members = query.order_by(
        asc(models.Member.lastname), asc(models.Member.firstname)
    ).all()

    return members


def soft_delete_member(db, member_id: int):
    """
    Markiert ein Mitglied als gelöscht (Soft Delete).
    """
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        return None

    member.is_deleted = True
    member.deleted_at = datetime.utcnow()
    db.commit()
    return member


def get_member_api(db: Session, member_id: int) -> schemas.MemberResponse:
    """
    Holt ein einzelnes Mitglied aus der Datenbank anhand seiner ID.
    Enthält auch Gruppeninformationen (falls vorhanden).

    :param db: Aktive Datenbanksession
    :param member_id: ID des gesuchten Mitglieds
    :return: MemberResponse (inkl. Gruppe)
    :raises HTTPException: Wenn das Mitglied nicht gefunden wird
    """
    member = (
        db.query(models.Member)
        .options(joinedload(models.Member.group))
        .filter(models.Member.id == member_id)
        .first()
    )

    if not member:
        raise HTTPException(status_code=404, detail="Mitglied nicht gefunden")

    # Mit Schema validieren / serialisieren (inkl. datetime→date-Konvertierung)
    return schemas.MemberResponse.model_validate(member)

def get_member(db: Session, member_id: int) -> models.Member | None:
    return (
        db.query(models.Member)
        .options(joinedload(models.Member.group))
        .filter(models.Member.id == member_id)
        .first()
    )

def list_active_members(db: Session):
    """Liefert nur aktive Mitglieder (nicht gelöscht)."""
    return (
        db.query(models.Member)
        .filter(models.Member.is_deleted == False)
        .order_by(asc(models.Member.lastname), asc(models.Member.firstname))
        .all()
    )


def list_deleted_members(db: Session):
    """Liefert nur gelöschte Mitglieder (Soft Deleted)."""
    return (
        db.query(models.Member)
        .filter(models.Member.is_deleted == True)
        .order_by(asc(models.Member.lastname), asc(models.Member.firstname))
        .all()
    )


def restore_member(db: Session, member_id: int):
    """
    Hebt Soft-Delete eines Mitglieds auf.
    """
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member or not member.is_deleted:
        return None

    member.is_deleted = False
    member.deleted_at = None
    db.commit()
    db.refresh(member)
    return member


def wipe_member(db: Session, member_id: int) -> bool:
    """
    Entfernt ein Mitglied vollständig aus der Datenbank.
    """
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        return False

    db.delete(member)
    db.commit()
    return True

def search_members(db: Session, query: str, include_deleted: bool = False):
    """
    Durchsucht Mitglieder anhand von Vorname, Nachname oder E-Mail-Adresse (case-insensitive).
    Optional können auch gelöschte Mitglieder berücksichtigt werden.

    :param db: Aktive SQLAlchemy-Datenbanksession
    :param query: Suchstring (Teil eines Namens oder einer E-Mail)
    :param include_deleted: Wenn True, werden auch gelöschte Mitglieder einbezogen
    :return: Liste von Member-Objekten, sortiert nach Nachname und Vorname
    """
    if not query:
        return []

    search_term = f"%{query.strip().lower()}%"
    q = db.query(models.Member).filter(
        or_(
            func.lower(models.Member.firstname).like(search_term),
            func.lower(models.Member.lastname).like(search_term),
            func.lower(models.Member.email).like(search_term),
        )
    )

    if not include_deleted:
        q = q.filter(models.Member.is_deleted == False)

    members = q.order_by(asc(models.Member.lastname), asc(models.Member.firstname)).all()
    return members


def get_member_by_email(db: Session, email: str):
    """Mitglied anhand der E-Mail suchen."""
    return db.query(models.Member).filter(models.Member.email == email).first()

def validate_group(db: Session, group_id: int | None) -> models.Group:
    """
    Validiert, ob eine gültige Gruppe existiert.
    Gibt die gefundene Gruppe oder die Default-Gruppe zurück.
    """
    group = None
    if group_id:
        group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        group = group_service.get_default_group(db)
    if not group:
        raise HTTPException(status_code=400, detail="Keine gültige Gruppe gefunden.")
    return group


def validate_unique_email(db: Session, email: str, member_id: int | None = None):
    """
    Stellt sicher, dass keine doppelte E-Mail existiert.
    """
    query = db.query(models.Member).filter(models.Member.email == email)
    if member_id:
        query = query.filter(models.Member.id != member_id)
    existing = query.first()
    if existing:
        raise HTTPException(status_code=400, detail="E-Mail-Adresse bereits vergeben.")
    return True


def validate_birth_and_membership_dates(
        birthdate: str | date | None,
        member_since: str | date | None
) -> tuple[date | None, date | None]:
    """
    Prüft, ob Geburts- und Eintrittsdatum technisch sinnvoll sind.
    (Keine UI-Hinweise wie „über 80 Jahre“ — nur Integritätsvalidierung.)

    Unterstützt sowohl Strings ("YYYY-MM-DD") als auch datetime.date-Objekte.

    :param birthdate: Geburtsdatum (optional, str oder date)
    :param member_since: Eintrittsdatum (optional, str oder date)
    :return: Tupel aus (birthdate, member_since) als date-Objekte oder None
    :raises HTTPException: Bei unlogischen oder ungültigen Datumswerten
    """

    def normalize_date(value: str | date | None) -> date | None:
        """Hilfsfunktion: wandelt Strings in date um, akzeptiert date direkt."""
        if value is None:
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ungültiges Datumsformat '{value}' (erwartet YYYY-MM-DD)."
                )
        raise HTTPException(
            status_code=400,
            detail=f"Ungültiger Typ für Datum: {type(value).__name__}"
        )

    birth = normalize_date(birthdate)
    since = normalize_date(member_since)
    today = datetime.now().date()

    if birth and since and birth > since:
        raise HTTPException(status_code=400, detail="Eintrittsdatum liegt vor dem Geburtsdatum.")
    if birth and birth > today:
        raise HTTPException(status_code=400, detail="Geburtsdatum liegt in der Zukunft.")
    if since and since > today:
        raise HTTPException(status_code=400, detail="Eintrittsdatum liegt in der Zukunft.")

    return birth, since