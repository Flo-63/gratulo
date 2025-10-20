"""
===============================================================================
Project   : gratulo
Module    : app/core/middleware_fastapi.py
Created   : 2025-10-20
Author    : Florian
Purpose   : FastAPI-compatible CSP middleware (ASGI), derived from Flask version.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""



# Standard Library
import logging
import secrets
from urllib.parse import urlparse

# Third-Party
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Initialize logger for CSP-related events
from app.core.logging import get_csp_logger
csp_logger = get_csp_logger()

class CSPMiddleware(BaseHTTPMiddleware):
    """
    Middleware for Content Security Policy (CSP) enforcement.

    This class is designed to enforce or report Content Security Policy (CSP) headers
    for incoming HTTP requests. It generates a cryptographically secure nonce for each
    request, which can be used to securely include inline scripts or styles. Additionally,
    the middleware provides support for adding an OAuth domain to CSP directives if configured,
    and handles CSP violation reports through a designated endpoint.

    Attributes:
        report_only (bool): Indicates whether the CSP headers are applied in report-only
            mode. Defaults to False.
        report_uri (str): The endpoint for receiving CSP violation reports. Defaults to
            "/csp-report".
        oauth_authorize_url (str): The OAuth authorization URL used to dynamically add
            its domain to relevant CSP directives. Defaults to an empty string.
    """

    def __init__(self, app, report_only: bool = False, report_uri: str = "/csp-report", oauth_authorize_url: str = ""):
        super().__init__(app)
        self.report_only = report_only
        self.report_uri = report_uri
        self.oauth_authorize_url = oauth_authorize_url

    async def dispatch(self, request: Request, call_next):
        """
        Called for each incoming request. Generates a nonce and adds a CSP header.
        """
        # Skip CSP for violation reports
        if request.url.path.endswith(self.report_uri):
            return await call_next(request)

        # Generate a cryptographically secure nonce
        csp_nonce = secrets.token_hex(16)
        request.state.csp_nonce = csp_nonce

        # Continue request processing
        response: Response = await call_next(request)

        # Build OAuth domain for CSP directives (if configured)
        parsed_url = urlparse(self.oauth_authorize_url)
        oauth_domain = f"{parsed_url.scheme}://{parsed_url.netloc}" if parsed_url.netloc else ""

        # CSP directives
        csp = {
            "default-src": ["'self'"],
            "script-src": [
                "'self'",
                "'unsafe-eval'",
                "https://cdnjs.cloudflare.com",
                "https://cdn.jsdelivr.net",
                "https://code.jquery.com",
                "https://accounts.google.com",
                "https://cdn.plot.ly",
                "https://kit.fontawesome.com",
                "https://stackpath.bootstrapcdn.com",
                oauth_domain,
                f"'nonce-{csp_nonce}'",
            ],
            "script-src-elem": [
                "'self'",
                "https://cdnjs.cloudflare.com",
                "https://cdn.jsdelivr.net",
                "https://code.jquery.com",
                "https://accounts.google.com",
                "https://cdn.plot.ly",
                "https://kit.fontawesome.com",
                "https://stackpath.bootstrapcdn.com",
                oauth_domain,
                f"'nonce-{csp_nonce}'",
            ],
            "style-src": [
                "'self'",
                "'unsafe-hashes'",
                "'unsafe-inline'",
                "https://cdnjs.cloudflare.com",
                "https://cdn.jsdelivr.net",
                "https://code.jquery.com",
                "https://fonts.googleapis.com",
                "https://stackpath.bootstrapcdn.com",
                "https://maxcdn.bootstrapcdn.com",
            ],
            "style-src-elem": [
                "'self'",
                "'unsafe-inline'",
                "https://cdnjs.cloudflare.com",
                "https://cdn.jsdelivr.net",
                "https://code.jquery.com",
                "https://fonts.googleapis.com",
                "https://stackpath.bootstrapcdn.com",
                "https://maxcdn.bootstrapcdn.com",
            ],
            "img-src": [
                "'self'",
                "data:",
                "https://server.arcgisonline.com",
            ],
            "font-src": [
                "'self'",
                "https://fonts.gstatic.com",
                "https://fonts.googleapis.com",
                "https://cdn.jsdelivr.net",
                "https://cdnjs.cloudflare.com",
                "https://maxcdn.bootstrapcdn.com",
                "data:",
            ],
            "connect-src": [
                "'self'",
                "https://accounts.google.com",
                "https://www.googleapis.com",
                "https://cdn.jsdelivr.net",
                oauth_domain,
            ],
            "object-src": ["'none'"],
            "media-src": ["'self'"],
            "form-action": ["'self'"],
            "frame-src": ["'self'", oauth_domain],
            "frame-ancestors": ["'self'"],
            "worker-src": ["'self'"],
            "base-uri": ["'self'"],
        }

        # Add report URI if applicable
        if self.report_uri:
            csp["report-uri"] = [self.report_uri]

        # Construct the CSP header
        csp_header_value = "; ".join(
            f"{directive} {' '.join(sources)}"
            for directive, sources in csp.items()
        )

        header_name = "Content-Security-Policy-Report-Only" if self.report_only else "Content-Security-Policy"
        response.headers[header_name] = csp_header_value

        # Log CSP application for debugging
        csp_logger.debug(f"CSP applied with nonce={csp_nonce} to {request.url.path}")

        return response
