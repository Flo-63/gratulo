# app/core/constants.py
import os
import datetime
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

# sicherstellen, dass .env geladen ist
load_dotenv()

# String aus .env holen
raw_date = os.getenv("CLUB_FOUNDATION_DATE", "2009-01-01")

try:
    CLUB_FOUNDATION_DATE = datetime.datetime.strptime(raw_date, "%Y-%m-%d").date()
except ValueError:
    raise RuntimeError(f"Ungültiges CLUB_FOUNDATION_DATE in .env: {raw_date}")

DB_URL = os.getenv("DB_URL")
LOCAL_TZ = ZoneInfo(os.getenv("LOCAL_TZ", "Europe/Berlin"))
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

# Redis URL: aus .env oder Default für Docker-Setup
REDIS_URL = os.getenv("REDIS_URL")

if not REDIS_URL:
    # Standard: im Docker-Netzwerk ist der Hostname "redis"
    REDIS_URL = "redis://redis:6379"

# Initial-Admin aus .env (nur setzen, wenn beide Werte vorhanden und nicht leer)
_env_user = os.getenv("INITIAL_ADMIN_USER", "").strip()
_env_pw = os.getenv("INITIAL_PASSWORD", "").strip()

if _env_user and _env_pw:
    INITIAL_ADMIN_USER = _env_user
    INITIAL_PASSWORD = _env_pw
else:
    INITIAL_ADMIN_USER = None
    INITIAL_PASSWORD = None