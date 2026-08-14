"""Belegpflicht: jede Uebung nennt eine Zahl, die im selben Report steht.

Der wichtigste Test ist test_kein_report_zeigt_eine_vorlage: faellt er, hat
jemand wieder einen Text eingebaut, der ohne Messung auskommt. Genau so ist
"Transition Review - listen to the detected transition points" entstanden
und stand danach in allen 51 Reports.

Die Trennung Uebung/Beobachtung ist ebenso Gegenstand: eine Beobachtung
darf feststellen, aber nicht auffordern.
"""

import json
from pathlib import Path

import pytest

from app.coach.uebungen import (
    SCHWELLE_PEGELSPRUNG_DB,
    _camelot_abstand,
    _uebergangsname,
    _zeit,
    baue,
)

AID = "test-analyse"


def _uebergang(index: int, **felder):
    basis = {"index": index, "mid_sec": 100.0 * index, "start_sec": 100.0 * index - 16}
    basis.update(felder)
    return basis


# --- Die Belegpflicht ------------------------------------------------------


def test_jede_uebung_nennt_eine_zahl_aus_dem_report():
    uebergaenge = [
        _uebergang(1, loudness_jump_db=4.2),
        _uebergang(2, loudness_jump_db=-5.0),
        _uebergang(3, loudness_jump_db=0.4),
    ]
    uebungen, _ = baue(AID, uebergaenge)

    assert len(uebungen) == 2, "nur die zwei ueber der Schwelle"
    for u in uebungen:
        assert u["metric"], "metric ist Pflicht"
        assert u["value"] is not None, "value ist Pflicht"
        # Die Zahl muss im Text auftauchen, sonst ist der Beleg unsichtbar.
        assert f"{abs(u['value']):.1f}".replace(".", ",") in u["description"]
        # Und sie muss zum genannten Uebergang gehoeren.
        passend = next(t for t in uebergaenge if t["index"] == u["transitionIndex"])
        assert passend["loudness_jump_db"] == u["value"]


def test_ohne_belegte_zahl_keine_uebung():
    """Der Kern des Auftrags: lieber schweigen als eine Vorlage zeigen."""
    uebergaenge = [
        _uebergang(1),                                  # gar kein Pegelwert
        _uebergang(2, loudness_jump_db=None),
        _uebergang(3, loudness_jump_db=1.2),            # unter der Schwelle
        _uebergang(4, camelot_before="8A", camelot_after="11B"),
    ]
    uebungen, _ = baue(AID, uebergaenge)
    assert uebungen == []


def test_schwelle_ist_einschliessend():
    genau, knapp = baue(AID, [_uebergang(1, loudness_jump_db=SCHWELLE_PEGELSPRUNG_DB)])[0], \
        baue(AID, [_uebergang(1, loudness_jump_db=SCHWELLE_PEGELSPRUNG_DB - 0.01)])[0]
    assert len(genau) == 1
    assert knapp == []


def test_uebung_traegt_alle_pflichtfelder():
    uebungen, _ = baue(AID, [_uebergang(2, loudness_jump_db=4.2)])
    u = uebungen[0]
    for feld in ("title", "description", "analysisId", "transitionIndex",
                 "atSec", "metric", "value", "target", "xp"):
        assert feld in u, f"{feld} fehlt"
    assert u["analysisId"] == AID
    assert u["transitionIndex"] == 2
    assert u["atSec"] == 184.0        # start_sec, zum Anspringen


def test_schlimmster_sprung_zuerst():
    uebungen, _ = baue(AID, [
        _uebergang(1, loudness_jump_db=3.2),
        _uebergang(2, loudness_jump_db=-7.5),
        _uebergang(3, loudness_jump_db=4.9),
    ])
    assert [abs(u["value"]) for u in uebungen] == [7.5, 4.9, 3.2]


def test_richtung_wird_benannt():
    lauter, _ = baue(AID, [_uebergang(1, loudness_jump_db=4.2)])
    leiser, _ = baue(AID, [_uebergang(1, loudness_jump_db=-4.2)])
    assert "lauter" in lauter[0]["description"]
    assert "leiser" in leiser[0]["description"]


# --- Tracknamen: nie erfinden ---------------------------------------------


def test_ohne_tracknamen_die_uebergangsnummer():
    assert _uebergangsname({"index": 7}) == "Übergang 7"
    assert "?" not in _uebergangsname({"index": 7})


def test_mit_tracknamen_die_namen():
    name = _uebergangsname({"index": 7, "track_out": "A", "track_in": "B"})
    assert name == "A → B"


# --- Beobachtungen: feststellen, nicht auffordern -------------------------


def test_beobachtungen_sind_von_uebungen_getrennt():
    uebungen, beobachtungen = baue(AID, [
        _uebergang(1, camelot_before="8A", camelot_after="11B"),
        _uebergang(2, energy_dip_pct=35.0),
    ])
    assert uebungen == [], "ohne Pegelsprung keine Uebung"
    assert len(beobachtungen) == 2


def test_beobachtungen_fordern_nicht_auf():
    """Kein Imperativ - sonst ist es eine Aufgabe ohne Beleg."""
    _, beobachtungen = baue(AID, [
        _uebergang(1, camelot_before="8A", camelot_after="11B"),
        _uebergang(2, energy_dip_pct=35.0),
    ])
    for b in beobachtungen:
        text = b["text"].lower()
        for aufforderung in ("mix ihn", "übe ", "ziel:", "achte", "probier",
                             "wiederhol", "korrigier"):
            assert aufforderung not in text, f"{aufforderung!r} in {b['text']!r}"
        assert "nicht ablesbar" in text, "die Unsicherheit muss dastehen"


def test_camelot_abstand_rechnet_ueber_das_rad():
    assert _camelot_abstand("8A", "9A") == 1
    assert _camelot_abstand("12A", "1A") == 1      # ueber die Null
    assert _camelot_abstand("8A", "8B") == 1       # Dur/Moll-Wechsel
    assert _camelot_abstand("8A", "11B") == 4
    assert _camelot_abstand(None, "8A") is None


def test_zeit_wird_als_minuten_gezeigt():
    assert _zeit(767) == "12:47"
    assert _zeit(0) == "0:00"
    assert _zeit(None) == "?"


# --- Der Bestand ----------------------------------------------------------


def _reports():
    ordner = Path(__file__).resolve().parents[3] / "daten" / "analysis_results"
    return sorted(ordner.glob("*.json")) if ordner.exists() else []


@pytest.mark.skipif(not _reports(), reason="kein Datenstamm in dieser Umgebung")
def test_kein_report_zeigt_eine_vorlage():
    """Ueber den echten Bestand: keine Uebung ohne metric/value, und keine,
    deren Zahl nicht im selben Report unter demselben Index steht."""
    verstoesse = []
    for pfad in _reports():
        try:
            report = json.loads(pfad.read_text(encoding="utf-8"))
        except Exception:
            continue
        nach_index = {t.get("index"): t for t in (report.get("setTransitions") or [])}
        for u in (report.get("exercises") or []):
            if not u.get("metric") or u.get("value") is None:
                verstoesse.append(f"{pfad.name}: Uebung ohne Zahl - {u.get('title')!r}")
                continue
            t = nach_index.get(u.get("transitionIndex"))
            if t is None:
                verstoesse.append(f"{pfad.name}: Uebung ohne passenden Uebergang")
                continue
            if t.get(u["metric"]) != u["value"]:
                verstoesse.append(
                    f"{pfad.name} #{u['transitionIndex']}: {u['metric']}="
                    f"{u['value']} steht so nicht im Report ({t.get(u['metric'])})")
    assert not verstoesse, "\n".join(verstoesse[:10])
