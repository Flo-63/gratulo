# gratulo

## Überblick

gratulo ist eine modulare Anwendung auf Basis von FastAPI zur Erstellung und zum Versand personalisierter Gratulations-E-Mails –  
zum Beispiel zu Geburtstagen, Jubiläen oder anderen besonderen Anlässen. Durch die vollständige Anpassung der Datumsfelder und 
Ereignislogik ermöglicht Gratulo eine flexibler Einsatz für verschiedene Domänen – z. B. Vereine, Firmen, Servicepläne oder Kundenbeziehungen.

Es können verschiedene Vorlagen für unterschiedliche Ereignisse und Empfängergruppen verwendet werden.  
Die Anwendung ist insbesondere für Vereine, Organisationen und Gruppen geeignet, die regelmäßig Glückwünsche oder Informationsmails versenden möchten.

Empfänger und Gruppen können manuell gepflegt, per CSV-Datei importiert oder über eine API synchronisiert werden.  
Zur Bearbeitung von Vorlagen wird der Editor **TinyMCE** in der GPL Community Edition verwendet.

---

## Funktionen

- Automatischer Versand von Glückwunsch-E-Mails (Geburtstage, Jubiläen usw.) oder Erinnerungen zu Terminen etc.
- **Zwei vollständig konfigurierbare Datumsfelder** für unterschiedliche Anwendungsfälle:
  - Frei benennbare Feldnamen (z. B. "Geburtstag", "Vereinseintritt", „Wartungstermin“, „Servicebeginn“ etc.)
  - Einstellbare Bedeutung der Datumsfelder als `ANNIVERSARY` (z. B. Jubiläen) oder `EVENT` (z. B. regelmäßige Termine)
  - Frequenzsteuerung für wiederkehrende Events in Monaten (z. B. alle 6 Monate)
- Erkennung und Behandlung von "runden" Geburtstagen und Jubiläen
- Verwaltung von Adressaten und Gruppen über UI, Import oder API
- Vorlagenbasierte E-Mail-Erstellung über TinyMCE Community Edition
- Zeitgesteuerter Versand mit APScheduler
- Sichere Admin-Authentifizierung mit JWT (python-jose)
- 2FA mit TOTP wählbar, Nutzung von Google Authenticator oder ähnlichen 
- Unterstützung für SQLite und PostgreSQL
- Asynchroner E-Mail-Versand über aiosmtplib
- Mail Queue mit Rate-Limiter für E-Mail-Versand
- Konfigurierbare Mailer-Einstellungen in der Benutzeroberfläche
- REST Api zur Verwaltung von Adressaten und Gruppen (abschaltbar)
- API-Dokumentation direkt in der Anwendung (Swagger und ReDoc)
- Schutz vor Brute-Force-Anmeldeversuchen mit Redis
- Verschlüsselte Speicherung aller sensiblen Daten
- DSGVO-konforme Löschmechanismen (Soft-Delete und Wipe)
- Ansicht des Queue Status und der Job-Logs in der UI
- Installation in Docker Container (dockerfile und docker-compose.yml sind enthalten)

---

## Technische Basis

| Komponente               | Technologie                               |
|--------------------------|-------------------------------------------|
| Backend                  | FastAPI                                   |
| Datenbank                | SQLite (Standard) / PostgreSQL (optional) |
| ORM                      | SQLAlchemy + Alembic                      |
| Templates                | Jinja2                                    |
| Scheduler                | APScheduler + cron-descriptor             |
| Authentifizierung        | Passlib + bcrypt + python-jose            |
| E-Mail                   | aiosmtplib + email-validator              |
| E-Mail Queue und Limiter | Redis                                     |
| Schutzmechanismus Login  | Redis + fastapi-limiter                   |
| Template-Editor          | TinyMCE (Community Edition)               |

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

# Rate Limiter für Mailversand
RATE_LIMIT_MAILS = 25       # max. Mails pro Zeitfenster (Google akzeptiert bis zu 50/Minute)
RATE_LIMIT_WINDOW = 60      # Zeitfenster für Linit (sekunden) 

# ---------------------------------------------------------------------
# REST API, Service-Authentifizierung
# ---------------------------------------------------------------------
ENABLE_REST_API=True | False    # Einschalten / Aussschalten des REST Endpoints. Default: True 

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

# ---------------------------------------------------------------------
# Benutzerdefinierte Labels und Datumsfelder
# ---------------------------------------------------------------------
LABEL_DATE1="Geburtstag"             # Bezeichnung des ersten Datumsfelds
LABEL_DATE1_TYPE="ANNIVERSARY"       # Typ: ANNIVERSARY oder EVENT
LABEL_DATE1_FREQUENCY_MONTHS=12      # Nur bei EVENT relevant: Wiederholung alle X Monate

LABEL_DATE2="Eintritt"               # Bezeichnung des zweiten Datumsfelds
LABEL_DATE2_TYPE="ANNIVERSARY"
LABEL_DATE2_FREQUENCY_MONTHS=12

# Bereichs-/Entitätsbezeichnungen für UI
LABEL_SECTION2="Mitgliedschaft"      # z. B. "Servicevertrag", "Teamzugehörigkeit"
LABEL_ENTITY_SINGULAR="Mitglied"     # Singular: z. B. "Kunde", "Kollege"
LABEL_ENTITY_PLURAL="Mitglieder"     # Pluralform
LABEL_ENTITY_GENDER="n"              # "m", "f" oder "n"

```

Diese Konfiguration enthält:
- Alle Kernparameter für Laufzeit, Authentifizierung und API
- Neue Konfigurationsoptionen für die Feldbezeichnungen und Feldtypen
   → erlaubt flexible Anpassung der Anwendung für andere Domänen (z. B. Firmen, Vereine, Servicepläne)
- Steuerung der Ereignislogik:
  - ANNIVERSARY: erkennt automatisch runde Jubiläen
  - EVENT: nutzt eine einstellbare Wiederholungsfrequenz in Monaten
- Anpassung aller Beschriftungen in der UI (Einzahl, Mehrzahl, Gender)Verschlüsselungs-Token (APP_SECRET) für gespeicherte Daten
- Sitzungsparameter und HTTPS-Optionen
- Redis-Verbindung für Rate Limiting und Anmelde-Schutz
- Steuerung der "Dosierung" des Mail Versand
- JWT-Einstellungen für API-Authentifizierung
- Admin-Standardkonto für den Erststart 

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


### Bauen mit Docker Compose
```bash
docker compose build --no-cache
oder
docker compose up -d --force-recreate
```
So wird der Container komplett neu gebaut, mit no-cache wird der build-cache ebenfalls neu erstellt.  

### Laufenlassen unter Docker Compose
```bash
docker compose up -d
```
Die mitgelieferte Datei docker-compose.yml startet automatisch:
- den gratulo-Container (FastAPI-Anwendung),
- eine Redis-Instanz (Rate Limiting, Brute-Force-Schutz),
- optional eine PostgreSQL-Datenbank.

### Docker Logs anzeigen:
```bash
docker compose logs -f
```
### Container beenden:

```bash
    docker compose down
 ```
---

## API-Dokumentation

* Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/swagger)
* ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/doc)

---

## Zukünftige Erweiterungen

* Dashboard mit Versandstatistiken und Fehleranalyse
* Zentrale Benachrichtigungsübersicht für anstehende Ereignisse
* Unterstützung mehrsprachiger Vorlagen
* Newsletter Funktionen

---

## Lizenz

Dieses Projekt steht unter der
**[PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/)**.
Die Nutzung, Veränderung und Weitergabe des Codes ist **nur für nichtkommerzielle Zwecke** gestattet.
Für eine Verwendung im kommerziellen oder organisatorischen Umfeld (z. B. innerhalb eines Unternehmens, im Rahmen von Dienstleistungen oder zur Unterstützung geschäftlicher Prozesse) ist eine gesonderte kommerzielle Lizenz erforderlich.

Weitere Informationen finden Sie in der Datei
[COMMERCIAL_LICENSE_DE.md](./COMMERCIAL_LICENSE_DE.md)
---

## Autor

*[Florian Mösch](florian@moesch.ws)*
[GitHub Profile](https://github.com/flo-63)

© 2025 Florian Mösch. Alle Rechte vorbehalten.

```

