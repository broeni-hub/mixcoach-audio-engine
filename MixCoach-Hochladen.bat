@echo off
setlocal

cd /d C:\Projekte\Projekte\MixCoach

echo.
echo   ===========================================================
echo    MixCoach - Aenderungen zu GitHub hochladen
echo   ===========================================================
echo.

git remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo   FEHLER: Kein GitHub-Repository eingerichtet.
    echo   Bitte zuerst MixCoach-GitHub-Einrichten.bat ausfuehren.
    echo.
    pause
    exit /b 1
)

echo   --- Was hat sich geaendert? -------------------------------
git status -s
echo.

git diff --quiet && git diff --cached --quiet
if not errorlevel 1 (
    echo   Keine lokalen Aenderungen. Trotzdem hochladen, falls noch
    echo   nicht gepushte Commits vorliegen...
    goto :push
)

set /p TEXT="   Kurze Beschreibung der Aenderung: "
if "%TEXT%"=="" set TEXT=Zwischenstand

git add -A
git commit -m "%TEXT%"

:push
echo.
echo   --- Hochladen ---------------------------------------------
git push
if errorlevel 1 (
    echo.
    echo   Push fehlgeschlagen. Falls der andere Rechner zwischen-
    echo   durch etwas hochgeladen hat, hilft meist:
    echo       git pull --rebase
    echo   und danach dieses Skript erneut ausfuehren.
    echo.
    pause
    exit /b 1
)

echo.
echo   Fertig - der andere Rechner kann jetzt "git pull" machen.
echo.
pause
