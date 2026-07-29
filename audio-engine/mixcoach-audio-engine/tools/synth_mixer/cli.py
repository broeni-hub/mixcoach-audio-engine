"""Kommandozeilen-Interface fuer den Synthetik-Mix-Generator.

Aufruf:
    python -m tools.synth_mixer.cli generate ^
        --tracks-dir C:\\path\\to\\tracks --out-dir .\\datasets\\synthetic\\v1 ^
        --num-mixes 200 --tracks-per-mix 4-8 --seed 42 ^
        --genres house,electro ^
        --profile-distribution clean=0.5,off_phrase=0.1,off_beat=0.1,key_clash=0.1,abrupt=0.1,train_wreck=0.1
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .config import DEFAULT_PROFILE_DISTRIBUTION, SAMPLE_RATE
from .generator import ChainBuildError, generate_one_mix, scan_track_pool


def _parse_range(value: str) -> tuple[int, int]:
    if "-" in value:
        lo, hi = value.split("-", 1)
        return int(lo), int(hi)
    n = int(value)
    return n, n


def _parse_distribution(value: str) -> dict[str, float]:
    dist = {}
    for part in value.split(","):
        name, weight = part.split("=")
        dist[name.strip()] = float(weight)
    return dist


def _write_wav(path: Path, waveform, sample_rate: int) -> None:
    import soundfile as sf
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), waveform, sample_rate, format="WAV")


def cmd_generate(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir)
    mixes_dir = out_dir / "mixes"
    labels_dir = out_dir / "labels"
    mixes_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    if args.audio_format == "mp3":
        print("HINWEIS: mp3-Export ist noch nicht verdrahtet (kein Encoder "
              "eingebunden) - falle auf wav zurueck. WAV-Dateien werden bei "
              "diesen Laengen/Mengen recht gross; bei Platzknappheit vorerst "
              "manuell nachkomprimieren.")
    audio_format = "wav"

    tracks_per_mix = _parse_range(args.tracks_per_mix)
    profile_distribution = _parse_distribution(args.profile_distribution) \
        if args.profile_distribution else dict(DEFAULT_PROFILE_DISTRIBUTION)
    genres = tuple(g.strip() for g in args.genres.split(",") if g.strip()) if args.genres else ()

    pool = scan_track_pool(Path(args.tracks_dir), genres)
    print(f"{len(pool)} Tracks im Pool (Ordner: {args.tracks_dir}, Genre-Filter: {genres or 'keiner'}).")
    if len(pool) < tracks_per_mix[1]:
        print(f"FEHLER: Pool zu klein fuer bis zu {tracks_per_mix[1]} Tracks pro Mix.")
        return 1

    manifest = {
        "generator_version": __version__,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "tracks_dir": str(args.tracks_dir),
        "out_dir": str(out_dir),
        "num_mixes": args.num_mixes,
        "tracks_per_mix": list(tracks_per_mix),
        "seed": args.seed,
        "genres": list(genres),
        "profile_distribution": profile_distribution,
        "sample_rate": SAMPLE_RATE,
        "audio_format": audio_format,
        "pool_size": len(pool),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")

    rng = random.Random(args.seed)
    analysis_cache: dict = {}
    ok, skipped, failed = 0, 0, 0

    for i in range(1, args.num_mixes + 1):
        mix_id = f"synth_{i:06d}"
        label_path = labels_dir / f"{mix_id}.json"
        mix_path = mixes_dir / f"{mix_id}.wav"

        if label_path.exists() and mix_path.exists():
            skipped += 1
            continue

        n_tracks = rng.randint(*tracks_per_mix)
        t0 = time.time()
        try:
            waveform, label = generate_one_mix(
                pool, n_tracks, profile_distribution, rng, mix_id, analysis_cache,
            )
        except ChainBuildError as e:
            print(f"[{i}/{args.num_mixes}] {mix_id}: UEBERSPRUNGEN ({e})")
            failed += 1
            continue
        except Exception as e:
            print(f"[{i}/{args.num_mixes}] {mix_id}: FEHLER ({e})")
            failed += 1
            continue

        _write_wav(mix_path, waveform, SAMPLE_RATE)
        label_path.write_text(label.model_dump_json(indent=1), encoding="utf-8")
        ok += 1
        print(f"[{i}/{args.num_mixes}] {mix_id}: {len(label.tracks)} Tracks, "
              f"{len(label.transitions)} Uebergaenge, {label.duration_seconds:.0f}s "
              f"({time.time() - t0:.0f}s)")

    print(f"\nFertig. {ok} neu erzeugt, {skipped} uebersprungen (schon vorhanden), {failed} fehlgeschlagen.")
    print(f"Ausgabe: {mixes_dir} / {labels_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m tools.synth_mixer.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Synthetische Trainings-Mixes generieren.")
    gen.add_argument("--tracks-dir", required=True, type=Path)
    gen.add_argument("--out-dir", required=True, type=Path)
    gen.add_argument("--num-mixes", type=int, default=200)
    gen.add_argument("--tracks-per-mix", default="4-8")
    gen.add_argument("--seed", type=int, default=42)
    gen.add_argument("--genres", default="")
    gen.add_argument("--profile-distribution", default="")
    gen.add_argument("--audio-format", choices=("wav", "mp3"), default="wav")
    gen.set_defaults(func=cmd_generate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
