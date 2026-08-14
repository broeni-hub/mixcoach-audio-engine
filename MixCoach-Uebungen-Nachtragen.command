#!/bin/bash
# ============================================================
#  MixCoach-Uebungen-Nachtragen: ersetzt die alte Vorlage-Uebung
#  durch Uebungen, die eine gemessene Zahl nennen.
#
#  Bis zum 14.08.2026 stand in JEDEM Report dieselbe Zeile:
#    "Transition Review - Listen to the detected transition points"
#  Sie war fest verdrahtet und hatte mit deinem Set nichts zu tun.
#
#  Was stattdessen entsteht, zum Beispiel:
#    "Bei 18:46 (Uebergang 6) kam der neue Track 5,4 dB lauter rein.
#     Mix ihn nochmal, Ziel: unter 1,0 dB."
#
#  Uebungen entstehen NUR aus dem Pegelsprung - der einzigen Groesse,
#  die gegen deine Bewertungen belegt ist (Spearman -0,34) und genug
#  Spannweite hat, dass ein Ziel Sinn ergibt. Wo nichts belegt ist,
#  steht KEINE Uebung. Das ist Absicht: eine allgemeine Uebung waere
#  schlimmer als keine, weil sie so aussieht, als haette das Werkzeug
#  etwas gemessen.
#
#  Camelot-Abstand und Energieloch erscheinen getrennt als
#  Beobachtungen - festgestellt, nicht bewertet.
#
#  Es wird ZUERST nur angezeigt, was sich aendern wuerde.
#  Kein Audio noetig, dauert Sekunden.
# ============================================================

set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE="$ROOT/audio-engine/mixcoach-audio-engine"
PY="$ROOT/.venv/bin/python"
export MIXCOACH_DATA_DIR="$ROOT/daten"

echo ""
echo "  ==========================================================="
echo "   MixCoach - Uebungen nachtragen"
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
"$PY" -m tools.backfill_uebungen --mit-archiv --leise
echo ""

read -r -p "  Aenderungen wirklich schreiben? [j/N] " ANTWORT
case "${ANTWORT:-n}" in
  j|J|y|Y) ;;
  *) echo ""; echo "  Abgebrochen, nichts geaendert."; echo ""
     read -r -p "  Enter zum Beenden..."; exit 0 ;;
esac

echo ""
"$PY" -m tools.backfill_uebungen --mit-archiv --leise --write
echo ""

# Die Referenzmetrik darf sich durch Textarbeit nicht bewegen. Faellt das
# hier durch, wurde mehr veraendert als beabsichtigt.
echo "  Kontrolle: bewegt sich die Referenzmetrik?"
"$PY" -m tools.analyze_timing_bias --check 2>/dev/null | tail -3
echo ""
echo "  Fertig. Beim naechsten Oeffnen eines Reports holt der Browser die"
echo "  neuen Uebungen von selbst - du musst nichts loeschen."
echo ""
read -r -p "  Enter zum Beenden..."
