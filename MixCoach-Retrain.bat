@echo off
rem ============================================================
rem  MixCoach-Retrain: trainiert das Erkennungs-Modell mit
rem  deinem gesammelten Feedback neu.
rem
rem  Trainiert NUR mit echten Sets (real-only ist seit
rem  28.07.2026 Standard - gemessen besser auf deinen Sets;
rem  synthetische Trainingsdaten werden nicht mehr verwendet).
rem
rem  Sicher: ein neues Modell wird NUR aktiviert, wenn es
rem  nachweislich besser ist als das aktuelle (eingebautes
rem  Gate). Sonst bleibt alles beim Alten - du kannst also
rem  nichts kaputt machen.
rem
rem  Wann laufen lassen: nach ein paar neuen gelabelten Sets
rem  (die App zeigt "X von 10 bis zum naechsten Training").
rem  Ohne Argument laeuft es nur, wenn genug Neues da ist.
rem  Mit  --force  laeuft es sofort.
rem
rem  Dauer: einige Minuten (rechnet Audio-Analysen der neuen
rem  Sets nach). Fenster offen lassen bis "Ergebnis:" erscheint.
rem ============================================================

cd /d C:\Projekte\Projekte\MixCoach\audio-engine\mixcoach-audio-engine
set MIXCOACH_DATA_DIR=C:\Projekte\Projekte\MixCoach\daten

echo.
echo   Pruefe, ob genug neues Feedback fuer ein Training da ist...
echo.
python -m app.calibration.auto_retrain %*

echo.
echo   Fertig. Dieses Fenster kannst du jetzt schliessen.
pause
