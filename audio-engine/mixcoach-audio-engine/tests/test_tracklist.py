"""Tracknamen aus der Tracklist des DJs (A3).

Der wichtigste Test ist test_ohne_zeiten_und_ohne_passende_zahlen_lieber_nichts:
faellt er, ordnet das Modul nach Position zu, obwohl ein Uebergang fehlt -
und dann steht unter JEDEM folgenden Uebergang ein falscher, aber
selbstbewusster Trackname. Das ist derselbe Fehler wie die Sekundenangabe,
die am 27.08. durch ein Fenster ersetzt wurde.

Hintergrund: ein fremder DJ bekommt heute 0 % Tracknamen, weil seine Tracks
nicht im Fingerabdruck-Index stehen. Das ist Bauart, kein Fehler - der Index
kennt 6113 Tracks, und das sind Sebastians.
"""

import pytest

from app.audio.tracklist import lesen, zuordnen


def _u(index, start):
    return {"index": index, "start_sec": float(start), "mid_sec": float(start) + 15}


# --- Die Tracklist lesen ---------------------------------------------------


def test_zeiten_in_minuten_und_sekunden():
    t = lesen("00:00 Track A\n05:42 Track B")
    assert [x["sec"] for x in t] == [0.0, 342.0]
    assert [x["titel"] for x in t] == ["Track A", "Track B"]


def test_zeiten_mit_stunden():
    assert lesen("1:05:42 Track A")[0]["sec"] == 3942.0


def test_gaengige_schreibweisen():
    """Wie DJs Tracklists wirklich schreiben."""
    for zeile in ("[05:42] Track A", "05:42 - Track A", "5.42  Track A",
                  "05:42) Track A"):
        gelesen = lesen(zeile)
        assert gelesen[0]["sec"] == 342.0, zeile
        assert gelesen[0]["titel"] == "Track A", zeile


def test_nummerierung_ohne_zeit():
    t = lesen("1. Track A\n2) Track B\n03 - Track C")
    assert [x["sec"] for x in t] == [None, None, None]
    assert [x["titel"] for x in t] == ["Track A", "Track B", "Track C"]


def test_leerzeilen_und_muell_fallen_weg():
    assert len(lesen("Track A\n\n  \nTrack B\n")) == 2


# --- Der Weg ueber Zeiten --------------------------------------------------


def test_mit_zeiten_wird_der_naechsten_grenze_zugeordnet():
    tracks = lesen("00:00 A\n05:42 B\n09:10 C")
    ue = [_u(1, 340), _u(2, 548)]
    b = zuordnen(ue, tracks)
    assert b["weg"] == "zeiten" and b["zugeordnet"] == 2
    assert (ue[0]["track_out"], ue[0]["track_in"]) == ("A", "B")
    assert (ue[1]["track_out"], ue[1]["track_in"]) == ("B", "C")


def test_mit_zeiten_geht_auch_bei_fehlendem_uebergang():
    """Der Vorteil des Zeit-Wegs: er braucht keine passenden Zahlen."""
    tracks = lesen("00:00 A\n05:00 B\n10:00 C\n15:00 D")
    ue = [_u(1, 298), _u(2, 898)]        # der Uebergang B->C fehlt
    b = zuordnen(ue, tracks)
    assert b["zugeordnet"] == 2
    assert (ue[0]["track_out"], ue[0]["track_in"]) == ("A", "B")
    assert (ue[1]["track_out"], ue[1]["track_in"]) == ("C", "D")


# --- Der Weg ueber die Reihenfolge -----------------------------------------


def test_ohne_zeiten_mit_passenden_zahlen():
    tracks = lesen("A\nB\nC")
    ue = [_u(1, 100), _u(2, 200)]
    b = zuordnen(ue, tracks)
    assert b["weg"] == "reihenfolge" and b["zugeordnet"] == 2
    assert (ue[1]["track_out"], ue[1]["track_in"]) == ("B", "C")


def test_ohne_zeiten_und_ohne_passende_zahlen_lieber_nichts():
    """Der Kern. Ein fehlender Uebergang verschoebe ALLE folgenden Namen."""
    tracks = lesen("A\nB\nC\nD")
    ue = [_u(1, 100), _u(2, 200)]        # 4 Tracks braeuchten 3 Uebergaenge
    b = zuordnen(ue, tracks)
    assert b["zugeordnet"] == 0
    assert "nicht sicher zuordnen" in b["grund"]
    assert all("track_in" not in u for u in ue)


# --- Gemessen schlaegt genannt ---------------------------------------------


def test_ein_fingerabdruck_treffer_wird_nicht_ueberschrieben():
    tracks = lesen("00:00 A\n05:00 B")
    ue = [{"index": 1, "start_sec": 298.0, "track_out": "Echt - Gemessen",
           "track_in": "Auch - Gemessen", "detection": "fingerprint"}]
    zuordnen(ue, tracks)
    assert ue[0]["track_out"] == "Echt - Gemessen"
    assert ue[0]["detection"] == "fingerprint"


def test_die_herkunft_steht_dabei():
    """Das Werkzeug hat es erkannt oder der Mensch hat es behauptet - das
    ist nicht dasselbe und gehoert unterscheidbar."""
    tracks = lesen("00:00 A\n05:00 B")
    ue = [_u(1, 298)]
    zuordnen(ue, tracks)
    assert ue[0]["detection"] == "tracklist"


def test_zu_wenig_eingabe_macht_nichts_kaputt():
    ue = [_u(1, 100)]
    assert zuordnen(ue, lesen("nur eine Zeile"))["zugeordnet"] == 0
    assert zuordnen([], lesen("A\nB"))["zugeordnet"] == 0
