#!/bin/bash
# ============================================================
#  MixCoach-Retrain: trainiert das Erkennungs-Modell mit
#  deinem gesammelten Feedback neu.
#
#  Mac-Entsprechung zu MixCoach-Retrain.bat. Die .bat laeuft
#  hier nicht: sie hat C:\Projekte\... fest verdrahtet und ruft
#  "python", was auf diesem Mac das System-Python 3.9 waere -
#  damit startet die Engine nicht (siehe CLAUDE.md).
#
#  Trainiert NUR mit echten Sets (real-only ist seit 28.07.2026
#  Standard - gemessen besser auf deinen Sets).
#
#  Sicher: ein neues Modell wird NUR aktiviert, wenn es das
#  eingebaute Gate besteht. Sonst bleibt alles beim Alten, und
#  das vorherige Modell wird als .backup gesichert
#  (MixCoach-Modell-Zurueck.command holt es zurueck).
#  Du kannst nichts kaputt machen.
#
#  Ohne Argument laeuft es nur, wenn genug Neues da ist
#  (Schwelle: 10 neue Sets). Sofort trainieren:
#  MixCoach-Retrain-Jetzt.command
# ============================================================

set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE="$ROOT/audio-engine/mixcoach-audio-engine"
PY="$ROOT/.venv/bin/python"

echo ""
echo "  ==========================================================="
echo "   MixCoach - Modell nachtrainieren"
echo "  ==========================================================="
echo ""

if [ ! -x "$PY" ]; then
  echo "  FEHLER: Python-Umgebung nicht gefunden unter"
  echo "    $PY"
  echo "  Bitte zuerst MixCoach-Mac-Reparieren.command ausfuehren."
  echo ""
  read -r -p "  Enter zum Beenden..."
  exit 1
fi

cd "$ENGINE" || exit 1
export MIXCOACH_DATA_DIR="$ROOT/daten"

echo "  Datenstamm: $MIXCOACH_DATA_DIR"
echo ""
echo "  Hinweis zur Dauer: die Gittersuche ueber die Auswahl-Parameter"
echo "  braucht seit dem 10.08.2026 nur noch EINEN LOSO-Durchgang statt"
echo "  einen je Gitterzelle - aus 500 Modell-Fits sind 25 geworden."
echo "  Was Zeit kostet, ist das Nachrechnen neuer Sets aus dem Audio."
echo ""
echo "  Pruefe, ob genug neues Feedback fuer ein Training da ist..."
echo ""

"$PY" -m app.calibration.auto_retrain "$@"
CODE=$?

echo ""
if [ $CODE -ne 0 ]; then
  echo "  Das Training ist mit Fehler $CODE abgebrochen."
  echo "  Haeufigste Ursache: eine Aufnahme fehlt, deren Labels gebraucht"
  echo "  werden - die Meldung oben nennt sie mit Namen."
else
  echo "  Fertig. Falls oben 'exported: false' steht, war das neue Modell"
  echo "  nicht besser - dann bleibt bewusst das alte aktiv."
  echo ""
  echo "  Damit ein neues Modell geladen wird, die Engine neu starten"
  echo "  (MixCoach-Start-Mac.command)."
fi
echo ""
read -r -p "  Enter zum Beenden..."
exit $CODE
