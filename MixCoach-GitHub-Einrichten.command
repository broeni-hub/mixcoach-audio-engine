#!/bin/bash
# ============================================================
#  MixCoach - GitHub einrichten (einmalig, auf dem Mac)
#
#  Mac-Entsprechung zu MixCoach-GitHub-Einrichten.bat. Die .bat
#  laeuft hier nicht: sie hat C:\Projekte\... fest verdrahtet und
#  schiebt den Branch "master", den es hier gar nicht gibt.
#
#  Dieses Skript ermittelt seinen Projektpfad selbst und laedt
#  ALLE Branches hoch - der Sinn ist Sicherung, und dabei darf
#  keine Arbeit zurueckbleiben.
#
#  Voraussetzung: auf github.com ist ein LEERES, PRIVATES
#  Repository angelegt (Anleitung: LIESMICH-GitHub.md, Abschnitt 1).
#  Beim Anlegen KEIN Haken bei README / .gitignore / Lizenz.
# ============================================================

set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT" || exit 1

echo ""
echo "  ==========================================================="
echo "   MixCoach - GitHub einrichten"
echo "  ==========================================================="
echo ""
echo "  Projektordner: $ROOT"
echo ""

if ! command -v git >/dev/null 2>&1; then
  echo "  FEHLER: Git ist nicht installiert."
  echo "  Im Terminal 'xcode-select --install' ausfuehren, dann erneut."
  echo ""
  read -r -p "  Enter zum Beenden..."
  exit 1
fi

if [ ! -d "$ROOT/.git" ]; then
  echo "  FEHLER: $ROOT ist kein Git-Repository."
  read -r -p "  Enter zum Beenden..."
  exit 1
fi

# --- Sicherheitsnetz: nichts hochladen, was geheim ist -------------------
# Der Push geht nach aussen und laesst sich nicht zurueckholen. Deshalb hier
# eine letzte Kontrolle, ob versehentlich eine .env im Index gelandet ist.
if git ls-files --error-unmatch "Frontend/.env" >/dev/null 2>&1; then
  echo "  ABBRUCH: Frontend/.env ist versioniert. Diese Datei enthaelt den"
  echo "  Supabase-Service-Role-Key und darf NICHT zu GitHub."
  echo "  Erst 'git rm --cached Frontend/.env' ausfuehren, dann erneut."
  echo ""
  read -r -p "  Enter zum Beenden..."
  exit 1
fi

echo "  Was hochgeladen wird: Code, Doku, Ground-Truth-Labels und das"
echo "  trainierte Modell - rund 8 MB. Audio, Fingerprints und die"
echo "  synthetischen Daten bleiben per .gitignore aussen vor."
echo ""
echo "  Was mitgeht und persoenlich ist, damit du es weisst:"
echo "    - daten/library/index.json listet 6113 Titel deiner Sammlung,"
echo "      mit vollem Pfad unter /Users/sebastianbroening/Music/"
echo "    - die Namen von 21 Set-Aufnahmen, darunter fremde Mitschnitte"
echo "    - labels_prefilled.csv mit deinen eigenen Bewertungen"
echo ""
echo "  Genau deshalb: das Repository MUSS privat sein."
echo ""
# Von Sebastian am 10.08.2026 genannt. Einfach Enter druecken uebernimmt sie;
# eine andere URL eintippen ueberschreibt sie.
VORGABE="https://github.com/broeni-hub/mixcoach-audio-engine.git"

echo "  Hinterlegt: $VORGABE"
read -r -p "  Enter zum Uebernehmen, oder andere URL eingeben: " URL
URL="${URL:-$VORGABE}"

if [ -z "${URL:-}" ]; then
  echo ""
  echo "  Keine URL angegeben. Abbruch."
  read -r -p "  Enter zum Beenden..."
  exit 1
fi
echo "  Verwende: $URL"

echo ""
echo "  --- Schritt 1: Zugangsdaten im Schluesselbund merken -------"
# Ohne das fragt Git bei JEDEM Push erneut nach Name und Token.
git config --global credential.helper osxkeychain
echo "  erledigt (macOS-Schluesselbund)"

echo ""
echo "  --- Schritt 2: offene Aenderungen sichern ------------------"
# NICHT blind 'git add -A'. Am 10.08.2026 hat genau das vier Dateien
# mitgenommen, die niemand im Repo haben wollte: drei Analyse-JSONs aus einem
# Testlauf und eine leere Relabel-Datei. Sie standen als "unversioniert" da,
# weil sie Muell waren - und wurden dadurch erst recht eingesammelt.
# Ein Push laesst sich nicht zurueckholen, also wird hier gefragt.
if [ -n "$(git status --porcelain)" ]; then
  echo ""
  echo "  Diese Aenderungen wuerden mitgehen:"
  echo ""
  git status -s | sed 's/^/    /'
  echo ""
  echo "    (?? = bisher unversioniert - genau hier lohnt der zweite Blick)"
  echo ""
  read -r -p "  Alles davon sichern und hochladen? [j/N] " OK
  case "${OK:-n}" in
    j|J|y|Y)
      git add -A
      git commit -m "Stand vor der GitHub-Uebertragung"
      ;;
    *)
      echo ""
      echo "  Abgebrochen. Raeum auf, was nicht mit soll, und starte neu."
      echo "  Nur committete Staende gehen hoch - offene Aenderungen bleiben liegen."
      echo ""
      read -r -p "  Enter zum Beenden..."
      exit 0
      ;;
  esac
else
  echo "  nichts Neues zu sichern - in Ordnung"
fi

echo ""
echo "  --- Schritt 3: Remote eintragen ----------------------------"
git remote remove origin 2>/dev/null
git remote add origin "$URL"
git remote -v

echo ""
echo "  --- Schritt 4: Hochladen -----------------------------------"
echo ""
echo "  Git fragt jetzt nach deinem GitHub-Login."
echo "    Username: dein GitHub-Name"
echo "    Password: NICHT dein Passwort, sondern der Access Token"
echo "              (LIESMICH-GitHub.md, Abschnitt 1)"
echo ""
echo "  Der Token wird nur dieses eine Mal abgefragt und danach im"
echo "  Schluesselbund abgelegt."
echo ""

AKTUELL="$(git branch --show-current)"
if ! git push -u origin --all; then
  echo ""
  echo "  Der Push ist fehlgeschlagen. Die haeufigsten Gruende:"
  echo "    - das Repository war nicht leer (README beim Anlegen erzeugt)"
  echo "    - Passwort statt Access Token eingegeben"
  echo "    - URL vertippt"
  echo ""
  echo "  Falls der Token falsch war, loescht dieser Befehl den"
  echo "  gemerkten Eintrag, danach fragt Git wieder:"
  echo "    printf 'protocol=https\\nhost=github.com\\n' | git credential-osxkeychain erase"
  echo ""
  read -r -p "  Enter zum Beenden..."
  exit 1
fi

echo ""
echo "  ==========================================================="
echo "   Fertig. Der Code liegt jetzt auf GitHub."
echo "  ==========================================================="
echo ""
echo "  Dein Arbeitsbranch ist '$AKTUELL'. Auf GitHub steht als"
echo "  Standard-Branch vermutlich 'main' - das ist der alte Stand."
echo "  Umstellen unter: Settings -> General -> Default branch."
echo ""
echo "  Ab jetzt im Alltag:"
echo "    - Aenderungen hochladen:  MixCoach-Hochladen.command"
echo "    - auf dem anderen Rechner: git pull"
echo ""
echo "  ACHTUNG: Git uebertraegt NUR Code und Labels. Audio, Analysen"
echo "  und der Fingerprint-Index gehen weiterhin per USB-Stick -"
echo "  siehe LIESMICH-GitHub.md, Abschnitt 4."
echo ""
read -r -p "  Enter zum Beenden..."
