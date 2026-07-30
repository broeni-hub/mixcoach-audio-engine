@echo off
echo ============================================================
echo  MixCoach: Python-Umfeld wird NEU und AUSSERHALB von OneDrive
echo  angelegt (dort kann OneDrive es nicht mehr kaputt machen).
echo  Das dauert einige Minuten - Fenster offen lassen!
echo ============================================================
echo.
set VENVDIR=%LOCALAPPDATA%\MixCoach\venv

where py >nul 2>&1
if %errorlevel%==0 (
    py -3 -m venv "%VENVDIR%"
) else (
    python -m venv "%VENVDIR%"
)

if not exist "%VENVDIR%\Scripts\python.exe" (
    echo.
    echo *** FEHLER: Python-Umfeld konnte nicht angelegt werden. ***
    echo *** Bitte Fenster fotografieren/abschreiben und melden.  ***
    pause
    exit /b 1
)

echo.
echo Bibliotheken werden installiert (librosa, fastapi, ...)...
"%VENVDIR%\Scripts\python.exe" -m pip install --upgrade pip >> "%~dp0venv_log.txt" 2>&1
"%VENVDIR%\Scripts\python.exe" -m pip install -r "C:\Projekte\Projekte\MixCoach\audio-engine\mixcoach-audio-engine\app\requirements.txt" >> "%~dp0venv_log.txt" 2>&1

if %errorlevel%==0 (
    echo.
    echo ============================================
    echo  FERTIG! Jetzt MixCoach-Start.bat doppelklicken.
    echo ============================================
) else (
    echo.
    echo *** FEHLER bei der Installation - Details in dd\venv_log.txt ***
)
pause
