"""Die Besitzer-Migration muss restlos umkehrbar sein (F2.1).

Der wichtigste Test ist test_hin_und_zurueck_ist_byteidentisch. Er ist
nicht theoretisch: die erste Fassung des Werkzeugs hat beim Zurueckgehen
182 Dateien veraendert, ohne dass inhaltlich etwas anders war - CRLF aus
der Windows-Zeit, von write_text stillschweigend zu LF gemacht. Nach dem
Fix waren es noch 113, weil die Archiv-Reports mit \\u00f6 statt oe
geschrieben sind.

Beides ist inhaltlich nichts und im Diff alles. Ein Werkzeug, das ueber
250 Dateien laeuft, darf so etwas nicht nebenbei tun.
"""

import json

import pytest

from tools import migriere_besitzer as mb

# Die Schreibweisen, die im echten Bestand vorkommen - und ein paar
# Nachbarn, damit die Erkennung nicht nur genau diese trifft.
FORMEN = [
    {"indent": None, "ensure_ascii": False, "crlf": False, "schluss": ""},
    {"indent": None, "ensure_ascii": True, "crlf": False, "schluss": ""},
    {"indent": 1, "ensure_ascii": False, "crlf": True, "schluss": "\n"},
    {"indent": 1, "ensure_ascii": True, "crlf": True, "schluss": ""},
    {"indent": 2, "ensure_ascii": False, "crlf": False, "schluss": "\n"},
    {"indent": 4, "ensure_ascii": True, "crlf": True, "schluss": "\n"},
]

INHALT = {
    "id": "abc", "fileName": "Möglicher Track - Grüße.wav",
    "verdicts": {"6": {"midSec": 1126.1, "verdict": "not_a_transition"}},
    "missed": [], "updatedAt": 1783926204.021257,
}


@pytest.mark.parametrize("form", FORMEN, ids=lambda f: f"i{f['indent']}-a{int(f['ensure_ascii'])}-c{int(f['crlf'])}-s{len(f['schluss'])}")
def test_hin_und_zurueck_ist_byteidentisch(tmp_path, form):
    pfad = tmp_path / "x.json"
    original = mb._bauen(INHALT, form)
    pfad.write_bytes(original)

    # hin
    daten = json.loads(pfad.read_bytes().decode("utf-8"))
    erkannt = mb._format_erkennen(pfad.read_bytes(), daten)
    assert erkannt is not None, "Schreibweise nicht erkannt"
    daten[mb.FELD] = mb.STANDARD_BESITZER
    mb._schreibe_wie_vorgefunden(pfad, daten, erkannt)
    assert pfad.read_bytes() != original
    assert json.loads(pfad.read_bytes().decode("utf-8"))[mb.FELD] == mb.STANDARD_BESITZER

    # zurueck
    daten = json.loads(pfad.read_bytes().decode("utf-8"))
    erkannt = mb._format_erkennen(pfad.read_bytes(), daten)
    daten.pop(mb.FELD)
    mb._schreibe_wie_vorgefunden(pfad, daten, erkannt)

    assert pfad.read_bytes() == original, "nach hin und zurueck nicht byteidentisch"


def test_crlf_ueberlebt():
    """Die konkrete Falle: 182 Dateien im Bestand haben CRLF."""
    form = {"indent": 1, "ensure_ascii": False, "crlf": True, "schluss": "\n"}
    roh = mb._bauen(INHALT, form)
    assert b"\r\n" in roh
    assert mb._format_erkennen(roh, INHALT) == form


def test_escapte_umlaute_ueberleben():
    """Die zweite Falle: die Archiv-Reports stehen mit \\u00f6 statt oe."""
    form = {"indent": None, "ensure_ascii": True, "crlf": False, "schluss": ""}
    roh = mb._bauen(INHALT, form)
    assert b"\\u00f6" in roh and "ö".encode("utf-8") not in roh
    assert mb._format_erkennen(roh, INHALT) == form


def test_unbekannte_schreibweise_wird_gemeldet():
    """Lieber eine gemeldete Unsicherheit als eine stille Umformatierung."""
    # Handgeschriebene Einrueckung, die json.dumps nie erzeugt.
    roh = b'{\n      "id":   "abc"\n}'
    assert mb._format_erkennen(roh, {"id": "abc"}) is None


def test_migration_ist_wiederholbar(tmp_path, monkeypatch):
    """Zweiter Lauf darf nichts mehr finden."""
    ordner = tmp_path / "reports"
    ordner.mkdir()
    (ordner / "a.json").write_bytes(mb._bauen(INHALT, FORMEN[0]))

    erst = mb._durchlauf(ordner, mb.STANDARD_BESITZER, True, False)
    assert erst["geaendert"] == 1
    zweit = mb._durchlauf(ordner, mb.STANDARD_BESITZER, True, False)
    assert zweit["geaendert"] == 0 and zweit["schon_gut"] == 1


def test_echte_uid_ersetzt_den_platzhalter(tmp_path):
    ordner = tmp_path / "reports"
    ordner.mkdir()
    pfad = ordner / "a.json"
    pfad.write_bytes(mb._bauen(INHALT, FORMEN[0]))

    mb._durchlauf(ordner, mb.STANDARD_BESITZER, True, False)
    mb._durchlauf(ordner, "echte-uid-1234", True, False)
    assert json.loads(pfad.read_bytes().decode("utf-8"))[mb.FELD] == "echte-uid-1234"


def test_trockenlauf_schreibt_nicht(tmp_path):
    ordner = tmp_path / "reports"
    ordner.mkdir()
    pfad = ordner / "a.json"
    original = mb._bauen(INHALT, FORMEN[0])
    pfad.write_bytes(original)

    zahlen = mb._durchlauf(ordner, mb.STANDARD_BESITZER, False, False)
    assert zahlen["geaendert"] == 1
    assert pfad.read_bytes() == original, "der Trockenlauf hat geschrieben"
