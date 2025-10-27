# 🐳 GRATULO Docker Setup

Dieses Setup ermöglicht den Betrieb von **gratulo** in klar getrennten Docker-Umgebungen:
- **Entwicklung (`dev`)** → Live-Mount & automatisches Reloading  
- **Test (`test`)** → Frischer Build ohne Mounts   
- **Public Release (`public`)** → Nutzung des von mir veröffentlichten Images  

- **Down / Wipe** → Stoppen oder vollständiges Entfernen inkl. Volumes  

Die gesamte Steuerung erfolgt über **ein einziges Skript**:  
`compose.sh` (Linux/macOS) oder `compose.bat` (Windows).

---

## Verzeichnisstruktur

```
gratulo/
└── docker/
    ├── docker-compose.yml          # Basis-Setup (Redis, Volumes, Service)
    ├── docker-compose.dev.yml      # Entwicklungs-Overrides
    ├── docker-compose.test.yml     # Test-Overrides (Build ohne Mount)
    ├── docker-compose.public.yml   # Overrides zur Nutzung des Public Releases
    ├── .env.base                   # Gemeinsame Basis-Konfiguration
    ├── .env.dev                    # Entwicklungs-Konfiguration (optional)
    ├── .env.test                   # Test-Konfiguration (optional)
    ├── .env.public                 # Konfiguration zur Nutzung des Public Releases (optional)
    ├── compose.sh                  # Universal-Skript (Linux/macOS)
    ├── compose.bat                 # Universal-Skript (Windows)
    └── README.md
```

---

## Nutzung

### Linux / macOS

```bash
./docker/compose.sh dev      # Entwicklung (mit Hot Reload)
./docker/compose.sh test     # Test (Build ohne Mounts)
./docker/compose.sh public   # Start des öffentlichen Release-Images

./docker/compose.sh down     # Container stoppen (Daten bleiben erhalten)
./docker/compose.sh wipe     # Container + Volumes löschen (mit Warnung)

```

---

### Windows (CMD oder PowerShell)

```bat
docker\compose.bat dev
docker\compose.bat test
docker\compose.bat public
docker\compose.bat down
docker\compose.bat wipe
```

**Hinweis:** 

Alle Compose-Skripte liegen im Verzeichnis `/docker`.  
Sie können von überall aus aufgerufen werden (z. B. aus dem Projekt-Root wie hier dargestellt),  
da sie automatisch in ihr eigenes Verzeichnis wechseln.

---

## Environment-Dateien

### Basiskonzept

- Die Datei **`.env.base`** wird **immer** geladen.  
- Die Datei **`.env.<mode>`** (`.env.dev`, `.env.test`, `.env.public`) wird **optional** ergänzt.  
- Wenn sie **nicht existiert**, läuft das Setup trotzdem weiter — du erhältst nur eine Warnung.  

**Beispielausgabe, wenn `.env.test` fehlt:**
```
Keine spezifische .env für 'test' gefunden – verwende nur .env.base
```

---

### Beispiel `.env.base`

```bash
REDIS_HOST=redis
REDIS_PORT=6379
APP_NAME=gratulo
```

### Beispiel `.env.dev`

```bash
DEBUG=true
APP_SECRET_KEY=<dev-secret>
```

### Beispiel `.env.public`

```bash
DEBUG=false
APP_SECRET_KEY=<prod-secret>
```

---

## Umgebungserklärung

| Umgebung   | Mounts | Build | Reload | Beschreibung                      |
|------------|--------|--------|--------|-----------------------------------|
| **dev**    | ✅ Ja (`.:/app`) | ❌ Nein | 🔁 Auto | Live Reload mit lokalem Code      |
| **test**   | ❌ Nein | ✅ Ja | ❌ Nein | Produktionsähnlicher Build        |
| **public** | ❌ Nein | ❌ Nein | ❌ Nein | Nutzung des public release Images |


## Hinweis für Windows-Entwickler

Der automatische Reload in der Entwicklungsumgebung `(compose.sh dev)` funktioniert nur,
wenn das Projektverzeichnis auf dem WSL-Dateisystem liegt `(z. B. /home/<user>/projects/gratulo)`.

**Grund:**
Docker Desktop mountet Windows-Laufwerke (`C:\`, `D:\` usw.) über ein Netzwerk-Dateisystem,
das keine Dateiänderungs-Events an Linux weitergibt. Dadurch erkennt `uvicorn' bzw. 'watchfiles'
keine Änderungen am Code, wenn das Projekt auf NTFS liegt.

**Empfehlung:**
Falls die live reload Funktion gewünscht ist, Projekt nach WSL verschieben:

```bash
mkdir -p ~/projects
cp -r /mnt/d/Python/gratulo ~/projects/
```

Dann in `docker-compose.dev.yml' die Mounts anpassen:

```
volumes:
  - ~/projects/gratulo/app:/app/app
  - ~/projects/gratulo/frontend:/app/frontend
```


---

## Erklärung: Mount vs. Build

### Entwicklung
```yaml
volumes:
  - .:/app
command: uvicorn app.main:app --reload
```

- Der lokale Code wird **direkt in den Container eingeblendet** (Bind-Mount).  
- Änderungen an Python-Dateien, Templates oder Frontend können sofort erkannt werden, sofern du unter Linux oder WSL arbeitest (Siehe Hinweis oben)  
- `docker compose down -v` löscht **nicht** deinen Code, da Bind-Mounts auf dem Host liegen.

---

### Test
```yaml
build:
  context: ..
```

- Kein Mount → Container nutzt den **lokal gebauten Code** aus dem Image.  
- Verhalten identisch zur Produktion.  
- Ideal für Integrationstests oder CI/CD-Pipelines.  

---

### Public
```yaml
image: florianmoesch/gratulo:latest
```

- Container nutzt das **von mir veröffentlichte Image** aus Docker Hub.  
- Keine lokalen Dateien werden eingebunden.  
- Stabil, sicher und reproduzierbar.

---

## Stoppen & Bereinigen

### Container stoppen (ohne Datenverlust)
```bash
./compose.sh down
```

### ⚠️ Container + Volumes löschen (mit Warnung)
```bash
./compose.sh wipe
```

Du wirst gefragt:
```
Du bist dabei, ALLE Container, Netzwerke und Volumes zu löschen!
Bist du sicher, dass du fortfahren willst? (yes/NO):
```

Nur bei Eingabe von **yes** werden Volumes gelöscht.

---

## Beispiel-Workflows

### Entwicklung
```bash
./compose.sh dev
# → startet Container mit Hot Reload und Live-Mount
# Änderungen an Backend oder Frontend werden sofort übernommen
```

### Test
```bash
./compose.sh test
# → baut Container neu ohne lokale Mounts
# Ideal für Integrationstests oder CI/CD
```

### Produktion
```bash
./compose.sh public
# → startet Container mit stabilem Image
```

---

## 💡 Tipps & Best Practices

- Verwende `.env.base` für alle gemeinsam genutzten Variablen (z. B. Redis, Ports).  
- `.env.dev`, `.env.test`, `.env.public` sollten **nur Unterschiede** enthalten.  
- Führe `./compose.sh test` vor jedem Release aus – so erkennst du Build-Probleme früh.  
- `./compose.sh wipe` ist mit **Sicherheitsabfrage** geschützt – kein versehentliches Datenlöschen.  
- Die Skripte funktionieren **identisch auf Windows und Linux/macOS**.  

---

## Beispiel-Ausgaben

### Wenn `.env.dev` existiert:
```
Verwende Umgebungsdateien: .env.base + .env.dev
Starte GRATULO in DEV-Umgebung...
```

### Wenn `.env.dev` fehlt:
```
Keine spezifische .env für 'dev' gefunden – verwende nur .env.base
Starte GRATULO in DEV-Umgebung...
```

---
## Spracheinstellung der Skripte

Beide Scripte unterstützen zweisprachige Ausgaben:
Deutsch (`de`) und Englisch (`en`).

Die Sprache wird direkt im Skript über eine Konstante eingestellt:

### Beispiel für Linux/macOS
```bash
LANGUAGE="de" 
```

### Beispiel für Windows
```bat
set LANGUAGE=de
```
---
## Hinweis

Dieses Setup wurde entwickelt, um:
- Einheitliche Docker-Workflows für **Entwicklung, Test und Produktion** zu bieten  
- Sichere Handhabung von Volumes zu gewährleisten  
- `.env`-Vererbung zu unterstützen, ohne ungewollte Abbrüche  
- Ein konsistentes Verhalten zwischen **Linux/macOS und Windows** sicherzustellen  

**Letzter Stand:** Oktober 2025  
**Maintainer:** Florian M.  

---

> „Ein sauberes Docker-Setup ist kein Luxus – es ist die Grundlage für Stabilität.“ 
