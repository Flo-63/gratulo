<p align="center">
  <picture>
    <source srcset="frontend/static/images/Logo-tailwindblue.svg" type="image/svg+xml">
    <img src="frontend/static/images/Logo-tailwindblue.png" alt="Gratulo Logo" width="100">
  </picture>
</p>


# 🚀 Schnellstart-Anleitung für **gratulo**

Willkommen bei **gratulo** — diese Anleitung zeigt Ihnen, wie Sie die Anwendung **ohne Installation von Python oder Abhängigkeiten** ausprobieren können.  
Mit Docker ist **gratulo** in nur wenigen Minuten einsatzbereit.

---

# 🐋 Voraussetzungen: Docker installieren

Damit **gratulo** ausgeführt werden kann, benötigen Sie eine laufende Docker-Umgebung.

---

## 🪟 Windows
1. Laden Sie **[Docker Desktop für Windows](https://www.docker.com/products/docker-desktop/)** herunter und installieren Sie es.  
2. Starten Sie Docker Desktop nach der Installation.  
3. Prüfen Sie in einer PowerShell oder CMD-Konsole:
   ```bash
   docker --version
   ```
   Wenn eine Versionsnummer angezeigt wird, ist Docker korrekt installiert.

> 💡 **Hinweis:**  
> Unter Windows 10/11 Home muss eventuell die **WSL2-Unterstützung** aktiviert werden.  
> Docker Desktop bietet dies bei der Installation automatisch an.

---

## 🍎 macOS
1. Laden Sie **[Docker Desktop für Mac](https://www.docker.com/products/docker-desktop/)** herunter.  
2. Installieren und starten Sie die Anwendung.  
3. Prüfen Sie mit:
   ```bash
   docker --version
   ```

---

## 🐧 Linux
1. Installieren Sie Docker über Ihren Paketmanager.  
   Beispiele:
   ```bash
   # Ubuntu / Debian
   sudo apt install docker.io

   # Fedora
   sudo dnf install docker
   ```
2. Starten Sie den Docker-Dienst:
   ```bash
   sudo systemctl start docker
   ```
3. Optional: Fügen Sie Ihren Benutzer zur Docker-Gruppe hinzu:
   ```bash
   sudo usermod -aG docker $USER
   ```
   (Danach einmal ab- und wieder anmelden.)

4. Testen Sie die Installation:
   ```bash
   docker run hello-world   
   ```
   
## 🧩 1. Umgebung vorbereiten

Nun richten Sie die Umgebungsdatei ein.

1. Kopieren Sie die Basis-Konfigurationsdatei:
   ```bash
   cp docker/.env.example_de docker/.env.base
   ```

   Sie können die bereitgestellten Standardeinstellungen verwenden, um **gratulo** lokal sofort zu testen —  
   **verwenden Sie diese jedoch nicht in einer Produktionsumgebung**, da sie Beispielschlüssel und Zugangsdaten enthalten.

---

## 2. **gratulo** starten

Starten Sie die Docker-Umgebung abhängig von Ihrem Betriebssystem.

### Linux / macOS
```bash
./docker/compose.sh public
```

### Windows
```bat
docker\compose.bat public
```

Sobald die Container gestartet sind, öffnen Sie Ihren Browser und rufen Sie auf:  
👉 **[http://localhost:8000](http://localhost:8000)**

> **Standard-Zugangsdaten:**  
> **Benutzer:** `admin@example.com`  
> **Passwort:** `ChangeMe123!`

---

## ⚙️ 3. Ersteinrichtung

1. Öffnen Sie die **Konfigurationsseite** in der Anwendung. (Sie finden ein Zahnrad ⚙️ oder einen entsprechenden Link in der Navigationsleiste.)  
   In diesem Bereich können Sie Ihren Mailserver verbinden und Systemeinstellungen anpassen.

2. Tragen Sie Ihre **SMTP-Serverdaten** ein und legen Sie Ihr **Administrator-Konto** an.

3. Öffnen Sie anschließend erneut die Datei `.env.public` und **entfernen Sie** die folgenden Zeilen:
   ```bash
   INITIAL_ADMIN_USER=
   INITIAL_PASSWORD=
   ```

   Dadurch wird sichergestellt, dass **gratulo** Ihr konfiguriertes Administratorkonto für die Anmeldung verwendet.

4. Melden Sie sich ab, indem Sie auf das Logout-Symbol in der oberen rechten Ecke klicken, und starten Sie anschließend den Server neu, um die Änderungen zu übernehmen:

#### Neustart (Linux / macOS)
```bash
./docker/compose.sh down
./docker/compose.sh public
```

#### Neustart (Windows)
```bat
docker\compose.bat down
docker\compose.bat public
```

Nun können Sie sich mit Ihren neu angelegten **Administrator-Zugangsdaten** anmelden.

---

## 🧭 4. Nächste Schritte

- Erkunden Sie die **Weboberfläche** und die integrierten Funktionen.  
- Passen Sie zusätzliche Einstellungen in `docker/.env.public` nach Bedarf an.  
- Wenn Sie Änderungen an der Umgebung vornehmen, starten Sie den Server wie oben beschrieben neu.

---

## 🧹 5. Umgebung stoppen oder zurücksetzen

Um die laufenden Container zu stoppen oder vollständig zu löschen:

### Linux / macOS
```bash
./docker/compose.sh down       # Stoppen (Daten bleiben erhalten)
./docker/compose.sh wipe       # Stoppen und Daten löschen
```

### Windows
```bat
docker\compose.bat down
docker\compose.bat wipe
```

---

## 📘 Weitere Informationen

Eine ausführliche Übersicht über die Docker-Umgebungen  
(`dev`, `test` und `public`) finden Sie unter  
👉 [README-DOCKER.md](./docker/README-DOCKER.md).

Für weiterführende Konfigurationen, Entwicklungsumgebungen oder CI/CD-Setups  
lesen Sie die **[Entwicklerdokumentation](./README_DE.md)**.

---

## ✅ Zusammenfassung

| Schritt | Aufgabe | Befehl |
|:-------:|:----------------------------|:-----------------------------------------------------------|
| 1 | Basis-Konfiguration kopieren | `cp docker/.env.example docker/.env.public` |
| 2 | **gratulo** starten | `./docker/compose.sh public` |
| 3 | SMTP + Admin konfigurieren | im Browser |
| 4 | Umgebung neu starten | `./docker/compose.sh down && ./docker/compose.sh public` |
| 5 | Stoppen oder Zurücksetzen | `./docker/compose.sh down` oder `wipe` |

---

> „Ein sauberes Setup ist die Grundlage für Stabilität.“
