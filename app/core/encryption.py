"""
===============================================================================
Project   : gratulo
Module    : app/core/encryption.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides encryption functionality for the Gratulo application.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""


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
    A type decorator for encrypting and decrypting database values.

    This class provides functionality to encrypt data before storing it in the
    database and decrypt it when retrieved. It uses Fernet symmetric encryption
    to secure the stored data. The encryption process ensures that sensitive
    information remains protected while stored in the database.

    Attributes:
        impl: SQLAlchemy's data type that this decorator wraps around. This is
            set to `LargeBinary`, which represents binary data.
        cache_ok (bool): Indicates whether results from this type are safe to
            cache.
    """

    impl = LargeBinary
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """
        Encrypts and processes a parameter value for database binding.

        This method takes a parameter value, checks its type, and performs encryption
        for secure storage in a database. If the value is `None`, it simply returns
        `None`. If the parameter is a string, it is encoded into bytes before
        encryption. The encryption is performed using the specified `fernet`
        encryption object.

        Args:
            value: Parameter value to be processed, which can be a string or `None`.
            dialect: Dialect being used by the database.

        Returns:
            The encrypted parameter value if the input value is not `None`. If the
            input value is `None`, it returns `None`.
        """
        if value is None:
            return None
        if isinstance(value, str):
            value = value.encode("utf-8")
        return fernet.encrypt(value)

    def process_result_value(self, value, dialect):
        """
        Processes and decrypts a database value if it exists and is encrypted.

        This method attempts to decrypt the value using the provided decryption method.
        If the value is an unencrypted string, it returns that as decoded text.
        In the case where the value is None or an exception occurs during
        decryption or decoding, None is returned.

        Args:
            value: The raw database value to be processed, potentially encrypted.
            dialect: The dialect used for database operations (unused in this function).

        Returns:
            The decrypted and decoded value as a string, the decoded unencrypted string,
            or None if the value is None or cannot be decoded.
        """
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
