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

jinja_templates.env.cache = {}
jinja_templates.env.auto_reload = True


def context(request, **kwargs):
    """
    Generates a context dictionary containing the request, the current year,
    and additional keyword arguments.

    Args:
        request: The HTTP request object.
        **kwargs: Arbitrary keyword arguments to include in the context.

    Returns:
        dict: A dictionary containing the request, the current year, and any
        provided keyword arguments.
    """
    return {"request": request, "year": datetime.now().year, **kwargs}
