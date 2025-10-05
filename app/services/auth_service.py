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
    Create a user record with normalized email and administrative privileges.

    :param email: User's email address.
    :type email: str
    :param is_admin: Flag to indicate if the user has administrative privileges.
    :type is_admin: bool
    :return: A dictionary containing the normalized email and admin status.
    :rtype: dict
    """
    return {
        "email": email.strip().lower(),
        "is_admin": is_admin,
    }
def verify_login(db: Session, email: str, password: str):
    """
    Verifies login credentials against initial admin settings or a database-stored
    configuration. The function validates either an initial admin user's login
    credentials from environment variables or performs a database-based email
    authentication if the configuration specifies the 'email' authentication
    method.

    :param db: A SQLAlchemy session object used to query the database
    :type db: Session
    :param email: The email address provided by the user for login
    :type email: str
    :param password: The password provided by the user for login
    :type password: str
    :return: A tuple where the first element is a boolean indicating success
        or failure, and the second element is a message string or None
    :rtype: Tuple[bool, Optional[str]]
    """
    config = db.query(MailerConfig).first()

    # 🟦 Falls Initial-Admin aus ENV gesetzt ist → bevorzugt akzeptieren
    if INITIAL_ADMIN_USER and INITIAL_PASSWORD:
        if config and config.auth_method == "oauth":
            # intern überschreiben
            config.auth_method = "email"

        if email == INITIAL_ADMIN_USER and password == INITIAL_PASSWORD:
            return True, None

    # 🟩 Normale DB-basierte Login-Logik
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
    Prüft Benutzername/Passwort des Service Users.
    """
    return username == SERVICE_USER and password == SERVICE_PASSWORD


def create_access_token(username: str):
    """
    Erzeugt ein JWT Token für den Service User.
    """
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": username, "exp": expire}
    return jwt.encode(to_encode, API_SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str):
    """
    Überprüft das JWT Token.
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