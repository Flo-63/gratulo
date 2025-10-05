from pydantic import BaseModel, Field, field_validator, EmailStr
from datetime import date, datetime
from typing import Optional

# ------------------------------
# 📘 GROUP SCHEMAS
# ------------------------------

class GroupBase(BaseModel):
    """
    Represents the foundational structure of a group entity.

    This class serves as a base model representation of a group, typically used
    for organizing entities with a name and a flag indicating if it's the default
    group.

    :ivar name: The name of the group.
    :type name: str
    :ivar is_default: Indicates if this group is the default group. Defaults to False.
    :type is_default: bool
    """
    name: str
    is_default: bool = False

class GroupCreate(GroupBase):
    """
    Represents a class for creating a new group entity.

    This class inherits from `GroupBase` and serves as a specialized
    implementation that handles the creation of group entities. It
    does not contain any unique methods but can extend `GroupBase`
    functionality if needed in the future.

    """
    pass

class GroupUpdate(GroupBase):
    """
    Represents an update to a group by inheriting from the base
    class `GroupBase`.

    This class is used to provide modifications or updates to the
    data of a group. It extends functionality provided by the base
    group class while maintaining consistency with its attributes
    and structure.
    """
    pass

class GroupResponse(GroupBase):
    """
    Represents a response object for a group.

    This class extends the `GroupBase` and includes additional
    attributes specific to the response context. It is
    designed to be used in scenarios where a group-related
    response object is needed in an ORM-enabled environment.

    :ivar id: Unique identifier for the group.
    :type id: int
    """
    id: int

    class Config:
        from_attributes = True


# ------------------------------
# 👤 MEMBER SCHEMAS
# ------------------------------

class MemberBase(BaseModel):
    """
    Represents a base model for a member.

    This class is designed to provide a structure for storing information
    about a member, including personal details and associated data. It
    inherits from `BaseModel` to leverage validation and data management
    features.

    :ivar firstname: The first name of the member.
    :type firstname: str
    :ivar lastname: The last name of the member.
    :type lastname: str
    :ivar email: The email address of the member.
    :type email: EmailStr
    :ivar birthdate: The date of birth of the member, if provided.
    :type birthdate: Optional[date]
    :ivar gender: The gender of the member, if provided.
    :type gender: Optional[str]
    :ivar member_since: The date when the membership started, if provided.
    :type member_since: Optional[date]
    :ivar group_id: The identifier of the group associated with the member, if provided.
    :type group_id: Optional[int]
    """
    firstname: str
    lastname: str
    email: EmailStr
    birthdate: Optional[date] = None
    gender: Optional[str] = None
    member_since: Optional[date] = None
    group_id: Optional[int] = None  # 🔹 Neue Zuordnung zu Gruppe


class MemberCreate(MemberBase):
    """
    Represents the creation of a new member entity.

    This class is derived from MemberBase and is used to define the
    structure and properties specific to creating a new member. It is
    intended to extend functionality relevant for member creation while
    maintaining a close relationship with the base member structure.
    """
    pass


class MemberUpdate(BaseModel):
    """
    Represents an update object for a member.

    This class is used to encapsulate the updates allowed for a member's profile
    information, including personal details, contact information, and membership
    attributes. It inherits from BaseModel, enabling validation and type enforcement
    on the provided data.

    :ivar firstname: Member's first name.
    :type firstname: Optional[str]
    :ivar lastname: Member's last name.
    :type lastname: Optional[str]
    :ivar email: Member's email address.
    :type email: Optional[EmailStr]
    :ivar birthdate: Member's date of birth.
    :type birthdate: Optional[date]
    :ivar gender: Member's gender.
    :type gender: Optional[str]
    :ivar member_since: The date when the member joined.
    :type member_since: Optional[date]
    :ivar group_id: The ID of the group to which the member belongs, allowing changes to group assignment.
    :type group_id: Optional[int]
    """
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    email: Optional[EmailStr] = None
    birthdate: Optional[date] = None
    gender: Optional[str] = None
    member_since: Optional[date] = None
    group_id: Optional[int] = None  # 🔹 Änderung der Gruppenzugehörigkeit erlaubt


class MemberResponse(MemberBase):
    """
    Represents a response for a member containing detailed information related to the
    member's status within the system. This class provides structured data that includes
    metadata such as deletion status, timestamps for deletion, and associated group details.

    The purpose of this class is to serve as a response model for member-related API endpoints.

    :ivar id: Unique identifier of the member.
    :type id: int
    :ivar is_deleted: Indicates whether the member is deleted. Defaults to ``False``.
    :type is_deleted: Optional[bool]
    :ivar deleted_at: Timestamp indicating when the member was deleted. Defaults to ``None``.
    :type deleted_at: Optional[date]
    :ivar group: Contains details about the associated group with the member.
    :type group: Optional[GroupResponse]
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

class TokenData(BaseModel):
    username: str