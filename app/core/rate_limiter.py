"""
===============================================================================
Project   : gratulo
Module    : shared/rate_limiter.py
Created   : 2025-10-15
Author    : Florian
Purpose   : Global Redis-based rate limiter for controlled mail throughput

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

import time
import logging
from redis import Redis
from app.core.constants import REDIS_URL, RATE_LIMIT_MAILS, RATE_LIMIT_WINDOW

logger = logging.getLogger(__name__)

# Redis-Verbindung über zentrale Konstante
redis_client = Redis.from_url(REDIS_URL, decode_responses=True)

def allow(key: str, limit: int = RATE_LIMIT_MAILS, window: int = RATE_LIMIT_WINDOW) -> bool:
    """
    Determines if a request is allowed under rate limiting constraints.

    This function implements a rate-limiting mechanism using a Redis client to
    track the number of requests made within a specified time window. It ensures
    that the number of requests does not exceed the permitted limit for the given
    key.

    Args:
        key (str): Unique identifier for which the rate limit is applied.
        limit (int): Maximum number of allowed requests within the time window.
        window (int): Time window in seconds for rate limiting.

    Returns:
        bool: True if the request is allowed, False if the rate limit is exceeded.
    """
    bucket = f"{key}:{int(time.time() // window)}"
    current = redis_client.incr(bucket)

    if current == 1:
        redis_client.expire(bucket, window)

    return current <= limit


def wait_for_slot(
    key: str,
    limit: int = RATE_LIMIT_MAILS,
    window: int = RATE_LIMIT_WINDOW,
    sleep_step: float = 2.0
):
    """
    Waits until a rate limit slot becomes available for the given key.

    This function enforces rate limiting by checking if a request can be
    processed for a given key, under specified limits. If the rate limit
    is exceeded, it waits for an available slot by sleeping for small
    intervals of time.

    Args:
        key (str): Identifier to track rate limits for.
        limit (int): Maximum number of allowed requests for the key
            within the given window. Default is RATE_LIMIT_MAILS.
        window (int): Time window in seconds during which the requests
            are counted towards the limit. Default is RATE_LIMIT_WINDOW.
        sleep_step (float): Time to wait in seconds between subsequent
            checks for the availability of a slot. Default is 2.0.
    """
    while not allow(key, limit, window):
        logger.info(f"⏳ Rate limit reached for '{key}'. Waiting for next slot...")
        time.sleep(sleep_step)
