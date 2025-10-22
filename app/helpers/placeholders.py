"""
===============================================================================
Project   : gratulo
Module    : app/helpers/placeholders.py
Created   : 2025-10-05
Author    : Florian
Purpose   : Resolves dynamic placeholders in email templates based on member data
            and configurable labels (ANNIVERSARY / EVENT).

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""

from datetime import datetime
from app.core.constants import LABELS


def resolve_placeholders(template_html: str, member, **extra) -> str:
    """
    Replaces placeholders in an HTML template string with corresponding values based on
    a provided member object and dynamic context. Handles case-insensitive matching and
    spacing tolerance for placeholder replacements.

    Args:
        template_html (str): The HTML template string containing placeholders to be resolved.
        member: The member object containing information such as gender, name, email,
            and other attributes used for placeholder substitutions.
        **extra: Additional dynamic context as key-value pairs to be included
            in the placeholder mapping.

    Returns:
        str: The HTML string with placeholders resolved to their corresponding values.
    """

    html = template_html or ""
    mapping = {}

    # --------------------------------------------------------------------
    # 🟩 Base member fields (always available)
    # --------------------------------------------------------------------
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
    else:
        anrede = "Liebe*r"
        anrede_lang = "Sehr geehrte*r"
        bezeichnung = LABELS.get("entity_singular", "Mitglied")
        pronomen = "sie"
        possessiv = "ihr"

    mapping.update({
        "Vorname": member.firstname or "",
        "Nachname": member.lastname or "",
        "Email": member.email or "",
        "Anrede": anrede,
        "AnredeLang": anrede_lang,
        "Bezeichnung": bezeichnung,
        "Pronomen": pronomen,
        "Possessiv": possessiv,
    })

    # --------------------------------------------------------------------
    # 🟨 Standard placeholders (legacy support)
    # --------------------------------------------------------------------
    if getattr(member, "birthdate", None):
        birthdate = member.birthdate.strftime("%d.%m.%Y")
        mapping["Geburtstag"] = birthdate
        mapping["geburtstag"] = birthdate
        years = datetime.now().year - member.birthdate.year - (
            (datetime.now().month, datetime.now().day) < (member.birthdate.month, member.birthdate.day)
        )
        mapping["Geburtstagsnummer"] = str(years)
        mapping["geburtstagsnummer"] = str(years)

    if getattr(member, "member_since", None):
        entry_date = member.member_since.strftime("%d.%m.%Y")
        mapping["Eintritt"] = entry_date
        mapping["eintritt"] = entry_date
        years = datetime.now().year - member.member_since.year - (
            (datetime.now().month, datetime.now().day) < (member.member_since.month, member.member_since.day)
        )
        mapping["Eintrittsnummer"] = str(years)
        mapping["eintrittsnummer"] = str(years)

    # --------------------------------------------------------------------
    # 🟦 Dynamic date labels from environment (e.g. Servicebeginn, Geburtstag)
    # --------------------------------------------------------------------
    label_field_map = {
        "date1": "birthdate",
        "date2": "member_since",
    }

    for key, field_name in label_field_map.items():
        label = LABELS.get(key, key.capitalize())
        label_type = LABELS.get(f"{key}_type", "ANNIVERSARY").upper()
        value = getattr(member, field_name, None)

        if not value:
            continue

        value_str = value.strftime("%d.%m.%Y")
        mapping[label] = value_str
        mapping[label.lower()] = value_str

        # Add numeric form (e.g. ServicebeginnNummer)
        if label_type == "ANNIVERSARY":
            years = datetime.now().year - value.year - (
                (datetime.now().month, datetime.now().day) < (value.month, value.day)
            )
            mapping[f"{label}Nummer"] = str(years)
            mapping[f"{label.lower()}nummer"] = str(years)

    # --------------------------------------------------------------------
    # 🟧 Additional dynamic context (from _select_template etc.)
    # --------------------------------------------------------------------
    for k, v in (extra or {}).items():
        if not k:
            continue
        mapping[k] = str(v)
        mapping[k.lower()] = str(v)

    # --------------------------------------------------------------------
    # 🟥 Perform replacements (case-insensitive, tolerant for spacing)
    # --------------------------------------------------------------------
    for key, val in mapping.items():
        if not isinstance(val, str):
            val = str(val)

        html = (
            html.replace(f"{{{{{key}}}}}", val)
            .replace(f"{{{{ {key} }}}}", val)
            .replace(f"{{{{{key.lower()}}}}}", val)
            .replace(f"{{{{ {key.lower()} }}}}", val)
        )

    return html
