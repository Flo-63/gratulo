"""
===============================================================================
Project   : gratulo
Module    : app/core/deps.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides dependency definitions for the Gratulo application.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

from pathlib import Path
from datetime import datetime
from fastapi.templating import Jinja2Templates
from app.core.constants import ENABLE_REST_API
from app.core import constants


# Basis-Verzeichnis: eine Ebene höher als "app"
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Datenverzeichnisse
DATA_DIR = BASE_DIR / "app" / "data"
INSTANCE_DIR = DATA_DIR / "instance"
UPLOADS_DIR = DATA_DIR / "uploads"

# Frontend-Pfade
FRONTEND_DIR = BASE_DIR / "frontend"
TEMPLATES_DIR = FRONTEND_DIR / "templates"
STATIC_DIR = FRONTEND_DIR / "static"

# Verzeichnisse sicherstellen
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


# Jinja2 Templates
jinja_templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
jinja_templates.env.globals["ENABLE_REST_API"] = ENABLE_REST_API

# Globale Variablen für Templates
jinja_templates.env.globals.update({
    "LABELS": constants.LABELS,
    "LABELS_DISPLAY": constants.LABELS_DISPLAY,
    "BASE_URL": constants.BASE_URL,
    "LOCAL_TZ": constants.LOCAL_TZ,
    "CLUB_FOUNDATION_DATE": constants.CLUB_FOUNDATION_DATE,
})


jinja_templates.env.cache = {}
jinja_templates.env.auto_reload = True


from fastapi import Request

def context(request: Request, **kwargs):
    """
    Generates a context dictionary including a Content Security Policy (CSP) nonce.

    This function retrieves or generates a CSP nonce and prepares a context dictionary
    that includes the incoming request, the current year, the CSP nonce, and any additional
    keyword arguments passed to it. The CSP nonce is used for security headers to permit
    specific inline scripts.

    Args:
        request (Request): The incoming HTTP request object, which may contain a `csp_nonce`
            within the state attribute.
        **kwargs: Additional key-value pairs to include in the resulting context dictionary.

    Returns:
        dict: A dictionary containing the request, the current year, a CSP nonce, and
            any additional keyword arguments passed to the function.
    """
    # Nonce aus Request holen (gesetzt von Middleware)
    nonce = getattr(request.state, "csp_nonce", None)

    # Sicherstellen, dass ein Nonce vorhanden ist
    if not nonce:
        import secrets
        nonce = secrets.token_hex(16)
        request.state.csp_nonce = nonce

    return {
        "request": request,
        "year": datetime.now().year,
        "csp_nonce": nonce,       # <--- hier wichtig!
        **kwargs,
    }
