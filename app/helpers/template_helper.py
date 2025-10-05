"""
===============================================================================
Project   : gratulo
Module    : app/helpers/template_helper.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides functions for validating template fields.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""



def validate_template_fields(name: str, content_html: str):
    """
    Validates the fields of a template and ensures they meet the specified conditions.

    This function checks if the provided `name` is not empty or consists solely of
    whitespace. For `content_html`, empty content is allowed.

    Args:
        name (str): The name of the template to validate.
        content_html (str): The HTML content of the template.

    Returns:
        tuple: A tuple containing a boolean and a string. The boolean indicates whether
               the validation was successful. If validation fails, the string contains
               an error message. If successful, the string is `None`.
    """
    if not (name or "").strip():
        return False, "Name darf nicht leer sein"
    # content_html darf leer sein (z.B. leeres Grundgerüst).
    return True, None

