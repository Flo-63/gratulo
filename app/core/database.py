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
    Provides a database session generator function.

    This function yields a database session object that can be used to interact
    with the database. It ensures that the database session is properly closed
    after use, preventing resource leaks and maintaining database integrity.

    Yields:
        Session: A database session instance for the current scope.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_database_exists():
    """
    Ensures the existence of a database.

    This function verifies if the database exists at the given `DATABASE_URL`.
    For SQLite, it automatically creates the necessary file and directory if it
    does not exist. For PostgreSQL/MySQL, it checks if the database exists and
    creates it if missing.

    Raises:
        Any exception raised by `make_url`, `database_exists`, or `create_database`
        depending on the database driver used.
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

from app.core import models
from sqlalchemy.orm import Session

def ensure_default_data(db: Session):
    """
    Ensures that the database contains necessary default data, such as a default group, an example email
    template, and a dummy mailer configuration. If any of these entries are missing, they will be created
    and added to the database.

    Args:
        db (Session): SQLAlchemy database session used to interact with the database.
    """
    # --- Standard-Gruppe ---
    default_group = db.query(models.Group).filter_by(is_default=True).first()
    if not default_group:
        default_group = models.Group(name="Standard", is_default=True)
        db.add(default_group)
        print("🆕 Created default group: 'Standard'")

    # --- Optional: Beispiel-Template ---
    if not db.query(models.Template).first():
        default_template = models.Template(
            name="Beispielvorlage",
            content_html="<h1>Willkommen!</h1><p>Dies ist eine Beispiel-E-Mail.</p>",
        )
        db.add(default_template)
        print("🆕 Created example template: 'Beispielvorlage'")

    # --- Optional: MailerConfig Dummy-Eintrag (nur bei leerer DB) ---
    if not db.query(models.MailerConfig).first():
        dummy_cfg = models.MailerConfig(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="dummy@example.com",
            smtp_password="dummy",
            use_tls=True,
            from_address="no-reply@example.com",
        )
        db.add(dummy_cfg)
        print("🆕 Created dummy mailer config")

    db.commit()
