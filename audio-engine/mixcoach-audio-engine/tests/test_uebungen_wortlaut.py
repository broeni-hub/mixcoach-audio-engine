"""Uebungstexte: kein Satz zweimal, und keiner behauptet, was nicht gemessen ist.

Anlass (14.09.2026): 32 Uebungen aus drei Analysen hatten nach Abzug von
Zeit, Wert und Klammer vier Formulierungen, die haeufigste stand 17-mal.
"""

import re
from collections import Counter

from app.coach.uebungen import (
    FASSUNGEN,
    GEMESSENES_MAXIMUM,
    STUFE_DEUTLICH,
    STUFE_WEIT,
    TITEL,
    baue,
)

AID = "11111111-2222-3333-4444-555555555555"

# Wahrnehmung und Wirkung sind nicht gemessen - in keiner Fassung.
NIE = ("hörbar", "hoerbar", "klingt", "raum ", "publikum", "dancefloor",
       "matsch", "spürbar", "wirkt", "kostet")
# Der Jitter ist eine Streuung: keine Richtung, weder zeitlich noch im Pegel.
NIE_BEIM_JITTER = ("zu früh", "zu frueh", "zu spät", "zu spaet", "lauter", "leiser")


def _uebergang(index, **felder):
    t = {"index": index, "mid_sec": 60.0 * index, "start_sec": 60.0 * index - 10}
    t.update(felder)
    return t


def _rumpf(text):
    """Text ohne Zeit, Wert und Klammer - uebrig bleibt die Formulierung."""
    text = re.sub(r"\d+:\d{2}", "«zeit»", text)
    text = re.sub(r"\d+,\d\s*(ms|dB)", "«wert»", text)
    return re.sub(r"\([^)]*\)", "«klammer»", text)


def test_im_report_steht_keine_formulierung_zweimal():
    # Die Obergrenzen aus dem Bestand: 6 knappe Jitter- und 4 knappe
    # Pegel-Uebungen in einem Report, dazu je Stufe mehrere.
    uebergaenge = (
        [_uebergang(i, beat_jitter_ms=15.5 + i * 0.3) for i in range(1, 7)]
        + [_uebergang(10 + i, beat_jitter_ms=21.0 + i * 0.5) for i in range(5)]
        + [_uebergang(20 + i, loudness_jump_db=3.2 + i * 0.1) for i in range(4)]
        + [_uebergang(30 + i, loudness_jump_db=-4.5 - i * 0.1) for i in range(3)]
        + [_uebergang(40 + i, loudness_jump_db=-6.0 - i * 0.2) for i in range(3)]
    )
    uebungen, _ = baue(AID, uebergaenge)
    assert len(uebungen) == 21
    rumpf = Counter(_rumpf(u["description"]) for u in uebungen)
    doppelt = {r: n for r, n in rumpf.items() if n > 1}
    assert not doppelt, doppelt


def test_jede_liste_ist_laenger_als_das_gemessene_maximum():
    for fall, maximum in GEMESSENES_MAXIMUM.items():
        assert len(FASSUNGEN[fall]) > maximum, fall


def test_jede_fassung_nennt_den_wert():
    for fall, liste in FASSUNGEN.items():
        for f in liste:
            assert "{w}" in f, (fall, f)


def test_jede_pegelfassung_nennt_die_richtung():
    for (art, _), liste in FASSUNGEN.items():
        if art in ("lauter", "leiser"):
            for f in liste:
                assert "{r}" in f, f


def test_keine_fassung_behauptet_wahrnehmung_oder_wirkung():
    for fall, liste in FASSUNGEN.items():
        for f in liste:
            klein = f.lower()
            for wort in NIE:
                assert wort not in klein, (fall, wort, f)
            if fall[0] == "beat_jitter_ms":
                for wort in NIE_BEIM_JITTER:
                    assert wort not in klein, (fall, wort, f)


def test_zu_laut_und_zu_leise_geben_entgegengesetzte_handgriffe():
    lauter, _ = baue(AID, [_uebergang(1, loudness_jump_db=4.5)])
    leiser, _ = baue(AID, [_uebergang(1, loudness_jump_db=-4.5)])
    assert "lauter" in lauter[0]["description"]
    assert "leiser" in leiser[0]["description"]
    assert lauter[0]["description"] != leiser[0]["description"].replace("leiser", "lauter")


def test_titel_traegt_den_aufwand():
    for faktor, stufe in ((1.05, "knapp"), (STUFE_DEUTLICH, "deutlich"), (STUFE_WEIT, "weit")):
        u, _ = baue(AID, [_uebergang(1, beat_jitter_ms=15.0 * faktor)])
        assert u[0]["title"].startswith(TITEL[("beat_jitter_ms", stufe)])


def test_gleicher_report_gleicher_wortlaut():
    # Deterministisch - ein Backfill darf den Text nicht bei jedem Lauf wuerfeln.
    uebergaenge = [_uebergang(i, beat_jitter_ms=16.0 + i) for i in range(1, 5)]
    a, _ = baue(AID, uebergaenge)
    b, _ = baue(AID, uebergaenge)
    assert [u["description"] for u in a] == [u["description"] for u in b]


def test_zwei_reports_beginnen_nicht_mit_derselben_fassung():
    einzeln = [_uebergang(1, beat_jitter_ms=16.0)]
    texte = {_rumpf(baue(f"{i:08d}-aaaa-bbbb-cccc-dddddddddddd", einzeln)[0][0]["description"])
             for i in range(20)}
    assert len(texte) > 1
