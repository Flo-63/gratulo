"""
===============================================================================
Project   : gratulo
Module    : app/services/member_service.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides services for managing members for UI and API Endpoints

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""



import csv
from datetime import datetime, date
from io import StringIO

from fastapi import HTTPException, UploadFile

from sqlalchemy import asc, literal, or_, func
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError

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
    Parses a CSV file to extract and normalize its rows.

    This function reads a CSV file, attempts to parse it using possible delimiters
    (`;` or `,`), and normalizes the headers based on a predefined mapping. The
    function validates that the file has valid content before converting its rows
    to a specific structure defined by expected fields. Only rows with at least one
    non-empty value are included in the output.

    Args:
        file (UploadFile): The file-like object containing CSV data to be parsed.

    Returns:
        list[dict]: A list of dictionaries representing the parsed and normalized
        rows from the CSV file.

    Raises:
        HTTPException: If the file cannot be read or parsed.
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
    Validates a list of rows containing user data against specified rules and the database.

    This function checks if all the required fields are present and properly formatted,
    ensuring data validity before processing further. Each row's errors, if any, are
    recorded, and additional fields such as group information are populated based on
    the database.

    Args:
        rows (list[dict]): A list of dictionaries representing user data to be validated.
            Each dictionary typically contains details such as "firstname", "lastname",
            "email", "birthdate", "member_since", "gender", and "group_name".
        db (Session): An active database session used for retrieving group-related data
            and default values required for validation.

    Returns:
        list[dict]: A list of validated rows where each dictionary includes the original
            user data, additional fields (e.g., "group_id"), and a dictionary of validation
            errors under the key "_errors", if any.
    """

    validated = []
    today = datetime.now().date()

    groups = group_service.list_groups(db)
    groups_by_name = {g.name.lower(): g for g in groups}
    default_group = group_service.get_default_group(db)

    # E-Mail-Duplikate zählen für Warnungen
    email_counts = {}
    for row in rows:
        email = (row.get("email") or "").strip().lower()
        if email:
            email_counts[email] = email_counts.get(email, 0) + 1

    for row in rows:
        errors = {}
        warnings = {}

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
        elif email_counts.get(email, 0) > 1:
            warnings["email"] = f"E-Mail wird {email_counts[email]}x verwendet (z.B. Familie)"
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

        # Fehler und Warnungen speichern
        row["_errors"] = errors
        row["_warnings"] = warnings
        validated.append(row)

    return validated


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
    """
    Saves or updates a member in the database. This function validates the provided
    data, ensuring the group exists, the email is unique, and the dates are valid.
    If the member `id` is provided, the function updates the existing member. If no
    `id` is given, a new member is created. The function commits the changes to the
    database, refreshing the member's state afterward.

    Args:
        db (Session): The database session to execute the queries.
        id (int | None): The ID of the member; if None, a new member is created.
        firstname (str): The first name of the member.
        lastname (str): The last name of the member.
        gender (str): The gender of the member.
        email (str): The email address of the member, which must be unique.
        birthdate (str | date | None): The birthdate of the member.
        member_since (str | date | None): The date the member joined.
        group_id (int): The ID of the group to which the member belongs.

    Returns:
        models.Member: The saved or updated member instance.

    Raises:
        HTTPException: If the group is not found, the email is not unique, the
        input dates are invalid, the member does not exist for the given ID, or
        there is a database error.
    """
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
    Commits new members to the database while removing all existing members. The function first deletes all current
    members in the database, then processes a given list of member dictionaries to create new member entries.
    Member-related information such as group associations, birthdays, and membership dates are validated and prepared
    before being saved in the database. The function ensures that a valid group is associated with each member entry.

    Args:
        db (Session): The database session used for executing queries and committing changes.
        rows (list[dict]): A list of dictionaries representing new member data. Each dictionary should include
            keys such as 'email', 'firstname', 'lastname', 'gender', 'group_id', 'group_name', 'member_since',
            and 'birthdate'.
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
    """
    Fetches a list of members from the database, with the ability to filter out deleted
    members and sort them by their last and first names in ascending order.

    Args:
        db (Session): Database session used to query the members.
        include_deleted (bool): If True, includes deleted members in the result.
            Defaults to False.

    Returns:
        List[models.Member]: A list of member objects retrieved from the database.
    """
    query = db.query(models.Member)
    if not include_deleted:
        query = query.filter(models.Member.is_deleted == literal(0))

    members = query.order_by(
        asc(models.Member.lastname), asc(models.Member.firstname)
    ).all()

    return members


def soft_delete_member(db, member_id: int):
    """
    Marks a member as deleted without removing the record from the database. This function
    sets the `is_deleted` attribute of the member to True and updates the `deleted_at`
    field with the current UTC time.

    Args:
        db: Database session used to query and update the member record.
        member_id (int): The ID of the member to be soft-deleted.

    Returns:
        models.Member: The updated member object if found; otherwise, None.
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
    Fetches a member from the database, including their associated group, and validates/serializes
    it into a response schema. If the member is not found, an HTTPException with status 404 is raised.

    Args:
        db: The database session used to query the member.
        member_id: The unique identifier of the member to be retrieved.

    Returns:
        An instance of schemas.MemberResponse containing the serialized member data.

    Raises:
        HTTPException: If no member with the specified ID is found in the database.
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
    """
    Fetches a member from the database based on the provided member ID. The function performs
    a database query to retrieve the member details, including the related group information
    using eager loading, if available.

    Args:
        db (Session): The SQLAlchemy database session used to query the database.
        member_id (int): The unique identifier of the member to retrieve.

    Returns:
        models.Member | None: The retrieved member object if found, otherwise None.
    """
    return (
        db.query(models.Member)
        .options(joinedload(models.Member.group))
        .filter(models.Member.id == member_id)
        .first()
    )

def list_active_members(db: Session):
    """
    Fetches a list of all active members from the database.

    An active member is defined as a member who is not marked as deleted.
    The list is returned sorted by lastname in ascending order and, within the
    same lastname, by firstname in ascending order.

    Args:
        db: Database session used to query for active members.

    Returns:
        List of active members sorted by lastname and firstname in ascending order.
    """
    return (
        db.query(models.Member)
        .filter(models.Member.is_deleted == False)
        .order_by(asc(models.Member.lastname), asc(models.Member.firstname))
        .all()
    )


def list_deleted_members(db: Session):
    """
    Fetches a list of deleted members from the database, ordered by lastname and firstname
    in ascending order.

    Args:
        db (Session): Database session used for querying the members table.

    Returns:
        list: A list of deleted members from the database. Each member is represented as an
        instance of the Member model.
    """
    return (
        db.query(models.Member)
        .filter(models.Member.is_deleted == True)
        .order_by(asc(models.Member.lastname), asc(models.Member.firstname))
        .all()
    )


def restore_member(db: Session, member_id: int):
    """
    Restore a deleted member in the database.

    This function retrieves a specific member from the database by its ID.
    If the member exists and is marked as deleted, it restores the member
    by setting their deleted status to `False` and clearing the deletion
    timestamp. The changes are then committed to the database.

    Args:
        db (Session): The database session object used for querying and
            updating the database.
        member_id (int): The unique identifier of the member to restore.

    Returns:
        models.Member: The restored member object if successful.
        None: If the member does not exist or is not marked as deleted.
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
    Deletes a member from the database by the given member ID.

    This function queries the database to find a member with the specified
    member ID. If the member is found, it deletes the member from the database
    and commits the changes. If the member is not found, it returns False.

    Args:
        db (Session): The database session used to execute queries.
        member_id (int): The ID of the member to delete.

    Returns:
        bool: True if the member was successfully deleted, False if the member
        was not found.
    """
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        return False

    db.delete(member)
    db.commit()
    return True

def search_members(db: Session, query: str, include_deleted: bool = False):
    """
    Searches for members in the database based on the given query and optional deletion status filter.

    This function performs a case-insensitive search for members by their first name, last name, or email.
    If `include_deleted` is set to False, only non-deleted members are included in the search results.
    The results are sorted alphabetically by last name and first name.

    Args:
        db (Session): The database session used to query the members.
        query (str): The search term used to find members. It is a case-insensitive match for first name,
            last name, or email.
        include_deleted (bool, optional): If True, includes deleted members in the search results.
            Defaults to False.

    Returns:
        List[models.Member]: A list of members matching the search criteria.
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
    """
    Fetches a single member from the database using their email address.

    This function queries the database to retrieve a member record that matches
    the provided email address. It returns the first result or `None` if no record
    is found.

    Args:
        db (Session): Database session object used to interact with the database.
        email (str): Email address of the member to retrieve.

    Returns:
        models.Member | None: The member object if found; otherwise, None.
    """
    return db.query(models.Member).filter(models.Member.email == email).first()

def validate_group(db: Session, group_id: int | None) -> models.Group:
    """
    Validates the provided group ID and retrieves a corresponding group object. If the group ID
    is not provided or invalid, retrieves the default group. Raises an exception if no valid
    group is found.

    Args:
        db (Session): A database session for querying data.
        group_id (int | None): The ID of the group to validate or retrieve.

    Returns:
        models.Group: The group object corresponding to the provided ID or the default group.

    Raises:
        HTTPException: If no valid group is found.
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
    Validates the uniqueness of an email address within the database. Ensures that the email
    is not already associated with an existing member. If a member ID is provided, the query
    excludes that member to support email updates for the specified member.

    Args:
        db (Session): Database session used to perform queries.
        email (str): Email address to validate for uniqueness.
        member_id (int | None, optional): ID of the member to exclude from the uniqueness
            check. Defaults to None.

    Raises:
        HTTPException: Raised if the email address is already associated with another
            member in the database.

    Returns:
        bool: True if the email address is unique and not associated with another
            member.
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
    Validates and normalizes the provided birthdate and member_since date inputs.

    This function ensures that the given dates are in the correct format and adhere
    to specific logical constraints, such as the birthdate not being in the future
    or the membership date not being earlier than the birthdate. It also converts
    string date inputs into Python date objects for further processing.

    Args:
        birthdate: The birthdate input, which could be a string, a date object,
            or None. Strings are expected in the YYYY-MM-DD format.
        member_since: The membership start date input, which could be a string,
            a date object, or None. Strings are expected in the YYYY-MM-DD format.

    Returns:
        A tuple of two elements:
            - A normalized birthdate as a date object or None if the input was empty.
            - A normalized member_since date as a date object or None if the input
              was empty.

    Raises:
        HTTPException: If any of the following conditions is violated:
            - An invalid date format is provided.
            - A date input has an unsupported type.
            - The membership date is earlier than the birthdate.
            - The birthdate is in the future.
            - The membership date is in the future.
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