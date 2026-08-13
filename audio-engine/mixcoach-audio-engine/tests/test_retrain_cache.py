"""Tests fuer den Feature-Cache in retrain_model.collect_feedback_rows().

Der wichtigste Test ist test_reine_mtime_aenderung_haelt_den_cache: faellt
er, ist der Cache nach jedem Checkout, Merge oder frischen Clone wieder
wertlos - und sein Neuaufbau braucht das echte Audio, das nicht
versioniert ist. Genau dafuer haengt der Schluessel am Inhalt.

Kein Test hier fasst Audio an: build_set_rows wird durch einen Zaehler
ersetzt. Damit misst "wie oft wurde gebaut?" direkt die Cache-Treffer.
"""

import json
import os
from pathlib import Path

import pytest

from app.calibration import retrain_model
from tools import migrate_feedback_cache_stamps

AID = "cache-test-analyse"
LABELS = {"true_transitions_sec": [120.0]}


@pytest.fixture
def aufbau(tmp_path, monkeypatch):
    """Ground Truth, Cache und Audio-Suche in den tmp-Ordner umbiegen.

    retrain_model bindet GROUND_TRUTH_DIR/RESULTS_DIR per 'from ... import'
    ein - die Namen muessen deshalb IM MODUL ersetzt werden, ein Patch auf
    app.paths liefe ins Leere (gleiche Falle wie in conftest.py).
    """
    gt_dir = tmp_path / "ground_truth"
    gt_dir.mkdir()
    monkeypatch.setattr(retrain_model, "GROUND_TRUTH_DIR", gt_dir)
    monkeypatch.setattr(retrain_model, "FEEDBACK_CACHE", tmp_path / "cache.json")
    # Keine Ergebnis-JSONs im tmp-Ordner: der fileName faellt damit auf die
    # Analyse-Id zurueck, und der echte Datenstamm bleibt unberuehrt.
    monkeypatch.setattr(retrain_model, "RESULTS_DIR", tmp_path / "ergebnisse")
    monkeypatch.setattr(retrain_model, "LEGACY_RESULTS_DIR", tmp_path / "alt")
    monkeypatch.setattr(retrain_model, "_find_audio", lambda aid: tmp_path / "set.wav")

    baute_fuer: list[str] = []

    def _falscher_bau(wav_path, truth, set_name):
        baute_fuer.append(set_name)
        return [{"set": set_name, "t": 120.0, "label": 1, "score": 0.9}]

    monkeypatch.setattr(retrain_model, "build_set_rows", _falscher_bau)

    gt_datei = gt_dir / f"{AID}.json"
    gt_datei.write_text(json.dumps(LABELS), encoding="utf-8")
    return gt_datei, baute_fuer


def _mtime_setzen(pfad: Path, sekunden: float) -> None:
    os.utime(pfad, (sekunden, sekunden))


def test_reine_mtime_aenderung_haelt_den_cache(aufbau):
    """Der Kern: gleicher Inhalt, andere Aenderungszeit -> kein Neuaufbau.

    Das ist die Lage nach jedem git-Checkout: Git stellt mtimes nicht
    wieder her, alle Dateien tragen die Zeit des Auscheckens.
    """
    gt_datei, baute_fuer = aufbau

    zeilen_kalt = retrain_model.collect_feedback_rows()
    assert baute_fuer == [AID], "erster Lauf muss bauen (Cache ist leer)"

    # Der Checkout: Zeitstempel weit verschoben, Bytes unveraendert.
    inhalt_vorher = gt_datei.read_bytes()
    _mtime_setzen(gt_datei, 1_000_000_000.0)
    assert gt_datei.read_bytes() == inhalt_vorher

    zeilen_warm = retrain_model.collect_feedback_rows()
    assert baute_fuer == [AID], "mtime-Aenderung hat den Cache entwertet"
    assert zeilen_warm == zeilen_kalt


def test_cache_traegt_auch_ohne_audio(aufbau, monkeypatch):
    """Der frische Clone: Labels da, Audio nicht - der Cache muss trotzdem
    liefern. Vor dem 13.08. lief die Audio-Suche VOR der Cache-Abfrage, damit
    war jede Aufnahme uebersprungen und der Retrain sah 0 Feedback-Zeilen."""
    _, baute_fuer = aufbau

    zeilen_mit_audio = retrain_model.collect_feedback_rows()
    assert baute_fuer == [AID]

    # Audio verschwindet (nicht versioniert), Labels bleiben.
    monkeypatch.setattr(retrain_model, "_find_audio", lambda aid: None)

    zeilen_ohne_audio = retrain_model.collect_feedback_rows()
    assert zeilen_ohne_audio == zeilen_mit_audio, "ohne Audio kam nichts zurueck"
    assert baute_fuer == [AID], "ohne Audio wurde gebaut - das kann nicht gehen"


def test_geaenderter_inhalt_baut_neu(aufbau):
    """Die Gegenprobe: echte Label-Aenderung muss durchschlagen."""
    gt_datei, baute_fuer = aufbau

    retrain_model.collect_feedback_rows()
    assert baute_fuer == [AID]

    # Andere Wahrheit, und zur Sicherheit die alte mtime beibehalten -
    # der Cache darf sich nicht auf den Zeitstempel verlassen duerfen.
    vorher = gt_datei.stat().st_mtime
    gt_datei.write_text(json.dumps({"true_transitions_sec": [130.0]}), encoding="utf-8")
    _mtime_setzen(gt_datei, vorher)

    retrain_model.collect_feedback_rows()
    assert baute_fuer == [AID, AID], "geaenderte Labels wurden nicht neu gebaut"


def test_alter_mtime_stempel_gilt_nicht_mehr(aufbau):
    """Ein Cache aus der mtime-Zeit darf nicht stillschweigend durchgehen.

    Das Praefix in STAMP_VERSION sorgt dafuer, dass ein alter Stempel einen
    neuen nie treffen kann - auch dann nicht, wenn die mtime zufaellig noch
    stimmt.
    """
    gt_datei, baute_fuer = aufbau

    alter_stempel = f"{AID}:{gt_datei.stat().st_mtime_ns}"
    retrain_model.FEEDBACK_CACHE.write_text(
        json.dumps({AID: {"stamp": alter_stempel,
                          "rows": [{"set": AID, "t": 999.0, "label": 1}]}}),
        encoding="utf-8",
    )

    zeilen = retrain_model.collect_feedback_rows()
    assert baute_fuer == [AID], "alter mtime-Stempel wurde als gueltig genommen"
    assert all(z["t"] != 999.0 for z in zeilen), "alte Zeilen sind durchgerutscht"


def test_stempel_haengt_am_inhalt_nicht_am_zeitstempel(tmp_path):
    """_gt_stamp direkt: gleicher Inhalt gleicher Stempel, ueber zwei
    verschiedene Dateien mit verschiedenen Zeitstempeln hinweg."""
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text('{"true_transitions_sec": [1.0]}', encoding="utf-8")
    b.write_text('{"true_transitions_sec": [1.0]}', encoding="utf-8")
    _mtime_setzen(a, 1_000_000_000.0)
    _mtime_setzen(b, 1_700_000_000.0)

    assert retrain_model._gt_stamp([("x", a, False)]) == \
        retrain_model._gt_stamp([("x", b, False)])

    b.write_text('{"true_transitions_sec": [2.0]}', encoding="utf-8")
    assert retrain_model._gt_stamp([("x", a, False)]) != \
        retrain_model._gt_stamp([("x", b, False)])


def test_stempel_ist_unabhaengig_von_der_reihenfolge(tmp_path):
    """Mehrere Analysen derselben Aufnahme: die Glob-Reihenfolge darf den
    Schluessel nicht bewegen (sonst baut ein Lauf grundlos neu)."""
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text('{"true_transitions_sec": [1.0]}', encoding="utf-8")
    b.write_text('{"true_transitions_sec": [2.0]}', encoding="utf-8")

    vorwaerts = retrain_model._gt_stamp([("a", a, False), ("b", b, True)])
    rueckwaerts = retrain_model._gt_stamp([("b", b, True), ("a", a, False)])
    assert vorwaerts == rueckwaerts
    assert vorwaerts.startswith(retrain_model.STAMP_VERSION + "|")


# --- Umschluesselung eines Caches aus der mtime-Zeit -----------------------
# tools/migrate_feedback_cache_stamps.py schreibt nur den Schluessel um.
# Der Test, auf den es ankommt: hinterher trifft der Cache wirklich.


def test_migration_macht_den_alten_cache_wieder_nutzbar(aufbau):
    """Alter Stempel rein, ein Lauf ohne Neubau raus - ohne Audio."""
    gt_datei, baute_fuer = aufbau

    alte_zeilen = [{"set": AID, "t": 120.0, "label": 1, "score": 0.5}]
    retrain_model.FEEDBACK_CACHE.write_text(
        json.dumps({AID: {"stamp": f"{AID}:{gt_datei.stat().st_mtime_ns}",
                          "rows": alte_zeilen}}),
        encoding="utf-8",
    )
    # Der Checkout: Bytes bleiben, die mtime ist weg.
    _mtime_setzen(gt_datei, 1_000_000_000.0)

    cache = json.loads(retrain_model.FEEDBACK_CACHE.read_text(encoding="utf-8"))
    neu, bericht = migrate_feedback_cache_stamps.migriere(cache, gt_datei.parent)
    retrain_model.FEEDBACK_CACHE.write_text(json.dumps(neu), encoding="utf-8")

    assert bericht["migriert"] == [AID]
    zeilen = retrain_model.collect_feedback_rows()
    assert baute_fuer == [], "nach der Migration wurde trotzdem neu gebaut"
    assert zeilen == alte_zeilen, "die Zeilen wurden veraendert"


def test_migration_verwirft_eintraege_ohne_labeldatei(tmp_path):
    """Ohne Ground-Truth-Datei gibt es keinen Inhalt zum Hashen."""
    cache = {"weg.mp3": {"stamp": "fehlt-hier:123", "rows": [{"t": 1.0}]}}
    neu, bericht = migrate_feedback_cache_stamps.migriere(cache, tmp_path)

    assert neu == {}
    assert len(bericht["verworfen"]) == 1
    assert "fehlt-hier" in bericht["verworfen"][0]


def test_migration_laesst_neue_schluessel_in_ruhe(tmp_path):
    """Zweiter Lauf darf nichts mehr bewegen (idempotent)."""
    gt = tmp_path / "abc.json"
    gt.write_text('{"true_transitions_sec": [1.0]}', encoding="utf-8")
    cache = {"set.mp3": {"stamp": f"abc:{gt.stat().st_mtime_ns}", "rows": [{"t": 1.0}]}}

    einmal, _ = migrate_feedback_cache_stamps.migriere(cache, tmp_path)
    zweimal, bericht = migrate_feedback_cache_stamps.migriere(einmal, tmp_path)

    assert zweimal == einmal
    assert bericht["schon_neu"] == ["set.mp3"] and bericht["migriert"] == []
