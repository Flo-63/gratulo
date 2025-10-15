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

jinja_templates.env.cache = {}
jinja_templates.env.auto_reload = True


def context(request, **kwargs):
    """
    Generates a context dictionary containing the provided request, the current year,
    and any additional keyword arguments.

    Args:
        request: The HTTP request object.
        **kwargs: Arbitrary keyword arguments to include in the returned dictionary.

    Returns:
        dict: A context dictionary containing the request, current year, and the
        additional keyword arguments.
    """
    return {"request": request, "year": datetime.now().year, **kwargs}
