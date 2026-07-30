@echo off
cd /d C:\Projekte\Projekte\MixCoach\audio-engine\mixcoach-audio-engine
echo ============================================================
echo  MixCoach - Duplikat-Analysen archivieren (einmaliges Aufraeumen)
echo  Nichts wird geloescht - Duplikate wandern nach "archived".
echo ============================================================
echo.
echo --- Ordner 1: daten\analysis_results (produktive Analysen) ---
"%LOCALAPPDATA%\MixCoach\venv\Scripts\python.exe" archive_duplicate_analyses.py --results-dir "C:\Projekte\Projekte\MixCoach\daten\analysis_results"
echo.
echo --- Ordner 2: analysis_results (im audio-engine-Ordner, u.a. Testlaeufe) ---
"%LOCALAPPDATA%\MixCoach\venv\Scripts\python.exe" archive_duplicate_analyses.py --results-dir analysis_results
echo.
echo FERTIG.
pause
