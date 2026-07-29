"""
MixCoach – Ergebnis-Rettung.

Sucht auf der Platte nach den verschollenen Ergebnis-JSONs. Gesucht wird
nach Dateinamen {analysis_id}.json fuer alle IDs, die in ground_truth/
liegen, aber im aktuellen analysis_results/ fehlen.

Aufruf (im Projektordner):
    # Nur suchen und anzeigen:
    python find_lost_results.py

    # Suchen und Funde nach analysis_results/ zurueckkopieren:
    python find_lost_results.py --copy

    # Andere/weitere Suchorte angeben:
    python find_lost_results.py --search-root "C:\\Users\\Sebro\\OneDrive" --search-root "D:\\"

Standard-Suchorte: C:\\Users\\Sebro\\OneDrive und C:\\Projekte
(anpassbar ueber --search-root; mehrfach angebbar).
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

# Ordner, in denen sicher nichts liegt - beschleunigt die Suche enorm.
SKIP_DIRS = {
    "Windows", "Program Files", "Program Files (x86)", "ProgramData",
    "$Recycle.Bin", "AppData", "node_modules", ".git", "__pycache__",
    ".venv", "venv", "System Volume Information",
}

DEFAULT_ROOTS = [
    Path(r"C:\Users\Sebro\OneDrive"),
    Path(r"C:\Projekte"),
]


def missing_ids(ground_truth_dir: Path, results_dir: Path) -> set[str]:
    gt_ids = {p.stem for p in ground_truth_dir.glob("*.json")}
    have = {p.stem for p in results_dir.glob("*.json")} if results_dir.exists() else set()
    return gt_ids - have


def search(roots: list[Path], wanted: set[str], exclude: Path) -> dict[str, list[Path]]:
    """Sucht {id}.json unter allen roots. exclude = aktueller results-Ordner."""
    wanted_names = {f"{i}.json": i for i in wanted}
    found: dict[str, list[Path]] = {}
    exclude = exclude.resolve()

    for root in roots:
        if not root.exists():
            print(f"Hinweis: Suchort {root} existiert nicht - uebersprungen.")
            continue
        print(f"Durchsuche {root} ...")
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            if Path(dirpath).resolve() == exclude:
                continue
            for name in filenames:
                if name in wanted_names:
                    aid = wanted_names[name]
                    found.setdefault(aid, []).append(Path(dirpath) / name)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description="Verschollene Ergebnis-JSONs finden")
    parser.add_argument("--ground-truth-dir", type=Path, default=Path("ground_truth"))
    parser.add_argument("--results-dir", type=Path, default=Path("analysis_results"))
    parser.add_argument("--search-root", action="append", type=Path, default=None,
                        help="Suchort (mehrfach angebbar). Default: OneDrive + C:\\Projekte")
    parser.add_argument("--copy", action="store_true",
                        help="Funde nach analysis_results/ zurueckkopieren")
    args = parser.parse_args()

    if not args.ground_truth_dir.exists():
        print(f"FEHLER: {args.ground_truth_dir} nicht gefunden - "
              f"bitte im Projektordner ausfuehren.")
        return 1

    wanted = missing_ids(args.ground_truth_dir, args.results_dir)
    if not wanted:
        print("Nichts zu suchen: Zu allen Ground-Truth-IDs existiert ein Ergebnis-JSON.")
        return 0

    print(f"Suche Ergebnis-JSONs fuer {len(wanted)} verschollene Analysen ...\n")
    roots = args.search_root or DEFAULT_ROOTS
    found = search(roots, wanted, args.results_dir)

    print(f"\n=== Ergebnis ===")
    print(f"Gefunden:       {len(found)} von {len(wanted)}")
    for aid, paths in sorted(found.items()):
        for p in paths:
            print(f"  {aid[:8]}...  ->  {p}")

    not_found = wanted - set(found)
    if not_found:
        print(f"\nNicht gefunden ({len(not_found)}):")
        for aid in sorted(not_found):
            print(f"  {aid}")
        print("Diese Ergebnisse existieren als Datei nirgends (mehr) - die "
              "Analysen wurden vermutlich nie gespeichert oder geloescht.")

    if args.copy and found:
        args.results_dir.mkdir(exist_ok=True)
        copied = 0
        for aid, paths in found.items():
            target = args.results_dir / f"{aid}.json"
            if target.exists():
                continue
            # Bei mehreren Funden: die neueste Datei nehmen
            source = max(paths, key=lambda p: p.stat().st_mtime)
            shutil.copy2(source, target)
            copied += 1
        print(f"\n{copied} Datei(en) nach {args.results_dir} kopiert.")
        print("Jetzt export_labels_v3.py erneut laufen lassen (alte CSV vorher "
              "sichern/umbenennen!), dann sind Engine-Scores fuer diese Sets dabei.")
    elif found and not args.copy:
        print("\nZum Zurueckkopieren erneut mit --copy ausfuehren.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
