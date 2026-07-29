# Analyse REC013.WAV — Validierung auf ungesehenem Set

*2026-07-02 | Klassifikator kalibriert an REC002, hier zum ersten Mal validiert*

## Validierungs-Ergebnis

| | Roh-Detektor | Klassifikator |
| --- | --- | --- |
| Gemeldete Trackwechsel | 33 | 8 |
| Echte gefunden | 6/6 | 6/6 (Fenster −30/+60s) |
| Fehlalarme | 27 | 2 |

Hinweis zum Zeitfenster: Deine Angaben ("ab ca.") markieren den Blend-START, die Engine das Blend-ZENTRUM. Drei Treffer liegen 34–53s nach deiner Zeit — das passt zu 30–60s langen Blends. Bitte einmal gegenchecken (z.B. 15:25: läuft der Blend bis ~16:00?).

## Set-Bewertung

| Metrik | REC013 | REC002 (Vergleich) |
| --- | --- | --- |
| Overall | 73/100 | 66/100 |
| Phrase-Timing | 58/100 | 39/100 |
| Harmonie | 62/100 | 54/100 |
| Energie-Fluss | 69/100 | 69/100 |
| Tempo | 123 BPM | 123 BPM |
| Tonart | A Minor | A Minor |

## Erkannte Trackwechsel

| # | Zeit | Tonart | Beats neben Phrase | Score | Abgleich |
| --- | --- | --- | --- | --- | --- |
| 1 | 03:52 | G Minor → D Major | 0.5 | 82 | ECHT ✓ |
| 2 | 06:35 | D Major → C# Minor | 13.25 | 62 | ECHT ✓ |
| 3 | 09:28 | C# Minor → B Minor | 6.89 | 73 | ECHT ✓ |
| 4 | 15:59 | B Minor → G Minor | 13.75 | 58 | ECHT ✓ |
| 5 | 19:29 | G Minor → A Minor | 10.38 | 62 | ECHT ✓ |
| 6 | 22:19 | A Minor → A Minor | 1.52 | 92 | vermutl. Fehlalarm |
| 7 | 25:12 | A Minor → A Minor | 6.83 | 75 | ECHT ✓ |
| 8 | 29:04 | A Minor → E Minor | 2.66 | 90 | vermutl. Fehlalarm |

## Kalibrierungs-Stand (2 annotierte Sets)

Über beide Sets: Recall 10/11 echten Übergängen (91%), Precision 10/16 (63%) — gestartet waren wir bei 16% Precision. Neu aus diesem Set gelernt: Zonen in den ersten 90s / letzten 60s eines Sets sind nie Trackwechsel (Intro-Filter, in beiden Sets bestätigt). Bekannte offene Schwäche: In REC002 verdrängt ein Fehlalarm (24:10) den echten Übergang bei 25:20.