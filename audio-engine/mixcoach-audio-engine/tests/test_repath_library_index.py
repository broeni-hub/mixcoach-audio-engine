"""End-to-End-Test fuer tools/repath_library_index.py.

Der echte Lauf ist ein Einmalschuss ueber 6113 Eintraege und 12226
Feature-Dateien. Geht dabei etwas schief, ist im schlimmsten Fall die
Zuordnung zwischen Index und Fingerprints zerstoert - und die kostet
Stunden Rechenzeit. Deshalb hier eine vollstaendige Miniatur der Library
in einem Temp-Verzeichnis, inklusive der drei Faelle, die in der echten
Library garantiert vorkommen:

  * Umlaute im Pfad  -> NFC/NFD-Kanonisierung
  * fehlende Datei   -> Eintrag muss unveraendert bleiben
  * ID-Ueberschneidung zwischen alten und neuen tids -> zweiphasiges Rename

Das Skript wird als Unterprozess mit gesetztem MIXCOACH_DATA_DIR
aufgerufen - also genau so, wie es spaeter von Hand laeuft.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

ENGINE_ROOT = Path(__file__).resolve().parents[1]
OLD_ROOT = "C:/Users/Sebro/Music"


def _tid(path: str) -> str:
    return hashlib.md5(path.encode("utf-8", "replace")).hexdigest()[:16]


def _run(data_root: Path, new_root: Path, *extra: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "MIXCOACH_DATA_DIR": str(data_root)}
    return subprocess.run(
        [sys.executable, "-m", "tools.repath_library_index",
         "--old-root", OLD_ROOT, "--new-root", str(new_root), *extra],
        cwd=ENGINE_ROOT, env=env, capture_output=True, text=True,
    )


@pytest.fixture
def library(tmp_path: Path) -> dict:
    """Miniatur-Library aufbauen: Musik auf der Platte + passender Alt-Index."""
    data_root = tmp_path / "daten"
    new_root = tmp_path / "Music"
    fp_dir = data_root / "library" / "fp"
    lm_dir = data_root / "library" / "lm"
    fp_dir.mkdir(parents=True)
    lm_dir.mkdir(parents=True)

    # Relativpfade, wie sie unter beiden Wurzeln gelten. "Björk" bewusst mit
    # Umlaut: der Windows-Index enthaelt NFC, das Mac-Dateisystem liefert
    # beim Auflisten NFD zurueck.
    #
    # 24 vorhandene + 1 fehlende Datei = 96 % aufloesbar. Bewusst knapp
    # oberhalb der 95-%-Sperre, damit der Normalfall durchlaeuft und der
    # Schwellwert trotzdem scharf bleibt.
    relativ = [
        "Techno/aaa.mp3",
        "Techno/bbb.mp3",
        "Ambient/Björk - Unravel.mp3",   # NFC im Index
        "Ambient/ccc.mp3",
        *[f"Haus/fueller_{i:02d}.mp3" for i in range(20)],
    ]
    fehlt = "Techno/verschwunden.mp3"

    for rel in relativ:
        ziel = new_root / rel
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_bytes(b"nicht wirklich audio")

    # Die Björk-Datei auf der Platte in NFD umbenennen, waehrend der Index
    # weiter NFC enthaelt - genau die Konstellation nach einem Umzug von
    # Windows. APFS bewahrt die geschriebene Form, deshalb muss hier explizit
    # umbenannt werden; sonst laege NFC auf der Platte und der Test wuerde
    # die Kanonisierung gar nicht ausloesen.
    nfc_datei = new_root / "Ambient" / unicodedata.normalize("NFC", "Björk - Unravel.mp3")
    nfd_datei = new_root / "Ambient" / unicodedata.normalize("NFD", "Björk - Unravel.mp3")
    os.rename(nfc_datei, nfd_datei)

    tracks: dict[str, dict] = {}
    for i, rel in enumerate([*relativ, fehlt]):
        alter_pfad = f"{OLD_ROOT}/{rel}"
        tracks[_tid(alter_pfad)] = {
            "title": f"Track {i}", "artist": "Test", "bpm": 128.0,
            "key": "8A", "duration": 300.0,
            "path": alter_pfad,
            "mtime": 111111111111111111,   # veraltet, muss ueberschrieben werden
        }

    for tid in tracks:
        (fp_dir / f"{tid}.npy").write_bytes(b"fp:" + tid.encode())
        (lm_dir / f"{tid}.npz").write_bytes(b"lm:" + tid.encode())

    index_pfad = data_root / "library" / "index.json"
    index_pfad.write_text(json.dumps({"tracks": tracks}, ensure_ascii=False), encoding="utf-8")

    return {"data_root": data_root, "new_root": new_root, "index": index_pfad,
            "fp": fp_dir, "lm": lm_dir, "relativ": relativ, "fehlt": fehlt}


def test_dry_run_schreibt_nichts(library: dict) -> None:
    vorher = library["index"].read_bytes()
    ergebnis = _run(library["data_root"], library["new_root"], "--dry-run")

    assert ergebnis.returncode == 0, ergebnis.stdout + ergebnis.stderr
    assert "DRY RUN" in ergebnis.stdout
    assert library["index"].read_bytes() == vorher
    assert not list(library["index"].parent.glob("*.bak-*"))


def test_remapping_vollstaendig(library: dict) -> None:
    ergebnis = _run(library["data_root"], library["new_root"])
    assert ergebnis.returncode == 0, ergebnis.stdout + ergebnis.stderr

    tracks = json.loads(library["index"].read_text(encoding="utf-8"))["tracks"]
    assert len(tracks) == 25   # 24 umgeschrieben + 1 unveraendert

    # Jeder Eintrag hat beide Feature-Dateien - Akzeptanzkriterium 1.
    for tid in tracks:
        assert (library["fp"] / f"{tid}.npy").exists(), f"fp fehlt fuer {tid}"
        assert (library["lm"] / f"{tid}.npz").exists(), f"lm fehlt fuer {tid}"

    # Keine Waisen - Akzeptanzkriterium 2.
    assert {p.stem for p in library["fp"].glob("*.npy")} == set(tracks)
    assert {p.stem for p in library["lm"].glob("*.npz")} == set(tracks)


def test_backup_wird_angelegt(library: dict) -> None:
    vorher = library["index"].read_bytes()
    _run(library["data_root"], library["new_root"])

    backups = list(library["index"].parent.glob("index.json.bak-*"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == vorher


def test_fehlende_datei_bleibt_unveraendert(library: dict) -> None:
    alter_pfad = f"{OLD_ROOT}/{library['fehlt']}"
    alte_tid = _tid(alter_pfad)
    _run(library["data_root"], library["new_root"])

    tracks = json.loads(library["index"].read_text(encoding="utf-8"))["tracks"]
    assert alte_tid in tracks, "nicht aufloesbarer Eintrag darf nicht verschwinden"
    assert tracks[alte_tid]["path"] == alter_pfad
    assert tracks[alte_tid]["mtime"] == 111111111111111111


def test_mtime_wird_frisch_gelesen(library: dict) -> None:
    """Akzeptanzkriterium 4: sonst gilt jeder Track als veraendert."""
    _run(library["data_root"], library["new_root"])
    tracks = json.loads(library["index"].read_text(encoding="utf-8"))["tracks"]

    geprueft = 0
    for meta in tracks.values():
        p = Path(meta["path"])
        if not p.exists():
            continue
        assert meta["mtime"] == p.stat().st_mtime_ns
        geprueft += 1
    assert geprueft == 24


def test_metadaten_bleiben_erhalten(library: dict) -> None:
    _run(library["data_root"], library["new_root"])
    tracks = json.loads(library["index"].read_text(encoding="utf-8"))["tracks"]

    for meta in tracks.values():
        assert meta["artist"] == "Test"
        assert meta["bpm"] == 128.0
        assert meta["key"] == "8A"
        assert meta["title"].startswith("Track ")


def test_umlaut_pfad_auf_dateisystem_schreibweise(library: dict) -> None:
    """Der springende Punkt auf macOS.

    Der Index kommt mit NFC ("Björk" als ein Zeichen), das Dateisystem
    liefert beim Auflisten NFD. Beide finden dieselbe Datei, ergeben aber
    verschiedene md5-Summen. Steht die falsche Form im Index, laufen beim
    naechsten rekordbox-Import neue IDs auf - und die Fingerprints waeren
    ein zweites Mal verwaist.
    """
    _run(library["data_root"], library["new_root"])
    tracks = json.loads(library["index"].read_text(encoding="utf-8"))["tracks"]

    treffer = [m for m in tracks.values() if "rk - Unravel" in m["path"]]
    assert len(treffer) == 1
    pfad = treffer[0]["path"]

    # Die Schreibweise muss der entsprechen, die os.scandir zurueckgibt.
    echt = next(p for p in (library["new_root"] / "Ambient").iterdir()
                if "rk - Unravel" in unicodedata.normalize("NFC", p.name))
    assert pfad == echt.as_posix()

    # Und die tid muss zu genau dieser Schreibweise passen.
    tid = next(t for t, m in tracks.items() if m["path"] == pfad)
    assert tid == _tid(pfad)
    assert (library["fp"] / f"{tid}.npy").exists()

    # Der Test darf nicht versehentlich trivial werden: die naive Ersetzung
    # haette NFC ergeben, auf der Platte liegt NFD. Waeren beide gleich,
    # wuerde dieser Test die Kanonisierung gar nicht pruefen.
    naiv = (library["new_root"] / "Ambient" /
            unicodedata.normalize("NFC", "Björk - Unravel.mp3")).as_posix()
    assert naiv != pfad, "Testaufbau kaputt - NFC und NFD sind hier identisch"
    assert _tid(naiv) != tid, "naive Ersetzung ergaebe dieselbe tid"


def test_ueberschneidende_ids_verlieren_keine_daten(library: dict) -> None:
    """Zweiphasiges Rename: eine alte tid ist zugleich eine neue tid.

    Ohne die .tmp-Zwischenstufe wuerde das erste Rename die Datei
    ueberschreiben, die kurz darauf selbst noch Quelle ist.
    """
    index_pfad = library["index"]
    tracks = json.loads(index_pfad.read_text(encoding="utf-8"))["tracks"]

    # Die neue tid von "Techno/aaa.mp3" vorab ausrechnen ...
    neue_tid_aaa = _tid((library["new_root"] / "Techno/aaa.mp3").as_posix())
    # ... und einem ANDEREN Eintrag als alte tid verpassen.
    alte_tid_bbb = _tid(f"{OLD_ROOT}/Techno/bbb.mp3")
    tracks[neue_tid_aaa] = tracks.pop(alte_tid_bbb)
    index_pfad.write_text(json.dumps({"tracks": tracks}, ensure_ascii=False), encoding="utf-8")

    (library["fp"] / f"{alte_tid_bbb}.npy").rename(library["fp"] / f"{neue_tid_aaa}.npy")
    (library["lm"] / f"{alte_tid_bbb}.npz").rename(library["lm"] / f"{neue_tid_aaa}.npz")

    ergebnis = _run(library["data_root"], library["new_root"])
    assert ergebnis.returncode == 0, ergebnis.stdout + ergebnis.stderr

    neu = json.loads(index_pfad.read_text(encoding="utf-8"))["tracks"]
    assert len(neu) == 25
    for tid in neu:
        assert (library["fp"] / f"{tid}.npy").exists(), f"fp verloren bei {tid}"
        assert (library["lm"] / f"{tid}.npz").exists(), f"lm verloren bei {tid}"
    assert not list(library["fp"].glob("*.tmp")), "Phase 2 nicht abgeschlossen"
    assert not list(library["lm"].glob("*.tmp"))


def test_stoppt_wenn_zu_wenig_aufloesbar(library: dict, tmp_path: Path) -> None:
    """Akzeptanzkriterium 3: unter 95 % nicht weiterarbeiten."""
    leer = tmp_path / "leeres_musikverzeichnis"
    leer.mkdir()
    vorher = library["index"].read_bytes()

    ergebnis = _run(library["data_root"], leer)

    assert ergebnis.returncode == 3
    assert "STOPP" in ergebnis.stdout
    assert library["index"].read_bytes() == vorher, "bei Abbruch darf nichts geschrieben sein"


def test_kollision_bricht_ab(library: dict) -> None:
    """Zwei alte Eintraege, die auf denselben neuen Pfad zeigen."""
    tracks = json.loads(library["index"].read_text(encoding="utf-8"))["tracks"]
    doppelt_tid = _tid(f"{OLD_ROOT}/Techno/aaa_kopie.mp3")
    tracks[doppelt_tid] = {**next(iter(tracks.values())),
                           "path": f"{OLD_ROOT}/Techno/aaa.mp3"}
    library["index"].write_text(json.dumps({"tracks": tracks}, ensure_ascii=False),
                                encoding="utf-8")
    vorher = library["index"].read_bytes()

    ergebnis = _run(library["data_root"], library["new_root"])

    assert ergebnis.returncode == 2
    assert "Kollision" in ergebnis.stdout
    assert library["index"].read_bytes() == vorher


def test_verify_meldet_sauberen_zustand(library: dict) -> None:
    _run(library["data_root"], library["new_root"])
    ergebnis = _run(library["data_root"], library["new_root"], "--verify")

    assert ergebnis.returncode == 0
    assert "verwaiste Feature-Dateien    fp: 0, lm: 0" in ergebnis.stdout
