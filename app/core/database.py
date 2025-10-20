"""
===============================================================================
Project   : gratulo
Module    : core.database.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides database configuration and session management for the Gratulo application.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""


from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.engine.url import make_url
import os

from app.core.deps import INSTANCE_DIR


os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["LC_ALL"] = "C.UTF-8"
os.environ["LANG"] = "C.UTF-8"


# DB-Datei im Instance-Verzeichnis
default_sqlite_url = f"sqlite:///{INSTANCE_DIR}/mailer.db"
default_postgres_url = "postgresql+psycopg2://gratulo:secret@localhost:5432/gratulo"

#DATABASE_URL = os.getenv("DB_URL", default_postgres_url)


# if "client_encoding" not in DATABASE_URL:
#     DATABASE_URL += "?client_encoding=utf8"

# Engine PostgreSQL
#engine = create_engine(
#    DATABASE_URL,
#    pool_pre_ping=True,          # wichtig für stabile Verbindung
#    echo=False                   # debug=True falls du SQL sehen willst
#)

DATABASE_URL = os.getenv("DB_URL", default_sqlite_url)
# Engine SQLITE
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)


# Session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Gemeinsame Base-Klasse
Base = declarative_base()

# Dependency für FastAPI
def get_db():
    """
    Provides a database session for use within application logic.

    This function is a generator that yields a database session object.
    It ensures that the session is properly closed after use, regardless of
    whether the code using it completes successfully or raises an exception.

    Yields:
        Session: A database session instance.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_database_exists():
    """
    Ensures that the target database exists before connecting.

    For SQLite: Automatically created by SQLAlchemy.
    For Postgres/MySQL: Uses sqlalchemy_utils to create the DB if missing.
    """
    db_url = make_url(DATABASE_URL)

    # SQLite → Datei wird bei Bedarf automatisch erstellt
    if db_url.drivername.startswith("sqlite"):
        db_dir = os.path.dirname(db_url.database or "")
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        return

    # PostgreSQL/MySQL → prüfen und ggf. erstellen
    if not database_exists(db_url):
        print(f"⚙️ Creating missing database: {db_url.database}")
        create_database(db_url)
    else:
        print(f"✅ Database '{db_url.database}' already exists.")
