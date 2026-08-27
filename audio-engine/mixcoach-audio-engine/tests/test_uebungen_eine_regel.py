"""Die Auswahl- und Reihenfolge-Regel steht an genau einer Stelle.

Uebungen entstehen an zwei Orten: app/coach/uebungen.py je Report und
app/coach/profile.py ueber alle Sets, mit eigenem DE/EN-Text. Die TEXTE
duerfen verschieden sein. Die REGEL - welche Groesse zaehlt, ab wann, mit
welchem Ziel, in welcher Reihenfolge - darf es nicht.

Am 20.08.2026 stand sie zweimal da, und die zweite belegte Groesse waere
fast nur im Report gelandet und im Coach-Panel - dem, was der Nutzer sieht -
unsichtbar geblieben. Diese Tests halten fest, dass beide Seiten dieselbe
Regel benutzen und nicht nur zufaellig dasselbe tun.
"""

import pytest

from app.coach import profile
from app.coach.uebungen import (GROESSEN, SCHWELLE_BEAT_JITTER_MS,
                                SCHWELLE_PEGELSPRUNG_DB, ZIEL_BEAT_JITTER_MS,
                                ZIEL_PEGELSPRUNG_DB, sortieren,
                                ueber_der_schwelle, ueberschreitung)


def test_die_groessen_tabelle_kennt_beide_belegten_dimensionen():
    assert set(GROESSEN) == {"loudness_jump_db", "beat_jitter_ms"}
    for name, regel in GROESSEN.items():
        assert regel["schwelle"] > 0, name
        assert regel["ziel"] > 0, name
        assert regel["ziel"] < regel["schwelle"], f"{name}: Ziel ueber der Schwelle"


def test_die_schwellen_stimmen_mit_den_konstanten_ueberein():
    """Eine Tabelle, die von den Konstanten abweicht, waere die dritte Stelle."""
    assert GROESSEN["loudness_jump_db"]["schwelle"] == SCHWELLE_PEGELSPRUNG_DB
    assert GROESSEN["loudness_jump_db"]["ziel"] == ZIEL_PEGELSPRUNG_DB
    assert GROESSEN["beat_jitter_ms"]["schwelle"] == SCHWELLE_BEAT_JITTER_MS
    assert GROESSEN["beat_jitter_ms"]["ziel"] == ZIEL_BEAT_JITTER_MS


def test_der_pegelsprung_zaehlt_in_beide_richtungen():
    """Zu leise ist genauso unsauber wie zu laut - der Jitter dagegen ist
    eine Streuung und hat keine Richtung."""
    assert ueber_der_schwelle({"loudness_jump_db": -9.0}, "loudness_jump_db")
    assert ueber_der_schwelle({"loudness_jump_db": 9.0}, "loudness_jump_db")
    assert GROESSEN["beat_jitter_ms"]["betrag"] is False


def test_ueberschreitung_vergleicht_ueber_einheiten_hinweg():
    """9 dB sind das 3-fache ihrer Schwelle, 16 ms nur das 1,07-fache -
    nach nackter Zahl sortiert stuende 16 vor 9."""
    assert ueberschreitung("loudness_jump_db", 9.0) > ueberschreitung("beat_jitter_ms", 16.0)


def test_vielfalt_zuerst_nur_wo_abgeschnitten_wird():
    eintraege = [("loudness_jump_db", 9.0), ("loudness_jump_db", 6.0),
                 ("beat_jitter_ms", 26.0)]
    metrik, wert = (lambda e: e[0]), (lambda e: e[1])

    # Der Report zeigt alles: schlimmste zuerst.
    ohne = sortieren(eintraege, metrik, wert)
    assert [e[0] for e in ohne] == ["loudness_jump_db", "loudness_jump_db",
                                    "beat_jitter_ms"]

    # Das Profil schneidet nach drei ab: je Groesse eine zuerst.
    mit = sortieren(eintraege, metrik, wert, vielfalt_zuerst=True)
    assert [e[0] for e in mit] == ["loudness_jump_db", "beat_jitter_ms",
                                   "loudness_jump_db"]


def test_beide_seiten_reihen_dieselben_kandidaten_gleich(monkeypatch):
    """Der Kern: was das Profil auswaehlt, muss der gemeinsamen Regel folgen -
    nicht einer eigenen, die zufaellig dasselbe tut."""
    monkeypatch.setattr(profile, "_filtered_transitions",
                        lambda r: r.get("setTransitions") or [])

    report = {
        "id": "MixCoach9.WAV", "fileName": "MixCoach9.WAV",
        "createdAt": "2026-07-20T10:00:00Z", "scoringVersion": 3,
        "setTransitions": [
            {"index": 1, "mid_sec": 100.0, "loudness_jump_db": 9.0},   # 3,00-fach
            {"index": 2, "mid_sec": 200.0, "beat_jitter_ms": 26.0},    # 1,73-fach
            {"index": 3, "mid_sec": 300.0, "loudness_jump_db": 6.0},   # 2,00-fach
        ],
    }
    ergebnis = profile._highlights_and_exercises([report])
    reihenfolge = [u["metric"] for u in ergebnis["exercises"]]

    # Erwartet nach vielfalt_zuerst: 9 dB, dann die einzige Jitter-Stelle,
    # dann 6 dB. Nach nacktem Betrag waere 26 vor 9 gekommen.
    assert reihenfolge == ["loudness_jump_db", "beat_jitter_ms",
                           "loudness_jump_db"]
    assert [u["value"] for u in ergebnis["exercises"]] == [9.0, 26.0, 6.0]


def test_unter_der_schwelle_kommt_nichts(monkeypatch):
    monkeypatch.setattr(profile, "_filtered_transitions",
                        lambda r: r.get("setTransitions") or [])
    report = {
        "id": "MixCoach9.WAV", "fileName": "MixCoach9.WAV",
        "createdAt": "2026-07-20T10:00:00Z", "scoringVersion": 3,
        "setTransitions": [
            {"index": 1, "mid_sec": 100.0,
             "loudness_jump_db": SCHWELLE_PEGELSPRUNG_DB - 0.01,
             "beat_jitter_ms": SCHWELLE_BEAT_JITTER_MS - 0.01},
        ],
    }
    assert profile._highlights_and_exercises([report])["exercises"] == []
