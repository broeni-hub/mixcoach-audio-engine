"""Die Tracklist des DJs in einen gespeicherten Report eintragen (A3).

    python -m tools.tracklist_nachtragen <analysisId> <tracklist.txt>
    python -m tools.tracklist_nachtragen <analysisId> <tracklist.txt> --write

WOFUER
------
Ein fremder DJ bekommt heute 0 % Tracknamen: der Fingerabdruck-Index kennt
6113 Tracks, und das sind Sebastians. Statt den Fremden zu bitten, seine
Sammlung hochzuladen, bittet man ihn um seine TRACKLIST - eine Datei statt
dreihundert.

DAS FORMAT
----------
Eine Zeile je Track, in der Reihenfolge des Sets. Zeiten sind optional, aber
viel wert:

    00:00 Mosca - Orange Jack          <- mit Zeiten: robust, auch wenn die
    05:42 Facta - Ditto                   Engine einen Uebergang uebersieht
    09:10 Mosca - Eva Mendes

    1. Mosca - Orange Jack             <- nur Reihenfolge: geht nur, wenn
    2. Facta - Ditto                      die Zahlen passen (n Tracks
    3. Mosca - Eva Mendes                 brauchen n-1 Uebergaenge)

Erkannt werden [05:42], 05:42, 5.42, "05:42 -" und fuehrende Nummerierungen.

WAS NICHT PASSIERT
------------------
Wo der Fingerabdruck schon einen Treffer hat, bleibt der stehen - gemessen
schlaegt genannt. Und wenn ohne Zeiten die Zahlen nicht zusammenpassen, wird
NICHTS zugeordnet: nach Position zu raten wuerde alle folgenden Namen um eins
verschieben, und dann steht unter jedem Uebergang ein falscher, aber
selbstbewusster Name.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.audio.pipeline.scoring_version import naechste_revision, revision_von  # noqa: E402
from app.audio.tracklist import lesen, zuordnen  # noqa: E402
from app.paths import RESULTS_DIR  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("analysis_id")
    p.add_argument("tracklist", type=Path)
    p.add_argument("--write", action="store_true")
    p.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    args = p.parse_args()

    pfad = args.results_dir / f"{args.analysis_id}.json"
    if not pfad.exists():
        print(f"FEHLT: {pfad}")
        return 1
    if not args.tracklist.exists():
        print(f"FEHLT: {args.tracklist}")
        return 1

    report = json.loads(pfad.read_text(encoding="utf-8"))
    tracks = lesen(args.tracklist.read_text(encoding="utf-8", errors="replace"))
    uebergaenge = report.get("setTransitions") or []

    vorher = sum(1 for t in uebergaenge if t.get("track_in") or t.get("track_out"))
    bericht = zuordnen(uebergaenge, tracks)
    nachher = sum(1 for t in uebergaenge if t.get("track_in") or t.get("track_out"))

    print(f"Aufnahme      : {report.get('fileName')}")
    print(f"Tracklist     : {bericht['tracks']} Tracks"
          f"{' (mit Zeiten)' if bericht['weg'] == 'zeiten' else ' (nur Reihenfolge)'}")
    print(f"Uebergaenge   : {bericht['uebergaenge']}")
    print(f"Namen vorher  : {vorher}")
    print(f"Namen nachher : {nachher}")
    if bericht["grund"]:
        print(f"\n  NICHT ZUGEORDNET: {bericht['grund']}")
        print("  Abhilfe: Zeiten in die Tracklist schreiben, dann geht es auch")
        print("  bei unterschiedlichen Zahlen.")
        return 0
    print()
    for t in uebergaenge:
        if t.get("detection") == "tracklist":
            m = int(t.get("start_sec") or t.get("mid_sec") or 0)
            print(f"  {m//60:>3}:{m%60:02d}  {t.get('track_out')} → {t.get('track_in')}")

    if not args.write:
        print("\n  PROBELAUF - nichts geschrieben. Mit --write wiederholen.")
        return 0

    report["setTransitions"] = uebergaenge
    alt = revision_von(report)
    report["reportRevision"] = naechste_revision(report)
    pfad.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Geschrieben. reportRevision: {alt or 'fehlt'} -> {report['reportRevision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
