"""
docs_api.py
------------
Enthält:
 - API-Endpunkte zur Anzeige & zum Download der Markdown-Dokumentation
 - Eine angepasste Swagger-UI mit ausgeblendeten 'Schemas'
"""

import os
from fastapi import FastAPI, APIRouter, Response
from fastapi.responses import FileResponse, PlainTextResponse

# Router für statische API-Dokumentation
docs_api_router = APIRouter(prefix="/api/docs" )

# Pfad zur Markdown-Dokumentation
DOC_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "API_GUIDE.md")
DOC_PATH = os.path.abspath(DOC_PATH)


@docs_api_router.get("/guide", response_class=PlainTextResponse)
def read_api_guide() -> Response:
    """
    📖 Gibt den Inhalt der API-Dokumentation (Markdown) als Text zurück.
    Nutzbar direkt in Swagger oder im Browser.
    """
    if not os.path.exists(DOC_PATH):
        return Response("API documentation not found.", status_code=404)
    with open(DOC_PATH, "r", encoding="utf-8") as f:
        return Response(f.read(), media_type="text/markdown")


@docs_api_router.get("/download", response_class=FileResponse, response_model=None)
def download_api_guide():
    """
    📦 Download der Markdown-Datei der API-Dokumentation.
    """
    if not os.path.exists(DOC_PATH):
        return Response("API documentation not found.", status_code=404)
    return FileResponse(DOC_PATH, media_type="text/markdown", filename="API_GUIDE.md")

