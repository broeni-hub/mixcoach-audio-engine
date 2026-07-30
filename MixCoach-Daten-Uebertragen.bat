@echo off
setlocal enabledelayedexpansion

set SRC=C:\Projekte\Projekte\MixCoach\daten

echo.
echo   ===========================================================
echo    MixCoach - Daten fuer den Mac uebertragen
echo   ===========================================================
echo.
echo   Der CODE laeuft ab jetzt ueber GitHub (LIESMICH-GitHub.md).
echo   Dieses Skript kopiert nur, was GitHub NICHT uebertraegt.
echo.
echo   WICHTIG: Der Ordner "archived" ist KEIN Muell. Von deinen
echo   45 gelabelten Sets liegt bei 9 Stueck das Audio NUR dort.
echo   Ohne ihn verlierst du rund ein Drittel der Trainingsbasis.
echo   Die archivierten JSONs werden daher IMMER mitkopiert.
echo.
echo   Waehle, was mitkommen soll:
echo.
echo     [1] Nur die Analysen             ca.  3,5 MB
echo         Alle 22 Analysen + 16 archivierte. Verlaufsliste ist
echo         vollstaendig, Gewichts-Fitting funktioniert.
echo         NICHT moeglich: Wiedergabe und Modell-Retraining.
echo         Passt in jede Cloud - kein Stick noetig.
echo.
echo     [2] Analysen + alles Audio       ca.  9,3 GB   (empfohlen)
echo         Zusaetzlich die Mix-Dateien aus analysis_results UND
echo         archived. Damit ist alles moeglich, was auf diesem PC
echo         auch geht - inklusive Retraining. USB-Stick ab 16 GB.
echo.
echo     [3] Wie [2] plus Fingerprint-Index  ca. 9,6 GB
echo         Spart auf dem Mac nur das einmalige Neu-Indizieren.
echo.

set /p WAHL="   Deine Wahl (1/2/3): "

if "%WAHL%"=="" goto :fehler
if not "%WAHL%"=="1" if not "%WAHL%"=="2" if not "%WAHL%"=="3" goto :fehler

echo.
if "%WAHL%"=="1" (
    echo   Ziel z.B. ein Cloud-Ordner: C:\Users\Sebro\Dropbox\MixCoach-Transfer
) else (
    echo   Ziel z.B. ein USB-Stick: E:\MixCoach-Transfer
)
set /p ZIEL="   Ziel-Ordner OHNE abschliessenden Backslash: "

if "%ZIEL%"=="" goto :fehler

set OUT=%ZIEL%\MixCoach-Daten

echo.
echo   Kopiere nach %OUT% ...
echo   Fenster bitte NICHT schliessen.
echo.

rem --- 1) Analysen (JSON) - immer -----------------------------
echo   [1/4] Analysen...
robocopy "%SRC%\analysis_results" "%OUT%\analysis_results" *.json ^
    /R:2 /W:5 /NFL /NDL /NJH /NJS /XD "%SRC%\analysis_results\archived"

rem --- 2) Archivierte Analysen (JSON) - immer -----------------
echo   [2/4] Archivierte Analysen...
robocopy "%SRC%\analysis_results\archived" "%OUT%\analysis_results\archived" *.json ^
    /R:2 /W:5 /NFL /NDL /NJH /NJS

rem --- 3) Audio - nur bei Wahl 2 und 3 ------------------------
if not "%WAHL%"=="1" (
    echo   [3/4] Audio aus analysis_results - das dauert am laengsten...
    robocopy "%SRC%\analysis_results" "%OUT%\analysis_results" ^
        *.wav *.mp3 *.flac *.m4a *.aiff ^
        /R:2 /W:5 /MT:8 /NFL /NDL /NJH /NJS /XD "%SRC%\analysis_results\archived"

    echo   [3/4] Audio aus archived - enthaelt 9 gelabelte Sets...
    robocopy "%SRC%\analysis_results\archived" "%OUT%\analysis_results\archived" ^
        *.wav *.mp3 *.flac *.m4a *.aiff ^
        /R:2 /W:5 /MT:8 /NFL /NDL /NJH /NJS
) else (
    echo   [3/4] Audio uebersprungen ^(Wahl 1^).
)

rem --- 4) Fingerprint-Index - nur bei Wahl 3 ------------------
if "%WAHL%"=="3" (
    echo   [4/4] Fingerprint-Index...
    robocopy "%SRC%\library" "%OUT%\library" /E /R:2 /W:5 /MT:8 /NFL /NDL /NJH /NJS
) else (
    echo   [4/4] Fingerprint-Index uebersprungen.
)

echo.
echo   ===========================================================
echo    Fertig! Bitte diese Zahlen pruefen:
echo   ===========================================================
echo.

set /a N1=0
for %%F in ("%OUT%\analysis_results\*.json") do set /a N1+=1
set /a N2=0
for %%F in ("%OUT%\analysis_results\archived\*.json") do set /a N2+=1

echo     Analysen              : !N1!    (erwartet: 22)
echo     Archivierte Analysen  : !N2!    (erwartet: 16)

if not "%WAHL%"=="1" (
    set /a N3=0
    for %%F in ("%OUT%\analysis_results\*.wav" "%OUT%\analysis_results\*.mp3") do set /a N3+=1
    set /a N4=0
    for %%F in ("%OUT%\analysis_results\archived\*.wav" "%OUT%\analysis_results\archived\*.mp3") do set /a N4+=1
    echo     Audio-Dateien         : !N3!    (erwartet: 22)
    echo     Audio im Archiv       : !N4!    (erwartet: 9)
)

echo.
echo   Stimmen die Zahlen nicht, war zu wenig Platz auf dem Ziel
echo   oder der Vorgang wurde abgebrochen - dann einfach dieses
echo   Skript erneut ausfuehren, es kopiert nur Fehlendes nach.
echo.
echo   Naechster Schritt: LIESMICH-Daten-auf-den-Mac.md
echo.
pause
exit /b 0

:fehler
echo.
echo   Ungueltige Eingabe. Abbruch.
echo.
pause
exit /b 1
