"""Demucs-Stem-Separation - Grundlage fuer Harmonic-Clash und Vocal-Overlap.

WICHTIG: nur fuer kurze Ausschnitte (Uebergangsfenster, typ. 20-35s) gedacht,
NIEMALS fuer ein komplettes Set. Demucs auf CPU braucht je nach Rechner ein
Vielfaches der Audiolaenge an Rechenzeit - ein 60-Minuten-Set komplett zu
trennen wuerde die Analyse um viele Minuten bis Stunden verlaengern. Der
Composite-Score trennt deshalb nur die ~20-35s um jeden erkannten Uebergang,
nicht das ganze Set.

Das Modell (htdemucs, 4 Stems: drums/bass/other/vocals) wird einmal pro
Prozess geladen und fuer alle Uebergaenge wiederverwendet. Der ALLERERSTE
Aufruf laedt zusaetzlich die Modell-Gewichte aus dem Internet (einmalig,
mehrere hundert MB) - das kann beim ersten analysierten Set spuerbar laenger
dauern.

Ehrlichkeit: schlaegt die Trennung fehl (kein Internet beim ersten Download,
zu wenig RAM, kaputtes Audio-Fenster), liefert separate_window() None statt
eines kaputten Ergebnisses - die aufrufenden Scoring-Module behandeln das wie
jede andere "nicht messbar"-Situation im Rest der Codebase.
"""

from __future__ import annotations

import threading
from typing import Dict, Optional

import numpy as np

_separator = None
_separator_lock = threading.Lock()

# Stems, die Demucs' htdemucs-Modell liefert.
STEM_NAMES = ("drums", "bass", "other", "vocals")


def _get_separator():
    global _separator
    if _separator is None:
        with _separator_lock:
            if _separator is None:
                from demucs.api import Separator
                _separator = Separator(model="htdemucs", progress=False)
    return _separator


def stems_samplerate() -> int:
    """Samplerate, in der separate_window() seine Stems zurueckgibt."""
    return _get_separator().samplerate


def separate_window(waveform: np.ndarray, sample_rate: int) -> Optional[Dict[str, np.ndarray]]:
    """Trennt einen mono Audio-Ausschnitt in drums/bass/other/vocals.

    Gibt jeden Stem als MONO np.ndarray (Kanal-Mittelwert) bei
    stems_samplerate() zurueck - oder None, wenn die Trennung fehlschlaegt.
    """
    if waveform is None or waveform.size < sample_rate:  # < 1s ergibt nichts Sinnvolles
        return None

    try:
        import torch

        separator = _get_separator()
        stereo = np.stack([waveform, waveform], axis=0).astype(np.float32)
        wav_tensor = torch.from_numpy(stereo)
        with torch.no_grad():
            _, stems = separator.separate_tensor(wav_tensor, sr=sample_rate)
        return {name: tensor.mean(dim=0).cpu().numpy() for name, tensor in stems.items()}
    except Exception:
        return None
