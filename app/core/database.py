# app/core/database.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

from app.core.constants import DB_URL
from app.core.deps import INSTANCE_DIR


# DB-Datei im Instance-Verzeichnis
default_sqlite_url = f"sqlite:///{INSTANCE_DIR}/mailer.db"
DATABASE_URL = os.getenv("DB_URL", default_sqlite_url)

# Engine
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
    Yields a database session and ensures proper cleanup after use.

    This function provides a generator to work with a database session by
    yielding a session instance and ensuring its closure after the database
    operations are complete. It handles the session lifecycle by initializing
    the session before yielding and closing it in a `finally` block to prevent
    any resource leaks.

    :return: A generator yielding the database session object.
    :rtype: Generator[SessionLocal, None, None]
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
