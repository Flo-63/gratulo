from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.core.deps import jinja_templates, context

legal_ui_router = APIRouter(
    prefix="/legal",
    tags=["Legal"],
    include_in_schema=False
)

@legal_ui_router.get("/license", response_class=HTMLResponse)
def show_license(request: Request):
    """Lizenzbedingungen anzeigen"""
    return jinja_templates.TemplateResponse(
        "legal/license.html",
        context(request, page_title="Lizenzbedingungen")
    )

@legal_ui_router.get("/privacy", response_class=HTMLResponse)
def show_privacy(request: Request):
    """Datenschutzerklärung anzeigen"""
    return jinja_templates.TemplateResponse(
        "legal/privacy.html",
        context(request, page_title="Datenschutzerklärung")
    )

@legal_ui_router.get("/terms", response_class=HTMLResponse)
def show_terms(request: Request):
    """Nutzungsbedingungen anzeigen"""
    return jinja_templates.TemplateResponse(
        "legal/terms.html",
        context(request, page_title="Nutzungsbedingungen")
    )
