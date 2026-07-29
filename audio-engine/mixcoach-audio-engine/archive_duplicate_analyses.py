"""MixCoach - einmaliges Aufraeum-Script: archiviert Duplikat-Analysen.

Wird eine Datei mehrfach hochgeladen/erneut analysiert, haeuft sich
analysis_results/ mit mehreren Ergebnis-JSONs derselben Aufnahme an - das
verzerrt export_labels_v3.py (dieselbe Aufnahme taucht mehrfach in
labels_prefilled.csv auf) und die Analysen-Liste im Frontend.

Dieses Script gruppiert alle Analysen nach ihrem Dateinamen (fileName),
behaelt pro Gruppe nur die NEUESTE (nach Datei-Zeitstempel) und verschiebt
den Rest nach analysis_results/archived/ - genau wie der Delete-Button im
Frontend: nichts wird hart geloescht, alles bleibt fuer Retrain/Nachschlagen
erhalten.

Aufruf (im Projektordner):
    python archive_duplicate_analyses.py --results-dir analysis_results
    python archive_duplicate_analyses.py --results-dir analysis_results --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Archiviert Duplikat-Analysen (nur die neueste je Dateiname bleibt aktiv)."
    )
    parser.add_argument("--results-dir", type=Path, default=Path("analysis_results"))
    parser.add_argument("--dry-run", action="store_true", help="Nur anzeigen, nichts verschieben.")
    args = parser.parse_args()

    results_dir: Path = args.results_dir
    if not results_dir.exists():
        print(f"FEHLER: Ordner '{results_dir}' nicht gefunden.")
        return 1

    archived_dir = results_dir / "archived"

    groups: dict[str, list[Path]] = defaultdict(list)
    unreadable: list[str] = []

    for path in sorted(results_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            unreadable.append(f"{path.name} ({e})")
            continue
        file_name = (data.get("fileName") or data.get("filename") or "").strip()
        if not file_name:
            continue
        groups[file_name.lower()].append(path)

    print(f"Analyse-Ordner: {results_dir.resolve()}\n")

    to_archive: list[Path] = []
    for file_name, paths in sorted(groups.items()):
        if len(paths) < 2:
            continue
        paths_sorted = sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)
        newest, rest = paths_sorted[0], paths_sorted[1:]
        print(f"{file_name}: {len(paths_sorted)}x vorhanden -> behalte {newest.name} (neueste), archiviere {len(rest)}")
        to_archive.extend(rest)

    if not to_archive:
        print("Keine Duplikate gefunden - nichts zu tun.")
        if unreadable:
            _print_unreadable(unreadable)
        return 0

    suffix = " (DRY RUN - nichts wird tatsaechlich verschoben)" if args.dry_run else ""
    print(f"\n{len(to_archive)} Analyse(n) werden nach '{archived_dir.name}/' verschoben{suffix}:")

    if not args.dry_run:
        archived_dir.mkdir(exist_ok=True)

    locked: list[str] = []
    for path in to_archive:
        print(f"  - {path.name}")
        if args.dry_run:
            continue
        stem = path.stem
        try:
            path.rename(archived_dir / path.name)
        except OSError as e:
            locked.append(f"{path.name} ({e})")
            continue
        # Audio-Begleitdatei (gleicher Dateistamm, andere Endung) mit archivieren.
        for sibling in results_dir.glob(f"{stem}.*"):
            try:
                sibling.rename(archived_dir / sibling.name)
            except OSError as e:
                locked.append(f"{sibling.name} ({e})")

    if locked:
        print(f"\nWARNUNG: {len(locked)} Datei(en) waren gesperrt (z.B. Backend laeuft) und konnten nicht verschoben werden:")
        for entry in locked:
            print(f"  - {entry}")
        print("  -> Backend kurz stoppen und das Script erneut ausfuehren, um diese nachzuholen.")

    if unreadable:
        _print_unreadable(unreadable)

    print("\nFertig." + (" (Dry Run - es wurde nichts geaendert)" if args.dry_run else ""))
    return 0


def _print_unreadable(unreadable: list[str]) -> None:
    print(f"\nWARNUNG: {len(unreadable)} Datei(en) nicht lesbar, uebersprungen:")
    for entry in unreadable:
        print(f"  - {entry}")


if __name__ == "__main__":
    sys.exit(main())
