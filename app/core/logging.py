"""
===============================================================================
Project   : gratulo
Module    : app/core/logging.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides logging utilities for the Gratulo application.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""


import logging
import os

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_logging(level: str | int | None = None, log_to_file: bool = False):
    """
    Initialize the application's global logging configuration.

    This function sets up the logging format, date format, and log level.
    The level can be configured either via argument or the environment variable `LOG_LEVEL`.
    Example: LOG_LEVEL=DEBUG

    Args:
        level (str | int | None): Desired log level (e.g. 'DEBUG', 'INFO', 'WARNING').
                                  Overrides environment setting if provided.
        log_to_file (bool): If True, also log to `app/data/instance/app.log`.

    Returns:
        None
    """

    # --- Determine the effective log level ---
    env_level = os.getenv("LOG_LEVEL", "INFO").upper()
    if level is None:
        level = env_level

    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    # --- Base configuration ---
    handlers = [logging.StreamHandler()]

    if log_to_file:
        log_dir = os.path.join("app", "data", "instance")
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(os.path.join(log_dir, "app.log"))
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        handlers.append(file_handler)

    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=handlers,
    )

    logging.getLogger().info(f"✅ Logging initialized at level: {logging.getLevelName(level)}")


def get_audit_logger():
    """
    Get or create the audit logger for recording critical or sensitive events.

    Returns:
        logging.Logger: Configured audit logger instance.
    """
    audit_logger = logging.getLogger("audit")
    if not audit_logger.handlers:
        log_dir = os.path.join("app", "data", "instance")
        os.makedirs(log_dir, exist_ok=True)
        audit_file = os.path.join(log_dir, "audit.log")

        handler = logging.FileHandler(audit_file)
        handler.setFormatter(logging.Formatter("%(asctime)s [AUDIT] %(message)s", DATE_FORMAT))
        audit_logger.addHandler(handler)

        # Set the audit logger level based on global configuration
        global_level = logging.getLogger().level
        audit_logger.setLevel(global_level)
        audit_logger.propagate = False

    return audit_logger


def get_csp_logger():
    """
    Get or create a dedicated CSP logger for security header and violation logging.

    Returns:
        logging.Logger: Configured CSP logger instance.
    """
    csp_logger = logging.getLogger("csp")
    if not csp_logger.handlers:
        log_dir = os.path.join("app", "data", "instance")
        os.makedirs(log_dir, exist_ok=True)
        csp_file = os.path.join(log_dir, "csp.log")

        handler = logging.FileHandler(csp_file)
        handler.setFormatter(logging.Formatter("%(asctime)s [CSP] %(levelname)s: %(message)s", DATE_FORMAT))
        csp_logger.addHandler(handler)

        # Inherit global level
        global_level = logging.getLogger().level
        csp_logger.setLevel(global_level)
        csp_logger.propagate = False

    return csp_logger
