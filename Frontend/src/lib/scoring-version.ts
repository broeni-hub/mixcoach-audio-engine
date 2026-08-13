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

type MitVersion = { scoringVersion?: number | null } | null | undefined;

/** Version eines Reports, 0 wenn ungestempelt oder unbrauchbar. */
export function versionVon(report: MitVersion): number {
  const v = report?.scoringVersion;
  return typeof v === "number" && Number.isFinite(v) && v > 0 ? v : UNSTAMPED;
}

/**
 * Loest `eingehend` die gespeicherte Fassung ab?
 *
 * Nur bei ECHT hoeherer Version. Gleichstand heisst ausdruecklich "nein":
 * zwei Reports derselben Rechenvorschrift sind gleichwertig, und ein
 * unnoetiger Austausch wuerde nur Flackern erzeugen. Ein ungestempelter
 * Eingang (0) loest nie etwas ab - er koennte aus jeder Epoche stammen.
 */
export function loestAb(gespeichert: MitVersion, eingehend: MitVersion): boolean {
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
