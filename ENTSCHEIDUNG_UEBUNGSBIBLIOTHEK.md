# Entscheidungsvorlage: die statische Übungsbibliothek

**Stand 15.08.2026 · für Sebastian · Vorarbeit, keine Entscheidung**

`Frontend/src/lib/coach.ts` enthält 10 feste Übungen, die die Trainingsseite
(`app.training.tsx`) zeigt. Jede trägt ein `successCriteria` — woran der DJ
erkennen soll, dass er sie geschafft hat.

**6 von 10 nennen dort einen Wert, den MixCoach nicht berechnet.** Die App
verspricht ein Ziel, das sie nicht nachprüfen kann. Das ist dieselbe Klasse wie
die Vorlage „Transition Review", eine Seite weiter.

Der Inhalt ist deine Entscheidung. Hier steht je Übung: was heute dasteht,
warum es nicht trägt, und ein Vorschlag, der auf einer belegten Größe ruht.

---

## Was messbar ist

| Größe | befüllt | Zusammenhang mit deinem Urteil |
|---|---|---|
| `loudness_jump_db` | 86 % | **ρ −0,339** — der stärkste |
| `beat_alignment_score` | 86 % | ρ +0,325, aber σ 2,59 auf 83–98 (kaum Spannweite) |
| Camelot-Abstand | 100 % | ρ +0,053 — rechenbar, aber ohne Beleg |
| `energy_dip_pct` | 50 % | ρ +0,065 |
| `harmonic_clash_score` | 81 % | ρ −0,142 |
| `eq`, `creativity`, `timing`, `beatmatching` | **0 %** | wird nicht berechnet |

---

## Die sechs, die nicht tragen

**1 · `phrase-16` — 16-Bar Phrase Challenge**
Heute: *„Phrase alignment score ≥ 85"*
Warum nicht: `phrase_alignment_score` korreliert mit ρ −0,037; die Note `timing`
steht seit dem 31.07. bewusst auf `None`. Das Phrasenraster wandert weiter als
die Größe, die es messen soll.
Vorschlag: **„Der neue Track kommt mit weniger als 1 dB Pegelunterschied rein"**
— dieselbe Übung (Timing des Einsatzes), aber mit einem Kriterium, das MixCoach
misst. Oder als reine Selbsteinschätzung kennzeichnen.

**2 · `bass-swap` — 16-Bar Bass Swap**
Heute: *„EQ score ≥ 85"*
Warum nicht: `eq` ist in 51 von 51 Reports leer.
Vorschlag: Kriterium streichen, das erste behalten (*„No low-end overlap longer
than 1 beat"* — selbst hörbar, ehrlich als Selbsteinschätzung markiert).

**3 · `bass-patience` — Bass Patience Drill**
Heute: *„EQ score ≥ 75"*, dazu *„Zero bass overlap before bar 24"*
Warum nicht: `eq` leer; `bass_overlap_score` ist zu 15,5 % befüllt und zu 90 %
exakt 0 oder 100 — als Ziel unbrauchbar.
Vorschlag: wie 2 — Selbsteinschätzung statt Scheinmessung.

**4 · `warmup-flow` — Club Warm-Up Flow**
Heute: *„BPM drift ≤ 1.5 %"*
Warum nicht: `bpm_drift` ist in 89 % der Übergänge exakt 0,0 — das Kriterium ist
immer erfüllt und sagt nichts.
Vorschlag: **„Kein Übergang mit mehr als 3 dB Pegelsprung"** — passt zum
Warm-up-Gedanken (nichts springt heraus) und ist gemessen.

**5 · `freestyle-review` — Freestyle Set Review**
Heute: *„Creativity score ≥ 80"*
Warum nicht: `creativity` ist in 51 von 51 Reports leer.
Vorschlag: Kriterium streichen. *„At least 3 distinct transition types"* bleibt
und ist selbst nachzählbar.

**6 · `sync-hold` — 60-Second Sync Hold**
Heute: *„Your timing feels rock-solid"*
Warum nicht: klingt nach der Note `timing`, die auf `None` steht.
Vorschlag: als Selbsteinschätzung kennzeichnen — die Übung ist gut, nur das
Kriterium tut so, als würde es gemessen.

---

## Die vier, die in Ordnung sind

`vocal-clash`, `energy-buildup`, `monthly-review`, `key-lock` — ihre Kriterien
sind entweder ehrlich subjektiv formuliert („feels natural") oder selbst
nachzählbar. `key-lock` (*„No tracks clashing in key"*) wäre sogar messbar:
Camelot-Abstand ist zu 100 % befüllt. Ein Ausbau wäre möglich, ist aber nicht
nötig.

---

## Was ich gebaut habe, ohne zu entscheiden

`CoachExercise` hat ein neues Feld:

```ts
criterionVerifiable?: false;
criterionNote?: string;
```

Die Trainingsseite zeigt bei `criterionVerifiable: false` einen Hinweis:
**„Dieses Ziel kann MixCoach nicht nachprüfen — schätz selbst ein."**

Gesetzt ist es bei den sechs oben, weil dort **belegt** ist, dass die Größe
nicht misst. Bei allen anderen bleibt es leer, bis du entschieden hast.

Damit steht heute nichts Falsches mehr da, ohne dass eine Formulierung
vorweggenommen wäre, die dir gehört.

---

## Drei Wege

**A · Kennzeichnung reicht.** Aufwand: null, ist gebaut. Die Übungen bleiben,
der Hinweis sagt, was MixCoach kann und was nicht.

**B · Kriterien umschreiben.** Die sechs bekommen die Vorschläge oben. Aufwand:
eine Stunde, plus deine Formulierungen. Danach nennt jede Übung ein Ziel, das
die App prüfen kann.

**C · Bibliothek an die Engine hängen.** Die Übungen kämen wie im Report aus
`app/coach/uebungen.py` — aus dem eigenen Material statt aus einer festen
Liste. Aufwand: ein Tag. Das ist die eigentliche Antwort, aber sie gehört in
einen eigenen Auftrag.

Mein Rat: **A jetzt, B beim nächsten Mal, C wenn Punkt 3 die 60 % überschreitet.**
