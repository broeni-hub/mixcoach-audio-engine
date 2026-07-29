"""Tests fuer das Beat-Alignment im Uebergangsfenster (Composite-Score, Dim. 4)."""

from app.audio.scoring.beat_alignment import annotate_beat_alignment


def test_regular_beats_score_high():
    beats = [i * 0.5 for i in range(200)]  # 120 BPM, perfekt regelmaessig
    transitions = [{"start_sec": 40.0, "end_sec": 60.0}]

    annotate_beat_alignment(transitions, beats)

    assert transitions[0]["beat_alignment_score"] >= 95
    assert transitions[0]["scores"]["beat_alignment"] == transitions[0]["beat_alignment_score"]


def test_jittery_beats_score_low():
    # Zwei leicht phasenversetzte Pulse abwechselnd - simuliert schlechtes Beatmatching.
    beats = []
    t = 40.0
    while t < 60.0:
        beats.append(t)
        t += 0.35
        beats.append(t)
        t += 0.65

    transitions = [{"start_sec": 40.0, "end_sec": 60.0}]
    annotate_beat_alignment(transitions, beats)

    assert transitions[0]["beat_alignment_score"] is not None
    assert transitions[0]["beat_alignment_score"] < 50


def test_too_few_beats_returns_none():
    beats = [40.0, 41.0]
    transitions = [{"start_sec": 40.0, "end_sec": 60.0}]

    annotate_beat_alignment(transitions, beats)

    assert transitions[0]["beat_alignment_score"] is None


def test_missing_window_returns_none():
    transitions = [{"start_sec": None, "end_sec": None}]
    annotate_beat_alignment(transitions, [1.0, 2.0])

    assert transitions[0]["beat_alignment_score"] is None
