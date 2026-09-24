import { Scale } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ReferenzVergleich } from "@/lib/report-types";

/**
 * Dein Set gegen sechs fremde Profi-Sets — als SPANNE, nicht als Mittelwert.
 *
 * WARUM ES DIESE KARTE GIBT (24.09.2026)
 * --------------------------------------
 * Den Vergleich gab es bis heute nur in `tools/set_report.py`, also in der
 * Seite, die ein fremder DJ per Mail bekommt. Die App kannte ihn nicht.
 * Damit war die verschickte Seite kein Bild des Produkts, sondern ein
 * zweites Produkt — und genau das hat die erste DJ-Runde teuer gemacht.
 *
 * WAS HIER BEWUSST NICHT STEHT
 * ----------------------------
 * Ein Rückstand. Bis zum 23.09.2026 zeichnete die Skala ihr Band von 0 bis
 * zum MEDIAN der sechs, und alles darüber las sich als "schlechter als die
 * Profis". Ein Test-DJ schrieb dazu: "maybe I'm not a machine but I believe
 * 10ms is fucking amazing haha". Er hatte recht — sein Wert lag innerhalb
 * der Spanne, besser als Dixon bei Tomorrowland. Der Standardfehler des
 * Set-Medians (±1,8 ms) ist größer als der angezeigte Abstand (1,2 ms), und
 * gegen kein einziges Referenz-Set war ein Unterschied nachweisbar.
 *
 * KEINE ZAHL STEHT IN DIESER DATEI. Grenzen, Schwellen und Einheiten kommen
 * aus dem Report, der sie aus `app/coach/referenz.py` und
 * `app/coach/uebungen.py` bezieht. Wer hier einen Wert hinschreibt, baut die
 * sechste Kopie — am 23.09. lagen fünf davon im Produkt.
 */

const TEXTE = {
  de: {
    titel: "Im Vergleich",
    unter: "Dein Set gegen {n} fremde Profi-Sets. Gezeigt ist deren Spanne, nicht ihr Mittelwert.",
    innerhalb: "Liegt innerhalb der Spanne der {n} Vergleichs-Sets ({a}–{b} {e}).",
    darueber: "Liegt über der Spanne der {n} Vergleichs-Sets ({a}–{b} {e}).",
    darunter: "Liegt unter allen {n} Vergleichs-Sets ({a}–{b} {e}).",
    uebung: "Ab {s} {e} entsteht daraus eine Übung.",
    basis: "Median aus {k} Übergängen",
    spanne: "Spanne der Vergleichs-Sets",
    schwelle: "Schwelle",
    groessen: {
      loudness_jump_db: "Pegelsprung",
      beat_jitter_ms: "Beat-Jitter",
    } as Record<string, string>,
  },
  en: {
    titel: "In comparison",
    unter: "Your set against {n} other professional sets. Shown is their range, not their average.",
    innerhalb: "Within the range of the {n} reference sets ({a}–{b} {e}).",
    darueber: "Above the range of the {n} reference sets ({a}–{b} {e}).",
    darunter: "Below all {n} reference sets ({a}–{b} {e}).",
    uebung: "From {s} {e} on, this turns into an exercise.",
    basis: "Median of {k} transitions",
    spanne: "Range of the reference sets",
    schwelle: "Threshold",
    groessen: {
      loudness_jump_db: "Level jump",
      beat_jitter_ms: "Beat jitter",
    } as Record<string, string>,
  },
} as const;

function zahl(v: number, lang: "de" | "en"): string {
  const s = (Math.round(v * 10) / 10).toFixed(1);
  return lang === "de" ? s.replace(".", ",") : s;
}

function fuellen(vorlage: string, werte: Record<string, string | number>): string {
  return Object.entries(werte).reduce(
    (t, [k, v]) => t.split(`{${k}}`).join(String(v)),
    vorlage,
  );
}

export function ReferenzVergleichCard(
  { eintraege, lang }: { eintraege: ReferenzVergleich[]; lang: "de" | "en" },
) {
  // Kein Platzhalter, keine leere Karte: wo nichts gemessen ist, steht nichts.
  if (eintraege.length === 0) return null;
  const T = TEXTE[lang] ?? TEXTE.de;
  const sets = eintraege[0]?.referenzSets ?? 0;

  return (
    <Card className="glass">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Scale className="h-4 w-4 text-muted-foreground" /> {T.titel}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-xs text-muted-foreground mb-4">
          {fuellen(T.unter, { n: sets })}
        </p>

        <div className="space-y-5">
          {eintraege.map((e) => {
            const name = T.groessen[e.metrik] ?? e.metrik;
            // Die Skala endet hinter dem groessten der drei Bezugspunkte,
            // damit weder Schwelle noch Wert aus dem Bild laufen.
            const ende = Math.max(e.schwelle, e.max, e.wert) * 1.2 || 1;
            const pct = (v: number) => `${Math.min(100, Math.max(0, (v / ende) * 100))}%`;

            const satz = e.innerhalb === true
              ? T.innerhalb
              : e.wert > e.max ? T.darueber : T.darunter;
            const lage = fuellen(satz, {
              n: e.referenzSets,
              a: zahl(e.min, lang),
              b: zahl(e.max, lang),
              e: e.einheit,
            });
            const reisst = e.wert >= e.schwelle;

            return (
              <div key={e.metrik}>
                <div className="flex items-baseline justify-between gap-3">
                  <span className="text-sm font-medium">{name}</span>
                  <span className="text-sm tabular-nums">
                    {zahl(e.wert, lang)} {e.einheit}
                  </span>
                </div>

                <div className="relative mt-2 h-2 rounded-full bg-muted/40">
                  {/* Das Band der sechs */}
                  <div
                    className="absolute inset-y-0 rounded-full bg-muted-foreground/25"
                    style={{ left: pct(e.min), width: `calc(${pct(e.max)} - ${pct(e.min)})` }}
                    aria-label={T.spanne}
                  />
                  {/* Die Schwelle, ab der eine Uebung entsteht */}
                  <div
                    className="absolute inset-y-[-3px] w-px bg-foreground/40"
                    style={{ left: pct(e.schwelle) }}
                    aria-label={T.schwelle}
                  />
                  {/* Dieses Set */}
                  <div
                    className={`absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-background ${
                      reisst ? "bg-destructive" : "bg-primary"
                    }`}
                    style={{ left: pct(e.wert) }}
                  />
                </div>

                <p className="mt-2 text-xs text-muted-foreground">
                  {lage}
                  {reisst ? ` ${fuellen(T.uebung, { s: zahl(e.schwelle, lang), e: e.einheit })}` : ""}
                </p>
                <p className="mt-0.5 text-[11px] text-muted-foreground/70">
                  {fuellen(T.basis, { k: e.uebergaenge })}
                </p>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
