"""Fuellt composite_quality_score in bereits vorhandenen Analyse-Reports nach.

Warum: der Composite ist der einzige Uebergangs-Score, der je gegen menschliche
Bewertungen gefittet wurde (0,47 Training / 0,62 Test, gegen ~0 beim
angezeigten quality_score). Er steht aber nur in 128 von 431 Uebergaengen, weil
seine zwei staerksten Dimensionen - vocal_overlap (Gewicht 0,42) und
harmonic_clash (0,09) - aus der Demucs-Stem-Trennung kommen, und die war beim
Analysieren aus.

Gemessen am 10.08.2026: von Sebastians bewerteten Uebergaengen haben heute
**8** einen Composite. Mit Audio nachrechenbar waeren **138 weitere**. Erst
danach laesst sich die Frage "traegt der Composite als Kopfzahl?" ueberhaupt
messen statt meinen - 8 Punkte sind keine Datenbasis.

Was hier NICHT passiert: die Erkennung wird nicht neu gerechnet. Die Fenster
(start_sec/mid_sec/end_sec) kommen unveraendert aus dem gespeicherten Report,
es aendert sich also kein einziger Uebergangs-Zeitpunkt. Ergaenzt werden nur
die fuenf Dimensionen und der Composite daraus.

Was neu aus dem Audio gerechnet wird - bewusst, statt es aus dem Report zu
lesen: Energiekurve und Beat-Raster. Der Report enthaelt beides nur in der
gerundeten Frontend-Form (energyCurve als {t, value} mit ganzen Zahlen), und
exit_quality erwartet {time, rms}. Aus gerundeten Anzeigewerten einen Messwert
zu bauen waere genau die Sorte Pseudo-Praezision, gegen die dieses Projekt
antritt.

Ehrlichkeitslinie: schlaegt die Stem-Trennung fuer ein Fenster fehl, bleiben
harmonic_clash und vocal_overlap None und der Composite wird aus dem
gewichteten Rest gebildet - nie ein geratener Wert. Wie viele Fenster das
betrifft, steht in der Zusammenfassung.

Sicherung: die Reports sind versioniert. Geht ein Lauf schief, holt
'git checkout -- daten/analysis_results/' alles zurueck.

    python -m tools.backfill_composite --dry-run
    python -m tools.backfill_composite --nur-bewertete
    python -m tools.backfill_composite --set 04804f27-2755-4db3-8f0b-f57d3315737c
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.audio.beats import detect_beat_grid  # noqa: E402
from app.audio.energy import calculate_energy_curve  # noqa: E402
from app.audio.scoring.beat_alignment import annotate_beat_alignment  # noqa: E402
from app.audio.scoring.composite import annotate_composite_scores  # noqa: E402
from app.audio.scoring.exit_quality import annotate_exit_quality  # noqa: E402
from app.audio.scoring.stem_annotate import annotate_stem_based_scores  # noqa: E402
from app.paths import RESULTS_DIR  # noqa: E402

SR = 22050  # wie die Analyse selbst (app/main.py:223)
AUDIO_SUFFIXES = (".mp3", ".wav", ".WAV", ".flac", ".m4a", ".aiff", ".aif")
LABELS_CSV = Path(__file__).resolve().parents[1] / "labels_prefilled.csv"

DIMENSIONEN = ("harmonic_clash_score", "vocal_overlap_score",
               "exit_quality_score", "beat_alignment_score")


class _Audio:
    """Minimal-Huelle, wie sie beats.py und energy.py erwarten."""

    def __init__(self, waveform, filename):
        self.waveform = waveform
        self.sample_rate = SR
        self.duration_seconds = len(waveform) / SR
        self.filename = filename


def _audio_pfad(analysis_id: str) -> Path | None:
    for suffix in AUDIO_SUFFIXES:
        p = RESULTS_DIR / f"{analysis_id}{suffix}"
        if p.exists():
            return p
    return None


def _bewertete_sets() -> set[str]:
    """set_ids, zu denen es menschliche Bewertungen gibt - die sind zuerst
    dran, weil nur sie den Refit tragen."""
    if not LABELS_CSV.exists():
        return set()
    out: set[str] = set()
    with open(LABELS_CSV, encoding="cp1252", errors="replace") as f:
        for row in csv.DictReader(f, delimiter=";"):
            try:
                float(str(row.get("human_rating", "")).replace(",", "."))
            except (TypeError, ValueError):
                continue
            if row.get("set_id"):
                out.add(row["set_id"])
    return out


def _kandidaten(nur_bewertete: bool, ein_set: str | None) -> list[tuple[str, dict, Path]]:
    bewertet = _bewertete_sets() if nur_bewertete else None
    out = []
    for pfad in sorted(RESULTS_DIR.glob("*.json")):
        aid = pfad.stem
        if ein_set and aid != ein_set:
            continue
        if bewertet is not None and aid not in bewertet:
            continue
        try:
            report = json.loads(pfad.read_text(encoding="utf-8"))
        except Exception:
            continue
        trans = report.get("setTransitions") or []
        if not trans:
            continue
        if all(t.get("composite_quality_score") is not None for t in trans):
            continue  # schon vollstaendig
        audio = _audio_pfad(aid)
        if audio is None:
            continue
        out.append((aid, report, audio))
    return out


def _verarbeite(aid: str, report: dict, audio_pfad: Path) -> dict:
    import librosa

    waveform, _ = librosa.load(str(audio_pfad), sr=SR, mono=True)
    audio = _Audio(waveform, audio_pfad.name)

    energie = calculate_energy_curve(audio, window_seconds=1.0)
    beats = detect_beat_grid(audio).get("beats", [])

    # Arbeitskopien: die Scoring-Module erwarten die interne Form mit einem
    # verschachtelten scores-Dict. phrase kommt aus dem gespeicherten
    # phrase_alignment_score - im Composite hat es Gewicht 0,0, es geht also
    # nur in den breakdown ein, nicht in die Zahl.
    arbeit = []
    for t in report["setTransitions"]:
        arbeit.append({
            "start_sec": t.get("start_sec"),
            "mid_sec": t.get("mid_sec"),
            "end_sec": t.get("end_sec"),
            "scores": {"phrase": t.get("phrase_alignment_score")},
        })

    annotate_beat_alignment(arbeit, beats)
    annotate_exit_quality(arbeit, energie.get("points", []))
    annotate_stem_based_scores(arbeit, waveform, SR)
    annotate_composite_scores(arbeit)

    gefuellt = stems_fehl = 0
    for ziel, quelle in zip(report["setTransitions"], arbeit):
        for feld in DIMENSIONEN:
            ziel[feld] = quelle.get(feld)
        ziel["composite_quality_score"] = quelle.get("composite_quality_score")
        ziel["composite_breakdown"] = quelle.get("composite_breakdown")
        if ziel["composite_quality_score"] is not None:
            gefuellt += 1
        if quelle.get("vocal_overlap_score") is None:
            stems_fehl += 1

    report["compositeBackfilledAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return {"gefuellt": gefuellt, "gesamt": len(arbeit), "stems_fehl": stems_fehl}


def _schreibe(pfad: Path, report: dict) -> None:
    """Erst daneben schreiben, dann ersetzen - ein Absturz mittendrin darf
    keinen halben Report hinterlassen."""
    tmp = pfad.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(report), encoding="utf-8")
    os.replace(tmp, pfad)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true",
                    help="nur zeigen, was zu tun waere")
    ap.add_argument("--nur-bewertete", action="store_true",
                    help="nur Aufnahmen, zu denen es menschliche Bewertungen gibt")
    ap.add_argument("--set", dest="ein_set", help="genau diese analysisId")
    ap.add_argument("--limit", type=int, help="hoechstens so viele Aufnahmen")
    args = ap.parse_args()

    kandidaten = _kandidaten(args.nur_bewertete, args.ein_set)
    if args.limit:
        kandidaten = kandidaten[: args.limit]

    if not kandidaten:
        print("Nichts zu tun: kein Report ohne Composite, zu dem Audio vorliegt.")
        return 0

    offen = sum(sum(1 for t in r["setTransitions"]
                    if t.get("composite_quality_score") is None)
                for _, r, _ in kandidaten)
    print(f"{len(kandidaten)} Aufnahme(n), {offen} Uebergaenge ohne Composite.")
    if args.dry_run:
        for aid, report, audio in kandidaten:
            n = sum(1 for t in report["setTransitions"]
                    if t.get("composite_quality_score") is None)
            print(f"  {aid}  {n:>3} offen  {report.get('fileName')}")
        print("\n--dry-run: nichts geschrieben.")
        return 0

    t_start = time.time()
    summe_gefuellt = summe_gesamt = summe_fehl = 0
    for i, (aid, report, audio) in enumerate(kandidaten, 1):
        name = report.get("fileName") or aid
        print(f"[{i}/{len(kandidaten)}] {name} ...", flush=True)
        t0 = time.time()
        try:
            st = _verarbeite(aid, report, audio)
        except Exception as exc:
            print(f"    FEHLER: {type(exc).__name__}: {exc} - Report unveraendert")
            continue
        _schreibe(RESULTS_DIR / f"{aid}.json", report)
        summe_gefuellt += st["gefuellt"]
        summe_gesamt += st["gesamt"]
        summe_fehl += st["stems_fehl"]
        print(f"    {st['gefuellt']}/{st['gesamt']} Composite, "
              f"{st['stems_fehl']} ohne Stems, {time.time()-t0:.0f}s")

    print()
    print(f"Fertig in {(time.time()-t_start)/60:.1f} min.")
    print(f"  Composite gefuellt: {summe_gefuellt} von {summe_gesamt} Uebergaengen")
    if summe_fehl:
        print(f"  ohne Stem-Werte:    {summe_fehl} - dort ruht der Composite auf")
        print(f"                      den uebrigen Dimensionen, nicht auf einem Rateswert")
    print()
    print("Naechster Schritt: die Gewichte auf der groesseren Stichprobe neu fitten")
    print("  python -m app.calibration.fit_composite_weights")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
