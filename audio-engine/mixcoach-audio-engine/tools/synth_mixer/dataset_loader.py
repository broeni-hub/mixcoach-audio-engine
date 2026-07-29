"""Lese-Utility fuer generierte Mix/Label-Paare - der vorgesehene
Anbindungspunkt fuer eine kuenftige Eval-Pipeline (mixcoach_eval_pipeline.py
existiert im Projekt noch nicht, siehe README.md in diesem Ordner).

Absichtlich schreibgeschuetzt/minimal: iteriert nur ueber vorhandene
Mix/Label-Paare, validiert das Label-Schema per pydantic, laedt Audio erst
bei Bedarf (nicht alles auf einmal in den RAM).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

import numpy as np

from .schema import MixLabel


@dataclass
class DatasetEntry:
    mix_id: str
    label: MixLabel
    audio_path: Path

    def load_audio(self) -> tuple[np.ndarray, int]:
        import soundfile as sf
        waveform, sr = sf.read(str(self.audio_path), dtype="float32", always_2d=False)
        return waveform, sr


class SyntheticDataset:
    """Iteriert ueber alle Mix/Label-Paare in einem generierten Datensatz-
    Ordner (Struktur wie von cli.py erzeugt: <out_dir>/mixes, <out_dir>/labels)."""

    def __init__(self, out_dir: Path):
        self.out_dir = Path(out_dir)
        self.mixes_dir = self.out_dir / "mixes"
        self.labels_dir = self.out_dir / "labels"
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> Optional[dict]:
        import json
        manifest_path = self.out_dir / "manifest.json"
        if not manifest_path.exists():
            return None
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def __iter__(self) -> Iterator[DatasetEntry]:
        if not self.labels_dir.exists():
            return
        for label_path in sorted(self.labels_dir.glob("*.json")):
            mix_id = label_path.stem
            audio_path = self.mixes_dir / f"{mix_id}.wav"
            if not audio_path.exists():
                continue
            label = MixLabel.model_validate_json(label_path.read_text(encoding="utf-8"))
            yield DatasetEntry(mix_id=mix_id, label=label, audio_path=audio_path)

    def __len__(self) -> int:
        if not self.labels_dir.exists():
            return 0
        return sum(1 for _ in self.labels_dir.glob("*.json"))
