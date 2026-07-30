#!/bin/bash
# ============================================================
#  MixCoach-Start (macOS) - Gegenstueck zu MixCoach-Start.bat
#
#  Startet Analyse-Engine (Port 8000) + Web-App (Port 8080)
#  in zwei eigenen Terminal-Fenstern und oeffnet den Browser.
#  Beide Fenster offen lassen, solange MixCoach benutzt wird.
#
#  EINMALIG vor dem ersten Start noetig:
#    chmod +x MixCoach-Start-Mac.command
#  Danach genuegt ein Doppelklick im Finder.
# ============================================================

# Projektordner = der Ordner, in dem diese Datei liegt.
# Dadurch ist der Pfad NICHT fest verdrahtet - egal wo das
# Projekt auf dem Mac liegt, es funktioniert.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ENGINE="$ROOT/audio-engine/mixcoach-audio-engine"
FRONTEND="$ROOT/Frontend"
DATEN="$ROOT/daten"
PY="$ROOT/.venv/bin/python"

echo ""
echo "  MixCoach wird gestartet..."
echo "  Projektordner: $ROOT"
echo ""

if [ ! -d "$ENGINE" ]; then
  echo "  FEHLER: $ENGINE nicht gefunden."
  echo "  Liegt diese Datei wirklich im MixCoach-Hauptordner?"
  read -r -p "  Enter zum Beenden..."
  exit 1
fi

# Die Engine braucht Python 3.12 aus .venv im Projektstamm.
# Ohne diese Pruefung wuerde sie stillschweigend mit Apples
# Python 3.9 starten - und daran scheitert app/main.py.
if [ ! -x "$PY" ]; then
  echo "  FEHLER: Python-Umgebung nicht gefunden unter"
  echo "    $PY"
  echo "  Bitte zuerst MixCoach-Mac-Reparieren.command ausfuehren."
  read -r -p "  Enter zum Beenden..."
  exit 1
fi

# --- 1) Analyse-Engine in neuem Terminal-Fenster ---
osascript <<EOF
tell application "Terminal"
  do script "cd '$ENGINE' && export MIXCOACH_DATA_DIR='$DATEN' && echo '[MixCoach Engine] Port 8000 - Fenster offen lassen.' && '$PY' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
  activate
end tell
EOF

# --- 2) Web-App in neuem Terminal-Fenster ---
osascript <<EOF
tell application "Terminal"
  do script "cd '$FRONTEND' && echo '[MixCoach App] Port 8080 - Fenster offen lassen.' && npm run dev"
end tell
EOF

# --- 3) Warten, dann Browser oeffnen ---
echo "  Warte 12 Sekunden, bis beide Dienste hochgefahren sind..."
sleep 12
open "http://localhost:8080/app/analyses"

echo ""
echo "  Fertig! Die App ist im Browser geoeffnet."
echo "  Falls die Seite noch laedt: kurz warten und neu laden (Cmd+R)."
echo ""
echo "  Dieses Fenster kann geschlossen werden - die beiden"
echo "  anderen offen lassen."
