"""Parameter-Ranges und Presets fuer den Synthetik-Mix-Generator.

Alle Zahlen hier sind bewusst zentral gesammelt, damit Presets/Tuning nicht
quer durch generator.py/transitions.py verstreut sind.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SAMPLE_RATE = 22050  # gleiche Rate wie der Rest der Pipeline (app/audio/*,
# app/calibration/build_features.py) - vermeidet ein zusaetzliches Resample
# beim Einspeisen ins Training/die Eval-Pipeline. Abweichung vom 44100er
# Beispiel im Anfrage-Schema ist bewusst; wird im Manifest/Label ehrlich
# als "sample_rate" gemeldet, nicht hart auf 44100 behauptet.

BEATS_PER_BAR = 4
BAR_PHRASE_LENGTHS = (8, 16, 32)  # Bars pro Phrase, fuer das Phrasen-Raster

OVERLAP_BEATS_CHOICES = (4, 8, 16, 32, 64)
# "clean" soll nach einem echten, gemuetlichen Blend klingen - 4/8 Beats
# (~2-4s bei 120-140 BPM) fuehlen sich eher wie ein Cut an, nicht wie ein
# Uebergang. Kurze Overlaps bleiben den anderen Profilen vorbehalten
# (off_phrase/off_beat/abrupt/train_wreck duerfen/sollen kurz&hart sein).
CLEAN_OVERLAP_BEATS_CHOICES = (16, 32, 64)
CROSSFADE_CURVES = ("linear", "equal_power", "exponential", "s_curve")

MIN_BPM = 70.0
MAX_BPM = 180.0
# Schutz gegen kaputte/near-leere Dateien, die librosa zwar irgendwie laedt
# (kein Exception), aber mit einem winzigen Waveform - das fuehrt spaeter
# bei Time-Stretch/Beat-Erkennung zu "cannot reshape array of size 0 into
# shape (0)"-Fehlern (2 von 175 Mixes im ersten Grosslauf, 2026-07-13).
MIN_TRACK_DURATION_SECONDS = 20.0
MAX_BPM_STRETCH_FRACTION = 0.08  # Trackpaar verwerfen, wenn Time-Stretch groesser waere

BASS_HZ = 120.0  # Trennfrequenz fuer den simulierten Bass-Swap (EQ-Blend)

# Track-Auswahl: wie viele Tracks bilden EINEN Mix.
TRACKS_PER_MIX_MIN = 4
TRACKS_PER_MIX_MAX = 8

# Wieviel vom Ende/Anfang eines Tracks als Ueberblend-Material genutzt wird -
# grosszuegig, damit genug "solo"-Kontext vor/nach jedem Uebergang bleibt
# (der bestehende ML-Klassifikator verwirft Kandidaten < 90s nach Set-Start
# bzw. < 60s vor Set-Ende immer als "edge" - siehe app/audio/ml_classifier.py).
SEGMENT_SECONDS = 130.0

QUALITY_PROFILES = (
    "clean", "off_phrase", "off_beat", "key_clash", "abrupt", "train_wreck",
)

DEFAULT_PROFILE_DISTRIBUTION = {
    "clean": 0.5,
    "off_phrase": 0.1,
    "off_beat": 0.1,
    "key_clash": 0.1,
    "abrupt": 0.1,
    "train_wreck": 0.1,
}

# Reichweiten je Profil - siehe transitions.py fuer die deterministische
# expected_quality_label-Zuordnung (dort dokumentiert, nicht hier, damit
# Logik und Tabelle nicht auseinanderlaufen).
OFF_PHRASE_BEATS_RANGE = (1, 12)
OFF_BEAT_MS_RANGE = (50, 300)
ABRUPT_OVERLAP_BEATS = (1, 2)
KEY_CLASH_MIN_CAMELOT_DISTANCE = 3  # ">2 Camelot-Schritte" lt. Vorgabe
CLEAN_MAX_CAMELOT_DISTANCE = 1  # "passende Keys (+-1 auf dem Camelot-Wheel)" lt. Vorgabe

# Deckelt die zusaetzliche Mikro-Zeitstreckung, die den ueber den Overlap
# gemessenen Beat-Drift ausgleicht (siehe estimate_phase_offset_samples /
# render_transition). Gemessen wurde bis zu ~160ms Drift auf einem 16-Beat-
# Overlap (2026-07-14) - das waere hier z.B. bei 126 BPM/7.6s Overlap knapp
# 2% der Overlap-Laenge. Grosszuegig gedeckelt, damit eine verrauschte
# Messung (Fehlkorrelation) nicht in eine hoerbare Tonhoehen-/Tempo-
# Verzerrung des Overlaps selbst umschlaegt.
MAX_DRIFT_CORRECTION_FRACTION = 0.06

# Stil-Cluster fuer die Trackpaarung: Ordnername (direktes Elternverzeichnis
# der Audiodatei) -> "duerfen in einem Mix nacheinander vorkommen". Der
# bisherige --genres-Filter ("house,electro") ist zu grob - Minimal Techno,
# Afro House und Electro Pop landeten im selben Pool und wurden nur nach
# BPM/Tonart gepaart, nicht nach Stil (Sebastians Feedback: "stilistisch
# kaum zueinander passend", 2026-07-14). ENTWURF nach Tempo/Vibe-Logik -
# bei Bedarf anpassen, ist nur eine Datenstruktur, kein Code.
# Ordner, die in KEINEM Cluster auftauchen (z.B. Restebox-Ordner), matchen
# nur sich selbst - kein Absturz, nur keine Cross-Kombination.
STYLE_CLUSTERS: tuple[tuple[str, ...], ...] = (
    ("Deep House", "Melodic House", "Smooth House", "Detroit House", "Afro House", "Groove"),
    ("Funky House", "Tech House", "Bass House", "Pop House", "Upbeat", "Breaking Beats"),
    ("Experimental House", "Minimal", "Techno"),
    ("Electro Pop", "Soft Electro", "Electronica", "LoFi"),
    ("Bass Music", "Breaks", "UK Garage", "2 Step"),
)


@dataclass
class GeneratorConfig:
    tracks_dir: str
    out_dir: str
    num_mixes: int = 200
    tracks_per_mix: tuple[int, int] = (TRACKS_PER_MIX_MIN, TRACKS_PER_MIX_MAX)
    seed: int = 42
    profile_distribution: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_PROFILE_DISTRIBUTION))
    genres: tuple[str, ...] = ()  # Ordner-Substring-Filter, leer = alle
    audio_format: str = "wav"  # "wav" oder "mp3" (320kbps)
