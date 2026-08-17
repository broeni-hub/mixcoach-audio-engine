from app.experimental.analyzer import analyze_basic
from app.experimental.beatgrid import detect_beats
from app.audio.energy import calculate_energy_curve
from app.experimental.key_detector import detect_key
from app.experimental.models import TrackAnalysis
from app.experimental.phrasing import detect_phrases
from app.experimental.structure import detect_structure
from app.experimental.transitions import detect_energy_transitions
from app.experimental.vocals import detect_vocals


def analyze_audio(audio) -> TrackAnalysis:
    basic = analyze_basic(audio)
    beats = detect_beats(audio)
    phrases = detect_phrases(beats)
    key = detect_key(audio)
    transitions = detect_energy_transitions(audio)
    energy = calculate_energy_curve(audio)
    vocals = detect_vocals(audio)

    structure = detect_structure(
        duration=audio.duration_seconds,
        tempo=beats["tempo"],
        energy=energy,
    )

    result = {
        "filename": audio.filename,
        "duration": audio.duration_seconds,
        "sample_rate": audio.sample_rate,
        "basic": basic,
        "tempo": beats["tempo"],
        "key": key,
        "beat_count": len(beats["beats"]),
        "first_beats": beats["beats"][:20],
        "phrases": phrases,
        "transitions": transitions,
        "energy": energy,
        "structure": structure,
        "raw": {
            "beats": beats["beats"],
            "vocals": vocals,
        },
    }

    return TrackAnalysis(**result)