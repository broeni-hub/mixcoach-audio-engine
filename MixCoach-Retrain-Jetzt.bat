@echo off
rem ============================================================
rem  MixCoach-Retrain-Jetzt: trainiert das Modell SOFORT neu,
rem  ohne auf "genug neue Sets" zu warten.
rem
rem  Wie die normale MixCoach-Retrain.bat, aber mit --force:
rem  laeuft auch bei nur wenigen neuen Labels. Praktisch zum
rem  Ausprobieren direkt nach dem Labeln.
rem
rem  Trainiert (wie ueberall) NUR mit echten Sets - keine
rem  synthetischen Trainingsdaten. Neues Modell wird NUR
rem  aktiviert, wenn es das Gate besteht; altes wird als
rem  .backup gesichert (MixCoach-Modell-Zurueck.bat holt es
rem  zurueck). Du kannst nichts kaputt machen.
rem
rem  Dauer: einige Minuten. Fenster offen lassen bis
rem  "Ergebnis:" erscheint.
rem ============================================================

cd /d C:\Projekte\Projekte\MixCoach\audio-engine\mixcoach-audio-engine
set MIXCOACH_DATA_DIR=C:\Projekte\Projekte\MixCoach\daten

echo.
echo   Training startet sofort (nur echte Sets)...
echo.
python -m app.calibration.auto_retrain --force

echo.
echo   Fertig. Dieses Fenster kannst du jetzt schliessen.
pause
