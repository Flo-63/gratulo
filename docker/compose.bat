@echo off
setlocal enabledelayedexpansion
pushd "%~dp0"

REM -----------------------------------------------------------
REM Konfiguration
REM -----------------------------------------------------------
set LANGUAGE=de
set "MODE=%~1"
if "%MODE%"=="" set "MODE=dev"

set "BASE_ENV=.env.base"
set "MODE_ENV=.env.%MODE%"
set "TMP_ENV=.env.merged"
set "OVERRIDE_YML=.envfile.override.yml"

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
  set "err_base=Fehler: .env.base fehlt – Abbruch."
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
  set "err_base=Error: .env.base missing – aborting."
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
REM Environment-Dateien mergen
REM -----------------------------------------------------------
if not exist "%BASE_ENV%" (
  echo ? !err_base!
  goto END
)

copy /y "%BASE_ENV%" "%TMP_ENV%" >nul

if exist "%MODE_ENV%" (
  echo !env_used! .env.base + .env.%MODE%
  for /f "usebackq tokens=1,* delims==" %%A in ("%MODE_ENV%") do (
    call :UPDATE_ENV "%%A" "%%B" "%TMP_ENV%"
  )
) else (
  echo !env_missing!
)

echo ? Erzeugte Merge-Datei: %TMP_ENV%

(
  echo services:
  echo   gratulo:
  echo     env_file:
  echo       - %TMP_ENV%
) > "%OVERRIDE_YML%"

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
docker compose -f docker-compose.yml -f docker-compose.dev.yml -f "%OVERRIDE_YML%" up --build
goto END

:TEST
echo !start_test!
docker compose -f docker-compose.yml -f docker-compose.test.yml -f "%OVERRIDE_YML%" up --build
goto END

:PUBLIC
echo !start_public!
docker compose -f docker-compose.yml -f docker-compose.public.yml -f "%OVERRIDE_YML%" up -d
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

REM -----------------------------------------------------------
REM Funktion: Key in .env-Datei ersetzen oder hinzufügen
REM -----------------------------------------------------------
:UPDATE_ENV
set "key=%~1"
set "val=%~2"
set "file=%~3"
set "found="
(for /f "usebackq delims=" %%L in ("%file%") do (
  echo %%L | findstr /b "%key%=" >nul
  if not errorlevel 1 (
    echo %key%=%val%
    set "found=1"
  ) else (
    echo %%L
  )
)) > "%file%.tmp"
if not defined found echo %key%=%val%>>"%file%.tmp"
move /y "%file%.tmp" "%file%" >nul
set "found="
goto :eof

:END
popd
endlocal
pause
