#!/bin/bash
#
# Claude Code im MixCoach-Ordner starten
# ---------------------------------------
# Doppelklick genuegt. Setzt MIXCOACH_DATA_DIR und wechselt in den
# Projektstamm, damit Claude Code CLAUDE.md und die Daten findet.
#

set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE="$HOME/.local/bin/claude"

export MIXCOACH_DATA_DIR="$ROOT/daten"

if [ ! -x "$CLAUDE" ]; then
  # Vielleicht liegt es woanders im PATH (Homebrew, npm)
  if command -v claude >/dev/null 2>&1; then
    CLAUDE="$(command -v claude)"
  else
    echo ""
    echo "  Claude Code ist nicht installiert."
    echo "  Doppelklick auf ClaudeCode-Installieren.command."
    echo ""
    read -r -p "  Mit [Enter] schliessen ... " _
    exit 1
  fi
fi

cd "$ROOT" || exit 1

echo ""
echo "  Projektordner:    $ROOT"
echo "  MIXCOACH_DATA_DIR gesetzt"
echo "  Claude Code:      $("$CLAUDE" --version 2>&1)"
echo ""
echo "  Zum Beenden in Claude Code: /exit"
echo ""

exec "$CLAUDE"
