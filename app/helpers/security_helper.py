"""
===============================================================================
Project   : gratulo
Module    : app/helpers/security_helper.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides security-related helper functions for password hashing and verification.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""



from passlib.hash import bcrypt
import hashlib

def set_password(plain_password: str) -> str:
    """
    Hashes a plain text password using bcrypt hashing algorithm.

    This function takes a plain text password and generates a hashed version
    of it using the bcrypt library. The hashed password can be stored securely
    and used for comparisons during authentication.

    Args:
        plain_password: The plain text password to be hashed.

    Returns:
        A hashed string representation of the input password.
    """
    return bcrypt.hash(plain_password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies whether a plain text password matches a hashed password.

    This function compares a plain text password with a hashed password
    to determine if they match.

    Args:
        plain_password (str): The plain text password to verify.
        hashed_password (str): The hashed password to compare against.

    Returns:
        bool: True if the plain text password matches the hashed password,
        otherwise False.
    """
    return bcrypt.verify(plain_password, hashed_password)

def anonymize(value: str) -> str:
    """
    Anonymizes the provided string by generating a hashed version of it.

    The function takes a string input, encodes it, and calculates its SHA-256 hash.
    It then returns the first ten characters of the digest. If the input is an empty
    string, it returns a default placeholder ("-").

    Args:
        value (str): The string to be anonymized.

    Returns:
        str: A hashed and truncated string, or "-" if the input is empty.
    """
    if not value:
        return "-"
    return hashlib.sha256(value.encode()).hexdigest()[:10]

def mask_email(email: str) -> str:
    """
    Masks an email address by obfuscating the local name and part of the domain for privacy purposes.

    This function takes an email as input, validates its structure, and returns a masked version.
    If the given email is invalid or empty, a default masked value is returned.

    Args:
        email (str): The email address to be masked.

    Returns:
        str: The masked version of the provided email address.
    """
    if not email or "@" not in email:
        return "****"
    name, domain = email.split("@", 1)
    masked_name = name[0] + "****" + name[-1] if len(name) > 2 else "****"
    masked_domain = domain.split(".")[0][0] + "****"
    return f"{masked_name}@{masked_domain}..."