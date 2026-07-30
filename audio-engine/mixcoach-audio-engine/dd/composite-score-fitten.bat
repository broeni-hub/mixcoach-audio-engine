@echo off
cd /d C:\Projekte\Projekte\MixCoach\audio-engine\mixcoach-audio-engine
echo ============================================================
echo  MixCoach - Composite-Score-Gewichte gegen deine Bewertungen fitten
echo  Braucht: labels_prefilled.csv mit ausgefuellten human_rating-Werten
echo  UND Analysen, die bereits mit dem neuen Composite-Score gelaufen sind.
echo ============================================================
echo.
"%LOCALAPPDATA%\MixCoach\venv\Scripts\python.exe" -m app.calibration.fit_composite_weights --results-dir "C:\Projekte\Projekte\MixCoach\daten\analysis_results"
echo.
pause
