@echo off
cd /d C:\Projekte\Projekte\MixCoach\Frontend
echo ===== Frontend-Start %date% %time% ===== >> "%~dp0frontend_run.log"

rem Nach dem Ordner-Umzug fehlen die Startbefehle der Bibliotheken -
rem einmalig reparieren (dauert beim ersten Mal ein paar Minuten):
if not exist "node_modules\.bin\vite.cmd" (
    echo Einmalige Reparatur: Bibliotheken werden neu verknuepft ^(npm install^)...
    echo Bitte warten - das kann einige Minuten dauern.
    call npm install >> "%~dp0frontend_run.log" 2>&1
)

echo Frontend laeuft. Adresse: http://localhost:8080
echo Protokoll: dd\frontend_run.log - Dieses Fenster OFFEN LASSEN.
call npm run dev >> "%~dp0frontend_run.log" 2>&1
echo.
echo *** FRONTEND WURDE BEENDET - Details stehen in dd\frontend_run.log ***
pause
