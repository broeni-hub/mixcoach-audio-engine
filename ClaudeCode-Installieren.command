#!/bin/bash
#
# Claude Code auf dem Mac installieren
# -------------------------------------
# Nutzt den offiziellen Installer von Anthropic:
#   https://claude.ai/install.sh
#
# Der Befehl laedt ein Installationsskript von claude.ai und fuehrt es
# aus. Das ist der von Anthropic dokumentierte Weg (Stand 30.07.2026),
# aber du sollst wissen, was passiert, bevor du zustimmst - deshalb
# fragt dieses Skript vorher.
#
# Installiert wird nach ~/.local/bin/claude. Dieser Ordner liegt bei dir
# bereits im PATH (~/.zshrc), der Befehl ist danach also ueberall da.
#

set -u

clear
echo ""
echo "=========================================="
echo "  Claude Code installieren"
echo "=========================================="
echo ""
echo "  Was passiert:"
echo ""
echo "    curl -fsSL https://claude.ai/install.sh | bash"
echo ""
echo "  Das laedt Anthropics Installationsskript und fuehrt es aus."
echo "  Ziel: ~/.local/bin/claude   (liegt schon in deinem PATH)"
echo "  Aendert sonst nichts am System, braucht kein Passwort."
echo ""
echo "  Voraussetzung: ein bezahltes Claude-Konto (Pro, Max, Team oder"
echo "  Enterprise). Mit dem kostenlosen Konto laesst sich Claude Code"
echo "  nicht anmelden."
echo ""
read -r -p "  Installieren? [j/n] " ANTWORT

if [ "$ANTWORT" != "j" ] && [ "$ANTWORT" != "J" ]; then
  echo ""
  echo "  Abgebrochen. Nichts geaendert."
  read -r -p "  Mit [Enter] schliessen ... " _
  exit 0
fi

echo ""
echo "------------------------------------------"
echo "  Installation laeuft"
echo "------------------------------------------"
echo ""

if ! curl -fsSL https://claude.ai/install.sh | bash; then
  echo ""
  echo "  FEHLER bei der Installation (siehe oben)."
  echo "  Bitte den Text kopieren und Claude schicken."
  read -r -p "  Mit [Enter] schliessen ... " _
  exit 1
fi

echo ""
echo "------------------------------------------"
echo "  Kontrolle"
echo "------------------------------------------"
echo ""

CLAUDE="$HOME/.local/bin/claude"

if [ ! -x "$CLAUDE" ]; then
  echo "  Der Installer meldet Erfolg, aber unter"
  echo "    $CLAUDE"
  echo "  liegt nichts Ausfuehrbares. Bitte Claude Bescheid geben."
  read -r -p "  Mit [Enter] schliessen ... " _
  exit 1
fi

echo "  Version:  $("$CLAUDE" --version 2>&1)"
echo ""
echo "  Ausfuehrliche Diagnose:"
"$CLAUDE" doctor 2>&1 | head -20

echo ""
echo "=========================================="
echo "  Fertig"
echo "=========================================="
echo ""
echo "  So geht es weiter:"
echo ""
echo "    1. Doppelklick auf ClaudeCode-Starten.command"
echo "       (oeffnet Claude Code direkt im MixCoach-Ordner)"
echo ""
echo "    2. Beim ersten Mal fragt es nach der Anmeldung."
echo "       Es oeffnet dazu deinen Browser - dort bestaetigen."
echo ""
echo "    3. Dann den Inhalt von PROMPT_SKALIERUNG_2026-07-30.md"
echo "       hineinkopieren (alles unterhalb der ersten Trennlinie)."
echo ""
read -r -p "  Mit [Enter] schliessen ... " _
