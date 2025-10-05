import logging

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_logging(level=logging.INFO):
    """
    Configures the logging module with a specified level and a predefined format and
    date format. This function adjusts the logging settings for the application,
    including log detail level and appearance, making debugging and monitoring easier
    by outputting consistent and formatted log messages.

    :param level: The logging level to be configured. The default is `logging.INFO`.
    :type level: int
    """
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
    )

import os

def get_audit_logger():
    """
    Initializes and retrieves a dedicated audit logger, ensuring that audit logs are written to
    a file named `audit.log` within a specified directory (`app/data/instance`). If the logger
    has already been created, the existing instance is returned. The logger includes configurations
    such as logging level, formatter, and handler to manage audit-specific events.

    :raises OSError: An exception raised if the logger's directory cannot be created or is inaccessible.

    :return: A configured logger instance for audit logging.
    :rtype: logging.Logger
    """
    audit_logger = logging.getLogger("audit")
    if not audit_logger.handlers:
        # Create a dedicated audit log file inside instance/
        log_dir = os.path.join("app", "data", "instance")
        os.makedirs(log_dir, exist_ok=True)
        audit_file = os.path.join(log_dir, "audit.log")

        handler = logging.FileHandler(audit_file)
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(asctime)s [AUDIT] %(message)s", "%Y-%m-%d %H:%M:%S"))

        audit_logger.addHandler(handler)
        audit_logger.setLevel(logging.INFO)
        audit_logger.propagate = False  # don't duplicate to root log

    return audit_logger
