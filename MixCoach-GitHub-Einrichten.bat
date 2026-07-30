@echo off
setlocal

cd /d C:\Projekte\Projekte\MixCoach

echo.
echo   ===========================================================
echo    MixCoach - GitHub einrichten (einmalig, alter PC)
echo   ===========================================================
echo.
echo   Voraussetzung: Du hast auf github.com bereits ein LEERES
echo   privates Repository angelegt (siehe LIESMICH-GitHub.md).
echo   Beim Anlegen KEIN Haken bei README / .gitignore / Lizenz!
echo.

where git >nul 2>&1
if errorlevel 1 (
    echo   FEHLER: Git ist nicht installiert.
    echo   Bitte zuerst https://git-scm.com/download/win installieren.
    echo.
    pause
    exit /b 1
)

set /p URL="   Repository-URL einfuegen (z.B. https://github.com/DEINNAME/mixcoach.git): "

if "%URL%"=="" (
    echo.
    echo   Keine URL angegeben. Abbruch.
    pause
    exit /b 1
)

echo.
echo   --- Schritt 1: offene Aenderungen sichern -----------------
git add -A
git commit -m "Stand vor GitHub-Uebertragung" 2>nul
if errorlevel 1 echo   (nichts Neues zu sichern - in Ordnung)

echo.
echo   --- Schritt 2: Remote eintragen ---------------------------
git remote remove origin 2>nul
git remote add origin "%URL%"
git remote -v

echo.
echo   --- Schritt 3: Hochladen ----------------------------------
echo   Beim ersten Mal fragt Git nach deinem GitHub-Login.
echo   WICHTIG: Als Passwort NICHT dein GitHub-Passwort eingeben,
echo   sondern einen "Personal Access Token" (siehe LIESMICH-GitHub.md).
echo.
git push -u origin master
if errorlevel 1 (
    echo.
    echo   Der Push ist fehlgeschlagen. Haeufigste Gruende:
    echo     - Repository war nicht leer (README beim Anlegen erzeugt)
    echo     - Falsches Passwort statt Access Token
    echo     - URL vertippt
    echo.
    pause
    exit /b 1
)

echo.
echo   ===========================================================
echo    Fertig! Der Code liegt jetzt auf GitHub.
echo   ===========================================================
echo.
echo   Ab jetzt gilt:
echo     - Aenderungen hochladen:  MixCoach-Hochladen.bat
echo     - Auf dem Mac holen:      git pull
echo.
echo   ACHTUNG: Git uebertraegt NUR Code und Labels. Die Audio-
echo   Daten, Analysen und der Fingerprint-Index muessen weiterhin
echo   per USB-Stick uebertragen werden - siehe LIESMICH-GitHub.md.
echo.
pause
