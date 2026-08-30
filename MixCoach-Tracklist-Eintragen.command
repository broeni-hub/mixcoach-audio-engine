#!/bin/bash
# ============================================================
#  MixCoach-Tracklist-Eintragen: Tracknamen aus der Liste des DJs
#
#  WOFUER
#  Ein fremder DJ bekommt heute NULL Tracknamen im Report. Das ist
#  keine Panne, sondern Bauart: der Fingerabdruck-Index kennt 6113
#  Tracks - deine. Seine Tracks kennt er nicht, also steht im Report
#  neunmal "Uebergang 7" statt "Amelie Lens -> FJAAK".
#
#  Statt ihn zu bitten, seine ganze Sammlung hochzuladen, bittest du
#  ihn um seine TRACKLIST. Eine Datei statt dreihundert.
#
#  DAS FORMAT - eine Zeile je Track, in Set-Reihenfolge:
#
#    00:00 Amelie Lens - In My Mind        <- MIT ZEITEN ist viel
#    05:42 FJAAK - Gravel                     besser: es geht dann
#    09:10 Or:la - Mineral Fever              auch, wenn die Engine
#                                             einen Uebergang uebersieht
#    1. Amelie Lens - In My Mind           <- NUR REIHENFOLGE geht nur,
#    2. FJAAK - Gravel                        wenn die Zahlen passen
#    3. Or:la - Mineral Fever                 (n Tracks, n-1 Uebergaenge)
#
#  Erkannt werden [05:42], 05:42, 5.42 und fuehrende Nummerierungen.
#
#  WAS NICHT PASSIERT
#  Wo der Fingerabdruck schon einen Treffer hat, bleibt der stehen -
#  gemessen schlaegt genannt. Und wenn ohne Zeiten die Zahlen nicht
#  zusammenpassen, wird NICHTS zugeordnet: nach Position zu raten
#  wuerde alle folgenden Namen um eins verschieben.
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
echo "   MixCoach - Tracklist eintragen"
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

echo "  Die letzten Analysen:"
echo ""
"$PY" - <<'PYEOF'
import json, os
from pathlib import Path
ordner = Path(os.environ["MIXCOACH_DATA_DIR"]) / "analysis_results"
eintraege = []
for p in ordner.glob("*.json"):
    try: d = json.loads(p.read_text(encoding="utf-8"))
    except Exception: continue
    if not d.get("setTransitions"): continue
    mit = sum(1 for t in d["setTransitions"] if t.get("track_in") or t.get("track_out"))
    eintraege.append((d.get("createdAt") or "", d.get("id"), d.get("fileName"),
                      len(d["setTransitions"]), mit))
for _, aid, name, n, mit in sorted(eintraege, reverse=True)[:12]:
    print(f"    {aid}   {str(name)[:38]:<38} {n:>3} Uebergaenge, {mit:>3} mit Namen")
PYEOF
echo ""
read -r -p "  Analyse-ID: " AID
[ -z "${AID:-}" ] && { echo "  Abgebrochen."; read -r -p "  Enter..."; exit 0; }
echo ""
echo "  Pfad zur Tracklist-Datei (oder die Datei ins Fenster ziehen):"
read -r -p "  Datei: " DATEI
DATEI="${DATEI%\'}"; DATEI="${DATEI#\'}"; DATEI="$(echo "$DATEI" | xargs)"
[ -f "$DATEI" ] || { echo "  Datei nicht gefunden: $DATEI"; read -r -p "  Enter..."; exit 1; }

echo ""
echo "  Das wuerde eingetragen (es wird noch NICHTS geschrieben):"
echo ""
"$PY" -m tools.tracklist_nachtragen "$AID" "$DATEI"
echo ""

read -r -p "  Wirklich schreiben? [j/N] " ANTWORT
case "${ANTWORT:-n}" in
  j|J|y|Y) ;;
  *) echo ""; echo "  Abgebrochen, nichts geaendert."; echo ""
     read -r -p "  Enter zum Beenden..."; exit 0 ;;
esac

echo ""
"$PY" -m tools.tracklist_nachtragen "$AID" "$DATEI" --write
echo ""
echo "  Fertig. Der Report im Browser zeigt die Namen nach dem Neuladen -"
echo "  die reportRevision wurde hochgezaehlt."
echo ""
read -r -p "  Enter zum Beenden..."
