"""Backfill: ersetzt in BESTEHENDEN Report-JSONs die volumeCurve (bisher
ein Duplikat der Energiekurve, siehe analysis_mapper 2026-07-17) durch die
echte K-gewichtete Lautheitskurve - berechnet aus dem gespeicherten Audio.

Nur Reports, deren Audio noch neben dem JSON liegt, werden angefasst;
alle anderen behalten ehrlich ihren alten Stand (Fallback-Verhalten des
Mappers). Idempotent: bereits befuellte Reports (Punkte mit "lufs"-Feld)
werden uebersprungen.

Aufruf:
    python -m tools.backfill_loudness_curves
"""

from __future__ import annotations

import json
import sys

from app.api.analysis_mapper import _map_loudness_curve
from app.audio.loudness import loudness_curve
from app.jobs.job_manager import RESULTS_DIR

AUDIO_SUFFIXES = (".wav", ".mp3", ".flac", ".m4a", ".aiff", ".aif")


def main() -> int:
    import librosa

    done = skipped = failed = 0
    for json_path in sorted(RESULTS_DIR.glob("*.json")):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict) or "volumeCurve" not in data:
            continue
        existing = data.get("volumeCurve") or []
        if existing and isinstance(existing[0], dict) and "lufs" in existing[0]:
            skipped += 1
            continue

        audio_path = next(
            (RESULTS_DIR / f"{json_path.stem}{sfx}" for sfx in AUDIO_SUFFIXES
             if (RESULTS_DIR / f"{json_path.stem}{sfx}").exists()),
            None,
        )
        if audio_path is None:
            print(f"[uebersprungen, kein Audio] {data.get('fileName')}")
            skipped += 1
            continue

        try:
            waveform, sr = librosa.load(str(audio_path), sr=22050, mono=True)
            times, values = loudness_curve(waveform, sr)
            mapped = _map_loudness_curve({"loudness_curve": [
                {"time": float(t), "lufs": float(v)} for t, v in zip(times, values)
            ]})
            if not mapped:
                raise ValueError("leere Lautheitskurve")
            data["volumeCurve"] = mapped
            json_path.write_text(json.dumps(data), encoding="utf-8")
            done += 1
            print(f"[ok] {data.get('fileName')} ({len(mapped)} Punkte)")
        except Exception as e:
            failed += 1
            print(f"[FEHLER] {data.get('fileName')}: {e}")

    print(f"\nFertig: {done} befuellt, {skipped} uebersprungen, {failed} fehlgeschlagen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
