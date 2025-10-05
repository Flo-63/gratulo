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
    Builds a Cron schedule string based on the specified interval type, time, and optionally
    weekday or monthday. The generated string conforms to the standard Cron format.

    The function validates the provided parameters to ensure correctness. It raises appropriate
    exceptions if the parameters are missing, invalid, or outside of their allowed range.

    :param interval_type: The type of interval for the Cron schedule. Supported values are
                          'daily', 'weekly', and 'monthly'.
    :type interval_type: str
    :param time_str: The time string in the format 'HH:MM', which specifies the hour and minute
                     for the schedule.
    :type time_str: str
    :param weekday: For the 'weekly' interval type, this specifies the day of the week
                    (0–6, where 0 is Sunday and 6 is Saturday). This parameter is optional
                    for other interval types.
    :type weekday: str | None
    :param monthday: For the 'monthly' interval type, this specifies the day of the month
                     (1–28). This parameter is optional for other interval types.
    :type monthday: str | None
    :return: A string representing the Cron schedule in the format: 'minute hour day month day_of_week'.
    :rtype: str
    :raises HTTPException: If any parameters are missing or invalid, or if their values are outside
                           the expected range.
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
    Converts a cron expression into a human-readable string describing its scheduling.

    :param cron_expr: A string representing the cron expression. This must consist
                      of exactly 5 parts separated by spaces, corresponding to minute,
                      hour, day, month, and weekday in the format typically used for
                      CRON (e.g., "* * * * *").
    :raises ValueError: If the provided string does not contain exactly 5 parts
                        or is composed of an invalid cron format.
    :return: A human-readable German description of the schedule based on the cron
             expression (e.g., "Täglich um HH:MM"), or an error message stating the
             input was invalid.
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
