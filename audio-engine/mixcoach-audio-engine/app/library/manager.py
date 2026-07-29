"""Track-Library: rekordbox-Import + Fingerprint-Ablage.

Der DJ exportiert seine Sammlung in rekordbox als XML
(Datei -> Sammlung im xml-Format exportieren). Darin stehen die
Dateipfade aller Tracks. MixCoach liest die Audio-Dateien direkt von
der Platte und legt pro Track einen kompakten Fingerprint ab:

    <daten>/library/index.json     Metadaten aller Tracks
    <daten>/library/fp/<id>.npy    Chroma-Fingerprint (12 x N, float32)

Das Fingerprinting laeuft als Hintergrund-Thread (eine grosse Sammlung
dauert Minuten); der Fortschritt ist ueber get_status() abrufbar.
"""

from __future__ import annotations

import hashlib
import json
import threading
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

# EINEN Datenstamm mit dem Rest der App teilen (app.paths.DATA_ROOT:
# MIXCOACH_DATA_DIR falls gesetzt, sonst der Projektordner). Frueher
# hatte der Library-Manager eine EIGENE Pfad-Logik mit AppData-Fallback -
# ohne gesetzte Umgebungsvariable suchte die Library ihre Fingerprints
# damit an einem ANDEREN Ort als analysis_results/ground_truth lagen
# (stiller Divergenz-Fehler). app.paths importiert nur os/pathlib, also
# kein Import-Kreis durch die Pipeline (der urspruengliche Grund fuer die
# Sonderloesung war die Sorge vor genau so einem Kreis).
from app.paths import DATA_ROOT

LIBRARY_DIR = DATA_ROOT / "library"
FP_DIR = LIBRARY_DIR / "fp"
LM_DIR = LIBRARY_DIR / "lm"   # Landmark-Fingerprints (Shazam-Ergaenzung, siehe landmark_match.py)
INDEX_PATH = LIBRARY_DIR / "index.json"

_lock = threading.Lock()
_status = {
    "running": False,
    "total": 0,
    "done": 0,
    "failed": 0,
    "skipped": 0,
    "current": None,
    "last_error": None,
}

# Fingerprint-Cache pro Prozess (Index-Aenderung invalidiert).
_fp_cache: dict = {"stamp": None, "fingerprints": None}


def _track_id(path: str) -> str:
    return hashlib.md5(path.encode("utf-8", "replace")).hexdigest()[:16]


def _load_index() -> dict:
    if INDEX_PATH.exists():
        try:
            return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"tracks": {}}


def _save_index(index: dict) -> None:
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")


def parse_rekordbox_xml(data: bytes) -> list[dict]:
    """rekordbox-Sammlungs-XML -> Liste von Tracks mit lokalen Pfaden."""
    root = ET.fromstring(data)
    tracks = []
    for node in root.iter("TRACK"):
        location = node.get("Location")
        if not location:
            continue  # Playlist-Referenzen haben keine Location
        path = urllib.parse.unquote(location)
        for prefix in ("file://localhost/", "file://localhost", "file://"):
            if path.startswith(prefix):
                path = path[len(prefix):]
                break
        # Windows: "/C:/Users/..." -> "C:/Users/..."
        if len(path) > 2 and path[0] == "/" and path[2] == ":":
            path = path[1:]
        tracks.append({
            "title": node.get("Name") or Path(path).stem,
            "artist": node.get("Artist") or "",
            "bpm": float(node.get("AverageBpm") or 0) or None,
            "key": node.get("Tonality") or None,
            "duration": float(node.get("TotalTime") or 0) or None,
            "path": path,
        })
    return tracks


def _fingerprint_one(track: dict, index: dict) -> str:
    """Einen Track fingerprinten -> 'done' | 'skipped' | 'failed'."""
    import librosa

    from app.audio.library_match import decimate_chroma
    from app.audio.track_change_classifier import compute_chroma_matrix

    path = Path(track["path"])
    if not path.exists():
        return "failed"
    tid = _track_id(track["path"])
    mtime = path.stat().st_mtime_ns
    known = index["tracks"].get(tid)
    if known and known.get("mtime") == mtime and (FP_DIR / f"{tid}.npy").exists():
        return "skipped"

    waveform, sr = librosa.load(str(path), sr=22050, mono=True)
    if waveform.size < sr * 90:
        return "failed"  # unter 90s ist kein brauchbarer Club-Track
    chroma = compute_chroma_matrix(waveform, sr)
    coarse = decimate_chroma(chroma)
    FP_DIR.mkdir(parents=True, exist_ok=True)
    np.save(FP_DIR / f"{tid}.npy", coarse.astype(np.float32))

    index["tracks"][tid] = {
        "title": track["title"],
        "artist": track["artist"],
        "bpm": track.get("bpm"),
        "key": track.get("key"),
        "duration": round(waveform.size / sr, 1),
        "path": track["path"],
        "mtime": mtime,
    }
    return "done"


def _worker(tracks: list[dict]) -> None:
    index = _load_index()
    for track in tracks:
        with _lock:
            _status["current"] = f"{track['artist']} - {track['title']}".strip(" -")
        try:
            outcome = _fingerprint_one(track, index)
        except Exception as error:  # noqa: BLE001 - Fortschritt darf nicht sterben
            outcome = "failed"
            with _lock:
                _status["last_error"] = f"{track['title']}: {error}"
        with _lock:
            _status[{"done": "done", "skipped": "skipped", "failed": "failed"}[outcome]] += 1
        if outcome == "done":
            _save_index(index)  # nach jedem Track sichern (abbruchfest)
    _save_index(index)
    with _lock:
        _status["running"] = False
        _status["current"] = None
    _fp_cache["stamp"] = None  # Cache invalidieren


def start_import(tracks: list[dict]) -> bool:
    """Hintergrund-Fingerprinting starten. False, wenn schon eins laeuft."""
    with _lock:
        if _status["running"]:
            return False
        _status.update(running=True, total=len(tracks), done=0,
                       failed=0, skipped=0, current=None, last_error=None)
    threading.Thread(target=_worker, args=(tracks,), daemon=True).start()
    return True


def get_status() -> dict:
    with _lock:
        return dict(_status)


def list_tracks() -> list[dict]:
    index = _load_index()
    return [
        {"id": tid, **{k: v for k, v in meta.items() if k != "mtime"}}
        for tid, meta in sorted(index["tracks"].items(),
                                key=lambda kv: (kv[1].get("artist") or "", kv[1].get("title") or ""))
    ]


def build_landmark_index(tids: list[str] | None = None, track_cap_seconds: float = 360.0) -> dict:
    """Landmark-Fingerprints (app/audio/landmark_match) fuer die Library
    ablegen - KOMPLEMENTAER zum Chroma-Index, fuer harmonisch statische
    Tracks, die Chroma strukturell verfehlt (siehe landmark_match.py).

    Getrennt vom Chroma-Fingerprinting gehalten (eigenes LM_DIR, eigener
    Aufruf), weil der volle Lauf ueber >6000 Tracks mehrere Stunden dauert -
    das soll den schnellen Chroma-Reindex nicht blockieren und separat/ueber
    Nacht laufbar sein. tids=None -> alle Tracks im Index; sonst nur die
    genannten (z.B. Benchmark-Teilmenge). Ueberspringt bereits vorhandene."""
    import librosa

    from app.audio import landmark_match as lm

    index = _load_index()
    LM_DIR.mkdir(parents=True, exist_ok=True)
    todo = list(index["tracks"].items())
    if tids is not None:
        wanted = set(tids)
        todo = [(t, m) for t, m in todo if t in wanted]

    done = skipped = failed = 0
    for i, (tid, meta) in enumerate(todo, 1):
        out = LM_DIR / f"{tid}.npz"
        if out.exists():
            skipped += 1
            continue
        path = meta.get("path")
        if not path or not Path(path).exists():
            failed += 1
            continue
        try:
            wave, sr = librosa.load(path, sr=lm.SR, mono=True, duration=track_cap_seconds)
            fp = lm.fingerprint(wave, sr)
            np.savez_compressed(out, hashes=fp["hashes"], frames=fp["frames"])
            done += 1
        except Exception:
            failed += 1
        if i % 25 == 0 or i == len(todo):
            print(f"[landmark {i}/{len(todo)}] done={done} skipped={skipped} failed={failed}")
    return {"done": done, "skipped": skipped, "failed": failed, "total": len(todo)}


def load_landmark_fingerprints(tids: list[str] | None = None) -> dict[str, dict]:
    """tid -> {hashes, frames, path, title, artist, duration} fuer alle
    verfuegbaren Landmark-Fingerprints (die, deren .npz existiert)."""
    if not INDEX_PATH.exists() or not LM_DIR.exists():
        return {}
    index = _load_index()
    wanted = set(tids) if tids is not None else None
    out: dict[str, dict] = {}
    for tid, meta in index["tracks"].items():
        if wanted is not None and tid not in wanted:
            continue
        p = LM_DIR / f"{tid}.npz"
        if not p.exists():
            continue
        try:
            data = np.load(p)
        except Exception:
            continue
        out[tid] = {
            "hashes": data["hashes"], "frames": data["frames"],
            "path": meta.get("path"), "title": meta.get("title"),
            "artist": meta.get("artist"), "duration": meta.get("duration"),
        }
    return out


def load_fingerprints() -> list[dict]:
    """Alle Fingerprints fuer das Matching laden (mit Prozess-Cache)."""
    if not INDEX_PATH.exists():
        return []
    stamp = INDEX_PATH.stat().st_mtime_ns
    if _fp_cache["stamp"] == stamp and _fp_cache["fingerprints"] is not None:
        return _fp_cache["fingerprints"]
    index = _load_index()
    fingerprints = []
    for tid, meta in index["tracks"].items():
        fp_path = FP_DIR / f"{tid}.npy"
        if not fp_path.exists():
            continue
        try:
            chroma = np.load(fp_path)
        except Exception:
            continue
        fingerprints.append({
            "id": tid,
            "title": meta.get("title"),
            "artist": meta.get("artist"),
            "path": meta.get("path"),
            "duration": meta.get("duration"),
            "chroma": chroma,
        })
    _fp_cache["stamp"] = stamp
    _fp_cache["fingerprints"] = fingerprints
    return fingerprints
