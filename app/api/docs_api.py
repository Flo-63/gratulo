"""
===============================================================================
Project   : gratulo
Module    : app/api/docs_api.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides endpoints for serving API documentation.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
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
    Retrieves and serves the API guide documentation, formatted as plain text. This function checks if the
    documentation file is present at a predefined path. If the file exists, it reads its content and returns
    it with the appropriate media type. If the file does not exist, a not found response is returned.

    Args:
        None

    Returns:
        Response: A response containing the API guide documentation as plain text if the file exists,
        or a 404 response if the file is not found.
    """
    if not os.path.exists(DOC_PATH):
        return Response("API documentation not found.", status_code=404)
    with open(DOC_PATH, "r", encoding="utf-8") as f:
        return Response(f.read(), media_type="text/markdown")


@docs_api_router.get("/download", response_class=FileResponse, response_model=None)
def download_api_guide():
    """
    Downloads the API documentation guide.

    This endpoint allows users to download the API guide file, which is located at
    a predefined file path. If the file is not found, the endpoint responds with
    a 404 status code and an appropriate message.

    Returns:
        FileResponse: The API guide file if it exists.
        Response: A 404 response with an error message if the file is not found.
    """
    if not os.path.exists(DOC_PATH):
        return Response("API documentation not found.", status_code=404)
    return FileResponse(DOC_PATH, media_type="text/markdown", filename="API_GUIDE.md")

