"""
===============================================================================
Project   : gratulo
Module    : app/services/auth_service.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides authentication-related services for both UI and API Endpoints

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""



from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt
from fastapi import HTTPException, status

from app.core.models import MailerConfig
from app.core.schemas import TokenData
from app.core.constants import INITIAL_ADMIN_USER, INITIAL_PASSWORD
from app.core.encryption import API_SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, SERVICE_USER, SERVICE_PASSWORD
from app.helpers.security_helper import set_password, verify_password



def make_user(email: str, is_admin: bool = False) -> dict:
    """
    Creates a new user dictionary with the provided email and admin status.

    This function takes an email address, standardizes it to lowercase without
    leading or trailing spaces, and associates it with a boolean indicating
    whether the user has administrative privileges. The result is returned as a
    dictionary.

    Args:
        email (str): The email address of the user. It will be standardized to
            lowercase without leading or trailing spaces.
        is_admin (bool): A flag that specifies if the user is an admin. Defaults
            to False.

    Returns:
        dict: A dictionary containing the normalized email and the admin status.
    """
    return {
        "email": email.strip().lower(),
        "is_admin": is_admin,
    }
def verify_login(db: Session, email: str, password: str):
    """
    Verifies user login credentials. The function first checks if the
    INITIAL_ADMIN_USER and INITIAL_PASSWORD environment variables are set. If set
    and matched, it allows authentication for the initial admin user. Otherwise,
    it validates the credentials against the database configuration. The allowed
    authentication method must be 'email'. Fails if no valid email or password is
    provided or if the password verification fails.

    Args:
        db (Session): The database session used to query the MailerConfig table.
        email (str): The email address provided by the user.
        password (str): The plaintext password provided by the user.

    Returns:
        tuple: A tuple containing a boolean indicating success (True if login is
            verified, False otherwise) and an optional string message indicating
            the reason for failure if login verification fails.
    """
    config = db.query(MailerConfig).first()

    # Falls Initial-Admin aus ENV gesetzt ist → bevorzugt akzeptieren
    if INITIAL_ADMIN_USER and INITIAL_PASSWORD:
        if config and config.auth_method == "oauth":
            # intern überschreiben
            config.auth_method = "email"

        if email == INITIAL_ADMIN_USER and password == INITIAL_PASSWORD:
            return True, None

    # Normale DB-basierte Login-Logik
    if not config or config.auth_method != "email":
        return False, "Login-Methode ist nicht E-Mail"

    if email != config.login_email:
        return False, "Ungültige E-Mail"

    if not config.login_password:
        return False, "Kein Passwort gesetzt"

    if not verify_password(password, config.login_password):
        return False, "Ungültiges Passwort"

    return True, None

def authenticate_service_user(username: str, password: str) -> bool:
    """
    Authenticates a service user by comparing the provided username and password
    with predefined credentials.

    This function validates the login credentials for a service user by comparing
    the input username and password against stored service user credentials. If
    both match, the authentication is considered successful.

    Args:
        username: Username of the service user attempting to authenticate.
        password: Password of the service user attempting to authenticate.

    Returns:
        bool: True if authentication is successful, otherwise False.
    """
    return username == SERVICE_USER and password == SERVICE_PASSWORD


def create_access_token(username: str):
    """
    Creates a new access token for the given username.

    The function takes the username and generates a JWT access token
    that includes the username and an expiration time. The expiration time
    is determined based on the ACCESS_TOKEN_EXPIRE_MINUTES constant. The
    token is encoded using the API_SECRET_KEY and ALGORITHM constants.

    Args:
        username (str): The username for which the access token will be
            generated.

    Returns:
        str: A JSON Web Token (JWT) string that serves as the access token.
    """
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": username, "exp": expire}
    return jwt.encode(to_encode, API_SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str):
    """
    Verifies the provided JWT token, ensuring it is valid, signed, and belongs to the expected
    service user. Extracts the username from the token's payload if verification is successful.

    Args:
        token: A string containing the JWT token to verify. Must be signed with the correct
            secret key and the expected algorithm.

    Returns:
        The username extracted from the token's payload if the token is valid.

    Raises:
        HTTPException: If the token is invalid, expired, or not associated with the expected
            service user.
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