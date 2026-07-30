@echo off
setlocal enabledelayedexpansion

set SRC=C:\Projekte\Projekte\MixCoach

echo.
echo   ===========================================================
echo    MixCoach - Backup fuer Umzug auf einen neuen PC
echo   ===========================================================
echo.
echo   Dieses Skript kopiert alle wichtigen MixCoach-Daten
echo   (Programm-Code, Analysen, Fingerprint-Bibliothek, Modelle,
echo   Labels) an ein Ziel deiner Wahl, z.B. einen USB-Stick,
echo   eine externe Festplatte oder einen Netzwerk-Ordner.
echo.
echo   NICHT mitkopiert wird, was der neue PC selbst neu aufbaut
echo   (siehe UEBERTRAGUNG-ANLEITUNG.docx):
echo     - node_modules (Frontend-Bibliotheken, per npm install)
echo     - Python-Arbeitsordner .venv (per requirements.txt)
echo     - temporaere Cache- und Log-Dateien
echo.

set /p ZIEL="   Ziel-Ordner OHNE abschliessenden Backslash (z.B. E:\MixCoach-Uebertragung): "

if "%ZIEL%"=="" (
    echo.
    echo   Kein Ziel angegeben. Abbruch.
    pause
    exit /b 1
)

echo.
set /p GROSS="   Auch die rund 7,6 GB synthetischen Trainings-Mixes mitkopieren? Normalerweise NICHT noetig (j/N): "

set XD_SYNTH=
if /i "%GROSS%"=="j" (
    set XD_SYNTH=
) else (
    set XD_SYNTH="%SRC%\audio-engine\mixcoach-audio-engine\datasets\synthetic"
)

echo.
echo   Kopiere nach %ZIEL%\MixCoach ...
echo   Das kann je nach Ziel-Medium und Datenmenge mehrere Minuten
echo   bis eine Stunde dauern. Bitte dieses Fenster NICHT schliessen.
echo.

robocopy "%SRC%" "%ZIEL%\MixCoach" /E /R:2 /W:5 /MT:8 /NFL /NDL /XF *.log ^
    /XD "%SRC%\Frontend\node_modules" "%SRC%\audio-engine\.venv" __pycache__ .pytest_cache .output .tanstack .wrangler .lovable %XD_SYNTH%

echo.
echo   ===========================================================
echo    Fertig!
echo   ===========================================================
echo.
echo   Der Ordner "%ZIEL%\MixCoach" enthaelt jetzt alle Daten.
echo.
echo   Naechster Schritt: UEBERTRAGUNG-ANLEITUNG.docx lesen. Kurz
echo   gesagt: diesen Ordner auf dem neuen PC nach
echo   C:\Projekte\Projekte\MixCoach kopieren (GENAU dieser Pfad
echo   ist wichtig, weil die Start-Skripte ihn fest verwenden).
echo.
pause
