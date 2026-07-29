"""Library-Index von Windows- auf macOS-Pfade umschreiben (Job A).

Ausgangslage: alle 6113 Eintraege in daten/library/index.json zeigen auf
"C:/Users/Sebro/Music/...". Auf dem Mac ist davon nichts aufloesbar.

Der Knackpunkt steht in app/library/manager.py:56 -

    _track_id(path) = md5(path.encode("utf-8", "replace")).hexdigest()[:16]

Die Track-ID ist eine reine Funktion des Pfad-Strings. Neuer Pfad -> neue ID
-> die 12226 bereits berechneten Feature-Dateien (fp/*.npy + lm/*.npz) waeren
verwaist. Ein naiver Rescan wuerfe damit Stunden Fingerprint-Arbeit weg.

Umgekehrt heisst dasselbe aber: das Remapping ist exakt berechenbar. Es muss
nichts neu extrahiert werden - nur umbenannt.

    python -m tools.repath_library_index \
        --old-root "C:/Users/Sebro/Music" \
        --new-root "/Users/sebastianbroening/Music" \
        --dry-run

Ohne --dry-run wird geschrieben, vorher immer ein Backup angelegt.


Zwei Stolpersteine, die den Erfolg entscheiden
----------------------------------------------

1. mtime. manager.py:112 ueberspringt einen Track nur, wenn die gespeicherte
   mtime exakt der auf der Platte entspricht. Kopieren aendert mtimes je nach
   Methode. Deshalb liest dieses Skript die mtime nach dem Kopieren frisch aus
   dem Dateisystem, statt sich auf `cp -p` oder `rsync -t` zu verlassen.

2. Unicode-Normalform - in der Spec nicht erwaehnt, aber auf macOS der
   wahrscheinlichste Grund fuer ein stilles Scheitern. Windows speichert
   Dateinamen als NFC ("Björk" = B-j-oe-r-k mit einem Zeichen fuer oe),
   macOS-Dateisysteme liefern beim Auflisten traditionell NFD (oe = o +
   Kombinierender Trema). Beide Strings zeigen auf dieselbe Datei - exists()
   findet sie in beiden Formen -, aber ihre md5-Summen sind VERSCHIEDEN.

   Wuerde man die NFC-Form aus dem Windows-Index uebernehmen, waere der Index
   heute korrekt, und beim naechsten rekordbox-Import - der die Pfade neu vom
   Dateisystem liest - kaemen NFD-Strings, neue IDs, und die ganze Arbeit
   waere ein zweites Mal verloren. Genau derselbe Fehler, nur spaeter.

   Deshalb kanonisiert dieses Skript jeden Pfad auf die Schreibweise, die das
   Dateisystem selbst beim Auflisten zurueckgibt. Abschaltbar mit
   --no-canonicalize, aber es gibt keinen guten Grund dafuer.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE_ROOT))

# Die ID-Funktion wird importiert, nicht nachgebaut. Waere sie hier kopiert,
# koennten beide Stellen auseinanderlaufen und der Index still kaputtgehen.
from app.library.manager import FP_DIR, INDEX_PATH, LM_DIR, _track_id  # noqa: E402

# Unter diesem Anteil aufloesbarer Pfade wird nicht geschrieben: dann stimmt
# die Ordnerstruktur unter --new-root nicht mit der alten ueberein, und ein
# Teil-Remapping wuerde den Zustand nur schwerer reparierbar machen.
MIN_AUFLOESBAR = 0.95


def _norm_root(root: str) -> str:
    """Wurzelpfad vereinheitlichen: Backslashes zu /, kein Schluss-Slash."""
    return root.replace("\\", "/").rstrip("/")


def _canonical_on_disk(path: Path, cache: dict[Path, dict[str, str]]) -> Path:
    """Die Schreibweise zurueckgeben, die das Dateisystem selbst liefert.

    Sucht den Dateinamen im Elternverzeichnis ueber einen normalisierten,
    kleingeschriebenen Schluessel. Damit werden sowohl NFC/NFD- als auch
    Gross-/Kleinschreibungs-Unterschiede eingefangen. Das Listing pro
    Verzeichnis wird zwischengespeichert - eine Library hat viele Dateien,
    aber vergleichsweise wenige Ordner.
    """
    parent = path.parent
    eintraege = cache.get(parent)
    if eintraege is None:
        try:
            eintraege = {
                unicodedata.normalize("NFC", e.name).casefold(): e.name
                for e in os.scandir(parent)
            }
        except OSError:
            eintraege = {}
        cache[parent] = eintraege

    echt = eintraege.get(unicodedata.normalize("NFC", path.name).casefold())
    return parent / echt if echt else path


def plane(old_root: str, new_root: str, kanonisieren: bool) -> dict:
    """Das Remapping berechnen, ohne irgendetwas zu schreiben."""
    if not INDEX_PATH.exists():
        # Fast immer dieselbe Ursache: MIXCOACH_DATA_DIR ist nicht gesetzt,
        # also faellt app/paths.py auf den Engine-Ordner zurueck - die
        # Library liegt aber unter daten/. Siehe SETUP_MACOS.md.
        vermutet = ENGINE_ROOT.parents[1] / "daten"
        hinweis = ""
        if (vermutet / "library" / "index.json").exists():
            hinweis = (f"\n\nGefunden wurde er hier: {vermutet / 'library' / 'index.json'}"
                       f"\nEs fehlt die Umgebungsvariable:"
                       f'\n    export MIXCOACH_DATA_DIR="{vermutet}"')
        raise SystemExit(f"Index nicht gefunden: {INDEX_PATH}{hinweis}")

    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    tracks = index.get("tracks", {})

    plan: list[dict] = []           # erfolgreich aufgeloest
    fehlend: list[dict] = []        # Pfad existiert nicht auf der Platte
    ohne_praefix: list[str] = []    # Pfad beginnt gar nicht mit --old-root
    dir_cache: dict[Path, dict[str, str]] = {}

    for alte_tid, meta in tracks.items():
        alter_pfad = meta.get("path") or ""
        norm = alter_pfad.replace("\\", "/")

        if not norm.lower().startswith(old_root.lower()):
            ohne_praefix.append(alter_pfad)
            fehlend.append({"tid": alte_tid, "path": alter_pfad, "grund": "kein old-root-Praefix"})
            continue

        neuer_pfad = new_root + norm[len(old_root):]
        p = Path(neuer_pfad)
        if not p.exists():
            fehlend.append({"tid": alte_tid, "path": alter_pfad, "grund": "nicht auf der Platte"})
            continue

        if kanonisieren:
            p = _canonical_on_disk(p, dir_cache)
            neuer_pfad = p.as_posix()

        plan.append({
            "alte_tid": alte_tid,
            "neue_tid": _track_id(neuer_pfad),
            "alter_pfad": alter_pfad,
            "neuer_pfad": neuer_pfad,
            "mtime": p.stat().st_mtime_ns,
            "meta": meta,
        })

    # Kollisionen: zwei verschiedene alte IDs, die auf dieselbe neue zeigen.
    # Passiert, wenn zwei Windows-Pfade auf denselben Mac-Pfad zusammenfallen
    # (etwa durch Gross-/Kleinschreibung). Nicht raten - abbrechen.
    nach_neuer_tid: dict[str, list[dict]] = {}
    for e in plan:
        nach_neuer_tid.setdefault(e["neue_tid"], []).append(e)
    kollisionen = [v for v in nach_neuer_tid.values() if len(v) > 1]

    # Verwaiste Feature-Dateien nach dem Remapping: die, deren Name in keiner
    # neuen und keiner beibehaltenen (weil fehlenden) tid vorkommt.
    behaltene_tids = {e["tid"] for e in fehlend}
    ziel_tids = {e["neue_tid"] for e in plan} | behaltene_tids
    waisen_fp = sorted(p.stem for p in FP_DIR.glob("*.npy") if p.stem not in ziel_tids) if FP_DIR.is_dir() else []
    waisen_lm = sorted(p.stem for p in LM_DIR.glob("*.npz") if p.stem not in ziel_tids) if LM_DIR.is_dir() else []

    # Wie viele der geplanten Umbenennungen haben ueberhaupt Quelldateien?
    fehlende_fp = [e for e in plan if not (FP_DIR / f"{e['alte_tid']}.npy").exists()]
    fehlende_lm = [e for e in plan if not (LM_DIR / f"{e['alte_tid']}.npz").exists()]
    umbenannt_nfc_nfd = sum(
        1 for e in plan
        if e["neuer_pfad"] != new_root + e["alter_pfad"].replace("\\", "/")[len(old_root):]
    )

    return {
        "index": index,
        "gesamt": len(tracks),
        "plan": plan,
        "fehlend": fehlend,
        "ohne_praefix": ohne_praefix,
        "kollisionen": kollisionen,
        "waisen_fp": waisen_fp,
        "waisen_lm": waisen_lm,
        "fehlende_fp": fehlende_fp,
        "fehlende_lm": fehlende_lm,
        "unicode_korrekturen": umbenannt_nfc_nfd,
    }


def _rename_zweiphasig(plan: list[dict], verzeichnis: Path, endung: str) -> tuple[int, int]:
    """fp/<alt> -> fp/<neu>.tmp -> fp/<neu>.

    Zwei Phasen, weil sich alte und neue ID-Mengen ueberschneiden koennen: ein
    direktes Umbenennen wuerde eine Datei ueberschreiben, die spaeter selbst
    noch Quelle ist. Bricht Phase 1 ab, laesst sich der Zustand an den
    .tmp-Dateien ablesen und von Hand zu Ende fuehren.
    """
    if not verzeichnis.is_dir():
        return 0, 0
    verschoben = 0
    for e in plan:
        quelle = verzeichnis / f"{e['alte_tid']}{endung}"
        if e["alte_tid"] == e["neue_tid"] or not quelle.exists():
            continue
        quelle.rename(verzeichnis / f"{e['neue_tid']}{endung}.tmp")
        verschoben += 1

    fertig = 0
    for tmp in verzeichnis.glob(f"*{endung}.tmp"):
        tmp.rename(tmp.with_suffix(""))   # ".tmp" abschneiden
        fertig += 1
    return verschoben, fertig


def schreibe(ergebnis: dict, new_root: str) -> dict:
    """Backup, Umbenennen, neuen Index schreiben."""
    stempel = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = INDEX_PATH.with_name(f"{INDEX_PATH.name}.bak-{stempel}")
    backup.write_bytes(INDEX_PATH.read_bytes())
    if not backup.exists():
        raise SystemExit("Backup konnte nicht angelegt werden - es wird nichts geschrieben.")

    fp_v, fp_f = _rename_zweiphasig(ergebnis["plan"], FP_DIR, ".npy")
    lm_v, lm_f = _rename_zweiphasig(ergebnis["plan"], LM_DIR, ".npz")

    neue_tracks: dict[str, dict] = {}
    # Nicht aufgeloeste Eintraege unveraendert uebernehmen - sie behalten ihre
    # alte ID und damit die Zuordnung zu ihren Feature-Dateien.
    alte = ergebnis["index"].get("tracks", {})
    for e in ergebnis["fehlend"]:
        neue_tracks[e["tid"]] = alte[e["tid"]]

    for e in ergebnis["plan"]:
        meta = dict(e["meta"])          # title/artist/bpm/key/duration bleiben
        meta["path"] = e["neuer_pfad"]
        meta["mtime"] = e["mtime"]      # frisch von der Platte, nicht uebernommen
        neue_tracks[e["neue_tid"]] = meta

    neuer_index = dict(ergebnis["index"])
    neuer_index["tracks"] = neue_tracks

    # Atomar: erst daneben schreiben, dann ersetzen. Ein Absturz mitten im
    # Schreiben darf den Index nicht halb hinterlassen.
    tmp = INDEX_PATH.with_suffix(".json.neu")
    tmp.write_text(json.dumps(neuer_index, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, INDEX_PATH)

    return {"backup": backup, "fp": (fp_v, fp_f), "lm": (lm_v, lm_f), "eintraege": len(neue_tracks)}


def pruefe_akzeptanz() -> list[str]:
    """Die Kriterien 1 und 2 aus der Spec direkt am Ergebnis nachmessen."""
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    tracks = index.get("tracks", {})
    ohne_fp = [t for t in tracks if not (FP_DIR / f"{t}.npy").exists()]
    ohne_lm = [t for t in tracks if not (LM_DIR / f"{t}.npz").exists()]
    waisen_fp = [p.stem for p in FP_DIR.glob("*.npy") if p.stem not in tracks]
    waisen_lm = [p.stem for p in LM_DIR.glob("*.npz") if p.stem not in tracks]
    auf_platte = sum(1 for m in tracks.values() if Path(m.get("path", "")).exists())

    zeilen = [
        f"  1. Eintraege mit fp UND lm      {len(tracks) - max(len(ohne_fp), len(ohne_lm))}/{len(tracks)}"
        f"   (ohne fp: {len(ohne_fp)}, ohne lm: {len(ohne_lm)})",
        f"  2. verwaiste Feature-Dateien    fp: {len(waisen_fp)}, lm: {len(waisen_lm)}",
        f"  3. Pfade auf der Platte         {auf_platte}/{len(tracks)}"
        f"   ({auf_platte / len(tracks) * 100:.1f} %)" if tracks else "  3. Index leer",
    ]
    return zeilen


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--old-root", required=True, help='z.B. "C:/Users/Sebro/Music"')
    p.add_argument("--new-root", required=True, help='z.B. "/Users/sebastianbroening/Music"')
    p.add_argument("--dry-run", action="store_true", help="nur den Report, nichts schreiben")
    p.add_argument("--no-canonicalize", action="store_true",
                   help="Pfade NICHT auf die Schreibweise des Dateisystems bringen "
                        "(siehe Modulkopf - im Zweifel weglassen)")
    p.add_argument("--force", action="store_true",
                   help=f"auch unter {MIN_AUFLOESBAR:.0%} aufloesbaren Pfaden schreiben")
    p.add_argument("--verify", action="store_true",
                   help="nur die Akzeptanzkriterien am aktuellen Index nachmessen")
    args = p.parse_args()

    if args.verify:
        print("AKZEPTANZKRITERIEN am aktuellen Index")
        print("\n".join(pruefe_akzeptanz()))
        return 0

    old_root = _norm_root(args.old_root)
    new_root = _norm_root(args.new_root)
    e = plane(old_root, new_root, kanonisieren=not args.no_canonicalize)

    gesamt = e["gesamt"]
    aufloesbar = len(e["plan"])
    quote = aufloesbar / gesamt if gesamt else 0.0

    print("=" * 72)
    print("  Library-Index repathen" + ("   [DRY RUN]" if args.dry_run else ""))
    print("=" * 72)
    print(f"  Index                  {INDEX_PATH}")
    print(f"  {old_root}  ->  {new_root}")
    print()
    print(f"  Eintraege gesamt       {gesamt}")
    print(f"  aufloesbar             {aufloesbar}  ({quote:.1%})")
    print(f"  nicht auf der Platte   {len(e['fehlend'])}")
    if e["ohne_praefix"]:
        print(f"    davon ohne old-root-Praefix  {len(e['ohne_praefix'])}")
    print(f"  Kollisionen            {len(e['kollisionen'])}")
    print(f"  Unicode-Korrekturen    {e['unicode_korrekturen']}  (NFC/NFD bzw. Schreibweise)")
    print(f"  verwaiste fp / lm      {len(e['waisen_fp'])} / {len(e['waisen_lm'])}")
    print(f"  Plan ohne Quelldatei   fp: {len(e['fehlende_fp'])}, lm: {len(e['fehlende_lm'])}")
    print()

    for beispiel in e["fehlend"][:5]:
        print(f"    fehlt: {beispiel['path']}  [{beispiel['grund']}]")
    if len(e["fehlend"]) > 5:
        print(f"    ... und {len(e['fehlend']) - 5} weitere")
    print()

    if e["kollisionen"]:
        print("  ABBRUCH - Kollisionen (verschiedene alte IDs, gleiche neue ID):")
        for gruppe in e["kollisionen"][:10]:
            print(f"    neue tid {gruppe[0]['neue_tid']}")
            for g in gruppe:
                print(f"      {g['alter_pfad']}  ->  {g['neuer_pfad']}")
        return 2

    if gesamt and quote < MIN_AUFLOESBAR and not args.force:
        print(f"  STOPP - unter {MIN_AUFLOESBAR:.0%} aufloesbar.")
        print("  Die Ordnerstruktur unter --new-root passt nicht zur alten.")
        print("  Musik vollstaendig kopieren, dann erneut. (--force ueberschreibt das.)")
        return 3

    if args.dry_run:
        print("  DRY RUN - es wurde nichts geschrieben.")
        print(f"  Ohne --dry-run wuerden {aufloesbar} Eintraege umgeschrieben.")
        return 0

    ergebnis = schreibe(e, new_root)
    print(f"  Backup                 {ergebnis['backup'].name}")
    print(f"  fp umbenannt           {ergebnis['fp'][0]} verschoben, {ergebnis['fp'][1]} finalisiert")
    print(f"  lm umbenannt           {ergebnis['lm'][0]} verschoben, {ergebnis['lm'][1]} finalisiert")
    print(f"  Index geschrieben      {ergebnis['eintraege']} Eintraege")
    print()
    print("AKZEPTANZKRITERIEN")
    print("\n".join(pruefe_akzeptanz()))
    print()
    print("  Kriterium 4 (der eigentliche Test) laeuft separat: Fingerprint-Lauf")
    print("  starten, Ergebnis muss done=0 sein. Jedes done>0 heisst, dass die")
    print("  mtime-Behandlung nicht greift.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
