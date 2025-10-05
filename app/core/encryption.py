# app/core/encryption.py

import os
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.types import TypeDecorator, LargeBinary




try:
    SESSION_LIFETIME = int(os.getenv("SESSION_LIFETIME", 480))  # Default: 8 Stunden = 480 Minuten
except ValueError:
    SESSION_LIFETIME = 480

# HTTPS only flag
HTTPS_ONLY = os.getenv("HTTPS_ONLY", "true").lower() in ("true", "1", "yes")

# ---------------------------------------------------------------------------
# Schlüsselverwaltung
# ---------------------------------------------------------------------------

# Der Key muss einmalig erzeugt und dann sicher gespeichert werden.
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# ---------------------------------------------------------------------------

SECRET_KEY = os.environ.get("APP_SECRET")
if not SECRET_KEY:
    raise RuntimeError(
        "No SECRET_KEY set. Generate one with Fernet.generate_key() "
        "and set it as environment variable APP_SECRET."
    )

fernet = Fernet(SECRET_KEY.encode() if isinstance(SECRET_KEY, str) else SECRET_KEY)

API_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "changeme")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
SERVICE_USER = os.getenv("SERVICE_USER_NAME", "service_api")
SERVICE_PASSWORD = os.getenv("SERVICE_USER_PASSWORD", "supersecret")



# ---------------------------------------------------------------------------
# SQLAlchemy TypeDecorator für Verschlüsselung
# ---------------------------------------------------------------------------

class EncryptedType(TypeDecorator):
    """
    A custom SQLAlchemy TypeDecorator ensuring encryption and decryption
    of certain fields in the database.

    The `EncryptedType` class uses Fernet symmetric encryption to securely
    store sensitive data in the database. Before values are written to the
    database, they are encrypted. Data retrieved from the database is
    decrypted before being returned. This ensures that data is stored in an
    encrypted format, providing an extra layer of security.

    :ivar impl: The underlying database type used by this custom type.
    :type impl: SQLAlchemy type (e.g., LargeBinary)
    :ivar cache_ok: Indicates if the results of this type are safe to cache.
    :type cache_ok: bool
    """

    impl = LargeBinary
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Wird aufgerufen, bevor ein Wert in die DB geschrieben wird"""
        if value is None:
            return None
        if isinstance(value, str):
            value = value.encode("utf-8")
        return fernet.encrypt(value)

    def process_result_value(self, value, dialect):
        """Wird aufgerufen, wenn ein Wert aus der DB gelesen wird"""
        if value is None:
            return None
        try:
            decrypted = fernet.decrypt(value)
            return decrypted.decode("utf-8")
        except InvalidToken:
            # Falls ein alter unverschlüsselter Wert in der DB liegt
            try:
                return value.decode("utf-8")
            except Exception:
                return None
