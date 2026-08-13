"""Feedback-Cache von mtime- auf Inhalts-Schluessel umstellen (einmalig).

Ausgangslage: retrain_model bildete den Cache-Schluessel bis zum 10.08.2026
aus der mtime der Ground-Truth-Dateien. Seit der Umstellung auf einen
Inhalts-Hash (_gt_stamp) tragen alte Eintraege ein Schluesselformat, das
per Praefix nie mehr trifft - gewollt, denn ein alter Stempel belegt nichts
mehr. Die Folge ist aber, dass ein vorhandener Cache komplett ausfaellt und
neu gebaut werden muss: mehrere Minuten, und es braucht das echte Audio,
das nicht versioniert ist.

Dieses Skript schreibt nur den SCHLUESSEL um. Keine einzige Trainingszeile
wird angefasst, nichts wird neu berechnet, kein Audio gelesen.

    python -m tools.migrate_feedback_cache_stamps              # nur Bericht
    python -m tools.migrate_feedback_cache_stamps --write      # schreibt

Was dieses Skript NICHT pruefen kann
------------------------------------
Ob die gespeicherten Zeilen wirklich aus der Ground Truth stammen, die
JETZT auf der Platte liegt. Der alte Stempel belegt nur "gleiche mtime wie
damals", und genau diese mtime ist beim Checkout verloren gegangen. Diese
Bestaetigung muss von aussen kommen - aus der Git-Historie der Ground
Truth. Deshalb ist der Bericht die Voreinstellung und --write die bewusste
Entscheidung.

Fuer diesen Bestand wurde sie am 10.08.2026 so gefuehrt:
  - daten/ground_truth wurde von genau einem Commit geschrieben (c4e9feb,
    29.07.2026) und seitdem nie wieder geaendert.
  - Alle 37 Stempel liegen in einem Fenster von 0,17 s an genau diesem
    Import - keine Label-Datei wurde danach einzeln angefasst.
  - dca8553 hat alle 20 Eintraege gegen genau diesen Stand neu gerechnet.
Die Zeilen gehoeren also zum heutigen Inhalt; nur ihr Schluessel war
nicht mehr nachweisbar.

Im Zweifel nicht migrieren, sondern den Cache loeschen - er baut sich neu
auf, es kostet nur Zeit und die Audiodateien. Ein falsch uebernommener
Eintrag dagegen trainiert still auf veralteten Labels.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from app.calibration.retrain_model import FEEDBACK_CACHE, STAMP_VERSION, _gt_stamp
from app.paths import GROUND_TRUTH_DIR


def _alte_ids(stamp: str) -> list[str] | None:
    """Analyse-Ids aus einem alten Stempel ("aid:mtime|aid:mtime").

    None, wenn der Stempel schon das neue Format hat oder unlesbar ist.
    """
    if not isinstance(stamp, str) or stamp.startswith(STAMP_VERSION + "|"):
        return None
    ids = []
    for teil in stamp.split("|"):
        aid, trenner, rest = teil.rpartition(":")
        # Alter Stempel: Id + Doppelpunkt + reine Zahl (mtime in ns).
        if not trenner or not aid or not rest.isdigit():
            return None
        ids.append(aid)
    return ids or None


def migriere(cache: dict, gt_dir: Path) -> tuple[dict, dict]:
    """Cache mit neuen Schluesseln + Bericht (was wurde wie behandelt)."""
    neu: dict = {}
    bericht: dict[str, list[str]] = {"migriert": [], "schon_neu": [], "verworfen": []}

    for file_name, eintrag in cache.items():
        ids = _alte_ids((eintrag or {}).get("stamp", ""))
        if ids is None:
            # Neues Format oder unbrauchbar - unveraendert stehen lassen.
            # Ein unlesbarer Stempel trifft ohnehin nie, er kostet nur Platz.
            neu[file_name] = eintrag
            bericht["schon_neu"].append(file_name)
            continue

        dateien = [(aid, gt_dir / f"{aid}.json") for aid in ids]
        fehlend = [aid for aid, p in dateien if not p.exists()]
        if fehlend:
            # Ohne die Datei gibt es keinen Inhalt zum Hashen. Der Eintrag
            # wuerde auch im Betrieb nie treffen -> raus statt mitschleppen.
            bericht["verworfen"].append(f"{file_name} (fehlt: {', '.join(fehlend)})")
            continue

        neu[file_name] = {**eintrag,
                          "stamp": _gt_stamp([(aid, p, False) for aid, p in dateien])}
        bericht["migriert"].append(file_name)

    return neu, bericht


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--write", action="store_true",
                   help="wirklich schreiben (ohne: nur Bericht)")
    p.add_argument("--cache", type=Path, default=FEEDBACK_CACHE,
                   help=f"abweichende Cache-Datei (Vorgabe: {FEEDBACK_CACHE})")
    p.add_argument("--ground-truth", type=Path, default=GROUND_TRUTH_DIR,
                   help=f"abweichender Label-Ordner (Vorgabe: {GROUND_TRUTH_DIR})")
    args = p.parse_args()

    if not args.cache.exists():
        print(f"Kein Cache unter {args.cache} - nichts zu tun.")
        return 0

    cache = json.loads(args.cache.read_text(encoding="utf-8"))
    neu, bericht = migriere(cache, args.ground_truth)

    print(f"Cache: {args.cache}")
    print(f"Labels: {args.ground_truth}\n")
    for name in bericht["migriert"]:
        print(f"  MIGRIERT   {name}")
    for name in bericht["schon_neu"]:
        print(f"  UNVERAEND. {name} (Schluessel schon im neuen Format)")
    for name in bericht["verworfen"]:
        print(f"  VERWORFEN  {name}")
    print(f"\n{len(bericht['migriert'])} migriert, "
          f"{len(bericht['schon_neu'])} unveraendert, "
          f"{len(bericht['verworfen'])} verworfen.")

    if not args.write:
        print("\nNur Bericht. Zum Schreiben --write anhaengen.")
        return 0

    shutil.copy(args.cache, str(args.cache) + ".backup")
    args.cache.write_text(json.dumps(neu, default=float), encoding="utf-8")
    print(f"\nGeschrieben -> {args.cache} (alter Stand als .backup gesichert)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
