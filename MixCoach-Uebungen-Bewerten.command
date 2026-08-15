#!/bin/bash
# ============================================================
#  MixCoach - Welcher Hinweis hilft mehr?
#
#  Startet NUR die Analyse-Engine und oeffnet eine Seite mit
#  20 Uebergaengen. Zu jedem stehen ZWEI Formulierungen da.
#  Deine Frage: welcher Hinweis wuerde dich beim naechsten Mix
#  mehr veraendern?
#
#  Welcher Text woher stammt, siehst du bewusst nicht - und die
#  Seite verraet es auch nirgends. Sonst wuerdest du deine
#  eigene Entscheidung bewerten statt den Text.
#
#  Es gibt kein Richtig. Entscheide aus dem Bauch. Ein
#  ehrliches Ergebnis ist das Ziel, kein gutes.
#
#  Danach: MixCoach-Uebungen-Auswerten laeuft automatisch am
#  Ende dieses Skripts.
#
#  EINMALIG vor dem ersten Start:
#    chmod +x MixCoach-Uebungen-Bewerten.command
# ============================================================

set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE="$ROOT/audio-engine/mixcoach-audio-engine"
PY="$ROOT/.venv/bin/python"
export MIXCOACH_DATA_DIR="$ROOT/daten"

# Name des Durchgangs. Wer eine zweite, unabhaengige Runde will, aendert
# ihn - jeder Lauf bekommt eine eigene Datei unter daten/uebungen_bewertung/.
LAUF="${1:-abend1}"
PORT=8000

echo ""
echo "  ==========================================================="
echo "   MixCoach - Welcher Hinweis hilft mehr?"
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

echo "  Starte die Analyse-Engine..."
"$PY" -m uvicorn app.main:app --port "$PORT" --log-level warning &
ENGINE_PID=$!

# Aufraeumen, egal wie das Skript endet - sonst laeuft die Engine weiter.
trap 'kill "$ENGINE_PID" 2>/dev/null' EXIT

for _ in $(seq 1 40); do
  if curl -s -o /dev/null "http://127.0.0.1:$PORT/health"; then break; fi
  sleep 0.5
done

if ! curl -s -o /dev/null "http://127.0.0.1:$PORT/health"; then
  echo "  Die Engine ist nicht hochgekommen. Abbruch."
  read -r -p "  Enter zum Beenden..."
  exit 1
fi

URL="http://127.0.0.1:$PORT/uebungen-bewertung/$LAUF"
echo "  Bereit. Die Seite oeffnet sich jetzt im Browser:"
echo "    $URL"
echo ""
open "$URL"

echo "  Wenn du fertig bist (oder abbrechen willst):"
read -r -p "  Enter druecken - dann wird ausgewertet..."

echo ""
"$PY" -m tools.uebungen_bewertung_auswerten --lauf "$LAUF"
echo ""
read -r -p "  Enter zum Beenden..."
