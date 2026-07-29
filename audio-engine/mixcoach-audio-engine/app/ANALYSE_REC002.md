# Analyse REC002.WAV — v3, kalibriert mit Bastis Ground Truth

*2026-07-02 | Engine mit Trackwechsel-Klassifikator (kalibriert an diesem Set)*

## Kalibrierungs-Ergebnis

| | Vor Kalibrierung | Nach Kalibrierung |
| --- | --- | --- |
| Erkannte Trackwechsel | 34 | 8 |
| Echte gefunden (Recall) | 5/5 | 4/5 |
| Trefferquote (Precision) | 15% | 50% |

Der verpasste Übergang (25:20) wurde von einem Fehlalarm bei 24:10 "verdrängt" — der Mindestabstands-Filter ließ nur einen der beiden zu und wählte den falschen. Bekanntes Problem, steht auf der Fix-Liste.

## Deine Set-Bewertung (ehrliche Zahlen)

| Metrik | Wert | Einordnung |
| --- | --- | --- |
| Overall | 66/100 | solide Basis |
| Tempo | 123 BPM durchgehend | sehr stabil |
| Tempo-Match | 100/100 | Vorbehalt: globales Beat-Raster |
| Phrase-Timing | 39/100 | größtes Verbesserungspotenzial |
| Harmonie | 54/100 | Moll-Nachbarschaften, teils weite Sprünge |
| Energie-Fluss | 69/100 | ordentlich |
| Dominante Tonart | A Minor | |

## Erkannte Trackwechsel

| # | Zeit | Tonart | Beats neben Phrase | Score | Einordnung |
| --- | --- | --- | --- | --- | --- |
| 1 | 00:38 | D Minor → C# Minor | 13.22 | 58 | vermutl. Fehlalarm |
| 2 | 04:54 | C# Minor → A# Minor | 15.64 | 61 | ECHT ✓ |
| 3 | 10:11 | A# Minor → F Minor | 14.69 | 66 | ECHT ✓ |
| 4 | 15:03 | F Minor → A Minor | 5.87 | 70 | ECHT ✓ |
| 5 | 19:19 | A Minor → G Minor | 15.48 | 58 | ECHT ✓ |
| 6 | 24:10 | G Minor → A Minor | 7.58 | 73 | vermutl. Fehlalarm |
| 7 | 28:53 | A Minor → A Minor | 9.58 | 68 | vermutl. Fehlalarm |
| 8 | 31:31 | A Minor → G Minor | 6.12 | 74 | vermutl. Fehlalarm |

## Coaching-Hinweis (mit Vorbehalt)

Das Muster über deine echten Übergänge: Sie liegen im Schnitt ~13 Beats neben der 8-Bar-Phrasengrenze des auslaufenden Tracks. FALLS die Segment-Verankerung stimmt, wäre das der klassische Hinweis: Übergänge bewusst am Phrasenzähler starten (auf die 1 nach 8 Bars). ABER: Die Verankerung ist noch nicht gegen echte Downbeats validiert — nimm die Zahl als Hypothese, nicht als Urteil. Höre einen Übergang nach und prüfe, ob es sich versetzt anfühlt.

## Was als Nächstes die Engine besser macht

1. **Mehr annotierte Sets** — mit n=1 ist die Kalibrierung eine erste Näherung. Jedes weitere Set mit deinen Zeitangaben verbessert die Schwellen. 2-3 weitere Sets wären Gold.
2. **Verdrängungs-Problem fixen**: Bei zwei nahen Kandidaten sollte Harmonie-Wechsel den Ausschlag geben, nicht nur der Kombi-Score.
3. **Downbeat-Validierung** für belastbares Phrase-Timing.