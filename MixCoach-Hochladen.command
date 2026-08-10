#!/bin/bash
# ============================================================
#  MixCoach - Aenderungen zu GitHub hochladen
#
#  Mac-Entsprechung zu MixCoach-Hochladen.bat. Doppelklicken,
#  kurz beschreiben was sich geaendert hat, fertig.
# ============================================================

set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT" || exit 1

echo ""
echo "  ==========================================================="
echo "   MixCoach - zu GitHub hochladen"
echo "  ==========================================================="
echo ""

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "  FEHLER: Kein GitHub-Repository eingerichtet."
  echo "  Bitte zuerst MixCoach-GitHub-Einrichten.command ausfuehren."
  echo ""
  read -r -p "  Enter zum Beenden..."
  exit 1
fi

AKTUELL="$(git branch --show-current)"
echo "  Branch: $AKTUELL"
echo ""
echo "  --- Was hat sich geaendert? --------------------------------"
if [ -n "$(git status --porcelain)" ]; then
  git status -s | sed 's/^/    /'
  echo ""
  # Unversionierte Dateien getrennt hervorheben: sie sind der haeufigste Weg,
  # auf dem Muell ins Repo rutscht (Testreste, Zwischenstaende). Am 10.08.2026
  # sind so vier Dateien nach GitHub gelangt, die dort nicht hingehoerten.
  NEU="$(git ls-files --others --exclude-standard | wc -l | tr -d ' ')"
  if [ "$NEU" != "0" ]; then
    echo "  ACHTUNG: $NEU Datei(en) sind bisher unversioniert (?? oben)."
    echo "  Sie wuerden jetzt dauerhaft ins Repo aufgenommen."
    echo ""
    read -r -p "  Sollen die wirklich mit? [j/N] " OK
    case "${OK:-n}" in
      j|J|y|Y) ;;
      *) echo ""
         echo "  Abgebrochen. Raeum sie weg oder trag sie in .gitignore ein."
         echo ""
         read -r -p "  Enter zum Beenden..."; exit 0 ;;
    esac
    echo ""
  fi
  read -r -p "  Kurze Beschreibung der Aenderung: " TEXT
  [ -z "${TEXT:-}" ] && TEXT="Zwischenstand"
  git add -A
  git commit -m "$TEXT"
else
  echo "  Keine lokalen Aenderungen."
  echo "  Es wird trotzdem gepusht, falls noch Commits offen sind."
fi

echo ""
echo "  --- Hochladen ----------------------------------------------"
if ! git push -u origin "$AKTUELL"; then
  echo ""
  echo "  Push fehlgeschlagen. Hat der andere Rechner zwischendurch"
  echo "  etwas hochgeladen, hilft meist:"
  echo "      git pull --rebase"
  echo "  und danach dieses Skript erneut."
  echo ""
  read -r -p "  Enter zum Beenden..."
  exit 1
fi

echo ""
echo "  Fertig - der andere Rechner kann jetzt 'git pull' machen."
echo ""
read -r -p "  Enter zum Beenden..."
