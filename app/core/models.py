from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.core.database import Base
from app.core.constants import LOCAL_TZ
from app.core.encryption import EncryptedType

from sqlalchemy.types import TypeDecorator, Integer

class SQLiteBoolean(TypeDecorator):
    """
    Universeller, SQLite-kompatibler Boolean-Typ.
    Erzwingt numerische Speicherung & Filterung (False -> 0, True -> 1).
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
    Represents a template with a unique name and HTML content.

    This class is used to store templates, which consist of a unique name and
    corresponding HTML content that may be rendered later. The `id` attribute
    provides a unique identifier for each template in the database.

    :ivar id: An auto-generated unique identifier for the template.
    :type id: Integer
    :ivar name: The unique name of the template, used to distinguish it from others.
    :type name: String
    :ivar content_html: The HTML content of the template.
    :type content_html: Text
    """
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    content_html = Column(Text, nullable=False)

class Member(Base):
    """
    Represents a member within the system.

    This class is used to define attributes related to a member and maps these
    attributes to a database table. It includes personal details such as name,
    email, birthdate, and membership-related information. The table is named
    'members' in the database.

    :ivar id: Unique identifier for the member.
    :ivar firstname: The first name of the member. This data is encrypted.
    :ivar lastname: The last name of the member. This data is encrypted.
    :ivar email: The email address of the member. This data is encrypted and must
        be unique.
    :ivar birthdate: The date of birth of the member.
    :ivar gender: The gender of the member represented as a single character.
        (e.g., "m" for male, "w" for female, "d" for diverse).
    :ivar member_since: The date the member joined, optional field.
    :ivar group_name: The membership group name of the member. Defaults to
        'standard'.
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
    deleted_at = Column(DateTime, nullable=True)

    @property
    def is_active(self):
        return not self.is_deleted

class ImportMeta(Base):
    """
    Represents metadata for imports in the system.

    This class is used to track important information regarding imports, such as
    the last time an import was performed. It interacts with a database table
    via SQLAlchemy ORM and provides utility to work with the `last_imported`
    attribute using local time zone.

    :ivar id: The unique identifier for the import metadata record.
    :type id: int
    :ivar last_imported: The timestamp of the last import in UTC timezone.
    :type last_imported: datetime
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
    Represents a scheduled mailer job entity in the database.

    This class is used to manage and store information about mailer jobs,
    including the associated email template, scheduling details, and job
    execution logs.

    :ivar id: Unique identifier for the mailer job.
    :type id: int
    :ivar name: Name of the mailer job.
    :type name: str
    :ivar template_id: Foreign key linking this job to a specific template.
    :type template_id: int
    :ivar template: Association to the template entity related to this job.
    :type template: Template
    :ivar subject: The email subject that will be used for this job.
    :type subject: str
    :ivar selection: The selection criteria for recipients, such as "birthday"
        or "entry".
    :type selection: str
    :ivar group_id: Foreign key linking this job to a specific group (optional).
    :type group_id: int or None
    :ivar group: Association to the group entity related to this job.
    :type group: Group or None
    :ivar cron: Cron expression defining the schedule for recurring jobs (optional).
    :type cron: str or None
    :ivar once_at: Timestamp for one-time execution of the job (optional).
    :type once_at: datetime.datetime or None
    :ivar created_at: The UTC timestamp for when the job was created.
    :type created_at: datetime.datetime
    :ivar updated_at: The UTC timestamp indicating the last update to the job.
    :type updated_at: datetime.datetime
    :ivar logs: Collection of logs related to the execution of this job.
    :type logs: list[MailerJobLog]
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
    Represents a log entry for a mailer job execution.

    The MailerJobLog class stores details about individual executions of a mailer job,
    providing data such as the time of execution, duration, status, and metrics
    related to the execution (e.g., number of mails sent or errors encountered).

    :ivar id: The unique identifier for the log entry.
    :type id: int
    :ivar job_id: The identifier of the related mailer job.
    :type job_id: int
    :ivar job: The associated MailerJob instance.
    :type job: MailerJob
    :ivar executed_at: The datetime when the mailer job execution started, stored
        in UTC timezone.
    :type executed_at: datetime
    :ivar logical_date: Represents a logical date tied to the mailer job execution.
    :type logical_date: date
    :ivar status: The status of the mailer job execution (e.g., "ok", "failed").
    :type status: str
    :ivar details: Additional details or logs about the mailer job execution.
    :type details: str
    :ivar duration_ms: Execution duration of the mailer job, in milliseconds.
    :type duration_ms: int
    :ivar mails_sent: Number of mails successfully sent during execution.
    :type mails_sent: int
    :ivar errors_count: Number of errors encountered during execution.
    :type errors_count: int
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

    This class defines various attributes for SMTP configuration, email-based authentication,
    OAuth configuration, and administrative email settings. It is designed for use in applications
    that require email functionality and supports both basic email authentication and OAuth.

    :ivar id: Unique identifier for the mailer configuration.
    :type id: int
    :ivar smtp_host: The SMTP host address used for email communication.
    :type smtp_host: EncryptedType
    :ivar smtp_port: The port number used for connecting to the SMTP server.
    :type smtp_port: int
    :ivar smtp_user: The username used for authenticating with the SMTP server.
    :type smtp_user: EncryptedType
    :ivar smtp_password: The password used for authenticating with the SMTP server.
    :type smtp_password: EncryptedType
    :ivar use_tls: Indicates whether TLS should be used for SMTP communication.
    :type use_tls: bool
    :ivar from_address: The default "from" email address for outgoing emails.
    :type from_address: EncryptedType
    :ivar auth_method: Authentication method for email; "email" or "oauth".
    :type auth_method: str
    :ivar login_email: The email address for login-based authentication, if applicable.
    :type login_email: EncryptedType
    :ivar login_password: The password for login-based authentication, if applicable.
    :type login_password: EncryptedType
    :ivar oauth_client_id: The client ID used for OAuth authentication.
    :type oauth_client_id: EncryptedType
    :ivar oauth_client_secret: The client secret used for OAuth authentication.
    :type oauth_client_secret: EncryptedType
    :ivar oauth_provider_url: The URL of the OAuth provider.
    :type oauth_provider_url: str
    :ivar oauth_redirect_uri: The redirect URI configured for OAuth authentication.
    :type oauth_redirect_uri: str
    :ivar admin_emails: Comma-separated list of administrative email addresses.
    :type admin_emails: str
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
    Represents a database lock for a mailer job.

    This class defines a table structure for managing locks on mailer jobs in a
    relational database. It includes the primary key `job_id`, which uniquely
    identifies the job, and `acquired_at` that indicates the timestamp when the
    lock was acquired. It is useful for ensuring that certain mailer jobs are
    not executed concurrently.

    :ivar job_id: The unique identifier of the mailer job.
    :type job_id: int
    :ivar acquired_at: The UTC timestamp indicating when the job lock was acquired.
    :type acquired_at: datetime.datetime
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
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True, index=True)

    members = relationship("Member", back_populates="group", cascade="all, delete")
    mailer_jobs = relationship("MailerJob", back_populates="group", cascade="all, delete")

    is_default = Column(Boolean, default=False, nullable=False)


