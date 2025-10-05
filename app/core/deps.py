# app/core/deps.py

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
    Generate and return a context dictionary for use in templates.

    This function creates a context dictionary containing the request object,
    the current year, and additional key-value pairs passed through ``kwargs``.
    It provides a convenient way to supply common data to templates.

    :param request: The HTTP request object.
    :type request: Any
    :param kwargs: Additional key-value pairs to be included in the context.
    :return: A dictionary containing the request object, the current year,
             and additional context data from ``kwargs``.
    :rtype: dict
    """
    return {"request": request, "year": datetime.now().year, **kwargs}
