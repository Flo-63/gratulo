# gratulo

## Überblick

gratulo ist eine modulare Anwendung auf Basis von FastAPI zur Erstellung und zum Versand personalisierter Gratulations-E-Mails –  
zum Beispiel zu Geburtstagen, Jubiläen oder anderen besonderen Anlässen.

Es können verschiedene Vorlagen für unterschiedliche Ereignisse und Empfängergruppen verwendet werden.  
Die Anwendung ist insbesondere für Vereine, Organisationen und Gruppen geeignet, die regelmäßig Glückwünsche oder Informationsmails versenden möchten.

Empfänger und Gruppen können manuell gepflegt, per CSV-Datei importiert oder über eine API synchronisiert werden.  
Zur Bearbeitung von Vorlagen wird der Editor **TinyMCE** in der kostenfreien Version verwendet (Registrierung erforderlich).

---

## Funktionen

- Automatischer Versand von Glückwunsch-E-Mails (Geburtstage, Jubiläen usw.)
- Verwaltung von Mitgliedern und Gruppen über UI, Import oder API
- Vorlagenbasierte E-Mail-Erstellung über TinyMCE
- Zeitgesteuerter Versand mit APScheduler
- Sichere Authentifizierung mit JWT (python-jose)
- Unterstützung für SQLite und PostgreSQL
- Asynchroner E-Mail-Versand über aiosmtplib
- Konfigurierbare Mailer-Einstellungen in der Benutzeroberfläche
- API-Dokumentation direkt in der Anwendung (Swagger und ReDoc)
- Schutz vor Brute-Force-Anmeldeversuchen mit Redis
- Verschlüsselte Speicherung aller sensiblen Daten
- DSGVO-konforme Löschmechanismen (Soft-Delete und Wipe)
- Ansicht von Job-Logs in der UI
- Installation in Docker Container (dockerfile und docker-compose sind dabei)

---

## Technische Basis

| Komponente | Technologie |
|-------------|-------------|
| Backend | FastAPI |
| Datenbank | SQLite (Standard) / PostgreSQL (optional) |
| ORM | SQLAlchemy + Alembic |
| Templates | Jinja2 |
| Scheduler | APScheduler + cron-descriptor |
| Authentifizierung | Passlib + bcrypt + python-jose |
| E-Mail | aiosmtplib + email-validator |
| Schutzmechanismen | Redis + fastapi-limiter |
| Template-Editor | TinyMCE |

---

## Installation

1. Repository klonen:

    ```bash
       git clone https://github.com/<ihr-benutzername>/gratulo.git
       cd gratulo
    ```

2. Virtuelle Umgebung erstellen und aktivieren:

   ```bash
   python -m venv venv
   source venv/bin/activate      # Linux / Mac
   venv\Scripts\activate         # Windows
   ```

3. Abhängigkeiten installieren:

   ```bash
   pip install -r requirements.txt
   ```

4. ### .env-Datei anlegen

Beispielkonfiguration für `.env`:

```env
# ---------------------------------------------------------------------
# Anwendung
# ---------------------------------------------------------------------
APP_SECRET=<FERNET KEY>          # Schlüssel zur Verschlüsselung gespeicherter Daten
CLUB_FOUNDATION_DATE=            # Optional: Gründungsdatum des Vereins
INITIAL_ADMIN_USER=""            # Erstes Admin-Benutzerkonto
INITIAL_PASSWORD=""              # Startpasswort für den Admin
SESSION_LIFETIME=480             # Lebensdauer einer Sitzung (in Minuten)
HTTPS_ONLY=false                 # HTTPS erzwingen (Produktionsmodus)

# ---------------------------------------------------------------------
# Redis (Rate Limiting / Brute-Force-Schutz)
# ---------------------------------------------------------------------

# Für lokale Entwicklung (Redis läuft direkt auf dem Hostsystem)
# REDIS_URL=redis://localhost:6379/0

# Für Docker / Docker Compose (Redis als Service im Container-Netzwerk)
REDIS_URL=redis://redis:6379/0

# ---------------------------------------------------------------------
# Service-Authentifizierung
# ---------------------------------------------------------------------
SERVICE_USER_NAME=service_api
SERVICE_USER_PASSWORD=supersecret123

# ---------------------------------------------------------------------
# JWT-Konfiguration
# ---------------------------------------------------------------------
JWT_SECRET_KEY=topsecretjwtkey
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# ---------------------------------------------------------------------
# Basis-URL (z. B. für Links in Vorlagen und Weiterleitungen)
# ---------------------------------------------------------------------
BASE_URL=http://localhost:8000
```

Diese Konfiguration enthält:
- Verschlüsselungs-Token (APP_SECRET) für gespeicherte Daten
- Sitzungsparameter und HTTPS-Optionen
- Redis-Verbindung für Rate Limiting und Anmelde-Schutz
- JWT-Einstellungen für API-Authentifizierung
- Admin-Standardkonto für den Erststart 
- Basis-URL, z.B. zur Erzeugung von Links in E-Mail-Vorlagen

Die Konfiguration des SMTP Servers sowie des Admin Accounts erfolgt in der Ui.

**Nach dem Anlegen des Admin-Users sind die entsprechenden Einträge in der .env zu löschen!**

Bei Nutzung von Docker Compose wird automatisch der interne Redis-Service
unter redis angesprochen (REDIS_URL=redis://redis:6379/0).

---

## Anwendung starten

### Entwicklungsmodus:

```bash
uvicorn app.main:app --reload
```

Zugriff unter: [http://127.0.0.1:8000](http://127.0.0.1:8000)

### Produktion (Beispiel):

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## Installation und Betrieb mit Docker

### Manuelles Erstellen und Starten

```bash
docker build -t gratulo .
docker run -d -p 8000:8000 --env-file .env gratulo
```
Damit wird die Anwendung in einem Container gestartet, der Port 8000 nach außen bereitstellt.
Die Konfiguration erfolgt über die Datei .env im Projektverzeichnis.

### Start mit Docker Compose
```bash
docker-compose up -d
```
Die mitgelieferte Datei docker-compose.yml startet automatisch:
- den gratulo-Container (FastAPI-Anwendung),
- eine Redis-Instanz (Rate Limiting, Brute-Force-Schutz),
- optional eine PostgreSQL-Datenbank.

### Docker Logs anzeigen:
```bash
docker-compose logs -f
```
### Container beenden:

```bash
    docker-compose down
 ```

---

## API-Dokumentation

* Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/swagger)
* ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/doc)

---

## Zukünftige Erweiterungen

* Erweiterte Logik für besondere Geburtstage und Jubiläen (z. B. runde Geburtstage, langjährige Mitgliedschaften)
* Warteschlange für den E-Mail-Versand über Redis
* Dashboard mit Versandstatistiken und Fehleranalyse
* Zentrale Benachrichtigungsübersicht für anstehende Ereignisse
* Unterstützung mehrsprachiger Vorlagen


---

## Lizenz

Dieses Projekt steht unter der
**[PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/)**.
Die Nutzung und Weitergabe ist ausschließlich zu **nicht-kommerziellen Zwecken** gestattet.

---

## Autor

**Florian Mösch**

© 2025 Florian Mösch. Alle Rechte vorbehalten.

```

