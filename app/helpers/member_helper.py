# app/helpers/member_helpers.py

import re
from sqlalchemy.orm import Session
from datetime import datetime, date
from fastapi import HTTPException
from app.core.constants import CLUB_FOUNDATION_DATE
from app.services import group_service

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def render_import_error(row_num: int, message: str) -> str:
    """
    Generate a formatted import error message indicating the row number
    and the error description. Primarily intended for highlighting issues
    during data import operations.

    :param row_num: The number of the row where the import error occurred.
    :type row_num: int
    :param message: A descriptive message explaining the specific error
        encountered while importing data.
    :type message: str
    :return: A formatted error message that specifies the row number and
        provides detailed context of the issue.
    :rtype: str
    """
    return f"Fehler in Zeile {row_num}: {message}"


def parse_date_flexible(value: str, field_name: str, row_num: int) -> datetime.date:
    """
    Parses a date from a string using a flexible format. The function attempts to convert
    a given string into a date object, ensuring that the format matches the specified
    pattern. If conversion fails, it raises an HTTPException with a detailed error
    message.

    :param value: The string input that contains the date to parse.
    :type value: str
    :param field_name: The name of the field from which the date is sourced. Used
        for error reporting to provide context.
    :type field_name: str
    :param row_num: The row number in the dataset for error localization in
        case of failure.
    :type row_num: int
    :return: A `datetime.date` object if the parsing is successful.
    :rtype: datetime.date
    :raises HTTPException: When the input string cannot be parsed as a date
        matching the expected format.
    """
    try:
        return datetime.strptime(value.strip(), "%d.%m.%Y").date()
    except Exception:
        raise HTTPException(status_code=400, detail=render_import_error(row_num, f"{field_name} ungültig"))


def parse_member_since(value: str, row_num: int) -> datetime.date:
    """
    Parses and validates a membership date from a given input value. The method ensures
    the provided date falls within the acceptable range, starting from the club's
    foundation date up to the current date. If the validation fails, an exception is raised.

    :param value: Membership date provided as a string
    :param row_num: Row number associated with the input value, used for error context
    :return: A valid membership date as a `datetime.date` object
    :rtype: datetime.date

    :raises HTTPException: If the parsed date is earlier than the club's foundation date
        or is a future date
    """
    dt = parse_date_flexible(value, "Eintrittsdatum", row_num)
    if dt < CLUB_FOUNDATION_DATE:
        raise HTTPException(status_code=400, detail=render_import_error(row_num, f"Eintritt vor {CLUB_FOUNDATION_DATE}"))
    if dt > datetime.now().date():
        raise HTTPException(status_code=400, detail=render_import_error(row_num, "Eintritt in der Zukunft"))
    return dt


def normalize_gender(value: str) -> str:
    """
    Normalizes the input string representing a gender value by converting it to a standard
    format. Specifically, it converts male-related values to "m" and female-related values
    to "w". All input is stripped of leading/trailing spaces and converted to lowercase.

    :param value: The input string representing a gender value.
    :type value: str
    :return: A normalized gender value as "m" for male, "w" for female, or the original
        trimmed input if it cannot be normalized to these values.
    :rtype: str
    """
    if not value:
        return ""
    v = value.strip().lower()
    if v in ("m", "male", "mann"):
        return "m"
    if v in ("w", "f", "female", "frau"):
        return "w"
    return value.strip()

def normalize_date(value) -> date | None:
    """
    Normalisiert ein Datum, egal ob es als String ("YYYY-MM-DD"),
    datetime.date oder None übergeben wird.
    Gibt immer ein datetime.date-Objekt oder None zurück.
    """
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
        except ValueError as e:
            raise ValueError(f"Ungültiges Datumsformat '{value}': {e}")
    raise TypeError(f"Ungültiger Datentyp für Datum: {type(value)}")


def validate_rows_old(rows: list[dict], db: Session) -> list[dict]:
    """
    Validates and cleans a list of rows containing member data. This function ensures that every
    row adheres to specific validation rules, such as verifying the email format, presence of key
    fields, and consistency in dates. It also maps data to appropriate groups and provides defaults
    for missing groups. Invalid rows result in a detailed error message raised via HTTP exceptions.

    :param rows: A list of dictionaries, where each dictionary represents a row of member data to
        be validated. The expected keys include "email", "Vorname", "Nachname", "Geburtstag",
        "Eintrittsdatum", "group_name", "Geschlecht", and "Kombi".
    :type rows: list[dict]
    :param db: A database session for querying group information and retrieving default group details.
    :type db: Session
    :return: A list of cleaned and validated rows. Each row is a dictionary containing structured
        member data such as email, first name, last name, group ID, and gender, among others.
    :rtype: list[dict]
    :raises HTTPException: If any row fails validation due to reasons such as missing fields,
        invalid email format, duplicate emails, unrealistic birthdates, or invalid group names.
    """
    emails_seen = set()
    cleaned = []

    groups = group_service.list_groups(db)
    groups_by_name = {g.name.lower(): g for g in groups}  # Lookup dict
    default_group = group_service.get_default_group(db)

    for idx, row in enumerate(rows, start=2):
        if not any(v and str(v).strip() for v in row.values()):
            continue

        # --- E-Mail prüfen ---
        email = (row.get("email") or "").strip().lower()
        if not email:
            raise HTTPException(status_code=400, detail=render_import_error(idx, "E-Mail fehlt"))
        if not EMAIL_RE.match(email):
            raise HTTPException(status_code=400, detail=render_import_error(idx, "E-Mail ungültig"))
        if email in emails_seen:
            raise HTTPException(status_code=400, detail=render_import_error(idx, f"Doppelte E-Mail {email}"))
        emails_seen.add(email)

        # --- Namen prüfen ---
        firstname = (row.get("Vorname") or "").strip()
        lastname = (row.get("Nachname") or "").strip()
        if not firstname or not lastname:
            raise HTTPException(status_code=400, detail=render_import_error(idx, "Vorname/Nachname fehlt"))

        # --- Geburtstag prüfen ---
        birthdate_str = (row.get("Geburtstag") or "").strip()
        birthdate = None
        if birthdate_str:
            birthdate = parse_date_flexible(birthdate_str, "Geburtstag", idx)
            if birthdate.year < datetime.now().year - 105:
                raise HTTPException(status_code=400, detail=render_import_error(idx, "Geburtsjahr zu weit in der Vergangenheit"))
            if birthdate > datetime.now().date():
                raise HTTPException(status_code=400, detail=render_import_error(idx, "Geburtsjahr in der Zukunft"))

        # --- Eintrittsdatum prüfen ---
        member_since_str = (row.get("Eintrittsdatum") or "").strip()
        member_since = None
        if member_since_str:
            member_since = parse_member_since(member_since_str, idx)

        # --- Gruppe prüfen ---
        raw_group_name = (row.get("group_name") or "").strip().lower()
        if not raw_group_name:
            group = default_group
        else:
            group = groups_by_name.get(raw_group_name)
            if not group:
                raise HTTPException(
                    status_code=400,
                    detail=render_import_error(
                        idx,
                        f"Ungültige Gruppe (erlaubt: {', '.join([g.name for g in groups])})"
                    )
                )

        cleaned.append({
            "email": email,
            "firstname": firstname,
            "lastname": lastname,
            "kombi": (row.get("Kombi") or "").strip(),
            "member_since": member_since,
            "birthdate": birthdate,
            "group_id": group.id if group else None,
            "gender": normalize_gender(row.get("Geschlecht") or ""),
        })

    return cleaned