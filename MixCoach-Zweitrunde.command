#!/bin/bash
# ============================================================
#  MixCoach - Zweite Labelrunde (K1)
#
#  Startet NUR die Analyse-Engine und oeffnet die Seite fuer
#  den zweiten, blinden Durchgang. Die Web-App wird nicht
#  gebraucht - die Seite kommt direkt aus der Engine.
#
#  Was hier gemessen wird: wie gut du deine eigene Zeitangabe
#  ein zweites Mal triffst. Deine Angaben vom ersten Mal
#  bekommst du deshalb NICHT zu sehen, und die Reihenfolge der
#  Uebergaenge ist gewuerfelt.
#
#  Es geht NICHT darum, dieselbe Zahl wie beim ersten Mal zu
#  treffen. Hoer hin und entscheide neu. Ein ehrliches Ergebnis
#  ist das Ziel, kein gutes.
#
#  EINMALIG vor dem ersten Start:
#    chmod +x MixCoach-Zweitrunde.command
# ============================================================

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE="$ROOT/audio-engine/mixcoach-audio-engine"
DATEN="$ROOT/daten"
PY="$ROOT/.venv/bin/python"

# Gewaehltes Set: "Dixon WE2 Tomorrowland 2025.mp3".
# Begruendung steht in K1_AUFBAU_2026-07-31.md - kurz: die meisten
# eigenstaendigen Zeitangaben (16 korrigierte Uebergaenge), nur EINE
# Analyse (keine Doubletten), 120 min, Aufnahme vorhanden, und es ist
# keines der acht Sets ohne Ergebnis-JSON.
SET_ID="04804f27-2755-4db3-8f0b-f57d3315737c"

echo ""
echo "  MixCoach - zweite Labelrunde"
echo "  Projektordner: $ROOT"
echo ""

if [ ! -x "$PY" ]; then
  echo "  FEHLER: Python-Umgebung nicht gefunden unter"
  echo "    $PY"
  echo "  Bitte zuerst MixCoach-Mac-Reparieren.command ausfuehren."
  read -r -p "  Enter zum Beenden..."
  exit 1
fi

# Set-Id aus der Datei lesen, falls vorhanden - so muss niemand dieses
# Skript bearbeiten, wenn ein anderes Set gemessen werden soll.
if [ -f "$ROOT/.zweitrunde-set" ]; then
  SET_ID="$(tr -d '[:space:]' < "$ROOT/.zweitrunde-set")"
  echo "  Set aus .zweitrunde-set: $SET_ID"
fi

osascript <<EOF
tell application "Terminal"
  do script "cd '$ENGINE' && export MIXCOACH_DATA_DIR='$DATEN' && echo '[MixCoach Engine] Port 8000 - Fenster offen lassen, bis du fertig bist.' && '$PY' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
  activate
end tell
EOF

echo "  Warte 10 Sekunden, bis die Engine hochgefahren ist..."
sleep 10
open "http://127.0.0.1:8000/relabel/$SET_ID"

echo ""
echo "  Die Seite ist im Browser offen."
echo ""
echo "  Ablauf je Uebergang:"
echo "    1. Abspielen, an die Stelle springen, wo der Uebergang BEGINNT"
echo "    2. angeben, was du markiert hast (A geht raus / B kommt rein / beides)"
echo "    3. 'Uebernehmen und weiter'"
echo ""
echo "  Du kannst jederzeit abbrechen - der Stand wird nach jedem"
echo "  Uebergang gespeichert. Beim naechsten Start geht es weiter."
echo ""
echo "  Auswertung danach im Terminal:"
echo "    cd '$ENGINE'"
echo "    MIXCOACH_DATA_DIR='$DATEN' '$PY' -m tools.eval.relabel_agreement"
echo ""
