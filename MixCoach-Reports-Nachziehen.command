#!/bin/bash
# ============================================================
#  MixCoach-Reports-Nachziehen: bringt gespeicherte Reports auf
#  den ehrlichen Stand - und sorgt dafuer, dass die Korrektur
#  im Browser ankommt.
#
#  Was passiert:
#    * beatmatching und timing werden auf "nicht gemessen" gesetzt
#      (K1 hat belegt, dass diese zwei Zahlen nichts messen)
#    * notMeasured bekommt die vollstaendige Fuenferliste
#    * ein Stempel (scoringVersion) bleibt nur, wo er belegt ist
#    * reportRevision zaehlt hoch - ohne das bleibt jede Korrektur
#      auf der Platte liegen und erreicht keinen Browser, der die
#      Analyse schon kennt
#
#  Es wird ZUERST nur angezeigt, was sich aendern wuerde. Geschrieben
#  wird erst nach deiner Zustimmung.
#
#  Keine Audio-Analyse, kein Demucs: alles Noetige steht in den JSON.
#  Dauert Sekunden.
# ============================================================

set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE="$ROOT/audio-engine/mixcoach-audio-engine"
PY="$ROOT/.venv/bin/python"
export MIXCOACH_DATA_DIR="$ROOT/daten"

echo ""
echo "  ==========================================================="
echo "   MixCoach - Reports nachziehen"
echo "  ==========================================================="
echo ""

if [ ! -x "$PY" ]; then
  echo "  Python nicht gefunden unter"
  echo "    $PY"
  echo "  Bitte zuerst MixCoach-Mac-Reparieren.command ausfuehren."
  echo ""
  read -r -p "  Enter zum Beenden..."
  exit 1
fi

cd "$ENGINE" || { echo "  Engine-Ordner nicht gefunden."; read -r -p "  Enter..."; exit 1; }

echo "  Das wuerde sich aendern (es wird noch NICHTS geschrieben):"
echo ""
"$PY" -m tools.backfill_reports --mit-archiv
echo ""

read -r -p "  Aenderungen wirklich schreiben? [j/N] " ANTWORT
case "${ANTWORT:-n}" in
  j|J|y|Y) ;;
  *) echo ""; echo "  Abgebrochen, nichts geaendert."; echo ""
     read -r -p "  Enter zum Beenden..."; exit 0 ;;
esac

echo ""
"$PY" -m tools.backfill_reports --mit-archiv --write
echo ""

# Die Referenzmetrik darf sich durch eine Aufraeumarbeit nicht bewegen.
# Faellt das hier durch, wurde mehr veraendert als beabsichtigt.
echo "  Kontrolle: bewegt sich die Referenzmetrik?"
"$PY" -m tools.analyze_timing_bias --check 2>/dev/null | tail -4
echo ""
echo "  Fertig. Die Aenderungen liegen im Datenstamm; der Browser holt"
echo "  sie sich beim naechsten Oeffnen des Reports von selbst."
echo ""
read -r -p "  Enter zum Beenden..."
