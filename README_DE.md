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
````

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

4. Umgebungsdatei `.env` anlegen (Beispiel):

   ```env
   APP_NAME=gratulo
   SECRET_KEY=geheimes_schluesselwort
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=60

   # Datenbank
   DATABASE_URL=sqlite:///./gratulo.db
   # oder (optional)
   # DATABASE_URL=postgresql+psycopg2://benutzer:passwort@localhost/gratulo

   # E-Mail
   SMTP_HOST=smtp.server.de
   SMTP_PORT=587
   SMTP_USERNAME=absender@mail.de
   SMTP_PASSWORD=passwort
   EMAIL_FROM=absender@mail.de

   # Redis (Rate Limiting / Brute-Force-Schutz)
   REDIS_URL=redis://localhost:6379/0
   ```

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

---

## API-Dokumentation

* Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## Zukünftige Erweiterungen

* Erweiterte Logik für besondere Geburtstage und Jubiläen (z. B. runde Geburtstage, langjährige Mitgliedschaften)
* Warteschlange für den E-Mail-Versand über Redis
* Dashboard mit Versandstatistiken und Fehleranalyse
* Zentrale Benachrichtigungsübersicht für anstehende Ereignisse
* Unterstützung mehrsprachiger Vorlagen
* Erweiterte Personalisierung (z. B. Platzhalter für Vorname, Alter, Mitgliedsjahre)

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

