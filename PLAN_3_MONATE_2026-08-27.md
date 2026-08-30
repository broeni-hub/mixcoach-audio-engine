# MixCoach — Drei Monate bis zum ersten zahlenden Nutzer

Stand: 27.08.2026 · Maßgeblich bleibt `PRODUKTVISION.md` · Alle Zahlen unten
sind am 27.08. am Repo und am Datenbestand nachgemessen.

---

## 0 · Wozu dieses Dokument

Sebastian hat drei Monate, in denen MixCoach seine Hauptaufgabe ist. Das
Fernziel ist ein Einkommen von **15.000 €/Monat**, mittel- bis langfristig.
Dieses Dokument sagt, was die drei Monate dafür leisten müssen — und was sie
ausdrücklich **nicht** leisten werden.

`ROADMAP.md` bleibt gültig für die Aufgabenblöcke. Dieses Dokument setzt die
Reihenfolge und die Messgrößen.

---

## 1 · Die Zielzahl, ehrlich gerechnet

| Preis/Monat | nötige Abos für 15.000 € | nötige kostenlose Nutzer (4 % Umwandlung) |
|---|---|---|
| 12 € | 1.250 | ~31.000 |
| 19 € | 790 | ~20.000 |
| 29 € | **520** | ~13.000 |
| 49 € | 306 | ~7.700 |
| B2B (DJ-Schule, 500 €/Monat) | **30 Kunden** | — |

**Der Preis ist der größte Hebel — größer als jede Produktentscheidung.**
Zwischen 12 € und 29 € liegt der Unterschied zwischen 1.250 und 520 Kunden.

In `ROADMAP.md` steht „Pro, Ziel 9–14 €/Monat", festgelegt am 06.07.2026
**ohne einen einzigen Marktkontakt**. Dieselbe Roadmap legt die Zielgruppe auf
„ambitionierte Hobby-DJs, nicht Profis" fest — ebenfalls ungeprüft. Beide
Annahmen gehören in Monat 3 auf den Prüfstand.

**Was die drei Monate NICHT liefern:** 15.000 €/Monat. Realistisch sind
5–20 Zahlende, also 60–580 € je nach Preis. Der Wert liegt nicht im Betrag,
sondern im Beweis, dass überhaupt jemand zahlt.

---

## 2 · Wo wir stehen (27.08.2026)

| Vision | Stand | Beleg |
|---|---|---|
| **Live-Schwelle** | **erfüllt und geprüft** | 3 von 3 Bedingungen, Selbsttest grün |
| 1 · Erkennung | 58 % | Recall 70 %, Precision 74 %, σ 54,6 s |
| 2 · Report | 80 % | 2 belegte Größen |
| 3 · Coach | 56 % | 202 Übungen, **kein Nützlichkeitsnachweis** (J7: p = 0,263) |
| 4 · Fortschritt | 55 % | eine Achse trägt (r = −0,73), eine ist flach (r = −0,004) |
| 5 · Teilen | 10 % | nicht begonnen |
| Teil 3 · Online | 15 % | Auth seit 27.08., sonst nichts |
| Bezahlschranke | **0 %** | Stripe ist ein Kommentar, kein Code |

**Technisch weiter als es aussieht. Als Geschäft bei null — weil es noch nie
ein Fremder benutzt hat.**

---

## 3 · Der Befund, der die Reihenfolge bestimmt

Am 27.08. gemessen, getrennt nach eigenen und fremden Sets. Fremde Sets sind
der ehrliche Stellvertreter für einen fremden DJ: dessen Tracks sind genauso
wenig im Fingerabdruck-Index.

| | eigenes Set | **fremdes Set** |
|---|---|---|
| Übergänge mit Tracknamen | 56 % | **0 %** |
| Marker sitzt richtig | 22 % | **39 %** |
| echter Übergang, Marker daneben | 48 % | **43 %** — Median 51 s, p90 125 s |
| gar kein Übergang an der Stelle | 30 % | **19 %** |

Von zehn Markern in einem fremden Set sitzen vier richtig, vier zeigen im
Mittel 51 s daneben, zwei zeigen auf nichts — und **kein einziger Track hat
einen Namen**.

**Der erste Klick entscheidet.** Ein DJ klickt „anhören bei 14:32", hört
mitten in einen Track und weiß in fünf Sekunden Bescheid. Er schreibt nicht
„euer Marker ist 51 s daneben", er schreibt „interessant, danke" und schickt
nie wieder ein Set.

Deshalb kommt **vor** dem ersten externen Test eine Phase, die den Report
belastbar macht. Sonst misst der Test die kaputte erste Minute, nicht das
Produkt.

---

## 4 · Phase A — Wochen 1–3: den Report belastbar machen

Ziel: Ein „nein" von einem DJ soll ein „nein" zum **Produkt** sein, nicht zu
einer falschen Zeitangabe.

### A1 · Der Marker wird ein Fenster (2–3 Tage)

σ = 54,6 s ist zweimal gemessen und in drei Monaten nicht wegzuoptimieren.
Die *Behauptung* lässt sich aber ehrlich machen:

- heute: „Übergang bei 14:32" — falsch, und zerstört Vertrauen beim ersten Klick
- künftig: „Übergang zwischen 14:10 und 15:20" — wahr und brauchbar

Steht seit dem 30.07. als **K3** in `ZUKUNFTSWEGE_2026-07-30.md`. Anzeige-Umbau,
keine Forschung.

**Messgröße:** Anteil der menschlichen Korrekturen, die im angezeigten Fenster
liegen. Ziel ≥ 75 %.

### A2 · Betriebspunkt messen (1 Tag)

`min_p 0,6` ist darauf getrimmt, viel zu finden. Für den ersten Eindruck ist
das falsch herum: **sechs richtige Marker schlagen zehn, von denen zwei auf
nichts zeigen.** Precision gegen Recall neu abwägen — als Messung, nicht als
Behauptung.

**Messgröße:** Precision bei verschiedenen `min_p`. Entscheidung erst danach.

### A3 · Tracknamen ohne Library (2–3 Tage)

Fremde Tracks sind nicht im Index, und das ist Bauart, kein Fehler. Der Weg
drumherum: **den DJ nach seiner Tracklist fragen** — die hat fast jeder aus
der rekordbox-History. Die Engine ordnet sie den erkannten Wechseln zeitlich
zu. Kein Upload von 300 Dateien, kein Fingerprinting.

**Messgröße:** Anteil benannter Übergänge in einem fremden Set. Ziel ≥ 70 %.

### A4 · Gegenprobe an eigenen Sets

A1–A3 an drei eigenen Aufnahmen durchspielen und den Report so lesen, als
käme er von fremd. Erst wenn der überzeugt, geht er raus.

---

## 5 · Phase B — Woche 4: der Concierge-Test

**Fünf DJs. Kein Hosting, kein Konto, keine Bezahlung.** Sie schicken ein Set
per Link, Sebastian analysiert lokal, schickt den Report zurück.

### Wo die fünf herkommen

Für fünf Leute ist ein Forenbeitrag der falsche Hebel — persönliche Ansprache
wandelt um ein Vielfaches besser.

1. **Eigenes Umfeld zuerst.** Fünf Direktnachrichten schlagen jeden Forenbeitrag.
2. **Discord-Kanäle mit Mix-Feedback** — der eine Ort, wo ein öffentlicher
   Beitrag sofort passt, weil man dort ohnehin um Bewertung bittet.
   Ausgangspunkt: der [DJ-Mag-Server](https://djmag.com/news/dj-mag-launches-new-discord-community).
3. **Foren erst ab Monat 2** (siehe unten).

### Die Ansprache

> „Ich habe ein Werkzeug gebaut, das die Übergänge in einem DJ-Set misst —
> Pegelsprünge, Beat-Genauigkeit. Schick mir ein Set, ich schick dir die
> Auswertung zurück. Kostenlos, kein Konto, keine Anmeldung. Wenn's Mist ist,
> sag mir das bitte auch."

Kein Produkt anbieten, sondern ein Geschenk. Und ausdrücklich um Kritik bitten.

### Was gemessen wird

**Nicht** „gefällt es dir". Sondern:

| Frage | wie gemessen |
|---|---|
| Schickt er ein **zweites** Set, ohne dass du fragst? | zählen |
| Was sagt er als **Erstes**? | wörtlich mitschreiben |
| Deckt sich das mit dem, was der Report betont? | vergleichen |
| Würde er 12 € zahlen? 29 €? | direkt fragen — das Zögern ist die Antwort, nicht das Wort |

### Abbruchkriterium

**Schicken weniger als zwei von fünf ein zweites Set, wird nicht weitergebaut.**
Dann ist die Frage falsch gestellt, und wir ändern sie — statt drei Monate in
eine Antwort zu stecken, die niemand gestellt hat.

---

## 6 · Phase C — Monat 2: online und geschlossene Beta

- **Hosting**, Dateispeicher, DSGVO-Grundlage, Löschkonzept.
  Größenordnung: 313 MB je Set (Median), 15 GB für 46 Sets.
- **Die drei offenen Punkte bei Sebastian:** Anmelde-Durchlauf mit
  `MIXCOACH_AUTH=an`, `SUPABASE_SERVICE_ROLE_KEY`, Postfach-Test des
  Passwort-Resets.
- **10–20 DJs** über Einladungscode.
- **J7 mit fremden Bewertern** — der Nützlichkeitsnachweis für Punkt 3, den
  die Runde vom 17.08. nicht erbringen konnte (13:7, p = 0,263), weil
  Sebastian seine eigenen Übungen bewertet hat.

### Jetzt die Kanäle

**Regel für alle:** Erst die Regeln lesen, dann posten. Die meisten DJ-Foren
und -Subreddits verbieten Produktbeiträge oder erlauben sie nur an bestimmten
Tagen. Ein Bann kostet den Kanal dauerhaft.

| Kanal | Publikum |
|---|---|
| [DJ TechTools Forum](https://forum.djtechtools.com/) | größte technik-nahe Community — die Leute, die sich für Messwerte interessieren |
| [VirtualDJ Forums](https://virtualdj.com/forums/) | sehr groß, **mit deutschsprachigem Unterforum** |
| [Algoriddim / djay](https://community.algoriddim.com/) | softwareaffin |
| r/Beatmatch | Lernende, sehr aktiv |
| r/DJs | erfahrener |
| deejayforum.de | größtes deutschsprachiges Forum |
| techno.de | passt zum Material |
| [djjax.de/community](https://djjax.de/community/) | klein, technikorientiert |

**Messgröße Monat 2: Wiederkehr.** Wie viele laden in Woche 2 noch ein Set
hoch? In Woche 4? Zufriedenheit wird nicht gemessen — sie lügt.

---

## 7 · Phase D — Monat 3: Preis und Modell

Stripe ist das Werkzeug, **nicht die Aufgabe**. Die Aufgabe ist die Frage,
welches Produkt MixCoach eigentlich ist.

### Drei Modelle gleichzeitig testen

1. **12 €/Monat** — die Roadmap-Annahme
2. **29 €/Monat** — Semi-Profis
3. **8 € je Analyse**, kein Abo — niedrigere Hemmschwelle

Beta-Tester bekommen unterschiedliche Angebote. Wer zögert, bei welchem Preis?

### Und ein Gespräch, das alles ändern kann

**Eine DJ-Schule anrufen.** Frage: Was wäre ein Werkzeug wert, das die
Übergänge Ihrer Schüler bewertet? Lautet die Antwort „200 € im Monat für zehn
Schüler", ist das eine andere Firma als die, die gerade gebaut wird — und
das weiß man nach drei Monaten statt nach zwei Jahren. Für 15.000 € bräuchte
es dann **30 Kunden statt 520**.

---

## 8 · Was am Ende dasteht

Nicht Umsatz. **Vier Zahlen, aus denen sich der Weg zu 15.000 € rechnen lässt:**

1. **Wiederkehrquote** — laden Tester ein zweites, drittes Set hoch?
2. **Umwandlungsquote** — wie viele von den Kostenlosen zahlen?
3. **Preisbereitschaft** — bei welchem Preis kippt es?
4. **Der wirksamste Kanal** — woher kam der Tester, der geblieben ist?

Mit diesen vier Zahlen ist 15.000 € eine Rechnung mit bekannten Größen. Ohne
sie ist jede Planung darüber geraten.

---

## 9 · Was in diesen drei Monaten NICHT gebaut wird

- **Die Erkennung verbessern.** Gemessen erledigt: 20 zusätzliche gelabelte
  Sets bringen +1,6 pp Precision. Das ist Forschung, kein Produkt.
- **Sekundengenauigkeit.** σ = 54,6 s, und die menschliche Untergrenze ist
  nach zwei gescheiterten K1-Durchläufen unbekannt.
- **Weitere Messwerte**, bevor die zwei vorhandenen jemandem etwas wert sind.
- **Teilen (Punkt 5).** Marketing durch geteilte Reports braucht Nutzer, die
  teilen wollen.

---

## 10 · Der ehrliche Ausblick

Der Hebel zu 15.000 € ist **nicht das Produkt, sondern die Verteilung**:
DJ-Foren, YouTube, lokale Szene, vielleicht eine Kooperation. Realistisch
12–24 Monate — und nur, wenn diese drei Monate zeigen, dass Leute
wiederkommen und zahlen.

Und ein Wort zu „passiv": Ein Set sind 313 MB und Minuten Rechenzeit.
520 Abonnenten mit je vier Sets im Monat sind rund 650 GB Upload und 2.000
CPU-Läufe monatlich, dazu Support und Modellpflege. Das ist **hebelbares**
Einkommen — passiv ist es nicht.
