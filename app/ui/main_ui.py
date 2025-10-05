from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.core.deps import jinja_templates, context
from app.core.database import get_db
from app.core.models import MailerConfig
from app.core.constants import INITIAL_ADMIN_USER, INITIAL_PASSWORD

main_ui_router = APIRouter(include_in_schema=False)


# ---------------------------
# Root -> Login wenn nicht eingeloggt
# ---------------------------
@main_ui_router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    if "user" not in request.session:
        return RedirectResponse("/login", status_code=303)
    return RedirectResponse("/admin", status_code=303)


# ---------------------------
# Admin-Seite
# ---------------------------
@main_ui_router.get("/admin", response_class=HTMLResponse)
async def admin(request: Request):
    if "user" not in request.session:
        return RedirectResponse("/login", status_code=303)
    return jinja_templates.TemplateResponse("admin.html", context(request))


# ---------------------------
# Login-Seite
# ---------------------------
@main_ui_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    config = db.query(MailerConfig).first()
    using_env_login = False

    # 1. Prüfen: ENV hat Vorrang (nur wenn beide nicht leer sind)
    if INITIAL_ADMIN_USER and INITIAL_PASSWORD:
        auth_method = "email"
        using_env_login = True
        print("Verwende ENV-basierte Login-Daten (auth_method=email)")
    # 2. Sonst DB-Konfiguration nutzen
    elif config and config.auth_method:
        auth_method = config.auth_method
        print(f"Verwende DB-Konfiguration (auth_method={auth_method})")
    else:
        auth_method = None
        print("❌ Keine Auth-Methode gefunden (ENV & DB leer)")

    # 3. Wenn nichts da → Fehler
    if not auth_method:
        print("Zeige Fehlermeldung an Benutzer")
        return jinja_templates.TemplateResponse(
            "login.html",
            context(request, error_message="❌ Keine Authentisierungsmethode konfiguriert."),
            status_code=400,
        )

    # 4. Erfolgreiches Rendern
    print(f" Login-Seite wird angezeigt mit auth_method={auth_method}, using_env_login={using_env_login}")
    return jinja_templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "auth_method": auth_method,
            "using_env_login": using_env_login,
        },
    )

