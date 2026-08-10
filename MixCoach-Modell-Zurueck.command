#!/bin/bash
# ============================================================
#  MixCoach-Modell-Zurueck: macht das letzte Training rueckgaengig
#  und stellt das VORHERIGE Modell wieder her.
#
#  Nutzt die Sicherung track_change_gbm.json.backup, die bei jedem
#  Training angelegt wird. Das aktuelle Modell wird vorher als
#  .aktuell weggelegt - du kommst also in beide Richtungen zurueck.
# ============================================================

set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS="$ROOT/audio-engine/mixcoach-audio-engine/app/models"
CUR="$MODELS/track_change_gbm.json"
BAK="$MODELS/track_change_gbm.json.backup"

echo ""
echo "  ==========================================================="
echo "   MixCoach - vorheriges Modell zurueckholen"
echo "  ==========================================================="
echo ""

if [ ! -f "$BAK" ]; then
  echo "  Kein Backup gefunden unter"
  echo "    $BAK"
  echo "  Es gibt nichts zum Zuruecksetzen."
  echo ""
  read -r -p "  Enter zum Beenden..."
  exit 0
fi

# Betriebspunkt beider Staende zeigen, damit klar ist, was getauscht wird.
zeige() {
  "$ROOT/.venv/bin/python" - "$1" <<'PY' 2>/dev/null || echo "    (nicht lesbar)"
import json, sys
d = json.load(open(sys.argv[1]))
s = d.get("selection", {})
v = d.get("loso_validation", {})
print(f"    min_p={s.get('min_probability')}  gap={s.get('min_gap_seconds')}s"
      f"  F1={v.get('f1')}  R={v.get('recall')}  P={v.get('precision')}")
PY
}

echo "  AKTUELL aktiv:"
zeige "$CUR"
echo "  Das Backup davor:"
zeige "$BAK"
echo ""
read -r -p "  Wirklich zurueckholen? [j/N] " ANTWORT
case "${ANTWORT:-n}" in
  j|J|y|Y) ;;
  *) echo ""; echo "  Abgebrochen, nichts geaendert."; echo ""
     read -r -p "  Enter zum Beenden..."; exit 0 ;;
esac

cp -f "$CUR" "$CUR.aktuell" && echo "  Aktuelles Modell gesichert als .aktuell"
cp -f "$BAK" "$CUR" && echo "  Vorheriges Modell wiederhergestellt"

echo ""
echo "  Fertig. Jetzt die Engine neu starten (MixCoach-Start-Mac.command),"
echo "  damit das zurueckgeholte Modell geladen wird."
echo ""
read -r -p "  Enter zum Beenden..."
