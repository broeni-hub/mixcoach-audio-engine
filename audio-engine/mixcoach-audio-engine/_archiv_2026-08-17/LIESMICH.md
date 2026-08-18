# Toter Vorfahr, archiviert am 17.08.2026

Hier liegt `app/experimental/` — 39 Python-Dateien, die von **keiner Datei
außerhalb importiert werden**. Vor dem Verschieben nachgemessen, und zwar
breiter als beim letzten Mal, weil ein Grep in diesem Projekt schon zweimal
Treffer übersehen hat:

- keine Importe in `app/`, `tools/`, `tests/`
- der Ordnername kommt sonst nur in Dokumentation vor, in keiner
  `.command`-Datei, keiner Konfiguration, keinem Frontend-Modul
- keine dynamischen Importe (`importlib`) und keine `sys.path`-Eintragung,
  die auf diesen Ordner zeigt — die vorhandenen fügen alle nur den
  Engine-Stamm hinzu
- `detect_transition_zones` wird ausschließlich hier **definiert**, nirgends
  gerufen

## Warum das wichtig war

`CLAUDE.md` hat diesen Ordner an drei Stellen als die lebende
Kandidatensuche geführt — in der Projektkarte und zweimal in der Diagnose zur
Zeitabweichung. Jeder Leser, der der Karte folgte, landete auf einem
46-Zeiler, der seit Wochen niemanden interessiert.

## Wo die Sache wirklich passiert

`app/audio/set_analyzer_helpers.py`, Funktion
`detect_set_transition_zones()` — 351 Zeilen, mit drei Bewertungsfunktionen
für Blend, Drop und Bass-Swap.

**Die Diagnose in `CLAUDE.md` bleibt inhaltlich richtig:** auch die lebende
Fassung sucht eine RMS-Delle, und das ist im DJ-Mix der Breakdown vor dem
Drop — also das *Ende* des Blends, während der Mensch den *Anfang* labelt.
Daran ändert dieser Umzug nichts, und σ = 54,58 s bleibt die Zahl, an der
sich jede Änderung messen lassen muss.

Was die alte Formulierung allerdings unterzeichnet hat: die lebende Fassung
ist erheblich differenzierter als der archivierte Vorfahr. Sie glättet die
RMS-Kurve (gleitender Mittelwert, Fenster 7) und vergleicht drei Fenster
gegeneinander (vorher / Mitte / nachher), statt nur eine normierte Kurve
abzuschreiten. Das ist als Beobachtung notiert, nicht als neue Diagnose —
für eine andere Aussage über die Ursache der Verspätung bräuchte es eine
Messung, und die steht hier nicht dahinter.

## Warum nicht gelöscht

Dasselbe wie beim Archiv vom 13.08.: Der Ordner wird nicht mehr gelesen,
bleibt aber liegen, damit nachvollziehbar ist, was hier stand. Wer ihn
löschen will, kann das gefahrlos tun — die Prüfung oben ist der Beleg.
