"""
===============================================================================
Project   : gratulo
Module    : app/api/auth_api.py
Created   : 2025-10-05
Author    : Florian
Purpose   : Manages authentication functionalities for the application, including token
            generation and validation for service-specific access.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""



from fastapi import APIRouter, HTTPException, Depends, Form
from fastapi.security import OAuth2PasswordBearer
from app.services.auth_service import authenticate_service_user, create_access_token, verify_token

auth_api_router = APIRouter(prefix="/api/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


@auth_api_router.post("/token")
def get_token(username: str = Form(...), password: str = Form(...)):
    """
    Authenticates the user and generates a JWT access token upon successful
    authentication.

    Args:
        username: The username of the user attempting to authenticate.
        password: The password associated with the given username.

    Raises:
        HTTPException: If the provided username or password is invalid, an
        HTTPException with a status code of 401 is raised.

    Returns:
        dict: A dictionary containing the generated access token and token
        type as "bearer".
    """
    if not authenticate_service_user(username, password):
        raise HTTPException(status_code=401, detail="Ungültige Anmeldedaten")

    access_token = create_access_token(username)
    return {"access_token": access_token, "token_type": "bearer"}


def require_service_auth(token: str = Depends(oauth2_scheme)):
    """
    Verifies the provided token using the OAuth2 scheme and retrieves the associated username.

    This function handles the authentication of a service by ensuring the integrity of the
    JWT token through verification. It extracts the username related to the provided token.

    Args:
        token (str): The token to be verified, extracted via the OAuth2 scheme.

    Returns:
        str: The username extracted from the verified token.
    """
    username = verify_token(token)
    return username
