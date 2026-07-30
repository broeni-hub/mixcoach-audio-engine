@echo off
cd /d C:\Projekte\Projekte\MixCoach\audio-engine\mixcoach-audio-engine
echo ===== Backend-Start %date% %time% ===== >> "%~dp0backend_run.log"

rem Alle Analyse-Daten (Reports + Audio-Kopien) liegen im Projektordner:
set MIXCOACH_DATA_DIR=C:\Projekte\Projekte\MixCoach\daten

rem Einmaliger Umzug: alte Analyse-Daten aus AppData in den Projektordner holen.
if exist "%LOCALAPPDATA%\MixCoach\analysis_results" (
    echo Alte Analyse-Daten werden in den Projektordner verschoben...
    robocopy "%LOCALAPPDATA%\MixCoach\analysis_results" "C:\Projekte\Projekte\MixCoach\daten\analysis_results" /E /MOVE >nul
    rmdir "%LOCALAPPDATA%\MixCoach\analysis_results" >nul 2>&1
)

echo Backend laeuft. Protokoll: dd\backend_run.log
echo Dieses Fenster OFFEN LASSEN.
"%LOCALAPPDATA%\MixCoach\venv\Scripts\python.exe" -m uvicorn app.main:app --port 8000 >> "%~dp0backend_run.log" 2>&1
echo.
echo *** BACKEND WURDE BEENDET - Details stehen in dd\backend_run.log ***
pause
