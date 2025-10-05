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



from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.core.database import Base
from app.core.constants import LOCAL_TZ
from app.core.encryption import EncryptedType

from sqlalchemy.types import TypeDecorator, Integer

class SQLiteBoolean(TypeDecorator):
    """
    Custom TypeDecorator for SQLite to handle boolean-like values.

    This class extends TypeDecorator from SQLAlchemy to provide a custom implementation
    for handling boolean-like values in SQLite, which does not have a native BOOLEAN type.
    It overrides the binding and result processing to ensure proper storage and retrieval
    of boolean values as integers, while maintaining compatibility with Python's
    True/False.

    Attributes:
        impl (TypeEngine): The SQLAlchemy implementation type, in this case, Integer.
        cache_ok (bool): Indicates if the type decorator is safe to cache. It is set to True.
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
    Represents a template entity used for storing template-related metadata
    and content.

    This class is typically associated with a database table for managing
    templates effectively. It includes attributes such as an identifier,
    name, and HTML content of the template.

    Attributes:
        id (int): Unique identifier for the template.
        name (str): Unique name of the template.
        content_html (str): HTML content of the template.
    """
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    content_html = Column(Text, nullable=False)

class Member(Base):
    """
    Represents a member of a group with personal and group-related attributes.

    This class is used to model a member's information, including personal details,
    group associations, and data deletion status. It supports features such as
    encrypted fields for personal data, soft deletion, and relationships to other
    entities. It is designed to work with SQLAlchemy for database interactions.

    Attributes:
        id (int): The unique identifier for the member.
        firstname (EncryptedType): The member's first name, stored as encrypted data.
        lastname (EncryptedType): The member's last name, stored as encrypted data.
        email (EncryptedType): The member's email address, stored as encrypted data,
            required to be unique.
        birthdate (Date): The member's date of birth.
        gender (str): The member's gender, represented as a one-character string.
            Values include 'm' for male, 'w' for female, and 'd' for diverse.
        member_since (Date): The date the member joined, which is optional and may be null.
        group_id (int): The foreign key reference to the associated group's ID.
        group (Group): The associated group object for the member.
        is_deleted (SQLiteBoolean): Indicates whether the member has been soft-deleted.
        deleted_at (DateTime): The timestamp of when the member was marked as deleted.
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
    Represents metadata about an import operation.

    This class is used to store information about the most recent import,
    including the timestamp of when it was last performed. It provides a
    localized version of the last imported timestamp as a convenient
    property.

    Attributes:
        id (int): The primary key of the import metadata.
        last_imported (datetime): The timestamp of the last import, stored
            in UTC.
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
    Represents a mailer job for scheduling and managing email campaigns.

    The MailerJob class is used to define email jobs with specific templates,
    scheduling options, and groups. This is part of a system that manages
    scheduled or event-driven email tasks. Each mailer job is linked to a
    template and optionally associated with a specific group. The class also
    supports scheduling via cron expressions or a specific date/time. Logs
    related to mailer jobs are tracked and managed.

    Attributes:
        id (int): Unique identifier for the mailer job.
        name (str): Name of the mailer job. Must be unique.
        template_id (int): Foreign key to the associated email template.
        template (Template): Relationship to the template used by the mailer job.
        subject (str): Subject line for the email.
        selection (str): Specifies selection criteria (e.g., "birthday" or "entry").
        group_id (int): Foreign key linking the job to a specific group.
        group (Group): Relationship to the group associated with the mailer job.
        cron (str): Cron expression for scheduling recurring jobs.
        once_at (datetime): Specific date and time for one-time jobs.
        created_at (datetime): When the mailer job was created (UTC time).
        updated_at (datetime): Last update time of the mailer job (UTC time).
        logs (list[MailerJobLog]): Logs related to this mailer job.
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
    Represents a log entry for a mailer job.

    This class captures detailed information about individual executions of
    mailer jobs, including execution time, status, performance metrics, and
    any associated error counts. It supports relationships with the parent
    `MailerJob` entity and provides utility properties for local timezone
    conversion and human-readable cron expressions.

    Attributes:
        id (int): Unique identifier for the log entry.
        job_id (int): Foreign key that references the associated mailer job.
        job (MailerJob): Relationship to the mailer job that owns this log.
        executed_at (datetime): Timestamp when the mailer job was executed
            (in UTC).
        logical_date (date): Business or logical date for the log entry's
            execution.
        status (str): Status of the execution, e.g., "ok", "failed", etc.
        details (str): Additional details or notes about the execution.
        duration_ms (int): Duration of the execution in milliseconds.
        mails_sent (int): Number of emails successfully sent during execution.
        errors_count (int): Number of errors encountered during execution.
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
    Represents the configuration settings for a mailer system.

    This class defines the necessary attributes required to configure and manage
    a mailer, such as SMTP settings, authentication methods, OAuth configurations,
    and administrative email management. It is designed to support flexible setup
    for both standard email login and OAuth-based authentication methods.

    Attributes:
        id (int): Unique identifier for the mailer configuration.

        smtp_host: The SMTP host used for email transmission.
        smtp_port (int): The SMTP port used; defaults to 587.
        smtp_user: The username for the SMTP server authentication.
        smtp_password: The password for the SMTP server authentication.
        use_tls (bool): Indicates whether TLS is used for the SMTP connection.
        from_address: The email address used as the sender in outgoing emails.

        auth_method (str): The authentication method; defaults to "email".
            Could be "email" for standard email login or "oauth" for OAuth-based
            authentication.

        login_email: The email address used for standard email login authentication.
        login_password (str): The password associated with the email address used
            for login.

        oauth_client_id: The OAuth client ID for authentication.
        oauth_client_secret: The OAuth client secret for authentication.
        oauth_provider_url (str): The URL of the OAuth provider.
        oauth_redirect_uri (str): The URI used for OAuth redirection.

        admin_emails (str): Comma-separated list of administrative email addresses.
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

    # Email-Login
    login_email = Column(EncryptedType, nullable=True)
    login_password = Column(String, nullable=True)

    # OAuth-Konfiguration
    oauth_client_id = Column(EncryptedType, nullable=True)
    oauth_client_secret = Column(EncryptedType, nullable=True)
    oauth_provider_url = Column(String(500), nullable=True)
    oauth_redirect_uri = Column(String(500), nullable=True)

    # Admin-E-Mails (Komma-getrennt)
    admin_emails = Column(Text, nullable=True)

class MailerJobLock(Base):
    """
    Represents a lock for mailer jobs to manage concurrent processing.

    The MailerJobLock model ensures that mailer jobs are executed in
    a controlled manner, preventing multiple processes from acting
    on the same job simultaneously. This class primarily tracks job
    identifiers and the time at which the lock was acquired.

    Attributes:
        job_id (int): The unique identifier for the mailer job lock.
        acquired_at (datetime): The UTC timestamp when the lock was acquired.
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
    """
    Represents a group entity in the database.

    A class that defines a group which can consist of multiple members and can
    be associated with various mailer jobs. It also provides attributes to
    identify and manage groups, such as marking a group as default.

    Attributes:
        id (int): Unique identifier for the group.
        name (str): The name of the group. Must be unique.
        members (List[Member]): The list of members associated with the group.
        mailer_jobs (List[MailerJob]): The list of mailer jobs associated with the group.
        is_default (bool): Indicates whether this group is the default group.
    """
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True, index=True)

    members = relationship("Member", back_populates="group", cascade="all, delete")
    mailer_jobs = relationship("MailerJob", back_populates="group", cascade="all, delete")

    is_default = Column(Boolean, default=False, nullable=False)


