@echo off
cd /d C:\Projekte\Projekte\MixCoach\audio-engine\mixcoach-audio-engine
set MIXCOACH_DATA_DIR=C:\Projekte\Projekte\MixCoach\daten
echo ============================================================
echo  MixCoach Modell-Training mit deinem gesammelten Feedback
echo  Dauer: ca. 10-30 Minuten. Fenster offen lassen!
echo  Fortschritt steht in: dd\retrain_log.txt
echo ============================================================
echo ===== Training %date% %time% ===== >> "%~dp0retrain_log.txt"
"%LOCALAPPDATA%\MixCoach\venv\Scripts\python.exe" -m app.calibration.retrain_model >> "%~dp0retrain_log.txt" 2>&1
echo.
echo FERTIG. Ergebnis steht in dd\retrain_log.txt
echo Danach: MixCoach-Start.bat neu ausfuehren, damit das Backend
echo das neue Modell laedt.
pause
