"""Fuellt loudness_jump_db in aelteren Reports nach - dem Messwert, der von
allen am staerksten mit Sebastians Urteil zusammenhaengt.

Gemessen am 13.08.2026 gegen seine eigenen Bewertungen:

    |loudness_jump_db|   Spearman -0,463  (n=57)
    beat_alignment       Spearman +0,315  (n=146)
    composite (Test)     Spearman +0,220  (n= 52)
    quality_score        Spearman +0,014  (n=205)

Doppelt so stark wie alles andere, mit dem physikalisch richtigen Vorzeichen
(groesserer Pegelsprung = schlechtere Bewertung), echter Spannweite
(-9,0 bis +9,3 dB, sigma 2,65) und nur 8 % exakten Nullen. Das ist der
aussichtsreichste Kandidat fuer eine Kopfzahl, die wirklich etwas misst - und
fuer Bedingung 3 der Live-Schwelle, die auf beat_alignment (sigma 2,59) und
bass_overlap (90 % exakt 0 oder 100) nicht ruhen kann.

Warum ueberhaupt ein Nachtrag noetig ist: der Wert fehlt nicht zufaellig,
sondern blockweise. 31 Reports haben ihn vollstaendig, 19 gar nicht, KEINER
teilweise - die leeren stammen alle aus der Zeit vor dem 17.07.2026, als die
Lautheitsmessung eingebaut wurde. `backfill_loudness_curves.py` hat damals nur
die KURVE nachgetragen, nicht den Sprung je Uebergang.

Bewusst nur EIN Rechenweg: aus dem Audio, exakt wie die Live-Pipeline
(loudness_curve -> annotate_transitions). Aus der gespeicherten volumeCurve zu
rechnen waere schneller und ginge auch fuer Reports ohne Audio - es waere aber
eine ZWEITE Rechenvorschrift fuer dasselbe Feld, und genau davor warnt
app/audio/pipeline/scoring_version.py. Reports ohne Audio bleiben deshalb
ehrlich leer.

Die Uebergangs-Fenster (start_sec/end_sec) kommen unveraendert aus dem
gespeicherten Report - es aendert sich kein Zeitpunkt, nur ein Messwert kommt
dazu.

Sicherung: die Reports sind versioniert. 'git checkout -- daten/analysis_results/'
holt alles zurueck.

    python -m tools.backfill_loudness_jump --dry-run
    python -m tools.backfill_loudness_jump
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.audio.loudness import annotate_transitions, loudness_curve  # noqa: E402
from app.paths import RESULTS_DIR  # noqa: E402

SR = 22050  # wie die Analyse selbst (app/main.py:223)
AUDIO_SUFFIXES = (".mp3", ".wav", ".WAV", ".flac", ".m4a", ".aiff", ".aif")


def _audio_pfad(analysis_id: str) -> Path | None:
    for suffix in AUDIO_SUFFIXES:
        p = RESULTS_DIR / f"{analysis_id}{suffix}"
        if p.exists():
            return p
    return None


def _kandidaten(ein_set: str | None) -> tuple[list, int]:
    """(bearbeitbar, uebersprungen_ohne_audio)"""
    offen, ohne_audio = [], 0
    for pfad in sorted(RESULTS_DIR.glob("*.json")):
        if ein_set and pfad.stem != ein_set:
            continue
        try:
            report = json.loads(pfad.read_text(encoding="utf-8"))
        except Exception:
            continue
        trans = report.get("setTransitions") or []
        if not trans:
            continue
        if any(t.get("loudness_jump_db") is not None for t in trans):
            continue
        audio = _audio_pfad(pfad.stem)
        if audio is None:
            ohne_audio += 1
            continue
        offen.append((pfad, report, audio))
    return offen, ohne_audio


def _verarbeite(report: dict, audio_pfad: Path) -> dict:
    import librosa

    waveform, _ = librosa.load(str(audio_pfad), sr=SR, mono=True)
    zeiten, werte = loudness_curve(waveform, SR)
    if zeiten.size == 0:
        return {"gefuellt": 0, "gesamt": len(report["setTransitions"]),
                "grund": "Aufnahme kuerzer als das Messfenster"}

    dauer = len(waveform) / SR
    # annotate_transitions arbeitet auf der internen Form; die Fenster stehen
    # unter denselben Namen im gespeicherten Report, also direkt nutzbar.
    annotate_transitions(report["setTransitions"], zeiten, werte, dauer)

    gefuellt = sum(1 for t in report["setTransitions"]
                   if t.get("loudness_jump_db") is not None)
    return {"gefuellt": gefuellt, "gesamt": len(report["setTransitions"]),
            "grund": ""}


def _schreibe(pfad: Path, report: dict) -> None:
    tmp = pfad.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(report), encoding="utf-8")
    os.replace(tmp, pfad)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--set", dest="ein_set", help="genau diese analysisId")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    offen, ohne_audio = _kandidaten(args.ein_set)
    if args.limit:
        offen = offen[: args.limit]

    if not offen:
        print("Nichts nachzutragen.")
        if ohne_audio:
            print(f"  {ohne_audio} Report(s) ohne Audio - bleiben ehrlich leer.")
        return 0

    n_ue = sum(len(r["setTransitions"]) for _, r, _ in offen)
    print(f"{len(offen)} Report(s), {n_ue} Uebergaenge ohne loudness_jump_db.")
    if ohne_audio:
        print(f"{ohne_audio} weitere(r) ohne Audio - bleiben leer, kein Ersatzwert.")
    if args.dry_run:
        for pfad, report, _ in offen:
            print(f"  {pfad.stem}  {len(report['setTransitions']):>3} Uebergaenge  "
                  f"{report.get('fileName')}")
        print("\n--dry-run: nichts geschrieben.")
        return 0

    t0 = time.time()
    summe = gesamt = 0
    for i, (pfad, report, audio) in enumerate(offen, 1):
        name = report.get("fileName") or pfad.stem
        print(f"[{i}/{len(offen)}] {name} ...", flush=True)
        try:
            st = _verarbeite(report, audio)
        except Exception as exc:
            print(f"    FEHLER: {type(exc).__name__}: {exc} - Report unveraendert")
            continue
        _schreibe(pfad, report)
        summe += st["gefuellt"]
        gesamt += st["gesamt"]
        hinweis = f"  ({st['grund']})" if st["grund"] else ""
        print(f"    {st['gefuellt']}/{st['gesamt']} gefuellt{hinweis}")

    print()
    print(f"Fertig in {(time.time()-t0)/60:.1f} min.")
    print(f"  nachgetragen: {summe} von {gesamt} Uebergaengen")
    if summe < gesamt:
        print(f"  {gesamt - summe} blieben leer - dort liegt ein Messfenster am")
        print("  Set-Rand. Das ist der vorgesehene Fall, kein Fehler.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
