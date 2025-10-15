"""
===============================================================================
Project   : gratulo
Module    : app/core/models.py
Created   : 2025-10-05
Author    : Florian
Purpose   : This module provides database models for the Gratulo application.

@docstyle: google
@language: english
@voice: imperative
===============================================================================
"""



from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.core.database import Base
from app.core.constants import LOCAL_TZ
from app.core.encryption import EncryptedType

from sqlalchemy.types import TypeDecorator, Integer

class SQLiteBoolean(TypeDecorator):
    """
    Type decorator that maps Python's boolean values to SQLite's integer type for
    database storage and retrieval.

    This class ensures that Python boolean values (`True` and `False`) are
    correctly interpreted and stored as SQLite integers (`1` and `0` respectively)
    and that SQLite integers are properly converted back to Python booleans upon
    retrieval.

    Attributes:
        impl (TypeEngine): Specifies that the underlying database storage will use
            SQLite's Integer type.
        cache_ok (bool): Indicates whether the type decorator is safe for result
            caching.
    """
    impl = Integer
    cache_ok = True

    def process_bind_param(self, value, dialect):
        # Dieser Teil greift bei Filtern UND Inserts/Updates
        if value in (None, "", "None"):
            return 0
        # Explizite Konvertierung in int zwingt SQLite zum richtigen Vergleich
        return int(bool(value))

    def process_result_value(self, value, dialect):
        # Dieser Teil greift beim Lesen
        if value in (None, "", "None"):
            return False
        return bool(int(value))

class Template(Base):
    """
    Represents a template with unique name and associated HTML content.

    The Template class is used to define and store information about specific
    templates, including their unique names and corresponding HTML content. It is
    also mapped to a database table for persistence.

    Attributes:
        id (int): The unique identifier for each template.
        name (str): The unique name of the template, which serves as its identifier.
        content_html (str): The HTML content associated with the template.
    """
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    content_html = Column(Text, nullable=False)

class Member(Base):
    """
    Represents a member entity in the database.

    The class models a member with personal details and group association,
    with attributes to manage GDPR-compliant soft deletion functionality.

    Attributes:
        id (int): Unique identifier for the member.
        firstname (EncryptedType): First name of the member, stored in an encrypted format.
        lastname (EncryptedType): Last name of the member, stored in an encrypted format.
        email (EncryptedType): Email address of the member, stored in an encrypted format and must be unique.
        birthdate (Date): Birthdate of the member.
        gender (str): Gender of the member represented by a single character ('m', 'w', 'd').
        member_since (Date): Date on which the member joined, optional field.
        group_id (int): Identifier for the group the member is associated with, optional field.
        group (Group): Relationship to the associated group entity.
        is_deleted (bool): Indicates whether the member has been marked as deleted for GDPR compliance.
        deleted_at (DateTime): Timestamp for when the member was marked as deleted, optional field.
    """
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)

    firstname = Column(EncryptedType, index=True, nullable=False)
    lastname = Column(EncryptedType, index=True, nullable=False)
    email = Column(EncryptedType, unique=True, index=True, nullable=False)

    birthdate = Column(Date, nullable=False)
    gender = Column(String(1), nullable=False, default="d")  # m, w, d
    member_since = Column(Date, nullable=True)

    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True, index=True)
    group = relationship("Group", back_populates="members")

    # DSGVO-konformes Soft-Delete
    is_deleted = Column(SQLiteBoolean, nullable=False, default=False, server_default="0")
    # is_deleted = Column(Boolean, nullable=False, default=False, server_default="false")
    deleted_at = Column(DateTime, nullable=True)

    @property
    def is_active(self):
        return not self.is_deleted

class ImportMeta(Base):
    """
    Represents metadata related to imports.

    This class maintains information about imports, including their
    timestamps. It provides mechanisms to retrieve metadata related
    to the import process and offers utilities for timezone
    conversion. Primarily used for tracking and auditing purposes.

    Attributes:
        id (int): The unique identifier for the import metadata record.
        last_imported (datetime): The timestamp of the last import in
            UTC timezone.
    """
    __tablename__ = "import_meta"

    id = Column(Integer, primary_key=True)
    last_imported = Column(DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc),
                           nullable=False)

    @property
    def last_imported_local(self):
        return self.last_imported.astimezone(LOCAL_TZ) if self.last_imported else None

class MailerJob(Base):
    """
    Represents a mailer job entity for defining email jobs with scheduling and
    related configurations.

    This class is used to store information about a specific mailer job, such
    as its associated template, scheduling details, and related group data.
    MailerJob provides relationships to related tables like Template, Group,
    and MailerJobLog, enabling data to be organized efficiently.

    Attributes:
        id (int): Unique identifier for the mailer job.
        name (str): Name of the mailer job, must be unique.
        template_id (int): Foreign key referencing the associated email template.
        template (Template): Relationship to the Template entity.
        subject (str): Subject line for the email, optional field.
        selection (str): Criteria for job selection, e.g., "birthday" or "entry".
        group_id (int): Foreign key referencing the associated group, optional.
        group (Group): Relationship to the Group entity.
        cron (str): Cron string for scheduling the email job, optional field.
        once_at (datetime): Specific date and time for a one-time email job,
            optional field.
        created_at (datetime): UTC timestamp when the job was created.
        updated_at (datetime): UTC timestamp when the job was last updated.
        logs (list[MailerJobLog]): Relationship to MailerJobLog entities, with
            cascading delete-orphan behavior.
    """
    __tablename__ = "mailer_jobs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)

    template_id = Column(Integer, ForeignKey("templates.id"), nullable=False)
    template = relationship("Template", backref="jobs")
    subject = Column(String(200), nullable=True)

    selection = Column(String(20), nullable=False)  # "birthday" oder "entry"

    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True, index=True)
    group = relationship("Group", back_populates="mailer_jobs")

    cron = Column(String(100), nullable=True)
    once_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc),
                        nullable=False)
    updated_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc),
                        nullable=False)

    logs = relationship(
        "MailerJobLog",
        back_populates="job",
        cascade="all, delete-orphan"
    )

    @property
    def created_at_local(self):
        if self.created_at is None:
            return None
        return self.created_at.astimezone(LOCAL_TZ)

    @property
    def updated_at_local(self):
        if self.updated_at is None:
            return None
        return self.updated_at.astimezone(LOCAL_TZ)

    @property
    def once_at_local(self):
        return self.once_at.astimezone(LOCAL_TZ) if self.once_at else None

class MailerJobLog(Base):
    """
    Represents a log entry for a specific mailer job.

    This class captures detailed information regarding the execution of a mailer
    job, including timestamps, execution status, and performance metrics. It is
    linked to a mailer job instance to maintain an audit trail of operations and
    their respective outcomes.

    Attributes:
        id (int): Unique identifier of the mailer job log entry.
        job_id (int): Identifier linking the log entry to a specific mailer job.
        job (MailerJob): Relationship mapping to the corresponding MailerJob entity.
        executed_at (datetime): Timestamp indicating when the job log was created.
        logical_date (date, optional): Logical date associated with the log entry,
            used for grouping or scheduling purposes.
        status (str): Status of the execution, typically indicating success or failure.
        details (str, optional): Detailed description or notes about the job execution.
        duration_ms (int, optional): Duration of the job execution in milliseconds.
        mails_sent (int, optional): Number of mails successfully sent during the execution.
        errors_count (int, optional): Number of errors encountered during the execution.
    """
    __tablename__ = "mailer_job_logs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("mailer_jobs.id", ondelete="CASCADE"), nullable=False)
    job = relationship("MailerJob", back_populates="logs")

    executed_at = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         nullable=False)

    logical_date = Column(Date, nullable=True)
    status = Column(String(20), nullable=False, default="ok")
    details = Column(Text, nullable=True)

    duration_ms = Column(Integer, nullable=True)
    mails_sent = Column(Integer, nullable=True, default=0)
    errors_count = Column(Integer, nullable=True, default=0)

    @property
    def cron_human(self):
        if not self.job or not self.job.cron:
            return None
        from app.helpers.cron_helpers import cron_to_human
        return cron_to_human(self.job.cron)

    @property
    def executed_at_local(self):
        if self.executed_at is None:
            return None
        return self.executed_at.astimezone(LOCAL_TZ)

class MailerConfig(Base):
    """
    Represents the configuration settings for a mailer service.

    This class is part of the database model and contains all necessary
    attributes required for configuring both standard SMTP settings as
    well as OAuth-based email settings. It supports features like TLS,
    credential encryption, and storage for administrative email addresses.

    Attributes:
        id (int): Primary key for the mailer configuration record.

        smtp_host (EncryptedType): The SMTP server hostname or IP address.
        smtp_port (int): The port used for SMTP communication. Defaults to 587.
        smtp_user (EncryptedType): The username to authenticate with the
            SMTP server.
        smtp_password (EncryptedType): The password used for SMTP authentication.
        use_tls (bool): Indicates whether TLS encryption is used during SMTP
            communication. Defaults to True.
        from_address (EncryptedType): The email address used as the sender address
            in outgoing emails.

        auth_method (str): The authentication method for sending emails, which
            can be either "email" (default) or "oauth".

        oauth_client_id (EncryptedType or None): The client ID used for OAuth
            authentication, if applicable.
        oauth_client_secret (EncryptedType or None): The client secret used for
            OAuth authentication, if applicable.
        oauth_provider_url (str or None): The URL for the OAuth provider.
        oauth_redirect_uri (str or None): The redirect URI used for OAuth flows.

        admin_emails (str or None): A comma-separated list of administrative email
            addresses for notifications or other purposes.
    """
    __tablename__ = "mailer_config"

    id = Column(Integer, primary_key=True, index=True)

    # Mailer
    smtp_host = Column(EncryptedType, nullable=False)
    smtp_port = Column(Integer, default=587)
    smtp_user = Column(EncryptedType, nullable=False)
    smtp_password = Column(EncryptedType, nullable=False)
    use_tls = Column(Boolean, default=True)
    from_address = Column(EncryptedType, nullable=False)

    # Authentifizierung
    auth_method = Column(String(20), default="email", nullable=False)  # "email" oder "oauth"

    # OAuth-Konfiguration
    oauth_client_id = Column(EncryptedType, nullable=True)
    oauth_client_secret = Column(EncryptedType, nullable=True)
    oauth_provider_url = Column(String(500), nullable=True)
    oauth_redirect_uri = Column(String(500), nullable=True)

    # Admin-E-Mails (Komma-getrennt)
    admin_emails = Column(Text, nullable=True)

class MailerJobLock(Base):
    """
    Represents a lock for job scheduling in a mailing system.

    This class is designed to handle and manage job locks in a mailing system.
    It tracks when a job lock is acquired and provides functionality to convert
    the acquisition time to a local timezone.

    Attributes:
        job_id (int): The unique identifier for the job lock.
        acquired_at (datetime.datetime): The UTC timestamp when the job lock
            was acquired.
    """
    __tablename__ = "mailer_job_locks"
    job_id = Column(Integer, primary_key=True)
    acquired_at = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         nullable=False)

    @property
    def acquired_at_local(self):
        return self.acquired_at.astimezone(LOCAL_TZ) if self.acquired_at else None

class Group(Base):
    """Represents a group entity within the system.

    This class is used to define a group with unique attributes such as name and
    default status. It also establishes relationships with other entities, such
    as members and mailer jobs. A group serves as a container for organizing
    related members and their associated activities.

    Attributes:
        id (int): The unique identifier of the group.
        name (str): The name of the group, must be unique and not null.
        members (list): A list of members associated with the group.
        mailer_jobs (list): A list of mailer jobs associated with the group.
        is_default (bool): Indicates if the group is a default group.
    """
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True, index=True)

    members = relationship("Member", back_populates="group", cascade="all, delete")
    mailer_jobs = relationship("MailerJob", back_populates="group", cascade="all, delete")

    is_default = Column(Boolean, default=False, nullable=False)


class AdminUser(Base):
    """Represents an admin user in the system with authentication and metadata.

    This class is used to define the database schema and interaction for
    admin users. It includes fields for authentication credentials,
    two-factor authentication support, and metadata such as creation time
    and last login. The `AdminUser` class inherits from `Base` and represents
    the `admin_users` table in the database.

    Attributes:
        id (int): The unique identifier for the admin user.
        username (str): The unique username for the admin user.
        password_hash (str): The hashed password of the admin user.
        is_2fa_enabled (bool): Indicates if two-factor authentication is enabled.
        created_at (datetime): The timestamp when the admin user was created.
        last_login_at (datetime): The timestamp of the last login of the admin user.
        is_active (bool): Indicates if the admin user account is active.
    """
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # 2FA-Felder
    totp_secret = Column(String(64), nullable=True)
    is_2fa_enabled = Column(SQLiteBoolean, nullable=False, default=False, server_default="0")
    backup_codes = Column(JSON, nullable=True)

    # Metadaten
    created_at = Column(DateTime(timezone=True),
                        default=lambda: datetime.now(timezone.utc),
                        nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(SQLiteBoolean, nullable=False, default=True, server_default="1")

    def __repr__(self):
        return f"<AdminUser(username={self.username!r}, active={self.is_active})>"