"""Referenzmetrik fuer die Transitions-Erkennung (Job B, Schritt 1).

Dieses Skript ist ab jetzt DIE Messlatte. Jede Aenderung an der Erkennung
wird hier gegengemessen - vorher/nachher, mit denselben Zahlen. Es laeuft
bewusst ohne Audio und ohne numpy/librosa: nur Standardbibliothek, damit
es auch dann funktioniert, wenn die Musik-Library nicht erreichbar ist
(genau der Zustand nach dem Umzug auf macOS).

    python -m tools.analyze_timing_bias                 # Report (mode=dedup)
    python -m tools.analyze_timing_bias --check         # Sollwerte pruefen
    python -m tools.analyze_timing_bias --mode spec     # alter Stand, 29.07.
    python -m tools.analyze_timing_bias --nur-verwertbar          # ohne Leerlaeufe
    python -m tools.analyze_timing_bias --predictions neu.json   # vorher/nachher

Vorzeichen-Konvention durchgehend:

    delta = correctedSec - midSec

    delta < 0  ->  der Mensch hat frueher korrigiert  ->  ENGINE WAR ZU SPAET
    delta > 0  ->  Engine war zu frueh

Warum zwei Ground-Truth-Verzeichnisse?
-------------------------------------
`app/paths.py` leitet DATA_ROOT aus MIXCOACH_DATA_DIR ab, mit dem
Projektordner als Fallback. Auf dem alten Rechner war die Variable mal
gesetzt (-> daten/ground_truth, 45 Dateien) und mal nicht
(-> mixcoach-audio-engine/ground_truth, 24 Dateien). Dadurch ist die
Ground Truth auf zwei Staemme auseinandergelaufen. Die 24 Dateien sind
namensgleich mit 24 der 45; 18 davon sind byteidentisch, 6 unterscheiden
sich (unterschiedliche Bewertungsstaende desselben Sets).

Das ist fuer die Metrik kein Detail, sondern ein Messfehler - siehe
--mode weiter unten.

Stand 13.08.2026: die zwei Staemme sind zusammengefuehrt
(tools/staemme_zusammenfuehren.py). Die drei nur im zweiten Stamm
vorhandenen missed-Angaben stehen jetzt in daten/, die neun
widerspruechlichen Urteile in daten/ground_truth/KONFLIKTE.md. Der zweite
Ordner ist nach _archiv_2026-08-13/ verschoben und wird nur noch von
dieser Metrik gelesen - bewusst: '--mode spec' zaehlt beide Ordner roh
und reproduziert damit die eingefrorenen Zahlen aus
CLAUDE_CODE_SPEC_2026-07-29.md. Wuerde man den Ordner hier weglassen,
verschoebe sich genau der Anker, an dem jede Aenderung gemessen wird.
Geschrieben wird dorthin nichts mehr.

Die drei Sichten (--mode)
-------------------------
spec      Beide Ordner roh. Zaehlt die 24 gemeinsamen Sets doppelt und
          REC001 vierzehnmal. Reproduziert die in
          CLAUDE_CODE_SPEC_2026-07-29.md dokumentierten Zahlen und bleibt
          allein dafuer erhalten - als Messgroesse ist sie falsch.
analyse   Je analysisId der zuletzt bearbeitete Stand (45 Sets). Das war
          bis 31.07.2026 '--mode dedup'.
dedup     Je AUFNAHME (fileName) der zuletzt bearbeitete Stand (28 Sets).
          SEIT 31.07.2026 DIE VORGABE. Vorher gruppierte dieser Modus nach
          analysisId; REC001 zaehlte dadurch elfmal, obwohl es eine einzige
          Aufnahme ist. collect_feedback_rows() im Retrain gruppiert seit
          jeher nach fileName - die Metrik zieht hier nur nach.

Die Sollwerte in SOLLWERTE gelten je Modus getrennt; --check sagt immer
an, gegen welchen Stand es prueft. Die alten spec-Werte bleiben gueltig,
sie messen nur etwas anderes als die Vorgabe.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.eval import gt_status  # noqa: E402

# tools/ liegt direkt unter mixcoach-audio-engine/
ENGINE_ROOT = Path(__file__).resolve().parents[1]
GT_DIRS = [
    # Seit 13.08.2026 im Archiv, siehe Docstring. Nur lesend, nur damit
    # '--mode spec' seinen eingefrorenen Anker behaelt.
    ENGINE_ROOT / "_archiv_2026-08-13" / "ground_truth",
    ENGINE_ROOT.parents[1] / "daten" / "ground_truth",
]

# Selbsttest je Sicht: reproduziert das Skript diese Zahlen nicht, stimmt
# etwas am Einlesen der Ground Truth - dann hat Weiterbauen keinen Sinn.
#
# spec stammt vom 29.07.2026 aus CLAUDE_CODE_SPEC_2026-07-29.md und ist der
# eingefrorene Anker. analyse und dedup sind am 31.07.2026 gemessen worden,
# als der Modus dedup von analysisId auf fileName umgestellt wurde. Sie
# entwerten die spec-Werte NICHT - sie zaehlen dieselbe Ground Truth nur
# ohne Doppelzaehlung, und das ergibt zwangslaeufig andere Zahlen.
SOLLWERTE = {
    "spec": {
        "quelle": "CLAUDE_CODE_SPEC_2026-07-29.md, Stand 29.07.2026",
        "n": 287, "zu_spaet_pct": 86, "median": -29.85, "sigma": 52.87,
        "innerhalb_8s_pct": 5, "innerhalb_16s_pct": 22,
    },
    "analyse": {
        "quelle": "gemessen 31.07.2026 (bis dahin '--mode dedup')",
        "n": 161, "zu_spaet_pct": 85.71, "median": -29.08, "sigma": 51.12,
        "innerhalb_8s_pct": 4.35, "innerhalb_16s_pct": 22.36,
    },
    "dedup": {
        "quelle": "gemessen 31.07.2026, Vorgabe seit dieser Aenderung",
        "n": 130, "zu_spaet_pct": 85.38, "median": -29.43, "sigma": 54.58,
        "innerhalb_8s_pct": 5.38, "innerhalb_16s_pct": 22.31,
    },
}
PRUEF_SCHLUESSEL = ["n", "zu_spaet_pct", "median", "sigma",
                    "innerhalb_8s_pct", "innerhalb_16s_pct"]


# ---------------------------------------------------------------- Einlesen


def _read_gt_files(mode: str, nur_verwertbar: bool = False) -> tuple[list[dict], list[str]]:
    """Ground-Truth-Dateien laden. Liefert (Datensaetze, Hinweise)."""
    hinweise: list[str] = []
    roh: list[tuple[Path, dict]] = []

    for gt_dir in GT_DIRS:
        if not gt_dir.is_dir():
            hinweise.append(f"FEHLT: {gt_dir} existiert nicht")
            continue
        for path in sorted(gt_dir.glob("*.json")):
            try:
                roh.append((path, json.loads(path.read_text(encoding="utf-8"))))
            except Exception as error:  # noqa: BLE001
                hinweise.append(f"unlesbar: {path.name}: {error}")

    doppelt = _count_duplicates(roh)
    if doppelt:
        hinweise.append(
            f"{doppelt} Set(s) liegen zusaetzlich im Archiv "
            f"(_archiv_2026-08-13/, seit 13.08.2026 zusammengefuehrt). "
            f"In --mode spec zaehlen sie doppelt - das ist dort gewollt, "
            f"damit die eingefrorenen Zahlen reproduzierbar bleiben."
        )

    # Ausschlussliste aus der Bestandsaufnahme (tools/eval/gt_status.py).
    # Nur gebraucht, wenn wirklich gefiltert oder nach Aufnahme gruppiert
    # wird - so bleibt --mode spec vom Bestand der Ergebnis-JSONs unabhaengig
    # und reproduziert seine Sollwerte auch dann noch, wenn die verschwinden.
    aufnahme_je_id: dict[str, str] = {}
    raus: set[str] = set()
    if mode == "dedup" or nur_verwertbar:
        try:
            gruppen, gt_hinweise = gt_status.aufnahmen()
        except Exception as error:  # noqa: BLE001
            hinweise.append(f"gt_status nicht auswertbar ({error}) - "
                            f"Gruppierung faellt auf analysisId zurueck")
            gruppen, gt_hinweise = [], []
        hinweise.extend(gt_hinweise)
        for a in gruppen:
            for aid in a.analysis_ids:
                aufnahme_je_id[aid] = a.schluessel
            if not a.verwertbar:
                raus.add(a.schluessel)

    if mode == "spec":
        datensaetze = [j for _, j in roh]
    else:
        # Je Gruppe den zuletzt bearbeiteten Stand gewinnen lassen. updatedAt
        # ist ein Unix-Timestamp, den feedback_store beim Speichern setzt.
        #
        # mode=analyse gruppiert nach analysisId, mode=dedup nach AUFNAHME.
        # Bewusst dieselbe "juengster gewinnt"-Regel wie bisher und KEINE
        # Vereinigung der Verdicts ueber mehrere Analysen derselben Aufnahme:
        # dieselbe Transition ist dort mehrfach bewertet, eine Vereinigung
        # wuerde sie erneut doppelt zaehlen - genau der Fehler, der hier
        # abgestellt wird.
        besten: dict[str, dict] = {}
        for path, j in roh:
            aid = j.get("analysisId") or path.stem
            key = aufnahme_je_id.get(aid, aid) if mode == "dedup" else aid
            vorher = besten.get(key)
            if vorher is None or (j.get("updatedAt") or 0) >= (vorher.get("updatedAt") or 0):
                besten[key] = j
        datensaetze = list(besten.values())

    if nur_verwertbar and aufnahme_je_id:
        vorher_n = len(datensaetze)
        datensaetze = [j for j in datensaetze
                       if aufnahme_je_id.get(j.get("analysisId") or "", "") not in raus]
        hinweise.append(f"--nur-verwertbar: {vorher_n - len(datensaetze)} Set(s) "
                        f"aussortiert, {len(datensaetze)} bleiben")

    return datensaetze, hinweise


def _count_duplicates(roh: list[tuple[Path, dict]]) -> int:
    gesehen: dict[str, int] = {}
    for path, j in roh:
        key = j.get("analysisId") or path.stem
        gesehen[key] = gesehen.get(key, 0) + 1
    return sum(1 for n in gesehen.values() if n > 1)


# ---------------------------------------------------------------- Auswertung


def _collect(datensaetze: list[dict], predictions: dict | None) -> dict:
    """Verdicts und Zeitfehler einsammeln.

    predictions: optional analysisId -> {transition-index (str): start_sec}.
    Ist ein Vorhersagewert vorhanden, ersetzt er midSec als Engine-Zeitpunkt -
    so wird eine neue Erkennung gegen exakt dieselbe Ground Truth gemessen.
    """
    verdicts: dict[str, int] = {}
    deltas: list[float] = []          # correctedSec - engine_sec, nur timing_off
    correct_deltas: list[float] = []  # Regressionswaechter auf der Gruppe correct
    missed = 0
    ohne_vorhersage = 0

    for j in datensaetze:
        aid = j.get("analysisId") or ""
        preds = (predictions or {}).get(aid) or {}

        for idx, v in (j.get("verdicts") or {}).items():
            verdict = v.get("verdict")
            if not verdict:
                continue
            verdicts[verdict] = verdicts.get(verdict, 0) + 1

            mid = v.get("midSec")
            if mid is None:
                continue

            if predictions is None:
                engine_sec = mid
            else:
                pred = preds.get(str(idx))
                if pred is None:
                    ohne_vorhersage += 1
                    continue
                engine_sec = float(pred)

            if verdict == "timing_off" and v.get("correctedSec") is not None:
                deltas.append(v["correctedSec"] - engine_sec)
            elif verdict == "correct":
                # Bei `correct` ist midSec der vom Menschen akzeptierte Wert.
                # Referenz ist also der urspruengliche midSec, nicht correctedSec.
                correct_deltas.append(mid - engine_sec)

        missed += len(j.get("missed") or [])

    return {
        "verdicts": verdicts,
        "deltas": deltas,
        "correct_deltas": correct_deltas,
        "missed": missed,
        "ohne_vorhersage": ohne_vorhersage,
        "n_sets": len(datensaetze),
    }


def _fehler_stats(deltas: list[float]) -> dict:
    if not deltas:
        return {"n": 0}
    absolut = sorted(abs(d) for d in deltas)
    zu_spaet = sum(1 for d in deltas if d < 0)

    def perzentil(p: float) -> float:
        # lineare Interpolation, damit kleine n nicht springen
        if len(absolut) == 1:
            return absolut[0]
        pos = p / 100 * (len(absolut) - 1)
        lo = int(pos)
        hi = min(lo + 1, len(absolut) - 1)
        return absolut[lo] + (absolut[hi] - absolut[lo]) * (pos - lo)

    def innerhalb(sekunden: float) -> float:
        return sum(1 for a in absolut if a <= sekunden) / len(absolut) * 100

    return {
        "n": len(deltas),
        "zu_spaet_pct": zu_spaet / len(deltas) * 100,
        "zu_frueh_pct": (len(deltas) - zu_spaet) / len(deltas) * 100,
        "median": statistics.median(deltas),
        "mittel": statistics.fmean(deltas),
        # Populations-Sigma: die 287 Werte SIND die Grundgesamtheit der
        # bewerteten Transitions, keine Stichprobe daraus.
        "sigma": statistics.pstdev(deltas) if len(deltas) > 1 else 0.0,
        "p50_abs": perzentil(50),
        "p75_abs": perzentil(75),
        "p90_abs": perzentil(90),
        "p95_abs": perzentil(95),
        "innerhalb_4s_pct": innerhalb(4),
        "innerhalb_8s_pct": innerhalb(8),
        "innerhalb_16s_pct": innerhalb(16),
    }


def auswerten(mode: str, predictions: dict | None = None,
              nur_verwertbar: bool = False) -> dict:
    datensaetze, hinweise = _read_gt_files(mode, nur_verwertbar=nur_verwertbar)
    roh = _collect(datensaetze, predictions)

    v = roh["verdicts"]
    correct = v.get("correct", 0)
    timing_off = v.get("timing_off", 0)
    not_a = v.get("not_a_transition", 0)
    bewertet = correct + timing_off + not_a
    echt_gefunden = correct + timing_off
    missed = roh["missed"]

    return {
        "mode": mode,
        "hinweise": hinweise,
        "n_sets": roh["n_sets"],
        "bewertet": bewertet,
        "verdicts": v,
        "missed": missed,
        "ohne_vorhersage": roh["ohne_vorhersage"],
        "hat_vorhersagen": predictions is not None,
        # Recall: von allen echten Transitions (gefundene + uebersehene) -
        # wie viele hat die Engine ueberhaupt gefunden?
        "recall_pct": echt_gefunden / (echt_gefunden + missed) * 100 if echt_gefunden + missed else 0.0,
        # Precision: von allen Markern der Engine - wie viele waren echt?
        "precision_pct": echt_gefunden / bewertet * 100 if bewertet else 0.0,
        # Strikt korrekt: Marker, den der Mensch ohne Korrektur akzeptiert hat.
        "strikt_korrekt_pct": correct / bewertet * 100 if bewertet else 0.0,
        "timing": _fehler_stats(roh["deltas"]),
        "regression_correct": _fehler_stats(roh["correct_deltas"]),
    }


# ---------------------------------------------------------------- Ausgabe


def _zeile(label: str, wert: str) -> str:
    return f"  {label:<34} {wert}"


def bericht(e: dict, vergleich: dict | None = None) -> str:
    z: list[str] = []
    z.append("=" * 72)
    z.append(f"  MixCoach - Timing-Bias der Transitions-Erkennung  [mode={e['mode']}]")
    z.append("=" * 72)

    for h in e["hinweise"]:
        z.append(f"  ! {h}")
    if e["hinweise"]:
        z.append("")

    z.append("DATENBASIS")
    z.append(_zeile("Sets", str(e["n_sets"])))
    z.append(_zeile("bewertete Transitions", str(e["bewertet"])))
    for k in ("correct", "timing_off", "not_a_transition"):
        n = e["verdicts"].get(k, 0)
        anteil = n / e["bewertet"] * 100 if e["bewertet"] else 0
        z.append(_zeile(f"  {k}", f"{n:>5}  ({anteil:.0f} %)"))
    z.append(_zeile("zusaetzlich als 'missed' erfasst", str(e["missed"])))
    z.append("")

    z.append("ERKENNUNG")
    z.append(_zeile("Recall", f"{e['recall_pct']:.0f} %"))
    z.append(_zeile("Precision", f"{e['precision_pct']:.0f} %"))
    z.append(_zeile("strikt korrekt", f"{e['strikt_korrekt_pct']:.0f} %"))
    z.append("")

    t = e["timing"]
    z.append(f"TIMING-FEHLER auf den {t.get('n', 0)} 'timing_off' mit correctedSec")
    z.append("  (negativ = Engine zu spaet)")
    if t.get("n"):
        z.append(_zeile("Engine zu spaet", f"{t['zu_spaet_pct']:.0f} %"))
        z.append(_zeile("Engine zu frueh", f"{t['zu_frueh_pct']:.0f} %"))
        z.append(_zeile("Median", f"{t['median']:+.2f} s"))
        z.append(_zeile("Mittelwert", f"{t['mittel']:+.2f} s"))
        z.append(_zeile("Sigma", f"{t['sigma']:.2f} s"))
        z.append("")
        z.append(_zeile("Absolutfehler p50 / p75", f"{t['p50_abs']:.1f} s / {t['p75_abs']:.1f} s"))
        z.append(_zeile("Absolutfehler p90 / p95", f"{t['p90_abs']:.1f} s / {t['p95_abs']:.1f} s"))
        z.append("")
        z.append(_zeile("innerhalb 4 s", f"{t['innerhalb_4s_pct']:.0f} %"))
        z.append(_zeile("innerhalb 8 s", f"{t['innerhalb_8s_pct']:.0f} %"))
        z.append(_zeile("innerhalb 16 s", f"{t['innerhalb_16s_pct']:.0f} %"))
    else:
        z.append("  keine Daten")
    z.append("")

    r = e["regression_correct"]
    z.append(f"REGRESSIONSWAECHTER - Gruppe 'correct' (n={r.get('n', 0)})")
    z.append("  Nicht hierauf optimieren, nur auf Verschlechterung achten.")
    if not e["hat_vorhersagen"]:
        z.append("  Ohne --predictions ist der Fehler hier per Definition 0 -")
        z.append("  die Gruppe wird erst mit einer neuen Erkennung aussagekraeftig.")
    elif r.get("n"):
        z.append(_zeile("innerhalb 8 s", f"{r['innerhalb_8s_pct']:.0f} %"))
        z.append(_zeile("Median", f"{r['median']:+.2f} s"))
    z.append("")

    if e["ohne_vorhersage"]:
        z.append(f"  ! {e['ohne_vorhersage']} Transitions ohne Vorhersage - nicht gewertet")
        z.append("")

    if vergleich is not None:
        z.append("=" * 72)
        z.append("  VORHER / NACHHER")
        z.append("=" * 72)
        a, b = vergleich["timing"], e["timing"]
        z.append(f"  {'Kennzahl':<26}{'vorher':>12}{'nachher':>12}{'Delta':>12}")
        for label, key, fmt in [
            ("Median (s)", "median", "{:+.2f}"),
            ("Sigma (s)", "sigma", "{:.2f}"),
            ("innerhalb 4 s (%)", "innerhalb_4s_pct", "{:.0f}"),
            ("innerhalb 8 s (%)", "innerhalb_8s_pct", "{:.0f}"),
            ("innerhalb 16 s (%)", "innerhalb_16s_pct", "{:.0f}"),
            ("Absolutfehler p90 (s)", "p90_abs", "{:.1f}"),
        ]:
            va, vb = a.get(key), b.get(key)
            if va is None or vb is None:
                continue
            z.append(f"  {label:<26}{fmt.format(va):>12}{fmt.format(vb):>12}{vb - va:>+12.2f}")
        z.append("")
        z.append("  Sigma ist die entscheidende Zahl: sinkt sie nicht, wurde nur ein")
        z.append("  konstanter Offset eingebaut und das Problem besteht weiter.")
        z.append("")

    return "\n".join(z)


TOLERANZEN = {"n": 0, "zu_spaet_pct": 0.5, "median": 0.01, "sigma": 0.01,
              "innerhalb_8s_pct": 0.5, "innerhalb_16s_pct": 0.5}


def pruefe_sollwerte(e: dict) -> tuple[bool, list[str]]:
    """Selbsttest gegen den eingefrorenen Stand DES JEWEILIGEN MODUS.

    Jeder Modus hat eigene Sollwerte, weil er eine andere Grundgesamtheit
    zaehlt. Der Selbsttest sagt darum immer an, gegen welchen Stand er
    prueft - sonst sieht ein Moduswechsel wie eine Regression aus.
    """
    t = e["timing"]
    soll = SOLLWERTE[e["mode"]]
    meldungen = [f"  Stand: {soll['quelle']}"]

    if soll.get("n") is None:
        meldungen.append("  Fuer diesen Modus ist noch kein Stand eingefroren -")
        meldungen.append("  gemessen wurde soeben:")
        for key in PRUEF_SCHLUESSEL:
            meldungen.append(f"    {key}: {t.get(key)}")
        return False, meldungen

    ok = True
    for key in PRUEF_SCHLUESSEL:
        ist, erwartet = t.get(key), soll[key]
        if ist is None or abs(ist - erwartet) > TOLERANZEN[key]:
            ok = False
            meldungen.append(f"  ABWEICHUNG {key}: soll {erwartet}, ist {ist}")
        else:
            meldungen.append(f"  ok         {key}: {ist} (soll {erwartet})")
    return ok, meldungen


# ---------------------------------------------------------------- CLI


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mode", choices=["spec", "analyse", "dedup"], default="dedup",
                   help="dedup (Vorgabe): je AUFNAHME (fileName) der zuletzt "
                        "bearbeitete Stand - REC001 zaehlt einmal, nicht elfmal. "
                        "analyse: je analysisId (das war bis 31.07.2026 'dedup'). "
                        "spec: beide GT-Ordner roh, reproduziert die Zahlen aus "
                        "CLAUDE_CODE_SPEC_2026-07-29.md.")
    p.add_argument("--nur-verwertbar", action="store_true", dest="nur_verwertbar",
                   help="Aufnahmen ohne Ergebnis-JSON und abgebrochene "
                        "Label-Sitzungen aussortieren (siehe tools.eval.gt_status)")
    p.add_argument("--predictions", type=Path,
                   help="JSON analysisId -> {index: start_sec}; ersetzt midSec "
                        "als Engine-Zeitpunkt und schaltet den Vorher/Nachher-Block frei")
    p.add_argument("--check", action="store_true",
                   help="Sollwerte pruefen, Exit-Code 1 bei Abweichung")
    p.add_argument("--json", type=Path, help="Ergebnis zusaetzlich als JSON ablegen")
    args = p.parse_args()

    vorher = None
    predictions = None
    if args.predictions:
        predictions = json.loads(args.predictions.read_text(encoding="utf-8"))
        vorher = auswerten(args.mode, predictions=None,
                           nur_verwertbar=args.nur_verwertbar)

    ergebnis = auswerten(args.mode, predictions=predictions,
                         nur_verwertbar=args.nur_verwertbar)
    print(bericht(ergebnis, vergleich=vorher))

    if args.json:
        args.json.write_text(json.dumps(ergebnis, indent=2, ensure_ascii=False),
                             encoding="utf-8")
        print(f"  JSON geschrieben: {args.json}\n")

    if args.check:
        if predictions is not None:
            print("  --check gilt nur ohne --predictions (Sollwerte = Ausgangsstand).")
            return 1
        if args.nur_verwertbar:
            print("  --check gilt nur ohne --nur-verwertbar (die Sollwerte sind "
                  "auf dem ungefilterten Bestand gemessen).")
            return 1
        ok, meldungen = pruefe_sollwerte(ergebnis)
        print(f"SELBSTTEST  [mode={ergebnis['mode']}]")
        print("\n".join(meldungen))
        print("\n  ERGEBNIS: " + ("reproduziert." if ok else "NICHT reproduziert."))
        return 0 if ok else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
