"""
===============================================================================
Project   : gratulo
Module    : app/services/auth_service.py
Created   : 2025-10-05
Author    : Florian
Purpose   : Auth services for UI/API with ENV override and AdminUser DB login
===============================================================================
"""

from datetime import datetime, timedelta
from typing import Tuple

from fastapi import HTTPException, status
from jose import jwt
from sqlalchemy.orm import Session

import pyotp
import base64
import qrcode
import io

from app.core.models import AdminUser  # <-- NEU: DB-User statt MailerConfig
from app.core.schemas import TokenData  # (belassen, falls extern genutzt)
from app.core.constants import (
    INITIAL_ADMIN_USER,
    INITIAL_PASSWORD,
)
from app.core.encryption import (
    API_SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    SERVICE_USER,
    SERVICE_PASSWORD,
)
from app.helpers.security_helper import verify_password  # bcrypt-check

# --------------------------------------------------------------------------------------
# Session-User Helper
# --------------------------------------------------------------------------------------

def make_user(email: str, is_admin: bool = False) -> dict:
    """
    Creates and returns a user object with normalized email, username, and admin status.

    Args:
        email: The email address of the user.
        is_admin: A boolean indicating whether the user has admin privileges.

    Returns:
        dict: A dictionary containing the user's email, username, and admin status.
    """
    norm = (email or "").strip().lower()
    return {
        "email": norm,
        "username": norm,
        "is_admin": bool(is_admin),
    }

# --------------------------------------------------------------------------------------
# Login Verification with ENV override
# --------------------------------------------------------------------------------------

_warned_env_login_once = False  # modulerweiter Warnschranke

def verify_login(db: Session, email: str, password: str) -> Tuple[bool, str | None]:
    """
    Verify user login credentials against the database or environment variables.

    This function attempts to validate login credentials. It first checks if
    environment variables `INITIAL_ADMIN_USER` and `INITIAL_PASSWORD` exist for
    a predefined admin user setup. If these are set and match the provided
    credentials, authentication succeeds immediately. Otherwise, it verifies
    the credentials against the `AdminUser` records in the database. It also
    checks if the user account is active and validates the password via bcrypt.

    Args:
        db (Session): The database session used to query `AdminUser` records.
        email (str): The email address or username provided by the user for login.
        password (str): The plain text password provided by the user for login.

    Returns:
        Tuple[bool, str | None]: A tuple where the first element indicates if
        authentication was successful (`True` for success, `False` for failure),
        and the second element is an error message (`None` if authentication
        succeeded, or a string describing the failure reason).
    """
    global _warned_env_login_once

    # 1) ENV override mode (strict)
    if INITIAL_ADMIN_USER and INITIAL_PASSWORD:
        if not _warned_env_login_once:
            print("⚠️  ENV-Login aktiv: INITIAL_ADMIN_USER/INITIAL_PASSWORD gesetzt. "
                  "Bitte diese Werte nach der Einrichtung entfernen.")
            _warned_env_login_once = True

        if (email or "").strip().lower() == INITIAL_ADMIN_USER.strip().lower() \
           and (password or "") == INITIAL_PASSWORD:
            return True, None
        return False, "Ungültige E-Mail oder Passwort"

    # 2) DB login via AdminUser
    if not email or not password:
        return False, "E-Mail und Passwort erforderlich"

    username = email.strip().lower()
    db_user = (
        db.query(AdminUser)
        .filter(AdminUser.username == username, AdminUser.is_active == True)  # noqa: E712
        .first()
    )
    if not db_user:
        return False, "Ungültige E-Mail"

    # bcrypt verify
    if not db_user.password_hash:
        return False, "Kein Passwort gesetzt"
    if not verify_password(password, db_user.password_hash):
        return False, "Ungültiges Passwort"

    return True, None

# --------------------------------------------------------------------------------------
# Service user
# --------------------------------------------------------------------------------------

def authenticate_service_user(username: str, password: str) -> bool:
    """
    Authenticates the service user by verifying the supplied username and password.

    The function checks the provided credentials against predefined constants
    representing the service user's username and password. It returns a boolean
    indicating whether the authentication was successful.

    Args:
        username: The username to authenticate.
        password: The password corresponding to the username.

    Returns:
        bool: True if the username and password match the predefined service
        credentials, False otherwise.
    """
    return username == SERVICE_USER and password == SERVICE_PASSWORD

def create_access_token(username: str):
    """
    Creates a new access token for a given username.

    Generates a JSON Web Token (JWT) containing the username and an expiration time.
    The token will be signed using the application's secret key and algorithm to
    ensure its integrity and authenticity.

    Args:
        username: The username for which the access token will be generated.

    Returns:
        str: The generated JWT, encoded as a string.
    """
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": username, "exp": expire}
    return jwt.encode(to_encode, API_SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    """
    Verifies the given JWT token by decoding it and validating the user's identity.
    If token validation fails for any reason, an HTTP exception is raised.

    Args:
        token (str): The JWT token to verify.

    Returns:
        str: The username extracted from the verified token.

    Raises:
        HTTPException: If the token is expired, invalid, or if the username does not match
        the service user.
    """
    try:
        payload = jwt.decode(token, API_SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username != SERVICE_USER:
            raise HTTPException(status_code=401, detail="Ungültiger Benutzer")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token abgelaufen")
    except Exception:
        raise HTTPException(status_code=401, detail="Ungültiges Token")


# ------------------------------------------------------------------------------
# 🔐 2FA-Funktionen
# ------------------------------------------------------------------------------

def generate_2fa_secret(user: AdminUser, db: Session) -> str:
    """
    Generates a new 2FA secret for a given user and enables 2FA for the user.

    This function creates a TOTP (Time-based One-Time Password) secret, assigns it
    to the user, and enables 2FA for the user in the database. The changes are
    committed, and the database session is refreshed to reflect the updates.

    Args:
        user: The AdminUser object for which the 2FA secret is to be generated and
            2FA is to be enabled.
        db: The Session object used for database operations.

    Returns:
        str: The generated TOTP secret in base32 format.
    """
    secret = pyotp.random_base32()
    user.totp_secret = secret
    user.is_2fa_enabled = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return secret


def generate_qr_code_uri(user: AdminUser, issuer_name: str = "Gratulo") -> str:
    """
    Generates a QR code URI for a user to enable TOTP-based authentication.

    The function takes a user object and an optional issuer name to construct
    a URI that can be used to create a QR code. The QR code enables the user
    to set up TOTP (Time-Based One-Time Password) authentication.

    Raises:
        ValueError: If the user does not have a TOTP secret.

    Args:
        user: The AdminUser object that the QR code URI will be generated for.
        issuer_name: The name of the entity providing the TOTP functionality.
                     Defaults to "Gratulo".

    Returns:
        str: The provisioning URI that can be used to generate a QR code.
    """
    if not user.totp_secret:
        raise ValueError("User hat kein TOTP-Secret.")
    totp = pyotp.TOTP(user.totp_secret)
    return totp.provisioning_uri(name=user.username, issuer_name=issuer_name)


def generate_qr_code_base64(uri: str) -> str:
    """
    Generates a QR code as a base64-encoded PNG image.

    This function creates a QR code from the provided URI, encodes the resulting
    QR code image into a PNG format, and then converts it to a base64-encoded
    string. The returned string can be used in applications where base64-encoded
    image data is required.

    Args:
        uri (str): The URI or data to be encoded into the QR code.

    Returns:
        str: A base64-encoded PNG representation of the QR code.
    """
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def verify_2fa_token(user: AdminUser, token: str) -> bool:
    """
    Verifies a provided two-factor authentication (2FA) token against the user's
    Time-based One-Time Password (TOTP) configuration to determine its validity.

    The method first checks whether the user has 2FA enabled and whether a valid
    TOTP secret is set for the user. If either condition is not met, the function
    immediately returns False. Otherwise, the given token is verified using the
    TOTP mechanism with a defined validity window.

    Args:
        user: The user object representing an admin user with potential 2FA
            configuration.
        token: The 2FA token to be verified.

    Returns:
        bool: True if the provided 2FA token is valid for the user's TOTP
        configuration and falls within the defined validation window. Returns
        False otherwise.
    """
    if not user.is_2fa_enabled or not user.totp_secret:
        return False
    totp = pyotp.TOTP(user.totp_secret)
    return totp.verify(token, valid_window=1)  # ±30 Sekunden Toleranz
