#!/bin/bash
#
# MixCoach - Ist die Musik vollstaendig auf dem Mac?
# --------------------------------------------------
# Schaut nur nach und sagt Bescheid. Aendert NICHTS.
# Doppelklicken, sooft du magst.
#

set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE="$ROOT/audio-engine/mixcoach-audio-engine"
DATEN="$ROOT/daten"
PY="$ROOT/.venv/bin/python"
MUSIK="$HOME/Music"
ALT_ROOT="C:/Users/Sebro/Music"

export MIXCOACH_DATA_DIR="$DATEN"

clear
echo ""
echo "=========================================="
echo "  Musik-Check   $(date '+%d.%m.%Y  %H:%M')"
echo "=========================================="
echo ""

if [ ! -x "$PY" ]; then
  echo "  FEHLER: Python-Umgebung fehlt unter $PY"
  read -r -p "  Enter zum Beenden ... " _
  exit 1
fi

# --- Laeuft gerade noch ein Kopiervorgang? --------------------------------
NEU="$(find "$MUSIK" -type d -newermt '-5 minutes' 2>/dev/null | wc -l | tr -d ' ')"
AUDIO="$(find "$MUSIK" -type f \( -iname '*.mp3' -o -iname '*.wav' -o -iname '*.aiff' \
         -o -iname '*.flac' -o -iname '*.m4a' \) 2>/dev/null | wc -l | tr -d ' ')"

echo "  Audiodateien in $MUSIK:  $AUDIO"
if [ "$NEU" -gt 0 ]; then
  echo "  Ordner in den letzten 5 Minuten geschrieben:  $NEU"
  echo "  -> Es wird offenbar noch kopiert."
  echo ""
  echo "  Zuletzt beschriebene Stellen:"
  find "$MUSIK" -type d -newermt '-5 minutes' 2>/dev/null | head -5 | sed "s|$MUSIK|  ~/Music|"
else
  echo "  In den letzten 5 Minuten wurde nichts geschrieben."
  echo "  -> Es laeuft vermutlich kein Kopiervorgang mehr."
fi

# --- Wie viel vom Index ist auffindbar? -----------------------------------
echo ""
echo "------------------------------------------"
echo "  Abgleich mit dem Library-Index"
echo "------------------------------------------"
echo ""

cd "$ENGINE" || exit 1

if ! grep -q "C:/Users/Sebro" "$DATEN/library/index.json" 2>/dev/null; then
  echo "  Der Index ist bereits auf den Mac umgestellt."
  echo "  Hier ist nichts mehr zu tun."
  echo ""
  read -r -p "  Mit [Enter] schliessen ... " _
  exit 0
fi

"$PY" -m tools.repath_library_index \
    --old-root "$ALT_ROOT" --new-root "$MUSIK" --dry-run \
    > /tmp/mixcoach-musikcheck.log 2>&1

sed -n '/Eintraege gesamt/,/Plan ohne/p' /tmp/mixcoach-musikcheck.log

echo ""
echo "------------------------------------------"
if grep -q "STOPP" /tmp/mixcoach-musikcheck.log; then
  echo "  NOCH NICHT SO WEIT."
  echo ""
  echo "  Unter 95 % der Tracks sind auffindbar. Warten,"
  echo "  bis das Kopieren durch ist, dann nochmal pruefen."
  echo ""
  echo "  Beispiele fuer Stellen, die noch fehlen:"
  grep "fehlt:" /tmp/mixcoach-musikcheck.log \
    | sed "s|.*$ALT_ROOT/||; s|/[^/]*$||" \
    | cut -d/ -f1-2 | sort -u | head -6 \
    | sed 's/^/      ~\/Music\//'
else
  echo "  BEREIT."
  echo ""
  echo "  Genug Tracks sind auffindbar. Naechster Schritt:"
  echo "  Doppelklick auf MixCoach-Mac-Reparieren.command"
fi
echo "------------------------------------------"
echo ""
read -r -p "  Mit [Enter] schliessen ... " _
