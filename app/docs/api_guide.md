# Gratulo API Guide

Willkommen bei der **Gratulo API** – der API zur Verwaltung von Mitgliedern und Gruppen für Gratulo.

---

## Authentifizierung

### Token anfordern
```bash
curl -X POST {{BASE_URL}}/api/auth/token \
     -F "username=service_api" \
     -F "password=supersecret123"
````

Antwort:

```json
{
  "access_token": "<TOKEN>",
  "token_type": "bearer"
}
```

### Token verwenden

```bash
-H "Authorization: Bearer <TOKEN>"
```

> **Hinweis:**
> Ersetze `{{BASE_URL}}` durch deine richtige Server-URL, z. B. `https://gratulo.myorg.de` oder `http://localhost:8000`.

---

## Mitglieder-Endpunkte

| Methode | Endpoint                                           | Beschreibung                                                       |
|----------|----------------------------------------------------|--------------------------------------------------------------------|
| GET      | `/api/members`                                    | Alle Mitglieder abrufen                                            |
| GET      | `/api/members?only_deleted=true`                  | Nur gelöschte Mitglieder abrufen                                   |
| GET      | `/api/members?include_deleted=true`               | Alle Mitglieder, auch gelöschte                                    |
| GET      | `/api/members/search?query=<string>`              | Mitglieder anhand von Name oder E-Mail suchen                      |
| GET      | `/api/members/search?query=<string>&include_deleted=true` | Mitglieder suchen, inklusive gelöschter Einträge                   |
| POST     | `/api/members`                                    | Neues Mitglied anlegen                                             |
| PATCH    | `/api/members/{id}`                               | Mitglied aktualisieren                                             |
| DELETE   | `/api/members/{id}`                               | Mitglied anonymisieren (Soft Delete)                               |
| POST     | `/api/members/{id}/restore`                       | Gelöschtes Mitglied wiederherstellen                               |
| DELETE   | `/api/members/{id}/wipe?force=true`               | Mitglied endgültig löschen                                         |

---

### Beispiel: Mitglieder-Suche

**Request (nur aktive Mitglieder):**
```bash
curl -X GET "{{BASE_URL}}/api/members/search?query=meier" \
     -H "Authorization: Bearer <TOKEN>"
````

**Request (inkl. gelöschte Mitglieder):**

```bash
curl -X GET "{{BASE_URL}}/api/members/search?query=meier&include_deleted=true" \
     -H "Authorization: Bearer <TOKEN>"
```

**Response:**

```json
[
  {
    "id": 42,
    "firstname": "Hans",
    "lastname": "Meier",
    "email": "hans.meier@example.com",
    "group": {
      "id": 3,
      "name": "Tennis"
    },
    "birthdate": "1988-04-10",
    "member_since": "2015-09-01",
    "is_deleted": false
  },
  {
    "id": 91,
    "firstname": "Klara",
    "lastname": "Meier",
    "email": "klara.meier@example.com",
    "group": {
      "id": 4,
      "name": "Schwimmen"
    },
    "birthdate": "1991-06-15",
    "member_since": "2010-03-01",
    "is_deleted": true
  }
]
```

---

💡 **Hinweis:**
Wenn `include_deleted=true` gesetzt ist, werden auch gelöschte Mitglieder (`is_deleted=true`) in den Ergebnissen angezeigt.

**Statuscodes:**

* `200 OK` – Trefferliste zurückgegeben
* `404 Not Found` – Keine Mitglieder gefunden
* `400 Bad Request` – Ungültige Anfrageparameter

---

## 👥 Gruppen-Endpunkte

| Methode | Endpoint      | Beschreibung         |
| ------- | ------------- | -------------------- |
| GET     | `/api/groups` | Alle Gruppen abrufen |
| POST    | `/api/groups` | Neue Gruppe anlegen  |

---

## ️ Technische Hinweise

* **Format für Datumsfelder:** `YYYY-MM-DD`
* **Authentifizierung:** Bearer Token
* **HTTP-Codes:**

  * `200 OK` – Erfolg
  * `204 No Content` – Erfolgreich gelöscht
  * `400 Bad Request` – Eingabefehler
  * `401 Unauthorized` – Kein Token oder ungültig
  * `404 Not Found` – Objekt nicht gefunden

---

## Dokumentation abrufen

Lade dieses Handbuch direkt aus der API herunter:

```bash
curl -X GET {{BASE_URL}}/api/docs/guide -o API_GUIDE.md
```

Oder im Browser ansehen:
[{{BASE_URL}}/api/docs/guide]({{BASE_URL}}/api/docs/guide)

---

(c) 2025 Florian Mösch – Made with ❤️  in Python & FastAPI

```
