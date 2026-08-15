#!/bin/bash
# ============================================================
#  MixCoach - Besitzer eintragen
#
#  Schreibt in jeden Report und jede Bewertung, wem sie gehoert.
#  Heute gibt es nur einen Nutzer, deshalb steht ueberall der
#  Platzhalter "local-single-user".
#
#  Warum ueberhaupt: die Analyse-Engine kennt bisher keinen
#  Nutzer - das Frontend schon. Damit MixCoach spaeter fuer
#  mehrere Leute laufen kann, braucht jede Datei einen Besitzer.
#  Solange du der einzige bist, aendert sich fuer dich nichts.
#
#  Es wird ZUERST nur angezeigt, was passieren wuerde.
#  Geschrieben wird erst nach deiner Zustimmung - und alles
#  laesst sich mit einem Befehl wieder zuruecknehmen (steht
#  danach auf dem Bildschirm).
#
#  EINMALIG vor dem ersten Start:
#    chmod +x MixCoach-Besitzer-Migrieren.command
# ============================================================

set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE="$ROOT/audio-engine/mixcoach-audio-engine"
PY="$ROOT/.venv/bin/python"
export MIXCOACH_DATA_DIR="$ROOT/daten"

# Wer der Besitzer ist. Ohne Angabe der Platzhalter; sobald deine
# Supabase-Kennung bekannt ist, hier eintragen oder als Argument
# uebergeben:  ./MixCoach-Besitzer-Migrieren.command <deine-uid>
BESITZER="${1:-}"

echo ""
echo "  ==========================================================="
echo "   MixCoach - Besitzer eintragen"
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

if [ -n "$BESITZER" ]; then
  ARGS=(--besitzer "$BESITZER")
  echo "  Besitzer: $BESITZER"
else
  ARGS=()
  echo "  Besitzer: local-single-user (Platzhalter, noch niemand angemeldet)"
fi
echo ""

echo "  Das wuerde passieren (es wird noch NICHTS geschrieben):"
echo ""
"$PY" -m tools.migriere_besitzer ${ARGS[@]+"${ARGS[@]}"}
echo ""

read -r -p "  Wirklich eintragen? [j/N] " ANTWORT
case "${ANTWORT:-n}" in
  j|J|y|Y) ;;
  *) echo ""; echo "  Abgebrochen, nichts geaendert."; echo ""
     read -r -p "  Enter zum Beenden..."; exit 0 ;;
esac

echo ""
"$PY" -m tools.migriere_besitzer ${ARGS[@]+"${ARGS[@]}"} --write
echo ""

# Eine Verwaltungsaenderung darf die Messung nicht bewegen. Faellt das
# hier durch, wurde mehr veraendert als beabsichtigt.
echo "  Kontrolle: bewegt sich die Referenzmetrik?"
"$PY" -m tools.analyze_timing_bias --check 2>/dev/null | tail -4
echo ""
read -r -p "  Enter zum Beenden..."
