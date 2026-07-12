@echo off
setlocal
cd /d "%~dp0"
title sunshine live Track-Logger

rem ---- Python finden (portable > py-Launcher > python im PATH) ----------
set "PY="
if exist "python-embed\python.exe" set "PY=python-embed\python.exe"
if not defined PY (
  py -3 --version >nul 2>&1
  if not errorlevel 1 set "PY=py -3"
)
if not defined PY (
  python --version >nul 2>&1
  if not errorlevel 1 set "PY=python"
)

rem ---- Kein Python? Portables Python einmalig herunterladen -------------
if not defined PY (
  echo Kein Python gefunden - lade portables Python herunter ^(einmalig, ca. 11 MB^) ...
  curl -L -o python-embed.zip https://www.python.org/ftp/python/3.12.8/python-3.12.8-embed-amd64.zip
  if errorlevel 1 goto fail
  mkdir python-embed 2>nul
  tar -xf python-embed.zip -C python-embed
  if errorlevel 1 goto fail
  del python-embed.zip
  set "PY=python-embed\python.exe"
  echo Fertig - portables Python liegt jetzt im Ordner python-embed\
)

echo.
echo  sunshine live Track-Logger
echo  Webseite: http://localhost:8765  (oeffnet sich gleich automatisch)
echo  Beenden:  Strg+C oder dieses Fenster schliessen
echo.
%PY% tracklogger.py --open %*
pause
exit /b

:fail
echo.
echo Download fehlgeschlagen - bitte Internetverbindung pruefen oder
echo Python 3 manuell installieren: https://www.python.org/downloads/
echo.
pause
