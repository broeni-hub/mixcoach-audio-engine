@echo off
rem ============================================================
rem  MixCoach-Start: startet Analyse-Engine + App zusammen.
rem
rem  Es oeffnen sich ZWEI zusaetzliche Fenster:
rem    "MixCoach Engine"  - die Python-Analyse (Port 8000)
rem    "MixCoach App"     - die Web-App        (Port 8080)
rem  Beide Fenster einfach OFFEN LASSEN, solange du MixCoach
rem  benutzt. Zum Beenden: beide Fenster schliessen.
rem
rem  Warum wichtig: laeuft die Engine nicht, rechnet die App im
rem  Browser mit einer stark eingeschraenkten Notfall-Auswertung
rem  (findet kaum Uebergaenge). Mit dieser Datei passiert das
rem  nicht mehr aus Versehen.
rem ============================================================

echo.
echo   MixCoach wird gestartet...
echo.

rem --- 1) Analyse-Engine (Python-Backend, Port 8000) ---
start "MixCoach Engine" cmd /k "cd /d C:\Projekte\Projekte\MixCoach\audio-engine\mixcoach-audio-engine && set MIXCOACH_DATA_DIR=C:\Projekte\Projekte\MixCoach\daten&& echo [MixCoach Engine] Startet auf Port 8000 - Fenster offen lassen. && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

rem --- 2) Web-App (Frontend, Port 8080) ---
start "MixCoach App" cmd /k "cd /d C:\Projekte\Projekte\MixCoach\Frontend && echo [MixCoach App] Startet auf Port 8080 - Fenster offen lassen. && npm run dev"

rem --- 3) Kurz warten, dann Browser oeffnen ---
echo   Warte 12 Sekunden, bis beide Dienste hochgefahren sind...
timeout /t 12 /nobreak >nul
start http://localhost:8080/app/analyses

echo.
echo   Fertig! Die App ist im Browser geoeffnet.
echo   Falls die Seite noch laedt: ein paar Sekunden warten und neu laden (F5).
echo.
echo   Dieses Fenster kannst du schliessen - die beiden anderen offen lassen.
pause
