def validate_template_fields(name: str, content_html: str):
    """
    Validates the mandatory fields for a template.

    Ensures that the "name" field is not empty or consists of only whitespace.
    The "content_html" is not validated as it is allowed to be empty.

    :param name: The name of the template which must not be empty.
    :type name: str
    :param content_html: The HTML content of the template, can be empty.
    :type content_html: str
    :return: A tuple where the first value is a boolean indicating the validation
        status, and the second value is a message or None if validation
        succeeded.
    :rtype: tuple[bool, str | None]
    """
    if not (name or "").strip():
        return False, "Name darf nicht leer sein"
    # content_html darf leer sein (z.B. leeres Grundgerüst).
    return True, None

