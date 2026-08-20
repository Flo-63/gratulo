"""
===============================================================================
Project   : gratulo
Module    : app/services/oauth_service.py
Created   : 2026-08-20
Author    : Florian
Purpose   : Google OpenID Connect (OAuth 2.0 Authorization Code) login flow.

            The mailer configuration only stores a client id/secret, so the
            provider is fixed to Google (all CSP allow-lists already point
            there). Authentication is delegated to Google; authorization is
            decided by the comma-separated ``admin_emails`` allow-list on the
            MailerConfig.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

import json
import urllib.error
import urllib.parse
import urllib.request

from app.core.constants import BASE_URL

# Fixed Google OIDC endpoints (the config UI only collects client id/secret).
GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"

OAUTH_SCOPE = "openid email profile"
HTTP_TIMEOUT = 10  # seconds


class OAuthError(Exception):
    """Raised when the OAuth exchange with the provider fails."""


def is_configured(config) -> bool:
    """
    Report whether OAuth is usable, i.e. a client id and secret are present.

    Args:
        config: The MailerConfig instance (or None).

    Returns:
        bool: True if both client id and secret are configured.
    """
    return bool(config and config.oauth_client_id and config.oauth_client_secret)


def redirect_uri() -> str:
    """
    Build the redirect URI that must be registered with the provider.

    Returns:
        str: ``<BASE_URL>/oauth/callback``.
    """
    return f"{BASE_URL.rstrip('/')}/oauth/callback"


def build_authorization_url(config, state: str) -> str:
    """
    Build the Google authorization URL for the Authorization Code flow.

    Args:
        config: The MailerConfig instance holding the client id.
        state (str): An opaque, per-request CSRF token to be echoed back.

    Returns:
        str: The fully-formed authorization endpoint URL.
    """
    params = {
        "client_id": config.oauth_client_id,
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": OAUTH_SCOPE,
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"


def _post_form(url: str, data: dict) -> dict:
    """Send an x-www-form-urlencoded POST and parse a JSON response."""
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise OAuthError(f"Token-Endpoint antwortete mit HTTP {e.code}")
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        raise OAuthError(f"Token-Endpoint nicht erreichbar: {type(e).__name__}")


def _get_json(url: str, access_token: str) -> dict:
    """Send an authenticated GET and parse a JSON response."""
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise OAuthError(f"Userinfo-Endpoint antwortete mit HTTP {e.code}")
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        raise OAuthError(f"Userinfo-Endpoint nicht erreichbar: {type(e).__name__}")


def fetch_userinfo(config, code: str) -> dict:
    """
    Exchange an authorization code for tokens and fetch the user's profile.

    The access token is obtained via a server-to-server call authenticated with
    the client secret, so the userinfo response it retrieves is trustworthy.

    Args:
        config: The MailerConfig instance (client id/secret).
        code (str): The authorization code returned to the redirect URI.

    Returns:
        dict: The provider's userinfo document (contains ``email`` and
        ``email_verified``).

    Raises:
        OAuthError: If the token exchange or userinfo lookup fails, or no
        access token is returned.
    """
    token_response = _post_form(
        GOOGLE_TOKEN_ENDPOINT,
        {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": config.oauth_client_id,
            "client_secret": config.oauth_client_secret,
            "redirect_uri": redirect_uri(),
        },
    )
    access_token = token_response.get("access_token")
    if not access_token:
        raise OAuthError("Kein Access-Token vom Provider erhalten")

    return _get_json(GOOGLE_USERINFO_ENDPOINT, access_token)


def allowed_admin_emails(config) -> list[str]:
    """
    Return the normalized (lower-cased, trimmed) admin allow-list.

    Args:
        config: The MailerConfig instance (or None).

    Returns:
        list[str]: The configured admin e-mail addresses; empty if none.
    """
    if not config or not config.admin_emails:
        return []
    return [e.strip().lower() for e in config.admin_emails.split(",") if e.strip()]


def is_admin_email(config, email: str) -> bool:
    """
    Check whether an e-mail address is on the admin allow-list.

    Args:
        config: The MailerConfig instance.
        email (str): The e-mail address to check.

    Returns:
        bool: True if the (normalized) e-mail is allow-listed.
    """
    return (email or "").strip().lower() in allowed_admin_emails(config)


def is_email_verified(userinfo: dict) -> bool:
    """
    Interpret the provider's ``email_verified`` claim (bool or string).

    Args:
        userinfo (dict): The provider userinfo document.

    Returns:
        bool: True only if the provider asserts the e-mail is verified.
    """
    value = userinfo.get("email_verified")
    return value is True or str(value).lower() == "true"
