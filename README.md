# 🎉 gratulo

[![FastAPI](https://img.shields.io/badge/FastAPI-0.118.0-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://www.python.org/)
[![License: PolyForm Noncommercial 1.0.0](https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-purple)](https://polyformproject.org/licenses/noncommercial/1.0.0/)
[![Build](https://img.shields.io/badge/build-passing-brightgreen)](#)

---

## 🧩 Overview

**gratulo** is a modular FastAPI-based application for managing and sending personalized congratulatory emails —  
for example, birthdays, anniversaries, or other special occasions.  
It now includes flexible date configuration, allowing you to redefine what each tracked date represents — for example, a membership anniversary or recurring service event.

It supports multiple customizable templates for different event types and recipient groups.  
The app is particularly suited for **clubs, associations, and small organizations**.

Recipients and groups can be:
- managed manually,
- imported via CSV list,
- or synchronized through the REST API.

Template editor uses **TinyMCE** (GPL Community Edition). 

---


## Features

- **Automated congratulatory email generation** (birthdays, anniversaries, and more)
- **Detection of "round" birthdays and anniversaries**
- **Two fully configurable date fields** for different use cases:
  - Customizable field names (e.g. “Birthday”, “Club entry”, “Service Start”, “Maintenance Date”)
  - Adjustable meaning of each field as either `ANNIVERSARY` (e.g. birthdays, memberships) or `EVENT` (e.g. recurring service or maintenance dates)
  - Optional frequency setting (in months) for repeating events, e.g. every 6 or 12 months
- **Group & Member Management** – manually, via import, or through the API
- **Template-based email creation** via **TinyMCE** (Community Edition)
- **Job Scheduler** powered by **APScheduler**
- **Secure authentication** (JWT via `python-jose`)
- **Configurable for 2FA with TOTP** for Admins, using **Google Authenticator** or similar 
- **SQLite or PostgreSQL** support via SQLAlchemy
- **Asynchronous mail delivery** using `aiosmtplib` via Redis queuing
- **Mail throttle** with configurable rate limits
- **Queue Status Monitoring and Job Logs** viewable directly in the admin interface
- **Configurable mailer settings** through a dedicated UI section
- **REST API** (can be switched off) with interactive **Swagger** and **ReDoc** documentation built into the app
- **Redis protection** against brute-force login attempts
- **Encrypted storage** for all sensitive data (AES-based field-level encryption)
- **GDPR-compliant deletion** – supports *soft delete* and *secure wipe*
- **Jinja2-based templates** for consistent UI

---

## Quick Start

If you simply want to try out **gratulo** without writing any code or installing Python,  
check out the **[Quick Start Guide](./QUICKSTART.md)**.  
It explains how to start gratulo in a few minutes using Docker.

---

## For Developers

This document covers development setup, configuration, and internal architecture.  
If you plan to contribute, extend, or integrate gratulo, start here.

For detailed Docker environment setup (development, test, public),  
refer to [docker/README-DOCKER.md](./docker/README-DOCKER.md).

---

## Table of Contents

1. [Features](#-features)
2. [Tech Stack](#-tech-stack)
3. [Installation](#-installation)
4. [Environment Configuration](#-environment-configuration)
5. [Running the Application](#-running-the-application)
6. [API Overview](#-api-overview)
7. [License](#-license)
8. [Author](#-author)

---

## Tech Stack

| Component                    | Technology |
|------------------------------|-------------|
| **Backend**                  | FastAPI (Starlette) |
| **Database**                 | SQLite (default) / PostgreSQL (optional) |
| **ORM**                      | SQLAlchemy + Alembic |
| **Templates**                | Jinja2 |
| **Scheduling**               | APScheduler + cron-descriptor |
| **Auth**                     | Passlib + bcrypt + python-jose |
| **Email**                    | aiosmtplib + email-validator |
| **Cache / Queue / Limiting** | Redis + fastapi-limiter |
| **Frontend Editor**          | TinyMCE |

---

##  Installation

###  Clone the Repository
```bash
git clone https://github.com/<your-username>/gratulo.git
cd gratulo
````

### Create and Activate a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate      # On Linux/Mac
venv\Scripts\activate         # On Windows
```

###  Install Dependencies

```bash
pip install -r requirements.txt
```

### Create `.env` File

Example `.env`:

```env
# ---------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------
APP_SECRET=<FERNET KEY>          # Used for encryption of stored data
CLUB_FOUNDATION_DATE=            # Optional: used for anniversary calculation
INITIAL_ADMIN_USER=""            # Automatically created admin account
INITIAL_PASSWORD=""              # Initial password for first admin
SESSION_LIFETIME=480             # Session lifetime in minutes
HTTPS_ONLY=false                 # Enforce HTTPS cookies in production

# ---------------------------------------------------------------------
# Redis (Rate Limiting / Brute Force Protection)
# ---------------------------------------------------------------------

# Use this for local development (Redis running directly on host)
# REDIS_URL=redis://localhost:6379/0

# Use this for Docker / Docker Compose (Redis as service)
REDIS_URL=redis://redis:6379/0

# Rate Limiter for mail send
RATE_LIMIT_MAILS = 25       # max. Mails per window (Google accepts up to 50/minute)
RATE_LIMIT_WINDOW = 60      # Window (seconds) for rate limit

# Frequency for running mail processing queue
MAIL_QUEUE_INTERVAL_SECONDS = 120


# ---------------------------------------------------------------------
# REST / Service Authentication
# ---------------------------------------------------------------------
ENABLE_REST_API=True | False    # Allows to disable REST Endpoints if set to false. Default: True 

SERVICE_USER_NAME=service_api
SERVICE_USER_PASSWORD=supersecret123

# ---------------------------------------------------------------------
# JWT Configuration
# ---------------------------------------------------------------------
JWT_SECRET_KEY=topsecretjwtkey
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# ---------------------------------------------------------------------
# Base URL (used for template links and redirects)
# ---------------------------------------------------------------------
BASE_URL=http://localhost:8000

# ---------------------------------------------------------------------
# Custom Labels and Date Fields
# ---------------------------------------------------------------------
LABEL_DATE1="Birthday"               # Label for first date field
LABEL_DATE1_TYPE="ANNIVERSARY"       # Type: ANNIVERSARY or EVENT
LABEL_DATE1_FREQUENCY_MONTHS=12      # For EVENT: repeat interval in months

LABEL_DATE2="Entry"                  # Label for second date field
LABEL_DATE2_TYPE="ANNIVERSARY"
LABEL_DATE2_FREQUENCY_MONTHS=12

# Section / Entity labels for UI
LABEL_SECTION2="Membership"          # e.g. “Service Contract”, “Team Affiliation”
LABEL_ENTITY_SINGULAR="Member"       # e.g. “Customer”, “Colleague”
LABEL_ENTITY_PLURAL="Members"
LABEL_ENTITY_GENDER="n"              # “m”, “f”, or “n”

```

This configuration defines:

The application now supports fully customizable field labels and event types.  
This allows Gratulo to adapt to various domains beyond clubs — e.g. for company anniversaries, recurring service appointments, or customer relationship reminders.

- `ANNIVERSARY` fields automatically detect *round* occasions (e.g., 10, 20, 25, 50 years)
- `EVENT` fields use a recurring frequency (in months)
- All UI captions (entity names, section titles, and grammatical gender) are configurable
- Encryption key (APP_SECRET) for Fernet-based field encryption.
- Session and HTTPS settings for cookie management.
- Redis connection for rate limiting and brute-force protection.
- Throttling mail send
- JWT security tokens for API authentication.
- Admin bootstrap credentials for first-time setup.
- Base URL for link generation inside email templates and redirects.
- Disable REST API

When running via Docker Compose, the app automatically connects to the Redis service
using the internal hostname redis (REDIS_URL=redis://redis:6379/0).

**After using the bootstrap admim credentials to configure the Admin-User, delete these settings from the .env !**

---

## Running the Application

### Development Mode

```bash
uvicorn app.main:app --reload
```

Visit: [http://127.0.0.1:8000](http://127.0.0.1:8000)

### Production Example (Gunicorn + Uvicorn Workers)

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

---

## API Overview

| Endpoint              | Method                    | Description                                 |
| --------------------- | ------------------------- | ------------------------------------------- |
| `/api/auth/token`     | POST                      | Obtain JWT token for service authentication |
| `/api/members`        | GET / POST / PUT / DELETE | Manage members and their attributes         |
| `/api/groups`         | GET / POST / DELETE       | Manage groups and associations              |
| `/api/templates`      | GET / POST                | Manage email templates                      |
| `/api/scheduler/jobs` | GET / POST / DELETE       | Manage scheduled sending tasks              |

redoc UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## License

This project is licensed under the
**[PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/)**.
You are free to use, modify, and share the code **for noncommercial purposes only**.
In case, Commercial use requires a separate license.  
See [`COMMERCIAL_LICENSE_EN.md`](./COMMERCIAL_LICENSE_EN.md) for details.

---

## Author

**Florian Mösch**
*florian@moesch.ws*
[GitHub Profile](https://github.com/flo-63)

---

## Future Enhancements (Planned)

-  **Dashboard for Sending Statistics**  
  Visual overview of sent, pending, and failed messages with filtering options.

- **Notification Center & Scheduling Overview**  
  Centralized interface for upcoming events, scheduled tasks, and mail history.

---

 *gratulo – celebrating people, one email at a time.*
 © 2025 Florian. Licensed under PolyForm Noncommercial 1.0.0.

```