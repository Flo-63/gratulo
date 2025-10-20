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

def is_round_birthday(age: int) -> bool:
    """Return True if the given age counts as a round-number birthday."""
    return age in ROUND_BIRTHDAY_YEARS


def is_round_entry(years: int) -> bool:
    """Return True if the given membership duration counts as a round-number anniversary."""
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