@echo off
cd /d "%~dp0"
echo sunshine live Track-Logger (Channel: Techno)
echo Webseite: http://localhost:8765
echo Beenden mit Strg+C oder Fenster schliessen.
echo.
py tracklogger.py 2>nul || python tracklogger.py
pause
