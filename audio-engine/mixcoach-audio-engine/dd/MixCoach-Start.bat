@echo off
echo ===== Starter ausgefuehrt %date% %time% ===== >> "%~dp0starter_log.txt"
echo MixCoach wird gestartet...
echo.
echo Schritt 1: Alte Server-Prozesse beenden...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1
timeout /t 2 /nobreak >nul
echo    erledigt.
echo.
echo Schritt 2: Backend-Fenster oeffnen...
start "MixCoach BACKEND (offen lassen)" cmd /k %~dp0start-backend.bat
timeout /t 3 /nobreak >nul
echo Schritt 3: Frontend-Fenster oeffnen...
start "MixCoach FRONTEND (offen lassen)" cmd /k %~dp0start-frontend.bat
echo.
echo Fertig! Nach ca. 15 Sekunden im Browser oeffnen:
echo    http://localhost:8080
echo Backend-Check: http://127.0.0.1:8000/health muss "0.3.0" zeigen
echo.
echo Dieses Fenster kann geschlossen werden. Die BEIDEN ANDEREN offen lassen!
pause
