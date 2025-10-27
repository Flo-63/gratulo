#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
WORKDIR="$(pwd)"

# -----------------------------------------------------------
# Konfiguration
# -----------------------------------------------------------
LANGUAGE="de"   # "de" oder "en"
MODE=${1:-dev}

# -----------------------------------------------------------
# Sprachstrings
# -----------------------------------------------------------
t() {
  case "$LANGUAGE" in
    de)
      case "$1" in
        usage) echo "Nutzung:" ;;
        dev_desc) echo "Starte Entwicklung (Hot Reload)" ;;
        test_desc) echo "Starte Testumgebung (Build ohne Mounts)" ;;
        public_desc) echo "Starte Public Release (fertiges Image)" ;;
        down_desc) echo "Stoppe Container (Daten bleiben erhalten)" ;;
        wipe_desc) echo "ALLES löschen inkl. Volumes (Datenbanken, Uploads)" ;;
        env_used) echo "Verwende Umgebungsdateien:" ;;
        env_missing) echo "Hinweis: Keine spezifische .env-Datei gefunden – verwende nur .env.base" ;;
        start_dev) echo "Starte GRATULO in Entwicklungsumgebung..." ;;
        start_test) echo "Starte GRATULO in Testumgebung..." ;;
        start_public) echo "Starte GRATULO im Public Release-Modus..." ;;
        stopping) echo "Stoppe Container (Volumes bleiben erhalten)..." ;;
        warn_title) echo "WARNUNG! Du bist dabei, ALLE Container, Netzwerke und Volumes zu löschen!" ;;
        warn_confirm) echo "Bist du sicher, dass du fortfahren willst? (yes/NO): " ;;
        deleting) echo "Lösche Container und Volumes..." ;;
        deleted) echo "Alles wurde gelöscht." ;;
        cancel) echo "Abgebrochen – keine Änderungen vorgenommen." ;;
        err_base) echo "Fehler: .env.base fehlt – Abbruch." ;;
        *) echo "$1" ;;
      esac ;;
    en)
      case "$1" in
        usage) echo "Usage:" ;;
        dev_desc) echo "Start development environment (Hot Reload)" ;;
        test_desc) echo "Start test environment (build without mounts)" ;;
        public_desc) echo "Start public release (final image)" ;;
        down_desc) echo "Stop containers (keep data)" ;;
        wipe_desc) echo "Delete EVERYTHING including all volumes (databases, uploads)" ;;
        env_used) echo "Using environment files:" ;;
        env_missing) echo "Note: No specific .env file found – using only .env.base" ;;
        start_dev) echo "Starting GRATULO in development mode..." ;;
        start_test) echo "Starting GRATULO in test mode..." ;;
        start_public) echo "Starting GRATULO in public release mode..." ;;
        stopping) echo "Stopping containers (volumes will be kept)..." ;;
        warn_title) echo "WARNING! You are about to delete ALL containers, networks and volumes!" ;;
        warn_confirm) echo "Are you sure you want to continue? (yes/NO): " ;;
        deleting) echo "Deleting containers and volumes..." ;;
        deleted) echo "All items have been removed." ;;
        cancel) echo "Cancelled – no changes made." ;;
        err_base) echo "Error: .env.base missing – aborting." ;;
        *) echo "$1" ;;
      esac ;;
  esac
}

# -----------------------------------------------------------
# Hilfe
# -----------------------------------------------------------
show_usage() {
  echo "$(t usage)"
  echo "  ./compose.sh dev       - $(t dev_desc)"
  echo "  ./compose.sh test      - $(t test_desc)"
  echo "  ./compose.sh public    - $(t public_desc)"
  echo "  ./compose.sh down      - $(t down_desc)"
  echo "  ./compose.sh wipe      - $(t wipe_desc)"
  exit 0
}

# -----------------------------------------------------------
# Environment-Dateien (Base = Pflicht, Mode = optional)
# → Merge zu einer temporären Datei für Compose
# -----------------------------------------------------------

BASE_ENV="${WORKDIR}/.env.base"
MODE_ENV="${WORKDIR}/.env.${MODE}"
TMP_ENV="${WORKDIR}/.env.merged"

if [[ ! -f "$BASE_ENV" ]]; then
  echo "❌ Fehler: $BASE_ENV fehlt – Abbruch."
  exit 1
fi

# Merge base + mode (mode überschreibt base)
cp "$BASE_ENV" "$TMP_ENV"
if [[ -f "$MODE_ENV" && -s "$MODE_ENV" ]]; then
  echo "✅ Verwende Umgebungsdateien: .env.base + .env.$MODE"
  awk -F= '!seen[$1]++' <(cat "$MODE_ENV" "$TMP_ENV") > "${TMP_ENV}.tmp" && mv "${TMP_ENV}.tmp" "$TMP_ENV"
else
  echo "ℹ️  Keine spezifische .env.$MODE gefunden – verwende nur .env.base"
fi

echo "→ Erzeugte Merge-Datei: $TMP_ENV"
cat > "${WORKDIR}/.envfile.override.yml" <<EOF
services:
  gratulo:
    env_file:
      - ${TMP_ENV}
EOF



# -----------------------------------------------------------
# Hauptlogik
# -----------------------------------------------------------
case "$MODE" in
  dev)
    echo "$(t start_dev)"
    docker compose \
      -f "${WORKDIR}/docker-compose.yml" \
      -f "${WORKDIR}/docker-compose.${MODE}.yml" \
      -f "${WORKDIR}/.envfile.override.yml" up --build
    ;;
  test)
    echo "$(t start_test)"
    docker compose -f docker-compose.yml -f docker-compose.test.yml "${ENV_FILES[@]}" up --build
    ;;
  public)
    echo "$(t start_public)"
    docker compose -f docker-compose.yml -f docker-compose.public.yml "${ENV_FILES[@]}" up -d
    ;;
  down)
    echo "$(t stopping)"
    docker compose down
    ;;
  wipe)
    echo ""
    echo "$(t warn_title)"
    echo ""
    read -p "$(t warn_confirm)" confirm
    if [[ "$confirm" == "yes" ]]; then
      echo "$(t deleting)"
      docker compose down -v
      echo "$(t deleted)"
    else
      echo "$(t cancel)"
    fi
    ;;
  *)
    show_usage
    ;;
esac
