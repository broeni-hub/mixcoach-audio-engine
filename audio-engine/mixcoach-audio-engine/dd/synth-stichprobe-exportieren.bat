@echo off
cd /d C:\Projekte\Projekte\MixCoach\audio-engine\mixcoach-audio-engine
echo ============================================================
echo  Stichprobe synthetischer Uebergaenge fuer manuelles Rating
echo ============================================================
"%LOCALAPPDATA%\MixCoach\venv\Scripts\python.exe" -m app.calibration.export_synth_mixer_sample_for_rating --dataset-dir datasets\synthetic\v1 --out synth_mixer_labels_prefilled_v2.csv
echo.
echo FERTIG. Datei: synth_mixer_labels_prefilled.csv
echo Naechster Schritt: In Excel oeffnen, audio_file an der Stelle
echo time_mmss anhoeren, human_rating (1-5) eintragen, speichern.
pause
