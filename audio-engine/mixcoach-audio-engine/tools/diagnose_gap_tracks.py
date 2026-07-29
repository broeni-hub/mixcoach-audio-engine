"""Gezielte Diagnose der 4 von Sebastian benannten Luecken-Tracks in
MixCoach2 (2026-07-17). Pro Track:

  1. Ist er ueberhaupt im Fingerprint-Index?
  2. Voller Set-Match: bestes Fenster/Score (Schwellen umgangen)
  3. SEGMENT-Match: nur innerhalb des von Sebastian korrigierten Segments
     gematcht - rankt der echte Track dort auf Platz 1? (Das entscheidet,
     ob ein Segment-basierter Zweitpass die Luecken sicher fuellen kann.)

Ground Truth (Sebastians Korrekturen + Tracklist):
  Segment 2:27-6:30    -> Julio Bashmore - Rhythm of Auld (Luecke 1)
  Segment 11:09-17:45  -> Frankey & Sandrino - Rana (Fenster brach bei 14:07 ab)
  Segment 28:30-33:55  -> Tom Trago - Brutal Romance (Luecke 3)
  Segment 37:46-43:06  -> Dalfie - R Rated (Luecke 4, Beinahe-Treffer 0.263)

Aufruf:
    python -m tools.diagnose_gap_tracks
"""

from __future__ import annotations

import sys

import numpy as np

ANALYSIS_ID = "d6dca722-2404-4641-9bc2-444a85f465c8"

# (Suchbegriffe fuer den Index, Segment-Start s, Segment-Ende s)
CASES = [
    (("bashmore", "auld"), 147.0, 390.0),
    (("frankey", "rana"), 669.0, 1065.0),
    (("trago", "brutal"), 1710.0, 2035.0),
    (("dalfie", "rated"), 2266.0, 2586.0),
]


def _find_fp(fingerprints, needles):
    for fp in fingerprints:
        hay = f"{fp.get('artist') or ''} {fp.get('title') or ''} {fp.get('path') or ''}".lower()
        if all(n in hay for n in needles):
            return fp
    return None


def main() -> int:
    import librosa

    from app.audio import library_match as lm
    from app.audio.track_change_classifier import compute_chroma_matrix
    from app.jobs.job_manager import RESULTS_DIR
    from app.library.manager import load_fingerprints

    fingerprints = load_fingerprints()
    audio_path = next(p for sfx in (".wav", ".mp3")
                      for p in [RESULTS_DIR / f"{ANALYSIS_ID}{sfx}"] if p.exists())
    wave, sr = librosa.load(str(audio_path), sr=22050, mono=True)
    chroma = compute_chroma_matrix(wave, sr)
    fps_rate = sr / (512 * lm.FP_DECIMATE)
    set_coarse = lm.decimate_chroma(chroma)

    original_min = lm.MIN_SCORE
    lm.MIN_SCORE = 0.05  # Diagnose: alles sichtbar machen
    try:
        for needles, seg_a, seg_b in CASES:
            print(f"\n=== {' '.join(needles)} | Segment {int(seg_a)//60}:{int(seg_a)%60:02d}-{int(seg_b)//60}:{int(seg_b)%60:02d} ===")
            fp = _find_fp(fingerprints, needles)
            if fp is None:
                print("  NICHT IM INDEX - Track wurde nie gefingerprintet!")
                continue
            print(f"  Im Index: {fp.get('artist')} - {fp.get('title')} (Dauer {fp.get('duration')}s)")

            # 2) Voller Set-Match
            hit = lm.match_track(set_coarse, np.asarray(fp["chroma"], dtype=np.float64), fps_rate)
            if hit is None:
                print("  Voll-Match: KEIN Fenster gefunden")
            else:
                s, e = int(hit["start"]), int(hit["end"])
                print(f"  Voll-Match: score={hit['score']:.3f} {s//60}:{s%60:02d}-{e//60}:{e%60:02d} stretch={hit['stretch']}")

            # 3) Segment-Match: Set auf das korrigierte Segment beschneiden,
            #    ALLE Pool-Tracks matchen, Rang des echten Tracks bestimmen.
            a_f, b_f = int(seg_a * fps_rate), int(seg_b * fps_rate)
            seg_coarse = set_coarse[:, a_f:b_f]
            prepared = lm._prepare_set(seg_coarse)
            pool = lm._prefilter_candidates(seg_coarse, fingerprints)
            scores = []
            for cand in pool:
                h = lm.match_track(seg_coarse, np.asarray(cand["chroma"], dtype=np.float64),
                                   fps_rate, prepared=prepared)
                if h is not None:
                    scores.append((h["score"], cand.get("path"), cand.get("artist"), cand.get("title")))
            scores.sort(key=lambda x: -x[0])
            true_path = fp.get("path")
            rank = next((i + 1 for i, (_, p, _, _) in enumerate(scores) if p == true_path), None)
            true_score = next((s for s, p, _, _ in scores if p == true_path), None)
            print(f"  Segment-Match: echter Track Rang {rank} von {len(scores)} "
                  f"(Score {true_score if true_score is None else round(true_score, 3)})")
            for s, _, art, tit in scores[:3]:
                print(f"    Top: {s:.3f} {art} - {tit}")
    finally:
        lm.MIN_SCORE = original_min
    return 0


if __name__ == "__main__":
    sys.exit(main())
