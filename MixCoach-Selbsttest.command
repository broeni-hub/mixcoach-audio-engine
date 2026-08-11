#!/bin/bash
# ============================================================
#  MixCoach - Selbsttest
#
#  Sagt, was WIRKLICH misst - und wo nur etwas so aussieht.
#
#  Anlass: am 11.08.2026 sind an einem Tag drei Dinge aufgefallen,
#  die wie ein Datenproblem aussahen und keines waren, sondern ein
#  stiller Ausfall: ein Schalter ohne Werkzeug dahinter, ein Skript
#  das den falschen Ordner las, und eine Cloud-Anbindung, die bei
#  jedem Aufruf scheiterte, ohne dass es jemand sah.
#
#  Dieses Skript prueft die Voraussetzungen, nicht den Code.
#  Laeuft ohne Audio, ohne Netz, in Sekunden. Aendert nichts.
#
#  Lesehilfe:
#    ok     die Voraussetzung ist da
#    WARN   laeuft, aber es gibt etwas zu wissen
#    FEHLT  hier wird NICHT gemessen, auch wenn alles normal aussieht
# ============================================================

set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE="$ROOT/audio-engine/mixcoach-audio-engine"
PY="$ROOT/.venv/bin/python"

if [ ! -x "$PY" ]; then
  echo ""
  echo "  FEHLER: Python-Umgebung nicht gefunden unter"
  echo "    $PY"
  echo "  Bitte zuerst MixCoach-Mac-Reparieren.command ausfuehren."
  echo ""
  read -r -p "  Enter zum Beenden..."
  exit 1
fi

cd "$ENGINE" || exit 1
export MIXCOACH_DATA_DIR="$ROOT/daten"

"$PY" -m tools.selbsttest
CODE=$?

echo ""
if [ $CODE -ne 0 ]; then
  echo "  Es gibt mindestens eine Stelle, an der nicht gemessen wird."
  echo "  Die Zeilen mit FEHLT nennen jeweils die Abhilfe."
else
  echo "  Keine stillen Ausfaelle."
fi
echo ""
read -r -p "  Enter zum Beenden..."
exit $CODE
