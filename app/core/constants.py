"""
===============================================================================
Project   : gratulo
Module    : app/core/constants.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides general constants and settings

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""


import os
import datetime
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

load_dotenv()

raw_date = os.getenv("CLUB_FOUNDATION_DATE", "2009-01-01")

try:
    CLUB_FOUNDATION_DATE = datetime.datetime.strptime(raw_date, "%Y-%m-%d").date()
except ValueError:
    raise RuntimeError(f"Ungültiges CLUB_FOUNDATION_DATE in .env: {raw_date}")

LOCAL_TZ = ZoneInfo(os.getenv("LOCAL_TZ", "Europe/Berlin"))
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

ENABLE_REST_API = os.getenv("ENABLE_REST_API", "true").lower() == "true"

# Redis URL: aus .env oder Default für Docker-Setup
REDIS_URL = os.getenv("REDIS_URL")

if not REDIS_URL:
    REDIS_URL = "redis://redis:6379"


# Einstellungen für Rate Limiter im Mailing
RATE_LIMIT_MAILS = int(os.getenv("MAILER_RATE_LIMIT", 40))       # max. Mails pro Minute
RATE_LIMIT_WINDOW = int(os.getenv("MAILER_RATE_WINDOW", 60))     # Sekunden

MAIL_QUEUE_INTERVAL_SECONDS = int(os.getenv("MAIL_QUEUE_INTERVAL_SECONDS", 120))


# ============================================================================
# 🎂 Definition "runde Jubiläen" / "runde Geburtstage"
# ============================================================================

# Liste der Altersjahre, die als "rund" gelten
ROUND_BIRTHDAY_YEARS = [
    10, 20, 30, 40, 50, 60, 70, 75, 80, 85, 90, 95, 100
]

# Liste der Vereinszugehörigkeitsjahre (z. B. Eintrittsjubiläen), die als "rund" gelten
ROUND_ENTRY_YEARS = [
    5, 10, 25, 40, 50, 60, 70
]

# ============================================================================
# 🏷️ Custom Field Labels (konfigurierbar über .env)
# ============================================================================

# Diese Labels können in Templates / UI als Beschriftung für Spalten, Felder etc. verwendet werden
# z. B. "Geburtstag" -> "Wartungstermin", "Eintritt" -> "Servicebeginn"

LABELS = {
    "date1": os.getenv("LABEL_DATE1", "Geburtstag"),
    "date1_type": os.getenv("LABEL_DATE1_TYPE", "ANNIVERSARY").upper(),
    "date1_frequency_months": int(os.getenv("LABEL_DATE1_FREQUENCY_MONTHS", "12")),
    "date2": os.getenv("LABEL_DATE2", "Eintritt"),
    "date2_type": os.getenv("LABEL_DATE2_TYPE", "ANNIVERSARY").upper(),
    "date2_frequency_months": int(os.getenv("LABEL_DATE2_FREQUENCY_MONTHS", "12")),
    "section2": os.getenv("LABEL_SECTION2", "Mitgliedschaft"),
    "entity_singular": os.getenv("LABEL_ENTITY_SINGULAR", "Mitglied"),
    "entity_plural": os.getenv("LABEL_ENTITY_PLURAL", "Mitglieder"),
    "entity_gender": os.getenv("LABEL_ENTITY_GENDER", "n"),
}
if LABELS["entity_gender"].lower() not in ("m", "f", "n"):
    LABELS["entity_gender"] = "n"


def _label_with_suffix(base_label: str, suffix: str = "datum") -> str:
    """
    Generates a label by optionally appending a suffix to the given base label.

    This function takes a base label and appends a suffix to it unless the base
    label already contains specific keywords. The suffix is intelligently appended
    to ensure proper grammatical structure.

    Args:
        base_label (str): The base string to which the suffix may be appended.
        suffix (str, optional): The string to append to the base label. Defaults to "datum".

    Returns:
        str: The resulting label after appending the suffix (if applicable).
    """
    label_lower = base_label.lower()
    if any(x in label_lower for x in ["datum", "termin", "beginn", "start"]):
        return base_label
    return f"{base_label}{'s' if not base_label.endswith('s') else ''}{suffix}"


# Precompute “display labels” (i.e. human-readable)
LABELS_DISPLAY = {
    "date1": (
        LABELS["date1"]
        if LABELS["date1_type"].upper() == "ANNIVERSARY"
        else _label_with_suffix(LABELS["date1"])
    ),
    "date1_type": LABELS["date1_type"],
    "date1_frequency_months": LABELS["date1_frequency_months"],
    "date2": (
        LABELS["date2"]
        if LABELS["date2_type"].upper() == "ANNIVERSARY"
        else _label_with_suffix(LABELS["date2"])
    ),
    "date2_type": LABELS["date2_type"],
    "date2_frequency_months": LABELS["date2_frequency_months"],
    "section2": LABELS["section2"],
    "entity_singular": LABELS["entity_singular"],
    "entity_plural": LABELS["entity_plural"],
    "entity_gender": LABELS["entity_gender"],
}

def is_round_birthday(age: int) -> bool:
    """
    Determines if the given age corresponds to a round-numbered birthday.

    A round-numbered birthday is defined as an age that appears in the
    set ROUND_BIRTHDAY_YEARS. This function checks if the provided age
    is in this set and returns a boolean result.

    Args:
        age: The age to check for a round-numbered birthday.

    Returns:
        bool: True if the age corresponds to a round-numbered birthday,
        False otherwise.
    """
    return age in ROUND_BIRTHDAY_YEARS


def is_round_entry(years: int) -> bool:
    """
    Determines whether a given year is part of the predefined round entry years.

    This function checks if the provided year is included in the list
    of ROUND_ENTRY_YEARS. It returns a boolean indicating the result of
    this membership test.

    Args:
        years: The year to check for inclusion in the ROUND_ENTRY_YEARS
            list.

    Returns:
        bool: True if the year is in ROUND_ENTRY_YEARS, False otherwise.
    """
    return years in ROUND_ENTRY_YEARS


# Initial-Admin aus .env (nur setzen, wenn beide Werte vorhanden und nicht leer)
_env_user = os.getenv("INITIAL_ADMIN_USER", "").strip()
_env_pw = os.getenv("INITIAL_PASSWORD", "").strip()

if _env_user and _env_pw:
    INITIAL_ADMIN_USER = _env_user
    INITIAL_PASSWORD = _env_pw
else:
    INITIAL_ADMIN_USER = None
    INITIAL_PASSWORD = None

SYSTEM_GROUP_ID_ALL = 999_999_999
SYSTEM_GROUP_NAME_ALL = "Alle Gruppen (System)"