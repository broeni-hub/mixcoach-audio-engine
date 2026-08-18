# Widersprechende Bewertungen aus der Stamm-Zusammenfuehrung

Erzeugt am 13.08.2026 von `tools/staemme_zusammenfuehren.py`.
**Entschieden am 17.08.2026 von Sebastian.**

Offen: **0**

---

## Die Entscheidung

> **Der neuere Stand gilt.** Das ist in allen neun Fällen der Stand aus
> `daten/`.

Begründung, nachgemessen: Alle vier betroffenen Ground-Truth-Dateien tragen in
`daten/` den Zeitstempel **13.07.2026 09:03**, im archivierten Engine-Stamm
dagegen **06.–08.07.2026**. Der `daten/`-Stand ist durchgehend der spätere.

Inhaltlich passt das zusammen: In acht der neun Fälle setzt der spätere Stand
`not_a_transition`, wo der frühere `correct` sagte — allein sechsmal in
`04804f27`. Das ist das Muster eines bewussten zweiten Durchgangs, in dem
Fehlalarme aussortiert wurden, nicht das eines Versehens.

**Folge für die Daten: keine.** Der `daten/`-Stand galt bereits als
maßgeblich; die Entscheidung bestätigt ihn. Nachgeprüft am 17.08.2026: Die
Ground Truth trägt in **9 von 9** Fällen den unten als „gilt" ausgewiesenen
Wert. Es wurde nichts geändert.

**Folge für die Metrik: keine.** Die Referenzmetrik hat seit der
Zusammenführung durchgehend auf diesem Stand gerechnet (`dedup`: 28 Aufnahmen,
286 bewertete Übergänge, Recall 70 %, Precision 74 %, σ 54,58 s).

---

## Die neun Fälle, zur Nachprüfbarkeit

Die Tabellen bleiben stehen. Wer die Entscheidung später anzweifelt, sieht
hier, worüber entschieden wurde — und kann die einzelnen Stellen anhören.

### `04804f27-2755-4db3-8f0b-f57d3315737c.json`

- zuletzt geändert `daten/`: 13.07.2026 09:03 ← **gilt**
- zuletzt geändert `engine/`: 06.07.2026 18:10

| Übergang | Stand `daten/` (gilt) | Stand `engine/` (verworfen) |
|---|---|---|
| 12 | `{"midSec": 2232.51, "verdict": "not_a_transition"}` | `{"midSec": 2232.51, "verdict": "correct"}` |
| 20 | `{"midSec": 3393.25, "verdict": "not_a_transition"}` | `{"midSec": 3393.25, "verdict": "correct"}` |
| 26 | `{"midSec": 4368.0, "verdict": "not_a_transition"}` | `{"midSec": 4368.0, "verdict": "correct"}` |
| 27 | `{"midSec": 4455.14, "verdict": "not_a_transition"}` | `{"midSec": 4455.14, "verdict": "timing_off", "correctedSec": 4337.71}` |
| 28 | `{"midSec": 4713.16, "verdict": "timing_off", "correctedSec": 4539.16}` | `{"midSec": 4713.16, "verdict": "correct"}` |
| 30 | `{"midSec": 5484.37, "verdict": "not_a_transition"}` | `{"midSec": 5484.37, "verdict": "correct"}` |

> Übergang 28 ist der einzige der neun, bei dem der spätere Stand **mehr**
> aussagt statt weniger: `timing_off` mit einer Korrektur auf 1:15:39, wo der
> frühere `correct` bei 1:18:33 sagte. Auch hier gilt der spätere.

### `4d427732-3536-4b45-b542-a3f1cfd44b81.json`

- `daten/`: 13.07.2026 09:03 ← **gilt** · `engine/`: 08.07.2026 10:13

| Übergang | Stand `daten/` (gilt) | Stand `engine/` (verworfen) |
|---|---|---|
| 8 | `{"midSec": 1378.34, "verdict": "not_a_transition"}` | `{"midSec": 1378.34, "verdict": "correct"}` |

### `8ad069d6-d387-45da-abf0-a7461e07acb8.json`

- `daten/`: 13.07.2026 09:03 ← **gilt** · `engine/`: 07.07.2026 10:37

| Übergang | Stand `daten/` (gilt) | Stand `engine/` (verworfen) |
|---|---|---|
| 6 | `{"midSec": 1126.14, "verdict": "not_a_transition"}` | `{"midSec": 1126.14, "verdict": "correct"}` |

### `d684297d-f39e-4daa-8879-7b213dfa4272.json`

- `daten/`: 13.07.2026 09:03 ← **gilt** · `engine/`: 06.07.2026 13:13

| Übergang | Stand `daten/` (gilt) | Stand `engine/` (verworfen) |
|---|---|---|
| 6 | `{"midSec": 1181.69, "verdict": "not_a_transition"}` | `{"midSec": 1181.69, "verdict": "timing_off", "correctedSec": 1135.94}` |

---

## Was mit dem Archiv passiert

Der archivierte Stamm (`audio-engine/mixcoach-audio-engine/_archiv_2026-08-13/`)
bleibt liegen. Seine `LIESMICH.md` verweist auf diese Datei und hält fest, dass
er nicht mehr gelesen wird — mit einer Ausnahme: `analyze_timing_bias --mode
spec` liest ihn absichtlich, um die eingefrorenen Zahlen aus
`CLAUDE_CODE_SPEC_2026-07-29.md` reproduzierbar zu halten. Und er enthält das
einzige Audio der Aufnahme `11da05af`.

Mit dieser Entscheidung ist die Voraussetzung erfüllt, die dort genannt ist:
*„Wer ihn löschen will, sollte vorher KONFLIKTE.md abgearbeitet haben."*
Gelöscht werden muss er deshalb nicht — aber es spricht ab jetzt nichts mehr
dagegen.
