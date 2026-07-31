"""Tests fuer den Energiebogen (app/audio/dramaturgie.py).

Der wichtigste Test ist test_liefert_keine_note_und_keinen_rat: das Modul
ist als Gegenentwurf zu beatmatching/timing entstanden, die am 31.07.2026
aus der Anzeige genommen wurden, weil sie Noten aus nicht gemessenen
Groessen bildeten. Faellt dieser Test, ist der Fehler zurueck.
"""

from app.audio.dramaturgie import MERKLICH, beschreibung, bogen


def _kurve(werte):
    return [{"t": i * 10, "value": v} for i, v in enumerate(werte)]


def _rampe(von, bis, n=120):
    return [von + (bis - von) * i / (n - 1) for i in range(n)]


def test_durchgehender_aufbau():
    b = bogen(_kurve(_rampe(10, 90)), dauer_sec=3600)
    assert b["form"] == "durchgehender Aufbau"
    assert b["anstieg_gesamt"] > MERKLICH
    assert b["drittel"][0] < b["drittel"][1] < b["drittel"][2]


def test_ausklang_zum_ende():
    b = bogen(_kurve(_rampe(90, 10)), dauer_sec=3600)
    assert b["form"] == "Ausklang zum Ende"
    assert b["anstieg_gesamt"] < -MERKLICH


def test_hoehepunkt_in_der_mitte():
    b = bogen(_kurve(_rampe(10, 90, 60) + _rampe(90, 10, 60)), dauer_sec=3600)
    assert b["form"] == "Bogen mit Hoehepunkt in der Mitte"
    assert 0.35 < b["peak_anteil"] < 0.65


def test_einbruch_in_der_mitte():
    b = bogen(_kurve(_rampe(90, 10, 60) + _rampe(10, 90, 60)), dauer_sec=3600)
    assert b["form"] == "Einbruch in der Mitte"


def test_rauschen_wird_nicht_zur_aussage():
    """Eine flache Kurve mit kleinen Schwankungen darf keine Richtung
    behaupten - sonst wird aus Rauschen eine Dramaturgie."""
    werte = [50 + (2 if i % 2 else -2) for i in range(120)]
    b = bogen(_kurve(werte), dauer_sec=3600)
    assert b["form"] == "gleichbleibend"
    assert abs(b["anstieg_gesamt"]) < MERKLICH


def test_ohne_kurve_kommt_none_und_keine_nullwerte():
    """Keine Kurve heisst kein gemessener Bogen - nicht ein Bogen aus
    Nullen. Das ist der Unterschied, um den es in NOT_YET_MEASURED geht."""
    assert bogen(None) is None
    assert bogen([]) is None
    assert bogen([{"t": 0, "value": 1}]) is None          # zu kurz
    assert bogen([{"t": 0, "kein_value": 1}] * 20) is None
    assert beschreibung(None) == []


def test_peak_und_aufbau_in_sekunden_nur_mit_dauer():
    b_ohne = bogen(_kurve(_rampe(10, 90)))
    assert b_ohne["peak_sec"] is None
    assert b_ohne["peak_anteil"] is not None

    b_mit = bogen(_kurve(_rampe(10, 90)), dauer_sec=1800)
    assert 0 < b_mit["peak_sec"] <= 1800


def test_liefert_keine_note_und_keinen_rat():
    """Kernregel des Moduls. Kein Score-Feld, kein Urteil im Text."""
    b = bogen(_kurve(_rampe(10, 90)), dauer_sec=3600)
    verboten = {"score", "quality", "bewertung", "note", "rating", "punkte_score"}
    assert not (verboten & set(b)), f"Bewertungsfeld aufgetaucht: {verboten & set(b)}"

    text = " ".join(beschreibung(b)).lower()
    for wort in ("gut", "schlecht", "solltest", "besser", "fehler", "zu frueh",
                 "zu spaet", "/100"):
        assert wort not in text, f"Urteil im Text: {wort!r}"


def test_beschreibung_bleibt_bei_kurzer_kurve_stumm_statt_zu_raten():
    b = bogen(_kurve([50] * 40), dauer_sec=600)
    saetze = beschreibung(b)
    assert any("gleichbleibend" in s for s in saetze)
    assert all("Aufbau" not in s for s in saetze)
