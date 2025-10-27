@echo off
setlocal enabledelayedexpansion
pushd "%~dp0"

REM -----------------------------------------------------------
REM Konfiguration
REM -----------------------------------------------------------
set LANGUAGE=de
REM set LANGUAGE=en

set "MODE=%~1"
if "%MODE%"=="" set "MODE=dev"

REM -----------------------------------------------------------
REM Sprachtexte
REM -----------------------------------------------------------
if /I "%LANGUAGE%"=="de" (
  set "usage=Nutzung:"
  set "dev_desc=Starte Entwicklung (Hot Reload)"
  set "test_desc=Starte Testumgebung (Build ohne Mounts)"
  set "public_desc=Starte Public Release (fertiges Image)"
  set "down_desc=Stoppe Container (behalte Daten)"
  set "wipe_desc=ALLES loeschen inkl. Volumes (Datenbanken, Uploads)"
  set "env_used=Verwende Umgebungsdateien:"
  set "env_missing=Hinweis: Keine spezifische .env-Datei gefunden – verwende nur .env.base"
  set "start_dev=Starte GRATULO in Entwicklungsumgebung..."
  set "start_test=Starte GRATULO in Testumgebung..."
  set "start_public=Starte GRATULO im Public Release-Modus..."
  set "stopping=Stoppe Container (Volumes bleiben erhalten)..."
  set "warn_title=WARNUNG! Du bist dabei, ALLE Container, Netzwerke und Volumes zu loeschen!"
  set "warn_confirm=Bist du sicher, dass du fortfahren willst? (yes/NO):"
  set "deleting=Lösche Container und Volumes..."
  set "deleted=Alles wurde gelöscht."
  set "cancel=Abgebrochen – keine Änderungen vorgenommen."
) else (
  set "usage=Usage:"
  set "dev_desc=Start development environment (Hot Reload)"
  set "test_desc=Start test environment (build without mounts)"
  set "public_desc=Start public release (final image)"
  set "down_desc=Stop containers (keep data)"
  set "wipe_desc=Delete EVERYTHING including all volumes (databases, uploads)"
  set "env_used=Using environment files:"
  set "env_missing=Note: No specific .env file found – using only .env.base"
  set "start_dev=Starting GRATULO in development mode..."
  set "start_test=Starting GRATULO in test mode..."
  set "start_public=Starting GRATULO in public release mode..."
  set "stopping=Stopping containers (volumes will be kept)..."
  set "warn_title=WARNING! You are about to delete ALL containers, networks and volumes!"
  set "warn_confirm=Are you sure you want to continue? (yes/NO):"
  set "deleting=Deleting containers and volumes..."
  set "deleted=All items have been removed."
  set "cancel=Cancelled – no changes made."
)

REM -----------------------------------------------------------
REM Usage
REM -----------------------------------------------------------
if /I "%MODE%"=="help" (
  echo !usage!
  echo   compose dev      - !dev_desc!
  echo   compose test     - !test_desc!
  echo   compose public   - !public_desc!
  echo   compose down     - !down_desc!
  echo   compose wipe     - !wipe_desc!
  goto END
)

REM -----------------------------------------------------------
REM Environment files
REM -----------------------------------------------------------
set "ENV_FILES=--env-file .env.base"
if exist ".env.%MODE%" (
    echo !env_used! .env.base + .env.%MODE%
    set "ENV_FILES=!ENV_FILES! --env-file .env.%MODE%"
) else (
    echo !env_missing!
)

REM -----------------------------------------------------------
REM Main logic
REM -----------------------------------------------------------
if /I "%MODE%"=="dev" goto DEV
if /I "%MODE%"=="test" goto TEST
if /I "%MODE%"=="public" goto PUBLIC
if /I "%MODE%"=="down" goto DOWN
if /I "%MODE%"=="wipe" goto WIPE

REM Unbekannter Modus -> Hilfe anzeigen
echo !usage!
echo   compose dev      - !dev_desc!
echo   compose test     - !test_desc!
echo   compose public   - !public_desc!
echo   compose down     - !down_desc!
echo   compose wipe     - !wipe_desc!
goto END

:DEV
echo !start_dev!
docker compose -f docker-compose.yml -f docker-compose.dev.yml %ENV_FILES% up --build
goto END

:TEST
echo !start_test!
docker compose -f docker-compose.yml -f docker-compose.test.yml %ENV_FILES% up --build
goto END

:PUBLIC
echo !start_public!
docker compose -f docker-compose.yml -f docker-compose.public.yml %ENV_FILES% up -d
goto END

:DOWN
echo !stopping!
docker compose down
goto END

:WIPE
echo.
echo !warn_title!
echo.
set /p "CONFIRM=!warn_confirm! "
if /I "!CONFIRM!"=="yes" (
    echo !deleting!
    docker compose down -v
    echo !deleted!
) else (
    echo !cancel!
)
goto END

:END
popd
endlocal
pause