"""Feedback-getriebenes Nachmatchen eines bereits analysierten Sets.

Vision-Datenschleife: die Korrekturen des DJs im Report ("startet
woanders" / "hier fehlte einer") liefern exakte Track-Grenzen. Zwischen
zwei Grenzen laeuft genau ein Track - dieses praezise Segment gewinnt der
echte Track auch dort, wo der automatische Voll-/Zweitpass an unsauberen
Grenzen scheiterte (gemessen 2026-07-17: Bashmore verfehlte die
automatische Luecke komplett, kam aber ueber sein korrigiertes Segment).

Bewusst KEIN Teil der Live-Analyse (setzt DJ-Feedback voraus) - wird per
Endpoint on-demand ausgeloest.
"""

from __future__ import annotations

from typing import Dict, List

from app.audio.library_match import (
    rematch_from_boundaries,
    transitions_from_matches,
)


def _boundaries_from_feedback(feedback: Dict) -> List[float]:
    """Korrigierte + nachgemeldete Uebergangszeiten (Sekunden), OHNE die als
    Fehlalarm ("not_a_transition") markierten."""
    bounds: List[float] = []
    for entry in (feedback.get("verdicts") or {}).values():
        verdict = entry.get("verdict")
        if verdict == "timing_off" and entry.get("correctedSec") is not None:
            bounds.append(float(entry["correctedSec"]))
        elif verdict == "correct" and entry.get("midSec") is not None:
            bounds.append(float(entry["midSec"]))
    bounds.extend(float(s) for s in (feedback.get("missed") or []))
    return sorted(bounds)


def _track_label(artist, title) -> str | None:
    return " - ".join(x for x in (artist, title) if x) or None


def apply_rematch(result: Dict, feedback: Dict, waveform, sample_rate: int) -> Dict:
    """Nachmatchen und das Report-Dict AKTUALISIEREN (in place + Rueckgabe).

    Vereinigt neue Segment-Treffer mit den bestehenden library.matches
    (neuer Treffer gewinnt bei Track-Kollision) und benennt die
    setTransitions neu (track_out/track_in/detection). Aendert die
    Uebergangs-ERKENNUNG nicht - nur die Track-Zuordnung, die der DJ
    ohnehin gerade korrigiert.
    """
    from app.audio.track_change_classifier import compute_chroma_matrix
    from app.library.manager import load_fingerprints

    boundaries = _boundaries_from_feedback(feedback)
    if len(boundaries) < 1:
        result["rematch"] = {"applied": False, "reason": "keine korrigierten Grenzen"}
        return result

    fingerprints = load_fingerprints()
    if not fingerprints:
        result["rematch"] = {"applied": False, "reason": "kein Fingerprint-Index"}
        return result

    chroma = compute_chroma_matrix(waveform, sample_rate)
    new_hits = rematch_from_boundaries(chroma, boundaries, fingerprints, sample_rate)

    # Identitaet ueber artist+title (nicht path): die gespeicherten
    # library.matches enthalten KEIN path-Feld (der Mapper legt nur
    # title/artist/start/end/score ab) - ein path-basierter Schluessel
    # liesse alte und neue Treffer desselben Tracks als Duplikate
    # nebeneinander stehen (real beobachtet 2026-07-17: Alma Negra, Rana
    # u.a. doppelt).
    def _key(m: Dict) -> str:
        return f"{(m.get('artist') or '').strip().lower()}|{(m.get('title') or '').strip().lower()}"

    by_id: Dict[str, Dict] = {}
    for m in (result.get("library") or {}).get("matches") or []:
        by_id[_key(m)] = dict(m)
    existing_count = len(by_id)

    for h in new_hits:
        k = _key(h)
        prev = by_id.get(k)
        # Neuer (praeziser Grenzen-)Treffer gewinnt nur, wenn er staerker
        # ist - sonst bleibt der bestehende (schuetzt gegen einen
        # schwaecheren Grenzen-Treffer, der einen guten Voll-Match ueberschreibt).
        if prev is None or h["score"] >= prev.get("score", 0):
            by_id[k] = {
                "title": h.get("title"), "artist": h.get("artist"),
                "path": h.get("path"),
                "start": h["start"], "end": h["end"], "score": h["score"],
            }

    matches = sorted(by_id.values(), key=lambda m: m["start"])
    result.setdefault("library", {})["matches"] = matches
    added = len(by_id) - existing_count

    # setTransitions neu benennen (gleiche 60s-Fenster-Logik wie die Pipeline).
    fp_transitions = transitions_from_matches(matches)
    for t in result.get("setTransitions") or []:
        mid = t.get("mid_sec")
        if mid is None:
            continue
        for ft in fp_transitions:
            if abs(mid - ft["mid"]) <= 60.0:
                t["track_out"] = _track_label(ft.get("from_artist"), ft.get("from_title"))
                t["track_in"] = _track_label(ft.get("to_artist"), ft.get("to_title"))
                t["detection"] = "fingerprint"
                break

    result["rematch"] = {
        "applied": True,
        "segments": len(boundaries) + 1,
        "matchesBefore": existing_count,
        "matchesAfter": len(matches),
        "added": added,
    }
    return result
