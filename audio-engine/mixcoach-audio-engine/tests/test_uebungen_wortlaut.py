"""Uebungstexte: kein Satz zweimal, und keiner behauptet, was nicht gemessen ist.

Anlass (14.09.2026): 32 Uebungen aus drei Analysen hatten nach Abzug von
Zeit, Wert und Klammer vier Formulierungen, die haeufigste stand 17-mal.
"""

import re
from collections import Counter
from difflib import SequenceMatcher
from itertools import combinations

import pytest

from app.coach.uebungen import (
    BIBLIOTHEK,
    FASSUNGEN,
    GEMESSENES_MAXIMUM,
    STUFE_DEUTLICH,
    STUFE_WEIT,
    TITEL,
    baue,
)

AID = "11111111-2222-3333-4444-555555555555"

# Wahrnehmung und Wirkung sind nicht gemessen - in keiner Fassung, in keiner
# Sprache. Die englische Bibliothek kam am 22.09.2026 dazu und faellt unter
# dieselben Regeln.
NIE = {"de": ("hörbar", "hoerbar", "klingt", "raum ", "publikum", "dancefloor",
              "matsch", "spürbar", "wirkt", "kostet"),
       "en": ("audible", "sounds ", "the room", "crowd", "dancefloor", "muddy",
              "feels ", "costs ")}
# Der Jitter ist eine Streuung: keine Richtung, weder zeitlich noch im Pegel.
NIE_BEIM_JITTER = {"de": ("zu früh", "zu frueh", "zu spät", "zu spaet", "lauter", "leiser"),
                   "en": ("too early", "too late", "louder", "quieter")}


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


@pytest.mark.parametrize("sprache", sorted(BIBLIOTHEK))
def test_jede_liste_ist_laenger_als_das_gemessene_maximum(sprache):
    fassungen, _ = BIBLIOTHEK[sprache]
    for fall, maximum in GEMESSENES_MAXIMUM.items():
        assert len(fassungen[fall]) > maximum, (sprache, fall)


@pytest.mark.parametrize("sprache", sorted(BIBLIOTHEK))
def test_jede_fassung_nennt_den_wert(sprache):
    fassungen, _ = BIBLIOTHEK[sprache]
    for fall, liste in fassungen.items():
        for f in liste:
            assert "{w}" in f, (sprache, fall, f)


@pytest.mark.parametrize("sprache", sorted(BIBLIOTHEK))
def test_jede_pegelfassung_nennt_die_richtung(sprache):
    fassungen, _ = BIBLIOTHEK[sprache]
    for (art, _), liste in fassungen.items():
        if art in ("lauter", "leiser"):
            for f in liste:
                assert "{r}" in f, (sprache, f)


@pytest.mark.parametrize("sprache", sorted(BIBLIOTHEK))
def test_jede_sprache_deckt_dieselben_faelle_ab(sprache):
    fassungen, titel = BIBLIOTHEK[sprache]
    assert set(fassungen) == set(FASSUNGEN), sprache
    assert set(titel) == set(TITEL), sprache


@pytest.mark.parametrize("sprache", sorted(BIBLIOTHEK))
def test_keine_fassung_behauptet_wahrnehmung_oder_wirkung(sprache):
    fassungen, _ = BIBLIOTHEK[sprache]
    for fall, liste in fassungen.items():
        for f in liste:
            klein = f.lower()
            for wort in NIE[sprache]:
                assert wort not in klein, (sprache, fall, wort, f)
            if fall[0] == "beat_jitter_ms":
                for wort in NIE_BEIM_JITTER[sprache]:
                    assert wort not in klein, (sprache, fall, wort, f)


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


@pytest.mark.parametrize("sprache", sorted(BIBLIOTHEK))
def test_keine_zwei_fassungen_derselben_groesse_sind_fast_gleich(sprache):
    """Wortgleich ist nicht der einzige Fehler - fast gleich liest sich genauso.

    Am 14.09.2026 zeigte die Vorfuehrung an Fabis Set zwei Uebungen, die sich
    nur in "lauter/leiser" und "nachziehen/hochziehen" unterschieden (96 %
    gleich). Die Pegel-Listen waren parallel gebaut. Geprueft wird ueber ALLE
    Fassungen einer Groesse, weil ein Report jede Kombination ziehen kann.
    """
    # Verglichen wird, was der Leser sieht: MIT dem Zielsatz, der an jede
    # Uebung derselben Groesse gleich angehaengt wird. Ohne ihn lag ein Paar
    # am 16.09.2026 bei 0,79 und kam durch - gelesen waren es 0,83, und
    # "Den einkommenden Kanal vorab anheben" stand zweimal untereinander.
    fassungen, _ = BIBLIOTHEK[sprache]
    ziel = " Ziel: unter «w»." if sprache == "de" else " Target: under «w»."
    for groesse in ("pegel", "jitter"):
        faelle = [k for k in fassungen
                  if (k[0] in ("lauter", "leiser")) == (groesse == "pegel")]
        texte = [(k, f.format(w="«w»", r=k[0] if k[0] in ("lauter", "leiser") else "") + ziel)
                 for k in faelle for f in fassungen[k]]
        zu_nah = [(round(SequenceMatcher(None, a, b).ratio(), 2), ka, kb)
                  for (ka, a), (kb, b) in combinations(texte, 2)
                  if SequenceMatcher(None, a, b).ratio() >= 0.80]
        assert not zu_nah, (sprache, groesse, zu_nah)


@pytest.mark.parametrize("sprache", sorted(BIBLIOTHEK))
def test_kein_satzanfang_zweimal_je_gruppe(sprache):
    """Gleich beginnende Zeilen untereinander lesen sich wie Copy-Paste - auch
    wenn der Rest verschieden ist.

    Am 16.09.2026 standen in Fabis Ü30-Report "startete der neue Track 8,7 dB
    leiser" und "startete der neue Track 4,5 dB leiser" direkt untereinander,
    bei 0,72 Aehnlichkeit - der Aehnlichkeitstest liess es durch. Im Bestand
    waren es 21 doppelte Anfaenge in 12 Reports.

    Sind die Anfaenge je Gruppe eindeutig, genuegt das: innerhalb eines Falls
    ist die Rotation wiederholungsfrei, solange die Liste laenger ist als das
    Maximum (test_jede_liste_ist_laenger_als_das_gemessene_maximum).
    """
    fassungen, _ = BIBLIOTHEK[sprache]
    for gruppe in ("lauter", "leiser", "beat_jitter_ms"):
        anfaenge = Counter(" ".join(f.split()[:3])
                           for k in fassungen if k[0] == gruppe for f in fassungen[k])
        doppelt = [a for a, n in anfaenge.items() if n > 1]
        assert not doppelt, (sprache, gruppe, doppelt)


@pytest.mark.parametrize("sprache", sorted(BIBLIOTHEK))
def test_report_mit_den_meisten_uebungen_hat_keinen_anfang_doppelt(sprache):
    # Hoechstwerte je Report im Bestand (16.09.2026): 11 Jitter, 7 zu laut, 4 zu leise.
    uebergaenge = (
        [_uebergang(i, beat_jitter_ms=15.5 + i * 0.3) for i in range(1, 7)]
        + [_uebergang(10 + i, beat_jitter_ms=21.0 + i * 0.5) for i in range(5)]
        + [_uebergang(20 + i, loudness_jump_db=3.2 + i * 0.1) for i in range(4)]
        + [_uebergang(25 + i, loudness_jump_db=4.3 + i * 0.1) for i in range(2)]
        + [_uebergang(28, loudness_jump_db=6.0)]
        + [_uebergang(30 + i, loudness_jump_db=-4.5 - i * 0.1) for i in range(3)]
        + [_uebergang(40, loudness_jump_db=-6.0)]
    )
    uebungen, _ = baue(AID, uebergaenge, sprache=sprache)
    anfaenge = Counter(
        (u["metric"] if u["metric"] == "beat_jitter_ms" else ("lauter" if u["value"] > 0 else "leiser"),
         " ".join(re.sub(r"^(Bei|At) \S+ \([^)]*\) ", "", u["description"]).split()[:3]))
        for u in uebungen)
    assert len(uebungen) == 22
    assert max(anfaenge.values()) == 1, [a for a, n in anfaenge.items() if n > 1]
