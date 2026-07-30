@echo off
rem ============================================================
rem  MixCoach-Modell-Zurueck: macht das letzte Training
rem  rueckgaengig und stellt das VORHERIGE Modell wieder her.
rem
rem  Nutzt die automatische Sicherung (track_change_gbm.json.backup),
rem  die bei jedem Training angelegt wird. Danach die Engine
rem  ueber MixCoach-Start.bat neu starten, damit das
rem  zurueckgeholte Modell geladen wird.
rem ============================================================

set MODELS=C:\Projekte\Projekte\MixCoach\audio-engine\mixcoach-audio-engine\app\models
set CUR=%MODELS%\track_change_gbm.json
set BAK=%MODELS%\track_change_gbm.json.backup

if not exist "%BAK%" (
  echo   Kein Backup gefunden - es gibt nichts zum Zuruecksetzen.
  pause
  goto :eof
)

echo.
echo   Sichere das AKTUELLE Modell als .aktuell (falls du es doch behalten willst)...
copy /Y "%CUR%" "%CUR%.aktuell" >nul
echo   Stelle das vorherige Modell wieder her...
copy /Y "%BAK%" "%CUR%" >nul
echo.
echo   Fertig. Jetzt bitte MixCoach-Start.bat neu starten,
echo   damit das zurueckgeholte Modell geladen wird.
echo.
pause
