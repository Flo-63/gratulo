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

def set_password(plain_password: str) -> str:
    """
    Hashes a plain text password using bcrypt.

    The function takes a plain text password and returns its hashed version
    using the bcrypt library. Bcrypt is a secure way to hash passwords, ensuring
    that user passwords are stored safely and resilient against attacks.

    Args:
        plain_password (str): The plain text password to be hashed.

    Returns:
        str: The hashed password as a string.
    """
    return bcrypt.hash(plain_password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies if a plain text password matches its hashed counterpart.

    This function takes a plain password and its corresponding hashed password and
    compares them for verification. It is commonly used for authentication purposes
    to ensure the validity of provided user credentials.

    Args:
        plain_password (str): The plain text password to verify.
        hashed_password (str): The hashed password to compare against.

    Returns:
        bool: True if the plain password matches the hashed password, False otherwise.
    """
    return bcrypt.verify(plain_password, hashed_password)