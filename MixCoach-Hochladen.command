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
  git status -s
  echo ""
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
