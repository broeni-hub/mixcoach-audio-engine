"""backfill_uebungen: als Staerke eingeschobene Kritik faellt aus gespeicherten Reports."""

from app.audio.coach_summary import LEER_POSITIV, LEER_VERBESSERUNG
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


def test_harmonie_kritik_faellt_jetzt_auch_unter_schwaechen():
    """Umgedreht am 23.09.2026 - eine Regel, die eine Messung widerlegt hat.

    Bis heute hiess dieser Test "test_kritik_unter_schwaechen_bleibt" und
    forderte das Gegenteil: unter weaknesses sei der Harmonie-Satz richtig,
    denn dort gehoert Kritik hin. Das stimmte, solange man annahm, dass ein
    weiter Tonartwechsel ein Mangel ist.

    Gemessen ist er keiner: Camelot-Abstand gegen das menschliche Urteil
    rho +0,063 (n=297, p 0,28); kompatible und inkompatible Wechsel werden
    gleich bewertet, Median 4,0 gegen 4,0, Mann-Whitney p = 0,355
    (tools/eval/harmonik.py). Eine Kritik ohne Beleg ist keine Kritik,
    sondern eine Behauptung - und die faellt, egal unter welcher
    Ueberschrift sie steht.
    """
    r = _report([ECHT], [HARMONIE])
    r["weaknesses"] = [HARMONIE]
    neu, _ = nachziehen(r)
    assert HARMONIE not in neu["weaknesses"]
    assert neu["weaknesses"] == [LEER_VERBESSERUNG]


def test_der_belegte_teil_desselben_eintrags_bleibt():
    """Der Grund, warum geschnitten und nicht verworfen wird.

    In weaknesses steht der Harmonie-Satz haeufig zusammen mit einem
    Pegel-Satz in EINEM String. Den ganzen Eintrag zu verwerfen waere
    derselbe Fehler wie beim ersten Backfill-Lauf desselben Tages, der die
    vier belegten Saetze des Bestands geloescht hat.
    """
    r = _report([ECHT], [""])
    r["weaknesses"] = [HARMONIE + PEGEL]
    neu, _ = nachziehen(r)
    assert len(neu["weaknesses"]) == 1
    assert "Nachbarfeld" not in neu["weaknesses"][0]
    assert "4.2 dB leiser" in neu["weaknesses"][0]


def test_einschub_ohne_herkunft_wird_am_satzmuster_erkannt():
    # REC003.WAV (a5ee0fde), Stand 12.07.: ein frueherer Lauf hat das
    # Uebergangs-feedback neu gebildet, der Satz steht nur noch unter strengths.
    alt = ("Uebergang bei 05:47 wechselt harmonisch weit (G# Minor -> A# Minor, "
           "Camelot 1A -> 3A) - waehle einen Track im Nachbarfeld des Camelot-Rads.")
    neu, _ = nachziehen(_report([alt], [""]))
    assert neu["strengths"] == [LEER_POSITIV]


# --- Das Muster ist an die echten Erzeuger gebunden ----------------------

def test_muster_trifft_den_harmonie_satz_weiterhin():
    """Der Harmonie-Satz hat seit dem 23.09.2026 keine Quelle mehr.

    _feedback erzeugt ihn nicht laenger (er war eine Aufforderung ohne
    Beleg, siehe dort). In den gespeicherten Reports steht er aber noch -
    311 mal - und der Backfill muss ihn dort weiter finden. Deshalb haengt
    dieser Test ab sofort am WORTLAUT AUS DEM BESTAND, nicht am Erzeuger.
    Beide Zeitformen, mm:ss und mmm:ss.
    """
    from tools.backfill_uebungen import KRITIK_MUSTER
    for at in ("05:47", "100:12"):
        satz = (f"Uebergang bei {at} wechselt harmonisch weit "
                "(G# Minor -> D Major, Camelot 1A -> 10B) - "
                "waehle einen Track im Nachbarfeld des Camelot-Rads.")
        assert KRITIK_MUSTER.search(satz), satz


def test_der_erzeuger_bildet_den_satz_nicht_mehr():
    """Gegenprobe zum Test darueber: die Quelle ist versiegt."""
    from app.audio.transition_quality import _feedback
    assert _feedback(347.0, {"key": "G# Minor", "camelot": "1A"},
                     {"key": "D Major", "camelot": "10B"}, 20) == ""


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


# --- Der Backfill darf die belegte Groesse nicht mitnehmen ----------------

def test_backfill_behaelt_den_pegelsatz_wenn_die_harmonik_faellt():
    """Der Fehler vom 23.09.2026, festgehalten.

    _saetze_neu baute das feedback-Feld allein aus transition_quality.
    _feedback neu und warf alles weg, was loudness/bass_overlap in der
    Live-Kette angehaengt hatten. Solange _feedback selbst noch einen Satz
    schrieb, sah der Verlust aus wie "dieser Uebergang hatte eben keinen
    Pegelsprung". Als _feedback verstummte, loeschte ein einziger Lauf alle
    311 Saetze des Bestands - darunter die vier belegten.

    Der Pegelsprung ist die aelteste belegte Groesse des Projekts. Er muss
    einen Backfill ueberleben, und zwar nachgerechnet aus loudness_jump_db,
    nicht aus dem alten Text.
    """
    r = _report([], [HARMONIE + PEGEL])
    r["setTransitions"][0]["loudness_jump_db"] = -4.2

    neu, _ = nachziehen(r)
    satz = neu["setTransitions"][0]["feedback"]

    assert "Nachbarfeld" not in satz          # Harmonik: weg
    assert "4.2 dB leiser" in satz            # Pegel: bleibt
    assert satz == PEGEL.strip()              # und sonst nichts


def test_backfill_baut_den_pegelsatz_auch_neu_wenn_er_fehlte():
    """Aus der Zahl, nicht aus dem Text - deshalb repariert derselbe Lauf
    auch Reports, denen ein frueherer Backfill den Satz genommen hat."""
    r = _report([], [HARMONIE])               # kein Pegel-Satz im Text
    r["setTransitions"][0]["loudness_jump_db"] = -4.2

    neu, _ = nachziehen(r)
    assert "4.2 dB leiser" in neu["setTransitions"][0]["feedback"]


def test_kleiner_sprung_bekommt_weiter_keinen_satz():
    """Unter der Schwelle bleibt es still - sonst waere jeder Uebergang ein Befund."""
    r = _report([], [HARMONIE])
    r["setTransitions"][0]["loudness_jump_db"] = -0.4

    neu, _ = nachziehen(r)
    assert neu["setTransitions"][0]["feedback"] == ""


# --- Die vierte Kopie: feedback.exercise ("SET FLOW") --------------------

def test_set_flow_satz_wird_mit_nachgezogen():
    """Gefunden am 23.09.2026 beim Oeffnen der laufenden App.

    Die Uebergangsliste war sauber, strengths und feedback.worked auch - und
    unter "SET FLOW" stand weiter ein Satz aus der Zeit vor dem 14.08.2026:
    Phrasenstart, BPM-Sprung und Camelot-Ratschlag in einem. Kein Lauf hatte
    feedback.exercise je angefasst.
    """
    alt = ("Uebergang bei 11:09 liegt 8 Beats neben dem Phrasenstart - starte "
           "den Uebergang ca. 8 Beats frueher oder spaeter; ausserdem wechselt "
           "harmonisch weit (D# Minor -> G Minor, Camelot 2A -> 6A) - waehle "
           "einen Track im Nachbarfeld des Camelot-Rads.")
    r = _report([], [""])
    r["weaknesses"] = [alt]
    r["feedback"] = {"worked": [], "improve": [alt], "exercise": alt}

    neu, _ = nachziehen(r)
    assert "Nachbarfeld" not in (neu["feedback"]["exercise"] or "")
    assert "Phrasenstart" not in (neu["feedback"]["exercise"] or "")


def test_set_flow_nimmt_den_belegten_satz_wenn_es_einen_gibt():
    """Entfallen soll das Unbelegte, nicht der ganze Abschnitt."""
    r = _report([], [""])
    r["feedback"] = {"worked": [], "improve": [PEGEL.strip()], "exercise": ""}

    neu, _ = nachziehen(r)
    assert "Pegelsprung" in neu["feedback"]["exercise"]


def test_set_flow_bleibt_leer_statt_den_leersatz_zu_wiederholen():
    """Sonst stuende derselbe Satz zweimal auf der Seite - einmal als
    'groesstes Problem', einmal als 'Set Flow'."""
    from app.audio.coach_summary import LEER_VERBESSERUNG
    r = _report([], [""])
    r["feedback"] = {"worked": [], "improve": [LEER_VERBESSERUNG], "exercise": "irgendwas"}

    neu, _ = nachziehen(r)
    assert neu["feedback"]["exercise"] == ""


def test_keine_vorlage_mehr_wenn_nichts_gemessen_ist():
    """Der Rueckfalltext ('Review the detected transition zones ...') nannte
    keine einzige Zahl - dieselbe Sorte Vorlage, die am 14.08.2026 aus den
    Uebungen geflogen ist."""
    from app.api.analysis_mapper import _build_exercise
    assert _build_exercise({"improvements": []}) == ""
    assert _build_exercise({}) == ""
