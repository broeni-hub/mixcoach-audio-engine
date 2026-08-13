# Zweiter Stamm, archiviert am 13.08.2026

Hier lag bis zum 13.08.2026 ein zweiter Satz Ergebnisse und
Bewertungen, parallel zum maszgeblichen Stamm in `daten/`.
Entstanden ist er, weil `MIXCOACH_DATA_DIR` nicht gesetzt war:
`app/paths.py` faellt dann auf den Engine-Ordner zurueck, und die
App legt Library, Ergebnisse und Ground Truth am falschen Ort ab.

Inhalt: 93 Analyse-Reports, 24 Bewertungen.

**Der Inhalt ist nicht verloren, sondern eingearbeitet.** Die
abweichenden Bewertungen wurden mit `daten/ground_truth/`
vereinigt (`tools/staemme_zusammenfuehren.py`); widersprechende
Urteile stehen in `daten/ground_truth/KONFLIKTE.md` und warten auf
eine Entscheidung.

Dieser Ordner wird nicht mehr gelesen. Er bleibt liegen, damit die
Zusammenfuehrung nachpruefbar ist. Wer ihn loeschen will, sollte
vorher KONFLIKTE.md abgearbeitet haben.

Die Audiodateien (`*.wav`) waren nie versioniert (.gitignore) und
sind hier nicht mitgezogen worden.