// Welche Rechenvorschrift hat die Zahlen in einem Report erzeugt?
//
// Gegenstueck zu app/audio/pipeline/scoring_version.py auf der Engine-Seite.
// Dort steht die Begruendung ausfuehrlich; kurz: derselbe Feldname hat je
// nach Rechenstand Verschiedenes bedeutet (composite_quality_score sprang am
// 12.07.2026 um 25 Punkte, ohne dass ein Uebergang besser wurde).
//
// Hier wird die Version zu dem, was sie im Frontend leisten muss: die
// Entscheidung, ob eine eingehende Fassung eine gespeicherte ABLOEST.
// Ohne diese Ordnung gibt es keinen Weg, einen falschen Report zu
// berichtigen - der Browser hat bis zum 13.08.2026 jede Analyse, die er
// einmal kannte, nie wieder angefasst.
//
// Zur Laufzeit ist das Feld laengst da: remoteProvider.getAnalysis() macht
// `(await res.json()) as AnalysisResult`, ein reiner Cast ohne Zod und ohne
// Feldabbildung. Der Wert der Engine kommt also durch, er war nur im Typ
// nicht deklariert und damit fuer keinen Code sichtbar.

/** Kein Stempel. Entspricht UNSTAMPED in scoring_version.py. */
export const UNSTAMPED = 0;

type MitVersion = {
  scoringVersion?: number | null;
  reportRevision?: number | null;
} | null | undefined;

/** Version eines Reports, 0 wenn ungestempelt oder unbrauchbar. */
export function versionVon(report: MitVersion): number {
  const v = report?.scoringVersion;
  return typeof v === "number" && Number.isFinite(v) && v > 0 ? v : UNSTAMPED;
}

/** Wie oft dieser Report berichtigt wurde. Fehlend = 0. */
export function revisionVon(report: MitVersion): number {
  const r = report?.reportRevision;
  return typeof r === "number" && Number.isFinite(r) && r > 0 ? r : 0;
}

/**
 * Loest `eingehend` die gespeicherte Fassung ab?
 *
 * Zwei Fragen, zwei Felder:
 *
 *   scoringVersion  - nach welcher Rechenvorschrift sind die Zahlen
 *                     entstanden? Hoehere Version loest ab.
 *   reportRevision  - wie oft wurde DIESE Datei berichtigt? Bei gleicher
 *                     Rechenvorschrift loest die hoehere Revision ab.
 *
 * Bis zum 13.08.2026 gab es nur die Version, und damit kam genau der
 * haeufige Fall nie an: eine reine Datenkorrektur darf die Version nicht
 * erhoehen (siehe scoring_version.py), also konnte sie sich auch nicht
 * weitergeben. Der Ehrlichkeits-Backfill hat 23 Reports berichtigt, von
 * denen kein einziger einen Browser erreicht haette, der sie schon kannte.
 *
 * Die Revision entscheidet ZUERST, und das ist kein Kompromiss, sondern die
 * genauere Ordnung: innerhalb EINER Analyse-id ist sie eine echte
 * Zeitreihenfolge. Die Pipeline schreibt die Datei genau einmal (Revision 1,
 * dabei entsteht die id ueberhaupt erst), danach schreibt nur noch ein
 * Berichtigungslauf, und jeder zaehlt hoch. Eine hoehere Revision ist damit
 * immer die spaetere Fassung derselben Analyse - auch dann, wenn die
 * Berichtigung die scoringVersion GESENKT hat.
 *
 * Genau dieser Fall ist real: sechs Reports trugen einen Stempel 3, den
 * niemand belegen konnte (Werte vom 02.07., kein composite_quality_score).
 * Ihn zu entfernen war richtig - aber nach einer reinen Versionsordnung
 * haette diese Korrektur nie einen Browser erreicht, weil 0 > 3 falsch ist.
 *
 * Die scoringVersion bleibt der Rueckfall fuer Altbestand, den noch nie ein
 * revisionsbewusstes Werkzeug angefasst hat (beide Revisionen 0).
 */
export function loestAb(gespeichert: MitVersion, eingehend: MitVersion): boolean {
  const altR = revisionVon(gespeichert);
  const neuR = revisionVon(eingehend);
  if (neuR !== altR) return neuR > altR;
  return versionVon(eingehend) > versionVon(gespeichert);
}

/**
 * Nutzereigenen Zustand vom alten auf den neuen Stand heben.
 *
 * Im Report-Objekt selbst steht nichts, was der Nutzer gesetzt hat - seine
 * Bewertungen liegen in daten/ground_truth/ auf der Engine, `archivedIds`
 * im Store daneben. Eine Ausnahme reist aber am Objekt mit: `archived`,
 * das sync.ts als `Stored = AnalysisResult & { archived?: boolean }`
 * anhaengt. Beim Ersetzen wuerde es sonst verschwinden, und eine
 * archivierte Analyse taeuchte wieder auf.
 */
export function mitNutzerstand<T extends object>(neu: T, alt: T): T {
  const archiviert = (alt as { archived?: boolean })?.archived;
  return archiviert === undefined ? neu : { ...neu, archived: archiviert };
}
