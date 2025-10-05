# app/helpers/placeholders.py

from datetime import datetime
from app.core.models import Member


def resolve_placeholders(template_html: str, member: Member) -> str:
    """
    Replaces placeholders in the given HTML template string with member-specific information.

    The function takes a template HTML string containing placeholders and a member object
    and substitutes the placeholders with specific values based on the member's information
    such as gender, name, email, birthdate, membership start date, and other attributes.

    :param template_html: The HTML template string that contains placeholders to be replaced.
    :param member: The `Member` object containing the data used to replace placeholders.
    :return: A string representing the HTML with the placeholders replaced by actual member data.
    :rtype: str
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
