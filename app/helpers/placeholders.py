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


def resolve_placeholders(template_html: str, member: Member) -> str:
    """
    Replaces placeholders in a template string with member-specific information.

    This function takes a template HTML string and a Member object, replacing predefined
    placeholders within the template with corresponding details from the Member object. The
    placeholders include variables for the member's personal information like their name,
    gender-specific titles, email, birthdate, and membership information. It supports gender
    distinctions (male, female, or diverse) for proper salutations.

    Args:
        template_html (str): A string containing placeholders to be replaced with member
            information.
        member (Member): An object containing properties such as firstname, lastname, email,
            gender, birthdate, and member_since to populate the placeholders.

    Returns:
        str: The generated string where all placeholders in the template have been replaced
            with the corresponding member-specific data.
    """

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

    geburtstag = ""
    geburtstag_nummer = ""
    if member.birthdate:
        geburtstag = member.birthdate.strftime("%d.%m.%Y")
        geburtstag_nummer = str(datetime.now().year - member.birthdate.year)

    mitglied_seit = ""
    if member.member_since:
        mitglied_seit = str(member.member_since.year)

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

    html = template_html
    for key, val in mapping.items():
        html = html.replace(key, val)
    return html
