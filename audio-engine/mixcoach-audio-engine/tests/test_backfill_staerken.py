"""backfill_uebungen: als Staerke eingeschobene Kritik faellt aus gespeicherten Reports."""

from app.audio.coach_summary import LEER_POSITIV
from tools.backfill_uebungen import nachziehen

HARMONIE = ("Uebergang bei 10:46 wechselt harmonisch weit (B Minor -> A Minor, "
            "Camelot 10A -> 8A) - waehle einen Track im Nachbarfeld des Camelot-Rads.")
PEGEL = " Achtung: Der neue Track kommt 4.2 dB leiser - deutlich hoerbarer Pegelsprung, Gain vorher angleichen."
ECHT = "Die Energie steigt im Verlauf an. Gute Dramaturgie."


def _report(strengths, feedbacks):
    uebergaenge = [{"index": i + 1, "mid_sec": 600.0 * (i + 1), "feedback": f,
                    "camelot_before": "10A", "camelot_after": "8A",
                    "key_before": "B Minor", "key_after": "A Minor"}
                   for i, f in enumerate(feedbacks)]
    return {"id": "aaaaaaaa-0000-0000-0000-000000000000", "setTransitions": uebergaenge,
            "strengths": list(strengths), "weaknesses": ["x"],
            "feedback": {"worked": list(strengths)[:2], "improve": ["x"]},
            "exercises": [], "observations": [], "notMeasured": [], "reportRevision": 3}


def test_harmonie_kritik_unter_staerken_faellt_weg():
    # REC012.WAV, Stand 20.07.2026
    neu, _ = nachziehen(_report([HARMONIE, ECHT], [HARMONIE, ""]))
    assert neu["strengths"] == [ECHT]
    assert neu["feedback"]["worked"] == [ECHT]


def test_angehaengter_pegelsatz_wird_trotz_neubildung_erkannt():
    # Fabi, cc3ab3b8: der Text entstand in loudness.py und faellt beim Neubilden
    # des Uebergangs-feedback weg - erkannt werden muss er am Original.
    neu, _ = nachziehen(_report([PEGEL], [PEGEL]))
    assert neu["strengths"] == [LEER_POSITIV]
    assert neu["feedback"]["worked"] == [LEER_POSITIV]


def test_naechste_staerke_rueckt_in_worked_nach():
    zweite = "Der Energiefluss wirkt überwiegend stabil."
    neu, _ = nachziehen(_report([HARMONIE, ECHT, zweite], [HARMONIE]))
    assert neu["feedback"]["worked"] == [ECHT, zweite]


def test_echte_staerken_bleiben_und_revision_zaehlt_nur_bei_aenderung():
    sauber = _report([ECHT], [HARMONIE])
    neu, _ = nachziehen(sauber)
    assert neu["strengths"] == [ECHT]
    zweiter, aenderungen = nachziehen(neu)
    assert not [a for a in aenderungen if a.startswith(("strengths", "feedback.worked"))]


def test_kritik_unter_schwaechen_bleibt():
    r = _report([ECHT], [HARMONIE])
    r["weaknesses"] = [HARMONIE]
    neu, _ = nachziehen(r)
    assert HARMONIE in neu["weaknesses"]


def test_einschub_ohne_herkunft_wird_am_satzmuster_erkannt():
    # REC003.WAV (a5ee0fde), Stand 12.07.: ein frueherer Lauf hat das
    # Uebergangs-feedback neu gebildet, der Satz steht nur noch unter strengths.
    alt = ("Uebergang bei 05:47 wechselt harmonisch weit (G# Minor -> A# Minor, "
           "Camelot 1A -> 3A) - waehle einen Track im Nachbarfeld des Camelot-Rads.")
    neu, _ = nachziehen(_report([alt], [""]))
    assert neu["strengths"] == [LEER_POSITIV]


# --- Das Muster ist an die echten Erzeuger gebunden ----------------------

def test_muster_trifft_den_harmonie_satz_aus_der_quelle():
    from app.audio.transition_quality import _feedback
    from tools.backfill_uebungen import KRITIK_MUSTER
    for mid in (347.0, 6012.0):   # mm:ss und mmm:ss
        satz = _feedback(mid, {"key": "G# Minor", "camelot": "1A"},
                         {"key": "D Major", "camelot": "10B"}, 20)
        assert satz and KRITIK_MUSTER.search(satz), satz


def test_muster_trifft_beide_pegelsaetze_aus_der_quelle():
    import numpy as np
    from app.audio.loudness import JUMP_NOTICEABLE_DB, JUMP_STRONG_DB, annotate_transitions
    from tools.backfill_uebungen import KRITIK_MUSTER
    zeiten = np.arange(0.0, 600.0, 0.5)
    for sprung in (JUMP_STRONG_DB + 0.5, -(JUMP_NOTICEABLE_DB + 0.5)):
        werte = np.where(zeiten < 300.0, -20.0, -20.0 + sprung)
        t = [{"start_sec": 290.0, "end_sec": 310.0, "feedback": ""}]
        annotate_transitions(t, zeiten, werte, 600.0)
        assert t[0]["feedback"] and KRITIK_MUSTER.search(t[0]["feedback"]), t[0]


def test_muster_trifft_den_bass_satz():
    # bass_overlap braucht Originaldateien; der Wortlaut steht dort in
    # annotate_bass_overlap und hier als Literal. Aendert er sich dort,
    # faellt es beim Lesen dieses Tests auf, nicht automatisch.
    from pathlib import Path
    from tools.backfill_uebungen import KRITIK_MUSTER
    quelle = (Path(__file__).resolve().parents[1] / "app/audio/bass_overlap.py").read_text(encoding="utf-8")
    assert "Beide Baesse liefen im Blend uebereinander (Overlap" in quelle
    assert KRITIK_MUSTER.search(" Beide Baesse liefen im Blend uebereinander (Overlap 100/100) - x")


def test_muster_trifft_keine_echte_staerke():
    from app.audio.coach_summary import _build_positives
    from tools.backfill_uebungen import KRITIK_MUSTER
    alle = _build_positives({"quality": {"energy_flow": 90, "transition_density": 90},
                             "dramaturgy": {"energy_trend": "rising"}})
    assert len(alle) == 3
    assert not [s for s in alle + [LEER_POSITIV] if KRITIK_MUSTER.search(s)]
