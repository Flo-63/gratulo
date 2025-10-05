from fastapi import APIRouter, HTTPException, Depends, Form
from fastapi.security import OAuth2PasswordBearer
from app.services.auth_service import authenticate_service_user, create_access_token, verify_token

auth_api_router = APIRouter(prefix="/api/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


@auth_api_router.post("/token")
def get_token(username: str = Form(...), password: str = Form(...)):
    """
    Authentifiziert den Service-User und gibt ein JWT-Token zurück.
    """
    if not authenticate_service_user(username, password):
        raise HTTPException(status_code=401, detail="Ungültige Anmeldedaten")

    access_token = create_access_token(username)
    return {"access_token": access_token, "token_type": "bearer"}


def require_service_auth(token: str = Depends(oauth2_scheme)):
    """
    Wird als Dependency in API-Endpoints verwendet.
    """
    username = verify_token(token)
    return username
