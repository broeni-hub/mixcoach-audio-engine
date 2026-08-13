#!/bin/bash
# ============================================================
#  MixCoach-Staemme-Zusammenfuehren: fuehrt die zwei Datenbestaende
#  zu einem zusammen.
#
#  Es gibt zwei Ordner mit Bewertungen und Ergebnissen: den
#  maszgeblichen unter daten/ und einen zweiten im Engine-Ordner.
#  Der zweite ist entstanden, weil MIXCOACH_DATA_DIR zeitweise nicht
#  gesetzt war. In ihm steckt Handarbeit, die im maszgeblichen fehlt.
#
#  Dieses Skript zeigt ERST, was passieren wuerde, und fragt dann.
#  Es loescht nichts. Widerspruechliche Bewertungen werden nicht
#  geraten, sondern in daten/ground_truth/KONFLIKTE.md gesammelt.
# ============================================================

set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE="$ROOT/audio-engine/mixcoach-audio-engine"
export MIXCOACH_DATA_DIR="$ROOT/daten"

echo ""
echo "  ==========================================================="
echo "   MixCoach - die zwei Datenbestaende zusammenfuehren"
echo "  ==========================================================="
echo ""

if [ ! -x "$ROOT/.venv/bin/python" ]; then
  echo "  Kein Python gefunden unter $ROOT/.venv/bin/python"
  echo "  Bitte zuerst MixCoach-Mac-Reparieren.command ausfuehren."
  echo ""
  read -r -p "  Enter zum Beenden..."
  exit 1
fi

echo "  Zuerst die Messlatte VORHER (das dauert einen Moment):"
echo ""
cd "$ENGINE" || exit 1
"$ROOT/.venv/bin/python" -m tools.analyze_timing_bias 2>/dev/null \
  | grep -E "Recall|Precision|Sigma|bewertete Transitions|missed" \
  | sed 's/^/    /'

echo ""
echo "  -----------------------------------------------------------"
echo "   Das wuerde passieren:"
echo "  -----------------------------------------------------------"
"$ROOT/.venv/bin/python" -m tools.staemme_zusammenfuehren | sed 's/^/  /'

echo ""
echo "  -----------------------------------------------------------"
echo ""
echo "  Nichts davon ist bisher geschrieben worden."
echo ""
read -r -p "  Soll das jetzt so ausgefuehrt werden? (ja/nein) " ANTWORT
echo ""

case "$ANTWORT" in
  ja|Ja|JA|j|J)
    "$ROOT/.venv/bin/python" -m tools.staemme_zusammenfuehren --write | sed 's/^/  /'
    echo ""
    echo "  Und die Messlatte NACHHER:"
    echo ""
    "$ROOT/.venv/bin/python" -m tools.analyze_timing_bias 2>/dev/null \
      | grep -E "Recall|Precision|Sigma|bewertete Transitions|missed" \
      | sed 's/^/    /'
    echo ""
    echo "  Aendert sich Recall, liegt das an zusaetzlich gefundenen"
    echo "  Bewertungen: die Messlatte wird laenger, nicht die Erkennung"
    echo "  schlechter."
    echo ""
    if [ -f "$ROOT/daten/ground_truth/KONFLIKTE.md" ]; then
      echo "  WICHTIG: Es gibt widerspruechliche Bewertungen. Sie stehen in"
      echo "    daten/ground_truth/KONFLIKTE.md"
      echo "  und warten auf deine Entscheidung. Bis dahin gilt der Stand"
      echo "  aus daten/."
      echo ""
    fi
    ;;
  *)
    echo "  Abgebrochen. Es wurde nichts geaendert."
    echo ""
    ;;
esac

read -r -p "  Enter zum Beenden..."
