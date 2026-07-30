@echo off
setlocal

set SRC=%USERPROFILE%\.claude
set ZIEL=C:\Projekte\Projekte\MixCoach\claude-code-verlauf

echo.
echo   ===========================================================
echo    MixCoach - Claude-Code-Verlauf sichern
echo   ===========================================================
echo.
echo   Der Chatverlauf von Claude Code liegt NICHT im Projekt-
echo   ordner, sondern unter:
echo     %SRC%
echo.
echo   Dieses Skript kopiert ihn in den Projektordner, damit er
echo   beim naechsten Backup automatisch mit uebertragen wird.
echo.

if not exist "%SRC%\projects" (
    echo   FEHLER: "%SRC%\projects" wurde nicht gefunden.
    echo   Wurde Claude Code auf diesem Rechner ueberhaupt benutzt?
    echo.
    pause
    exit /b 1
)

echo   Kopiere nach %ZIEL% ...
echo.

robocopy "%SRC%\projects" "%ZIEL%\projects" /E /R:2 /W:5 /NFL /NDL
robocopy "%SRC%" "%ZIEL%" CLAUDE.md settings.json /R:2 /W:5 /NFL /NDL

echo.
echo   ===========================================================
echo    Fertig!
echo   ===========================================================
echo.
echo   Gesicherte Ordner:
dir /b "%ZIEL%\projects"
echo.
echo   Naechster Schritt: LIESMICH-Verlauf-Uebertragen.md lesen.
echo.
pause
