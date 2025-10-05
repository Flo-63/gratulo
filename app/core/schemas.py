"""
===============================================================================
Project   : gratulo
Module    : app/core/schemas.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module defines schemas for data validation and serialization.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""



from pydantic import BaseModel, Field, field_validator, EmailStr
from datetime import date, datetime
from typing import Optional

# ------------------------------
#  GROUP SCHEMAS
# ------------------------------


class GroupBase(BaseModel):
    """
    Represents the base structure of a group entity.

    This class outlines the fundamental attributes and structure of a group,
    providing a template for creating or handling group-related data. It
    serves as a foundational class that can be extended or used for defining
    group configurations.

    Attributes:
        name (str): The name of the group.
        is_default (bool): Indicates whether this group is the default group.
    """
    name: str
    is_default: bool = False

class GroupCreate(GroupBase):
    """
    Represents a model for creating a new group.

    This class is intended to be used for defining the parameters required for
    creating a new group. It inherits from the `GroupBase` class, which may
    contain shared attributes or functionality for group-related operations.

    Attributes:
        None
    """
    pass

class GroupUpdate(GroupBase):
    """
    Represents an update to a group.

    This class is used to define the structure for updating group information.
    It extends from GroupBase and inherits all its properties, which form the
    base structure for group data. Typically, this class can be utilized when
    updating group-specific details through APIs or internal systems.

    Attributes:
        None
    """
    pass

class GroupResponse(GroupBase):
    """Represents the response for a group entity.

    This class is a response model that extends `GroupBase` and includes
    additional identifiers or information needed when handling group-related
    API operations or responses.

    Attributes:
        id (int): The unique identifier for the group.
    """
    id: int

    class Config:
        from_attributes = True


# ------------------------------
#  MEMBER SCHEMAS
# ------------------------------

class MemberBase(BaseModel):
    """Represents a member with basic details.

    This class is used for defining and managing member data, including their
    personal details and optional membership metadata. It extends `BaseModel`
    to utilize validation and parsing capabilities.

    Attributes:
        firstname (str): The first name of the member.
        lastname (str): The last name of the member.
        email (EmailStr): The email address of the member.
        birthdate (Optional[date]): The date of birth of the member. Defaults to None.
        gender (Optional[str]): The gender of the member. Defaults to None.
        member_since (Optional[date]): The date when the member joined. Defaults to None.
        group_id (Optional[int]): The ID of the group to which the member belongs. Defaults to None.
    """
    firstname: str
    lastname: str
    email: EmailStr
    birthdate: Optional[date] = None
    gender: Optional[str] = None
    member_since: Optional[date] = None
    group_id: Optional[int] = None  # 🔹 Neue Zuordnung zu Gruppe


class MemberCreate(MemberBase):
    """Represents a model for creating a member.

    This class is used for defining the creation of a member. It is a
    subclass of `MemberBase`, which serves as the base for member-related
    operations.

    Attributes:
        None
    """
    pass


class MemberUpdate(BaseModel):
    """
    Represents an update model for a member.

    This class is used to handle updates for a member's information. It contains
    various optional attributes representing the details of the member that can
    be updated, such as their personal details, membership information, or group
    association. This class is typically used in scenarios where partial updates
    to a member's data are required.

    Attributes:
        firstname (Optional[str]): The first name of the member.
        lastname (Optional[str]): The last name of the member.
        email (Optional[EmailStr]): The email address of the member.
        birthdate (Optional[date]): The birthdate of the member.
        gender (Optional[str]): The gender of the member.
        member_since (Optional[date]): The date since the member has been part
            of the organization or group.
        group_id (Optional[int]): The ID of the group the member belongs to.
    """
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    email: Optional[EmailStr] = None
    birthdate: Optional[date] = None
    gender: Optional[str] = None
    member_since: Optional[date] = None
    group_id: Optional[int] = None  # 🔹 Änderung der Gruppenzugehörigkeit erlaubt


class MemberResponse(MemberBase):
    """Representation of a member response.

    This class extends MemberBase and represents a detailed response for a
    member, including attributes such as id, deleted status, and group details.

    Attributes:
        id (int): Unique identifier for the member.
        is_deleted (Optional[bool]): Indicates if the member is deleted. Default
            is False.
        deleted_at (Optional[date]): Date when the member was deleted, if
            applicable. Default is None.
        group (Optional[GroupResponse]): Details of the group associated with the
            member. Default is None.
    """
    id: int
    is_deleted: Optional[bool] = False
    deleted_at: Optional[date] = None
    group: Optional[GroupResponse] = None  # 🔹 Optional: Gruppendetails im Response

    @field_validator("deleted_at", mode="before")
    def convert_datetime_to_date(cls, v):
        """Falls deleted_at ein datetime ist, in date konvertieren."""
        if isinstance(v, datetime):
            return v.date()
        return v

    class Config:
        from_attributes = True

# ------------------------------
#  AUTH SCHEMAS
# ------------------------------


class TokenData(BaseModel):
    """
    Represents the token data associated with a user.

    This class is used to store and manage token-related data, such as the
    username, for authentication purposes. It extends the BaseModel from Pydantic
    for data validation and parsing.

    Attributes:
        username (str): The username associated with the token.
    """
    username: str