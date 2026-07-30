# Claude-Code-Verlauf auf das MacBook übertragen

*Ergänzung zur UEBERTRAGUNG-ANLEITUNG — erstellt am 30.07.2026*

## Warum das nötig ist

Das Backup-Skript `MixCoach-Backup-Erstellen.bat` kopiert nur den Ordner
`C:\Projekte\Projekte\MixCoach`.

Der Chatverlauf von Claude Code liegt aber woanders:

    C:\Users\Sebro\.claude\projects\

Er war deshalb **nie Teil der Übertragung**. Das erklärt, warum auf dem MacBook
der bisherige Gesprächsverlauf fehlt.

**Nicht betroffen** (kommt über Dein Claude-Konto automatisch mit):

- Das MixCoach-Projektwissen inkl. `PROJEKTSTAND-CLAUDE.md` und der bisherigen Erkenntnisse
- Die Chats aus der Claude-Desktop-App

## Schritt 1 — Auf diesem PC sichern

Doppelklick auf `MixCoach-ClaudeCode-Verlauf-Sichern.bat`.

Danach liegt der Verlauf unter `C:\Projekte\Projekte\MixCoach\claude-code-verlauf\`
und wird beim nächsten Backup automatisch mitkopiert.

## Schritt 2 — Ordner auf den Mac bringen

USB-Stick, Netzwerk oder Cloud — wie in der Haupt-Anleitung.

## Schritt 3 — Auf dem MacBook einsetzen

Das ist der Punkt, an dem es leicht schiefgeht: **Claude Code findet einen Verlauf
nur, wenn der Ordnername exakt zum Projektpfad passt.** Der Ordnername ist der
Projektpfad, bei dem alle `\` `/` und `:` durch `-` ersetzt wurden.

Auf diesem PC heißt der Ordner deshalb:

    C--Projekte-Projekte-MixCoach

Auf dem Mac liegt das Projekt an einem anderen Pfad. Liegt es dort z.B. unter
`/Users/sebro/Projekte/MixCoach`, muss der Ordner umbenannt werden in:

    -Users-sebro-Projekte-MixCoach

**Vorgehen:**

1. Im Finder `Cmd + Shift + G` drücken, `~/.claude/projects` eingeben, Enter.
   (Existiert der Ordner nicht, einmal Claude Code im Projekt starten — dann wird er angelegt.)
2. Den Ordner `C--Projekte-Projekte-MixCoach` vom Stick dort hineinkopieren.
3. Den kopierten Ordner passend zum Mac-Pfad umbenennen (siehe oben).

## Schritt 4 — Prüfen

Im Terminal in den Projektordner wechseln und Claude Code starten, dann:

    /resume

Die alten Sitzungen sollten in der Liste erscheinen. Falls die Liste leer bleibt,
stimmt fast immer der Ordnername nicht — Schritt 3 nochmal prüfen.

## Falls der alte Rechner nicht mehr erreichbar ist

Dann ist der Verlauf verloren, aber nicht der Projektstand: `PROJEKTSTAND-CLAUDE.md`
und `MixCoach_bisherige_Erkenntnisse_Code_Review.md` liegen im Projektwissen und
sind auf dem Mac verfügbar. Einer neuen Claude-Code-Sitzung genügt:

    lies PROJEKTSTAND-CLAUDE.md

Damit ist der inhaltliche Stand wiederhergestellt — nur die Gesprächshistorie fehlt.
