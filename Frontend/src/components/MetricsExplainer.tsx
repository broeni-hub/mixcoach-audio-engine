// Klartext-Erklaerungen der Messwerte - einklappbar im Report, DE/EN.

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChevronDown, ChevronUp, HelpCircle } from "lucide-react";
import { useLang } from "@/lib/i18n";

type Metric = { name: string; what: string; good: string };

const TEXTS = {
  de: {
    title: "Was bedeuten die Werte?",
    guide: "Richtwert:",
    metrics: [
      { name: "Phrase-Timing", what: "Elektronische Musik ist in Phrasen von 16/32 Beats gebaut. Gemessen wird, wie viele Beats dein Übergang neben der nächsten Phrasengrenze des laufenden Tracks liegt.", good: "0–4 Beats daneben ist tight. Ab ~8 Beats fühlt der Floor, dass etwas 'zu früh' oder 'zu spät' kam." },
      { name: "Beatmatching / Tempo", what: "Der BPM-Unterschied beider Tracks während des Übergangs (Drift). Gemessen aus den Beat-Abständen vor und nach dem Übergang.", good: "Unter 1 BPM hört niemand. Ab ~2 BPM 'galoppiert' es." },
      { name: "Harmonie (Camelot)", what: "Die Tonarten beider Tracks, übersetzt ins Camelot-Rad (8A, 9A …). Kompatibel sind gleiche Zahl, Nachbarzahl mit gleichem Buchstaben oder Dur/Moll-Wechsel derselben Zahl.", good: "Kompatible Wechsel klingen fast immer rund. Inkompatible können funktionieren — sind aber Risiko." },
      { name: "Pegelsprung (dB)", what: "Lautheit (K-gewichtet, Rundfunk-Standard) kurz vor vs. kurz nach dem Übergang. Misst dein Gain-Staging.", good: "±1 dB ist sauber. Ab +2 dB hörbar, ab +4 dB drückt der neue Track alles weg." },
      { name: "Energie-Verlauf", what: "Die Energiekurve des Sets (RMS). Beim Übergang: wie tief die Energie einbricht. Übers Set: ob eine Dramaturgie erkennbar ist.", good: "Ein bewusster Breakdown ist gut — ein ungewolltes 30-Sekunden-Loch nicht." },
      { name: "Übergangs-Score", what: "Gesamtnote eines Übergangs aus Phrase, Tempo, Harmonie und Energieform — gewichtet nach dem, was DJs am stärksten hören.", good: "75+ ist ein sitzender Übergang. Unter 50 lohnt das Nachhören." },
      { name: "Bass-Overlap", what: "Nur messbar, wenn beide Tracks per Library erkannt wurden: Der Tiefton der Aufnahme wird mit dem Tiefton der Original-Tracks verglichen — liefen im Blend beide Bässe gleichzeitig?", good: "Unter 35 ist ein sauberer Bass-Swap. Ab 60 dröhnt es — Bass des alten Tracks früher rausdrehen." },
      { name: "Was (noch) nicht gemessen wird", what: "EQ-Arbeit im Detail und Kreativität zeigen wir bewusst leer statt geschätzt an. Bass-Overlap erscheint nur bei erkannten Track-Paaren. Was MixCoach nicht messen kann, bekommt keine erfundene Zahl.", good: "Leeres Feld = ehrliche Antwort, kein Fehler." },
    ] as Metric[],
  },
  en: {
    title: "What do the numbers mean?",
    guide: "Guideline:",
    metrics: [
      { name: "Phrase timing", what: "Electronic music is built in phrases of 16/32 beats. We measure how many beats your transition lands away from the outgoing track's next phrase boundary.", good: "0–4 beats off is tight. From ~8 beats the floor feels something came in 'too early' or 'too late'." },
      { name: "Beatmatching / tempo", what: "The BPM difference between both tracks during the blend (drift), measured from beat spacing before and after the transition.", good: "Below 1 BPM nobody hears it. From ~2 BPM it starts to 'gallop'." },
      { name: "Harmony (Camelot)", what: "Both tracks' keys translated to the Camelot wheel (8A, 9A …). Compatible: same number, neighbouring number with the same letter, or major/minor swap of the same number.", good: "Compatible moves almost always sound smooth. Incompatible ones can work — but they're a gamble." },
      { name: "Loudness jump (dB)", what: "Loudness (K-weighted, broadcast standard) shortly before vs. shortly after the transition. This measures your gain staging.", good: "±1 dB is clean. From +2 dB it's audible, from +4 dB the new track steamrolls everything." },
      { name: "Energy flow", what: "The set's energy curve (RMS). Per transition: how deep the energy dips. Across the set: whether there's a dramaturgy.", good: "A deliberate breakdown is fine — an accidental 30-second hole is not." },
      { name: "Transition score", what: "Overall grade per transition from phrase, tempo, harmony and energy shape — weighted by what DJs hear most.", good: "75+ is a transition that sits. Below 50 is worth re-listening." },
      { name: "Bass overlap", what: "Only measurable when both tracks were recognized via your library: the recording's low end is compared against the original tracks' low end — did both basslines run simultaneously during the blend?", good: "Below 35 is a clean bass swap. From 60 it rumbles — cut the outgoing bass earlier." },
      { name: "What is not (yet) measured", what: "Detailed EQ work and creativity are intentionally shown empty instead of guessed. Bass overlap only appears for recognized track pairs. Whatever MixCoach can't measure doesn't get an invented number.", good: "An empty field = an honest answer, not a bug." },
    ] as Metric[],
  },
};

export function MetricsExplainer() {
  const [open, setOpen] = useState(false);
  const lang = useLang();
  const T = TEXTS[lang];

  return (
    <Card>
      <CardHeader className="cursor-pointer select-none" onClick={() => setOpen((o) => !o)}>
        <CardTitle className="flex items-center justify-between text-base">
          <span className="flex items-center gap-2">
            <HelpCircle className="h-4 w-4 text-primary" />
            {T.title}
          </span>
          {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </CardTitle>
      </CardHeader>
      {open && (
        <CardContent className="space-y-3">
          {T.metrics.map((m) => (
            <div key={m.name} className="rounded-lg border border-border bg-card/40 p-3">
              <p className="text-sm font-semibold">{m.name}</p>
              <p className="mt-1 text-xs text-muted-foreground">{m.what}</p>
              <p className="mt-1 text-xs"><span className="text-green-500 font-medium">{T.guide}</span> <span className="text-muted-foreground">{m.good}</span></p>
            </div>
          ))}
        </CardContent>
      )}
    </Card>
  );
}
