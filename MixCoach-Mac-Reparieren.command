#!/bin/bash
#
# MixCoach - Reparatur nach dem Ordner-Umzug (macOS)
# ---------------------------------------------------
# Behebt vier Dinge:
#   1. MIXCOACH_DATA_DIR in ~/.zshrc zeigt auf den alten Ordner
#   2. Dateirechte, falls noetig (fragt dann nach dem Mac-Passwort)
#   3. Library-Index: Windows-Pfade -> Musikordner auf dem Mac
#   4. Frontend-Pakete neu installieren (die alten sind fuer Windows)
#
# Vor jedem Schreiben wird gesichert. Nichts wird geloescht,
# ausser den Windows-Paketen im Frontend (die npm neu holt).
# Das Skript kann gefahrlos mehrfach laufen.
#

set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE="$ROOT/audio-engine/mixcoach-audio-engine"
DATEN="$ROOT/daten"
PY="$ROOT/.venv/bin/python"
MUSIK="$HOME/Music"
ALT_ROOT="C:/Users/Sebro/Music"

FEHLER=0
STAND=""

trenner() {
  echo ""
  echo "=========================================="
  echo "  $1"
  echo "=========================================="
}

merke() { STAND="$STAND
  $1"; }

clear
echo ""
echo "=========================================="
echo "  MixCoach - Reparatur nach dem Umzug"
echo "=========================================="
echo ""
echo "  Projektordner:  $ROOT"
echo "  Musikordner:    $MUSIK"
echo ""
echo "  Vier Schritte. Vor dem Schreiben wird jeweils gefragt."
echo "  Dauer: ueberwiegend Schritt 4 (npm), ca. 2-5 Minuten."
echo ""
read -r -p "  Weiter mit [Enter], Abbruch mit [Strg]+[C] ... " _

# --- 0. Grundcheck --------------------------------------------------------
trenner "0/4  Grundcheck"

if [ ! -x "$PY" ]; then
  echo "  FEHLER: Python-Umgebung fehlt unter"
  echo "    $PY"
  echo "  Ohne sie geht nichts weiter."
  read -r -p "  Enter zum Beenden ... " _
  exit 1
fi
echo "  OK   Python:  $("$PY" -V 2>&1)"

if [ ! -d "$DATEN/library" ]; then
  echo "  FEHLER: $DATEN/library fehlt."
  read -r -p "  Enter zum Beenden ... " _
  exit 1
fi
echo "  OK   Daten:   $DATEN"

if [ ! -d "$MUSIK" ]; then
  echo "  FEHLER: Musikordner $MUSIK fehlt."
  read -r -p "  Enter zum Beenden ... " _
  exit 1
fi
echo "  OK   Musik:   $MUSIK"

# --- 1. MIXCOACH_DATA_DIR in ~/.zshrc -------------------------------------
trenner "1/4  Datenpfad in ~/.zshrc"

ZSHRC="$HOME/.zshrc"
SOLL="export MIXCOACH_DATA_DIR=\"$DATEN\""

if [ ! -f "$ZSHRC" ]; then
  echo "$SOLL" > "$ZSHRC"
  echo "  ~/.zshrc neu angelegt."
  merke "Datenpfad: neu eingetragen"
elif grep -Fq "MIXCOACH_DATA_DIR=\"$DATEN\"" "$ZSHRC"; then
  echo "  OK - zeigt schon auf den richtigen Ordner."
  merke "Datenpfad: war bereits korrekt"
else
  cp "$ZSHRC" "$ZSHRC.bak-$(date +%Y%m%d-%H%M%S)"
  echo "  Sicherung angelegt: $ZSHRC.bak-..."
  echo "  Alt:"
  grep -n "MIXCOACH_DATA_DIR" "$ZSHRC" | sed 's/^/       /'
  # alte Zeile(n) raus, neue rein
  grep -v "MIXCOACH_DATA_DIR" "$ZSHRC" > "$ZSHRC.tmp" && mv "$ZSHRC.tmp" "$ZSHRC"
  echo "$SOLL" >> "$ZSHRC"
  echo "  Neu:"
  echo "       $SOLL"
  merke "Datenpfad: korrigiert"
fi
export MIXCOACH_DATA_DIR="$DATEN"

# --- 2. Dateirechte -------------------------------------------------------
trenner "2/4  Dateirechte"

FREMD="$(find "$ROOT" -maxdepth 3 ! -user "$(id -un)" -print -quit 2>/dev/null)"

if [ -z "$FREMD" ]; then
  echo "  OK - alles gehoert dir, nichts zu tun."
  merke "Dateirechte: waren in Ordnung"
else
  echo "  Es gibt Dateien, die dir nicht gehoeren, z.B.:"
  echo "    $FREMD"
  echo ""
  echo "  Ohne Korrektur bricht die Frontend-Installation mit"
  echo "  'permission denied' ab."
  echo ""
  echo "  Der Befehl lautet:"
  echo "    sudo chown -R $(id -un):staff \"$ROOT\""
  echo ""
  echo "  Du wirst nach deinem Mac-Passwort gefragt."
  echo "  Beim Tippen erscheinen KEINE Zeichen - das ist normal."
  echo "  Bei 24 GB kann das ein paar Minuten dauern."
  echo ""
  read -r -p "  Ausfuehren? [j/n] " ANTWORT
  if [ "$ANTWORT" = "j" ] || [ "$ANTWORT" = "J" ]; then
    if sudo chown -R "$(id -un):staff" "$ROOT"; then
      echo "  Erledigt."
      merke "Dateirechte: korrigiert"
    else
      echo "  FEHLER beim Setzen der Rechte."
      FEHLER=1
      merke "Dateirechte: FEHLGESCHLAGEN"
    fi
  else
    echo "  Uebersprungen - Schritt 4 wird vermutlich scheitern."
    merke "Dateirechte: uebersprungen"
  fi
fi

# --- 3. Library-Index repathen --------------------------------------------
trenner "3/4  Library-Index auf den Mac umschreiben"

cd "$ENGINE" || exit 1

if grep -q "C:/Users/Sebro" "$DATEN/library/index.json" 2>/dev/null; then
  echo "  Der Index enthaelt noch Windows-Pfade. Erst der Probelauf:"
  echo ""
  "$PY" -m tools.repath_library_index \
      --old-root "$ALT_ROOT" --new-root "$MUSIK" --dry-run \
      > /tmp/mixcoach-repath-probe.log 2>&1
  cat /tmp/mixcoach-repath-probe.log

  if grep -q "STOPP" /tmp/mixcoach-repath-probe.log; then
    echo ""
    echo "  ------------------------------------------------------"
    echo "  ABBRUCH - der Probelauf sagt Nein, und das gilt."
    echo ""
    echo "  Es sind noch nicht genug Musikdateien am Platz"
    echo "  (unter 95 %). Typischer Grund: der Kopiervorgang"
    echo "  von der alten Platte laeuft noch."
    echo ""
    echo "  Was tun: warten, bis das Kopieren fertig ist, dann"
    echo "  MixCoach-Musik-Pruefen.command doppelklicken."
    echo "  Sobald das gruen meldet, dieses Skript nochmal starten."
    echo ""
    echo "  Der Index bleibt solange unveraendert - das ist gut,"
    echo "  ein zu frueher Lauf wuerde Tracks aus der Library werfen."
    echo "  ------------------------------------------------------"
    merke "Library-Index: noch nicht dran (Musik unvollstaendig)"
    ANTWORT="n"
  else
    echo ""
    echo "  Probelauf sieht gut aus (ueber 95 %, keine Kollisionen)."
    echo ""
    echo "  (Vor dem Schreiben legt das Werkzeug selbst eine"
    echo "   Sicherung index.json.bak-<Zeitstempel> an.)"
    echo ""
    read -r -p "  Jetzt umschreiben? [j/n] " ANTWORT
  fi

  if [ "$ANTWORT" = "j" ] || [ "$ANTWORT" = "J" ]; then
    if "$PY" -m tools.repath_library_index \
            --old-root "$ALT_ROOT" --new-root "$MUSIK"; then
      echo ""
      echo "  --- Nachmessen ---"
      "$PY" -m tools.repath_library_index --old-root x --new-root x --verify
      merke "Library-Index: umgeschrieben"
    else
      echo "  FEHLER beim Umschreiben."
      FEHLER=1
      merke "Library-Index: FEHLGESCHLAGEN"
    fi
  fi
else
  echo "  OK - keine Windows-Pfade mehr im Index."
  "$PY" -m tools.repath_library_index --old-root x --new-root x --verify 2>/dev/null | tail -12
  merke "Library-Index: war bereits umgestellt"
fi

# --- 4. Frontend-Pakete ---------------------------------------------------
trenner "4/4  Frontend-Pakete"

cd "$ROOT/Frontend" || exit 1

if [ -d node_modules/esbuild ] && [ -d node_modules/vite ]; then
  echo "  OK - die Pakete sind schon passend installiert."
  echo "  (esbuild ist da, das war der Windows-Stolperstein.)"
  merke "Frontend: war bereits in Ordnung"
  ANTWORT="n"
else
  echo "  Die mitkopierten Pakete stammen vom Windows-Rechner und"
  echo "  funktionieren hier nicht. npm holt sie passend neu."
  echo "  Das dauert 2-5 Minuten."
  echo ""
  read -r -p "  Jetzt neu installieren? [j/n] " ANTWORT
fi

if [ "$ANTWORT" = "j" ] || [ "$ANTWORT" = "J" ]; then
  rm -rf node_modules
  if npm ci; then
    echo "  Erledigt."
    merke "Frontend: Pakete neu installiert"
  else
    echo "  FEHLER bei npm ci (siehe oben)."
    FEHLER=1
    merke "Frontend: FEHLGESCHLAGEN"
  fi
else
  echo "  Uebersprungen."
  merke "Frontend: uebersprungen"
fi

# --- Abschluss: Testlauf --------------------------------------------------
trenner "Kontrolle"

cd "$ENGINE" || exit 1

echo "  Testsuite (dauert kurz) ..."
"$PY" -m pytest tests/ -q > /tmp/mixcoach-pytest.log 2>&1
PYTEST_CODE=$?
tail -5 /tmp/mixcoach-pytest.log
if [ "$PYTEST_CODE" -eq 0 ]; then
  merke "Testsuite: alle gruen"
else
  merke "Testsuite: NICHT gruen (siehe oben)"
  FEHLER=1
fi

echo ""
echo "  Referenzmetrik der Erkennung ..."
"$PY" -m tools.analyze_timing_bias --check 2>&1 | tail -8

# --- Zusammenfassung ------------------------------------------------------
trenner "Zusammenfassung"
echo "$STAND"
echo ""
if [ "$FEHLER" -eq 0 ]; then
  echo "  Durchgelaufen. Naechster Schritt:"
  echo "  Doppelklick auf MixCoach-Start-Mac.command"
else
  echo "  Es gab Probleme (oben mit FEHLER markiert)."
  echo "  Bitte den Text aus diesem Fenster kopieren und Claude schicken."
fi
echo ""
read -r -p "  Mit [Enter] schliessen ... " _
