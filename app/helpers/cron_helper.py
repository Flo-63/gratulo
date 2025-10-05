"""
===============================================================================
Project   : gratulo
Module    : app/helpers/cron_helper.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides helper functions for cron job scheduling.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

# app/helpers/cron_helper.py

from fastapi import HTTPException

WEEKDAYS = {
    "0": "Sonntag",
    "1": "Montag",
    "2": "Dienstag",
    "3": "Mittwoch",
    "4": "Donnerstag",
    "5": "Freitag",
    "6": "Samstag",
}


def build_cron(interval_type: str, time_str: str, weekday: str | None, monthday: str | None) -> str:
    """
    Constructs a CRON expression based on the specified interval type (daily, weekly, or monthly), time,
    and optional weekday or monthday. The CRON expression is used to define a schedule for specific
    intervals.

    This function validates the input parameters, ensuring that they conform to expected formats
    and ranges. Raises errors in case of invalid input.

    Args:
        interval_type: The type of interval for the schedule ("daily", "weekly", "monthly").
        time_str: The time of day for the schedule, formatted as "HH:MM".
        weekday: The day of the week for the schedule, where 0=Sunday, 6=Saturday (required for "weekly").
        monthday: The day of the month for the schedule, limited to values 1 through 28 (required for "monthly").

    Raises:
        HTTPException: Raised if the time is missing, incorrectly formatted, out of valid range,
            or if the interval type, weekday, or monthday is invalid or missing as required.

    Returns:
        str: A CRON expression string representing the schedule.
    """
    if not time_str or ":" not in time_str:
        raise HTTPException(status_code=400, detail="Uhrzeit fehlt oder ist ungültig")
    try:
        h, m = time_str.split(":")
        hour = int(h)
        minute = int(m)
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except Exception:
        raise HTTPException(status_code=400, detail="Uhrzeit ungültig (HH:MM)")

    if interval_type == "daily":
        return f"{minute} {hour} * * *"

    elif interval_type == "weekly":
        if weekday is None or weekday == "":
            raise HTTPException(status_code=400, detail="Wochentag fehlt")
        try:
            wd = int(weekday)
        except Exception:
            raise HTTPException(status_code=400, detail="Wochentag ungültig")
        if wd < 0 or wd > 6:
            raise HTTPException(status_code=400, detail="Wochentag außerhalb des Bereichs (0–6)")
        return f"{minute} {hour} * * {wd}"

    elif interval_type == "monthly":
        if monthday is None or monthday == "":
            raise HTTPException(status_code=400, detail="Tag im Monat fehlt")
        try:
            md = int(monthday)
        except Exception:
            raise HTTPException(status_code=400, detail="Tag im Monat ungültig")
        if md < 1 or md > 28:
            raise HTTPException(status_code=400, detail="Tag im Monat außerhalb des Bereichs (1–28)")
        return f"{minute} {hour} {md} * *"

    else:
        raise HTTPException(status_code=400, detail="Intervalltyp ungültig (daily|weekly|monthly)")


def cron_to_human(cron_expr: str) -> str:
    """
    Converts a cron expression into a more human-readable schedule description.

    This function takes a cron expression, which is a five-part string (minute, hour,
    day of the month, month, and day of the week), and interprets it into a human-readable
    format. Depending on the values in each part of the expression, it will return a
    description such as "Täglich um", "Wöchentlich am", or "Monatlich am". If the cron
    expression is invalid, an appropriate error message string is returned.

    Args:
        cron_expr: A five-part cron expression string (e.g., "30 7 * * 1").

    Returns:
        str: A human-readable representation of the cron schedule or an error message
            if the given cron expression is invalid.
    """
    try:
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            raise ValueError
        minute, hour, day, month, weekday = parts
    except Exception:
        return f"Ungültiger Cron-Ausdruck: {cron_expr}"

    # Uhrzeit
    try:
        t = f"{int(hour):02d}:{int(minute):02d}"
    except Exception:
        t = f"{hour}:{minute}"

    if day == "*" and month == "*" and weekday == "*":
        return f"Täglich um {t}"

    elif weekday != "*" and day == "*" and month == "*":
        wd = WEEKDAYS.get(weekday, weekday)
        return f"Wöchentlich am {wd} um {t}"

    elif day != "*" and month == "*" and weekday == "*":
        return f"Monatlich am {day}. um {t}"

    else:
        return f"Cron: {cron_expr}"
