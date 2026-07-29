"""Audio-Merkmale um jeden Transitions-Kandidaten herum zwischenspeichern.

Job B, Schritt 2 braucht viele Durchlaeufe ueber dieselben Stellen: eine
Erkennungsidee bauen, messen, verwerfen, naechste. Die Merkmale jedes Mal
neu aus dem Audio zu rechnen macht diesen Kreislauf unbrauchbar langsam.

Deshalb einmal extrahieren, dann nur noch aus dem Cache arbeiten.

Es wird bewusst NICHT das ganze Set analysiert, sondern nur ein Fenster um
jeden Kandidaten: gesucht wird der Blend-Onset VOR einem bereits bekannten
Punkt, alles andere ist Ballast. Bei 273 Kandidaten und 180 s Fenster sind
das ~14 h Audio statt ~25 h - und vor allem nur die Stellen, die zaehlen.

    python -m tools.blend_onset_cache                  # alles
    python -m tools.blend_onset_cache --limit 3        # Probelauf

Fenster: [mid - 150 s, mid + 30 s]. Die 150 s decken den Absolutfehler bis
ueber p95 ab (100 s) und lassen Luft fuer die Foote-Kernelbreite von
+-64 Beats (~30 s bei 128 BPM).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ENGINE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE_ROOT))

from tools.predictions_from_analyses import (  # noqa: E402
    ANALYSE_DIRS, GT_DIRS, MID_TOLERANZ_S, _sammle,
)

CACHE_DIR = ENGINE_ROOT / ".cache" / "blend_onset"

SR = 22050
HOP = 512
FENSTER_VOR = 150.0
FENSTER_NACH = 30.0
AUDIO_ENDUNGEN = (".wav", ".mp3", ".flac", ".m4a", ".aiff", ".aif")


def _finde_audio() -> dict[str, Path]:
    """analysisId -> Audiodatei des Sets."""
    out: dict[str, Path] = {}
    for d in ANALYSE_DIRS:
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if f.suffix.lower() in AUDIO_ENDUNGEN:
                out.setdefault(f.stem, f)
    return out


def _aufgaben() -> list[dict]:
    """Alle bewerteten Transitions, die Audio und passende Analyse haben."""
    analysen = _sammle(ANALYSE_DIRS)
    ground_truth = _sammle(GT_DIRS)
    audio = _finde_audio()

    aufgaben: list[dict] = []
    for aid, gt_datei in ground_truth.items():
        if aid not in analysen or aid not in audio:
            continue
        analyse = json.loads(analysen[aid].read_text(encoding="utf-8"))
        gt = json.loads(gt_datei.read_text(encoding="utf-8"))
        nach_index = {str(t.get("index")): t for t in (analyse.get("setTransitions") or [])}

        for idx, verdict in (gt.get("verdicts") or {}).items():
            t = nach_index.get(str(idx))
            if t is None or t.get("mid_sec") is None:
                continue
            if abs(float(t["mid_sec"]) - float(verdict.get("midSec", 0))) > MID_TOLERANZ_S:
                continue
            aufgaben.append({
                "aid": aid,
                "index": str(idx),
                "audio": audio[aid],
                "mid_sec": float(t["mid_sec"]),
                "start_sec_alt": float(t.get("start_sec") or 0.0),
                "verdict": verdict.get("verdict"),
                "corrected_sec": verdict.get("correctedSec"),
            })
    return aufgaben


def _extrahiere(aufgabe: dict) -> dict | None:
    """Merkmale fuer ein Fenster berechnen."""
    import librosa

    offset = max(0.0, aufgabe["mid_sec"] - FENSTER_VOR)
    dauer = (aufgabe["mid_sec"] - offset) + FENSTER_NACH

    wave, sr = librosa.load(str(aufgabe["audio"]), sr=SR, mono=True,
                            offset=offset, duration=dauer)
    if wave.size < sr * 20:
        return None

    chroma = librosa.feature.chroma_cqt(y=wave, sr=sr, hop_length=HOP)
    mfcc = librosa.feature.mfcc(y=wave, sr=sr, hop_length=HOP, n_mfcc=13)

    # Beats fuer die beat-synchrone Foote-Novelty. start_bpm bewusst offen
    # lassen - die Sets liegen zwischen 120 und 140 BPM.
    _, beat_frames = librosa.beat.beat_track(y=wave, sr=sr, hop_length=HOP,
                                             trim=False, units="frames")
    beats = librosa.frames_to_time(beat_frames, sr=sr, hop_length=HOP).tolist()

    # Zusatzmerkmale fuer den Blend-Onset. Alle auf demselben Raster wie
    # chroma/mfcc, damit sie sich frei kombinieren lassen.
    spek = np.abs(librosa.stft(wave, hop_length=HOP))
    freqs = librosa.fft_frequencies(sr=sr)
    bass = spek[freqs < 200].sum(axis=0)
    mitten = spek[(freqs >= 200) & (freqs < 2000)].sum(axis=0)
    hoehen = spek[freqs >= 2000].sum(axis=0)
    flachheit = librosa.feature.spectral_flatness(S=spek)[0]
    rms = librosa.feature.rms(S=spek)[0]

    # Chroma-Entropie: kommt eine zweite harmonische Schicht dazu, verteilt
    # sich die Energie auf mehr Tonklassen - die Verteilung wird flacher.
    c = chroma / (chroma.sum(axis=0, keepdims=True) + 1e-9)
    entropie = -(c * np.log(c + 1e-9)).sum(axis=0)

    return {
        "chroma": chroma.astype(np.float32),
        "mfcc": mfcc.astype(np.float32),
        "beats": np.asarray(beats, dtype=np.float32),
        "bass": bass.astype(np.float32),
        "mitten": mitten.astype(np.float32),
        "hoehen": hoehen.astype(np.float32),
        "flachheit": flachheit.astype(np.float32),
        "rms": rms.astype(np.float32),
        "entropie": entropie.astype(np.float32),
        # Alle Zeiten im Cache sind FENSTER-RELATIV. Wer absolute Zeiten
        # braucht, addiert offset. Einmal falsch gemacht kostet Stunden.
        "offset": np.float32(offset),
        "mid_rel": np.float32(aufgabe["mid_sec"] - offset),
        "sr": np.int32(sr),
        "hop": np.int32(HOP),
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out-dir", type=Path, default=CACHE_DIR)
    p.add_argument("--limit", type=int, help="nur die ersten N (Probelauf)")
    p.add_argument("--force", action="store_true", help="vorhandene neu rechnen")
    args = p.parse_args()

    aufgaben = _aufgaben()
    if args.limit:
        aufgaben = aufgaben[:args.limit]
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Kandidaten mit Audio und Analyse: {len(aufgaben)}")
    print(f"Cache: {args.out_dir}\n")

    fertig = uebersprungen = fehler = 0
    begonnen = time.time()
    verzeichnis: list[dict] = []

    for i, a in enumerate(aufgaben, 1):
        ziel = args.out_dir / f"{a['aid']}_{a['index']}.npz"
        eintrag = {k: (str(v) if isinstance(v, Path) else v)
                   for k, v in a.items() if k != "audio"}
        eintrag["datei"] = ziel.name

        if ziel.exists() and not args.force:
            uebersprungen += 1
            verzeichnis.append(eintrag)
            continue
        try:
            merkmale = _extrahiere(a)
            if merkmale is None:
                fehler += 1
                continue
            np.savez_compressed(ziel, **merkmale)
            fertig += 1
            verzeichnis.append(eintrag)
        except Exception as error:  # noqa: BLE001 - ein kaputtes Set darf den Lauf nicht toeten
            fehler += 1
            print(f"  FEHLER {a['aid']}_{a['index']}: {error}")

        if i % 10 == 0 or i == len(aufgaben):
            pro = (time.time() - begonnen) / max(1, fertig)
            rest = pro * (len(aufgaben) - i)
            print(f"[{i}/{len(aufgaben)}] neu={fertig} uebersprungen={uebersprungen} "
                  f"fehler={fehler}  noch ~{rest / 60:.0f} min")

    (args.out_dir / "verzeichnis.json").write_text(
        json.dumps(verzeichnis, indent=1), encoding="utf-8")
    print(f"\nfertig={fertig} uebersprungen={uebersprungen} fehler={fehler}")
    print(f"Verzeichnis: {args.out_dir / 'verzeichnis.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
