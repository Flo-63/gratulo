"""
===============================================================================
Project   : gratulo
Module    : app/helpers/member_helper.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides helper functions for member-related operations.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""



import re
from sqlalchemy.orm import Session
from datetime import datetime, date
import unicodedata
from fastapi import HTTPException
from app.core.constants import CLUB_FOUNDATION_DATE
from app.services import group_service

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def render_import_error(row_num: int, message: str) -> str:
    """
    Renders an import error message for a given row number and message.

    This function takes a row number and an error message as input, and returns a
    string that describes the error with the corresponding row number and message.
    It is used to provide clear and concise error feedback while processing data.

    Args:
        row_num (int): The row number where the error occurred.
        message (str): The accompanying error message that provides additional
            details about the issue.

    Returns:
        str: A formatted error message including the row number and the error message.
    """
    return f"Fehler in Zeile {row_num}: {message}"

def parse_date_flexible(value: str, field_name: str, row_num: int) -> datetime.date:
    """
    Parses a date string in the format "%d.%m.%Y" into a datetime.date object.

    This function tries to convert the given string value into a `datetime.date`
    object based on the provided format. In case of a failure, it raises an
    HTTPException with a detailed error message.

    Args:
        value (str): The string value that is expected to represent a date.
        field_name (str): The name of the field from where the value originated,
            used for error reporting.
        row_num (int): The row number to provide context in case of error.

    Returns:
        datetime.date: The parsed date object corresponding to the provided
        value.

    Raises:
        HTTPException: If the value cannot be parsed into a valid date.
    """
    try:
        return datetime.strptime(value.strip(), "%d.%m.%Y").date()
    except Exception:
        raise HTTPException(status_code=400, detail=render_import_error(row_num, f"{field_name} ungültig"))

def parse_member_since(value: str, row_num: int) -> datetime.date:
    """
    Parses the given membership start date and validates its correctness.

    This function takes a string representation of a date, parses it into a
    `datetime.date` object, and performs validation to ensure the date is within
    acceptable bounds. Specifically, it checks that the date is not earlier than
    the club's foundation date and not later than the current date.

    Args:
        value: The string representation of the membership start date.
        row_num: The row number from which the date originates, used for error
            reporting.

    Returns:
        A `datetime.date` object representing the parsed and validated date.

    Raises:
        HTTPException: If the parsed date is earlier than the club's foundation
            date or later than the current date.
    """
    dt = parse_date_flexible(value, "Eintrittsdatum", row_num)
    if dt < CLUB_FOUNDATION_DATE:
        raise HTTPException(status_code=400, detail=render_import_error(row_num, f"Eintritt vor {CLUB_FOUNDATION_DATE}"))
    if dt > datetime.now().date():
        raise HTTPException(status_code=400, detail=render_import_error(row_num, "Eintritt in der Zukunft"))
    return dt

def normalize_gender(value: str) -> str:
    """
    Normalizes a given gender value to a standardized format.

    The function processes the input gender value by removing leading and trailing
    whitespace, converting the string to lowercase, and mapping certain values to
    either "m" (for male) or "w" (for female). If the input does not match any of
    the predefined male or female identifiers, the function returns the sanitized
    original value.

    Args:
        value (str): The gender input string to be normalized.

    Returns:
        str: A normalized gender value ("m", "w", or the sanitized original value).
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
    Normalizes date input into a `date` object or returns `None` if input is `None`.

    This function handles three types of input:
    - If the input is `None`, it returns `None`.
    - If the input is already a `date` object, it returns the same object.
    - If the input is a `str`, it parses the string into a `date` object, assuming the
      format "%Y-%m-%d". Leading and trailing whitespace in the string is trimmed.
      If the trimmed string is empty, the function returns `None`.

    If the string input cannot be parsed into a `date` object, a `ValueError` is raised. In case
    the input is of an unsupported type, a `TypeError` is raised.

    Args:
        value: The input value that represents a date. Can be of type `None`, `date`, or `str`.

    Returns:
        A `date` object if the input is a valid representation of a date, or `None`
        if the input is `None` or an empty string.

    Raises:
        ValueError: If the input string format is invalid for date conversion.
        TypeError: If the input type is not supported.
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

def german_sort_key(value: str) -> str:
    if not value:
        return ""
    value = value.strip()

    # Unicode Normalisieren
    value = unicodedata.normalize("NFKD", value)

    # Deutsche Umlaut-Regeln
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
        "Ä": "Ae",
        "Ö": "Oe",
        "Ü": "Ue",
    }
    for src, dst in replacements.items():
        value = value.replace(src, dst)

    # Lowercase für echte Sortierung
    return value.lower()
