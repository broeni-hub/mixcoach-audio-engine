"""coach_summary: unter "Staerken" steht nur, was ein Lob ist."""

from app.audio.coach_summary import LEER_POSITIV, generate_coach_summary

# Die drei Saetze, die seit dem 14.08.2026 in feedback landen koennen - alle Kritik.
KRITIK = [
    "Uebergang bei 18:58 wechselt harmonisch weit (F# Minor -> F Minor, "
    "Camelot 11A -> 4A) - waehle einen Track im Nachbarfeld des Camelot-Rads.",
    " Der neue Track ist 2.2 dB lauter - leichter Pegelsprung.",
    " Beide Baesse liefen im Blend uebereinander (Overlap 100/100) - "
    "schneide den Bass des alten Tracks frueher raus (EQ/Kill).",
]


def _analyse(uebergaenge, trend="stable"):
    return {"quality": {"overall": 70, "rating": "ok"}, "rule_findings": [],
            "dramaturgy": {"energy_trend": trend},
            "transitions_detailed": uebergaenge}


def test_kritik_eines_glatten_uebergangs_wird_kein_lob():
    # Reproduziert an Analyse 1f80c254 (Fabi): label smooth, quality 89,
    # feedback "wechselt harmonisch weit" - stand unter strengths.
    for satz in KRITIK:
        c = generate_coach_summary(_analyse(
            [{"label": "smooth", "quality_score": 89, "feedback": satz}]))
        assert satz not in c["positives"]
        assert c["positives"] == [LEER_POSITIV]


def test_echte_staerke_bleibt_und_wird_nicht_verdraengt():
    c = generate_coach_summary(_analyse(
        [{"label": "smooth", "quality_score": 89, "feedback": KRITIK[0]}], trend="rising"))
    assert c["positives"] == ["Die Energie steigt im Verlauf an. Gute Dramaturgie."]


def test_kritik_rauer_uebergaenge_bleibt_verbesserung():
    c = generate_coach_summary(_analyse(
        [{"label": "rough", "quality_score": 40, "feedback": KRITIK[1]}]))
    assert KRITIK[1] in c["improvements"]
