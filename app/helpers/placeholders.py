"""
===============================================================================
Project   : gratulo
Module    : app/helpers/placeholders.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module defines functions for resolving placeholders in HTML templates.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

from datetime import datetime
from app.core.models import Member


def resolve_placeholders(template_html: str, member: Member, **extra) -> str:
    """
    Replaces placeholders in a template string with member-specific information
    and optional extra variables such as "age" (for birthdays) or "years"
    (for membership anniversaries).

    This function supports gender-based salutations, date formatting,
    and dynamic extension via keyword arguments for custom placeholders.

    Args:
        template_html (str): The HTML template string containing placeholders.
        member (Member): The member object providing user-specific data.
        **extra: Optional key-value pairs that extend the available placeholders,
                 e.g. age=40 or years=25.

    Returns:
        str: The template string with all placeholders replaced.
    """

    # -----------------------------------------------------------------------
    # Gender-specific text setup
    # -----------------------------------------------------------------------
    gender = (member.gender or "d").lower()

    if gender == "m":
        anrede = "Lieber"
        anrede_lang = "Sehr geehrter"
        bezeichnung = "Herr"
        pronomen = "er"
        possessiv = "sein"
    elif gender == "w":
        anrede = "Liebe"
        anrede_lang = "Sehr geehrte"
        bezeichnung = "Frau"
        pronomen = "sie"
        possessiv = "ihr"
    else:  # divers/neutral
        anrede = "Liebe*r"
        anrede_lang = "Sehr geehrte*r"
        bezeichnung = "Mitglied"
        pronomen = "sie"
        possessiv = "ihr"

    # -----------------------------------------------------------------------
    # Derived member data
    # -----------------------------------------------------------------------
    geburtstag = ""
    geburtstag_nummer = ""
    if member.birthdate:
        geburtstag = member.birthdate.strftime("%d.%m.%Y")
        geburtstag_nummer = str(datetime.now().year - member.birthdate.year)

    mitglied_seit = ""
    if member.member_since:
        mitglied_seit = str(member.member_since.year)

    # -----------------------------------------------------------------------
    # Default placeholder mapping
    # -----------------------------------------------------------------------
    mapping = {
        "{{Vorname}}": member.firstname or "",
        "{{Nachname}}": member.lastname or "",
        "{{Email}}": member.email or "",
        "{{Anrede}}": anrede,
        "{{AnredeLang}}": anrede_lang,
        "{{Bezeichnung}}": bezeichnung,
        "{{Pronomen}}": pronomen,
        "{{Possessiv}}": possessiv,
        "{{Geburtstag}}": geburtstag,
        "{{GeburtstagNummer}}": geburtstag_nummer,
        "{{MitgliedSeit}}": mitglied_seit,
    }

    # -----------------------------------------------------------------------
    # Extend mapping dynamically with optional extra context
    # -----------------------------------------------------------------------
    if "age" in extra and extra["age"] is not None:
        mapping["{{Alter}}"] = str(extra["age"])
    if "years" in extra and extra["years"] is not None:
        mapping["{{Jahre}}"] = str(extra["years"])

    # -----------------------------------------------------------------------
    # Perform replacements
    # -----------------------------------------------------------------------
    html = template_html
    for key, val in mapping.items():
        html = html.replace(key, val)

    return html
