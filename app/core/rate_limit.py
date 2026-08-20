"""
===============================================================================
Project   : gratulo
Module    : app/core/rate_limit.py
Created   : 2026-08-20
Author    : Florian
Purpose   : HTTP rate limiting helpers built on fastapi-limiter.

            Provides a trusted-proxy-aware client identifier (so per-IP limits
            cannot be bypassed by spoofing X-Forwarded-For) and a fail-open
            dependency factory (so a Redis outage degrades limiting instead of
            turning every guarded request into a 500).

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

import logging

from fastapi import HTTPException, Request, Response
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

from app.core.constants import TRUSTED_PROXY_COUNT

logger = logging.getLogger(__name__)


async def client_identifier(request: Request) -> str:
    """
    Identify the client for rate limiting using a trusted-proxy-aware IP.

    The left-most X-Forwarded-For entry is set by the client and therefore
    forgeable; using it lets an attacker rotate the header to get a fresh rate
    bucket on every request. With ``TRUSTED_PROXY_COUNT`` proxies in front (each
    appends exactly one entry as the request passes through), the real client IP
    is the entry that many positions from the right. If the header is missing or
    too short, fall back to the immediate peer address.

    Args:
        request (Request): The incoming request.

    Returns:
        str: ``"<client_ip>:<path>"`` – IP plus path, matching the library's
        default identifier shape so buckets stay per-endpoint.
    """
    ip = None
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if len(parts) >= TRUSTED_PROXY_COUNT:
            ip = parts[-TRUSTED_PROXY_COUNT]
    if not ip:
        ip = request.client.host if request.client else "unknown"
    return f"{ip}:{request.scope['path']}"


def rate_limit(times: int, seconds: int):
    """
    Build a fail-open rate-limit dependency.

    Behaves like fastapi-limiter's ``RateLimiter`` when Redis is healthy
    (including returning HTTP 429 once the limit is exceeded), but never turns a
    Redis outage into a 500: if the limiter is not initialized, or Redis errors
    mid-request, the request is allowed through (and the event is logged) so that
    authentication and other guarded endpoints stay available.

    Args:
        times (int): Allowed requests within the window.
        seconds (int): Window length in seconds.

    Returns:
        Callable: An async FastAPI dependency.
    """
    limiter = RateLimiter(times=times, seconds=seconds)

    async def dependency(request: Request, response: Response):
        if not FastAPILimiter.redis:
            logger.warning(
                "Rate limiter not initialized (Redis unavailable) – allowing "
                "request to %s without limiting.",
                request.scope.get("path"),
            )
            return
        try:
            return await limiter(request, response)
        except HTTPException:
            raise  # 429 Too Many Requests (and any explicit HTTP error) must propagate
        except Exception as e:
            logger.warning(
                "Rate limiter error (%s) – allowing request to %s without limiting.",
                type(e).__name__,
                request.scope.get("path"),
            )
            return

    return dependency
