"""Coach-Profil: Diagnosen und Uebungen ueber ALLE Sets eines DJs.

Das ist die Stufe, die aus Einzel-Reports einen echten Coach macht:
- Trends pro Skill (werde ich besser?)
- Muster, die ein einzelnes Set nicht zeigen kann ("zu frueh, wenn es
  schneller wird")
- Uebungen aus dem EIGENEN Material (konkrete Uebergaenge, anspringbar)

Ehrlichkeits-Regeln: Muster werden nur gemeldet, wenn genug Belege da
sind (Mindestanzahl), und Uebergaenge, die der DJ als "kein Uebergang"
markiert hat, fliessen nirgends ein.
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional

from app.jobs.job_manager import RESULTS_DIR
from app.jobs import feedback_store

# Mindest-Belege, bevor ein Muster behauptet wird.
MIN_PATTERN_SAMPLES = 4
SKILLS = ("timing", "beatmatching", "musicality", "flow", "overall")

TEXTS = {
    "de": {
        "p1_title": "Phrase-Timing leidet bei Wechseln in {worse} Tracks",
        "p1_evidence": ("Bei Uebergaengen in {worse} Tracks liegst du im Schnitt {w_val:.0f} Beats "
                        "neben der Phrase, in {better} nur {b_val:.0f} (gemessen an {n} Uebergaengen)."),
        "schneller": "schnellere", "langsamer": "langsamere",
        "p2_title": "Viele harmonisch riskante Key-Wechsel",
        "p2_evidence": ("{bad} von {n} Uebergaengen wechseln in eine nicht kompatible Tonart (Camelot). "
                        "Kompatible Wechsel klingen praktisch immer runder."),
        "p3_title": "Tempo-Drift in vielen Uebergaengen",
        "p3_evidence": ("{heavy} von {n} Uebergaengen haben mehr als 2 BPM Unterschied zwischen den Tracks "
                        "im Blend - das hoert man als Schieben oder Galoppieren."),
        "p4_title": "Energie bricht in Uebergaengen stark ein",
        "p4_evidence": ("In {deep} von {n} Uebergaengen faellt die Energie um 60% oder mehr - "
                        "der Dancefloor spuert das als Loch."),
        "tname": "Uebergang T{index}",
        "ex_title": "Mixe diesen Uebergang neu: {name}",
        "ex_desc": ("Aus '{file}' (Score {quality}). Hoere zuerst die Original-Stelle an, "
                    "dann mixe dieselben Tracks erneut. {target}."),
        "ex_target_phrase": "Ziel: unter 4 Beats Phrasen-Abweichung",
        "ex_target_score": "Ziel: Score ueber 75",
    },
    "en": {
        "p1_title": "Phrase timing suffers when switching to {worse} tracks",
        "p1_evidence": ("On transitions into {worse} tracks you average {w_val:.0f} beats off the phrase, "
                        "into {better} only {b_val:.0f} (measured on {n} transitions)."),
        "schneller": "faster", "langsamer": "slower",
        "p2_title": "Many harmonically risky key changes",
        "p2_evidence": ("{bad} of {n} transitions move to an incompatible key (Camelot). "
                        "Compatible moves almost always sound smoother."),
        "p3_title": "Tempo drift in many transitions",
        "p3_evidence": ("{heavy} of {n} transitions have more than 2 BPM difference between tracks "
                        "during the blend - audible as pushing or galloping."),
        "p4_title": "Energy collapses during transitions",
        "p4_evidence": ("In {deep} of {n} transitions the energy drops by 60% or more - "
                        "the dancefloor feels that as a hole."),
        "tname": "Transition T{index}",
        "ex_title": "Re-mix this transition: {name}",
        "ex_desc": ("From '{file}' (score {quality}). Listen to the original spot first, "
                    "then mix the same tracks again. {target}."),
        "ex_target_phrase": "Goal: under 4 beats phrase deviation",
        "ex_target_score": "Goal: score above 75",
    },
}


def _load_results() -> List[Dict]:
    results = []
    if not RESULTS_DIR.exists():
        return results
    for path in RESULTS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict) and data.get("setTransitions") is not None:
            results.append(data)
    results.sort(key=lambda r: r.get("createdAt") or "")
    return results


def _filtered_transitions(result: Dict) -> List[Dict]:
    """Uebergaenge OHNE die vom DJ als Fehlalarm markierten."""
    transitions = result.get("setTransitions") or []
    try:
        feedback = feedback_store.load_feedback(result.get("id") or "")
        verdicts = (feedback or {}).get("verdicts") or {}
    except Exception:
        verdicts = {}
    cleaned = []
    for t in transitions:
        v = verdicts.get(str(t.get("index")))
        if v and v.get("verdict") == "not_a_transition":
            continue
        cleaned.append(t)
    return cleaned


def _mean(values: List[float]) -> Optional[float]:
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 1) if values else None


def _camelot_compatible(a: Optional[str], b: Optional[str]) -> Optional[bool]:
    """Harmonisch vertraeglich nach Camelot-Rad (gleich, +-1, Moll/Dur-Wechsel)."""
    if not a or not b:
        return None
    try:
        na, la = int(a[:-1]), a[-1].upper()
        nb, lb = int(b[:-1]), b[-1].upper()
    except (ValueError, IndexError):
        return None
    if a.upper() == b.upper():
        return True
    if na == nb and la != lb:
        return True
    if la == lb and (abs(na - nb) == 1 or abs(na - nb) == 11):
        return True
    return False


def _skill_timeline(results: List[Dict]) -> List[Dict]:
    timeline = []
    for r in results:
        scores = r.get("scores") or {}
        timeline.append({
            "analysisId": r.get("id"),
            "fileName": r.get("fileName"),
            "createdAt": r.get("createdAt"),
            **{skill: scores.get(skill) for skill in SKILLS},
        })
    return timeline


def _trends(timeline: List[Dict]) -> Dict:
    """Letzte 3 Sets vs. die 3 davor - pro Skill. None, wenn zu wenig Daten."""
    trends = {}
    for skill in SKILLS:
        values = [t[skill] for t in timeline if t.get(skill) is not None]
        if len(values) < 4:
            trends[skill] = {"current": _mean(values[-3:]), "delta": None}
            continue
        recent = values[-3:]
        before = values[-6:-3] or values[:-3]
        trends[skill] = {
            "current": _mean(recent),
            "delta": round(_mean(recent) - _mean(before), 1),
        }
    return trends


def _patterns(all_transitions: List[Dict], lang: str = "de") -> List[Dict]:
    """Wiederkehrende, belegbare Muster ueber alle Sets."""
    T = TEXTS.get(lang, TEXTS["de"])
    patterns = []

    # 1) Phrase-Timing abhaengig von der Tempo-Richtung.
    up, down = [], []
    for t in all_transitions:
        beats = t.get("phrase_beats_off")
        b_in, b_out = t.get("bpm_after"), t.get("bpm_before")
        if beats is None or b_in is None or b_out is None:
            continue
        (up if b_in > b_out else down).append(abs(beats))
    if len(up) >= MIN_PATTERN_SAMPLES and len(down) >= MIN_PATTERN_SAMPLES:
        mu, md = _mean(up), _mean(down)
        if mu is not None and md is not None and abs(mu - md) >= 4:
            worse, better, w_val, b_val = (
                (T["schneller"], T["langsamer"], mu, md) if mu > md
                else (T["langsamer"], T["schneller"], md, mu)
            )
            patterns.append({
                "id": "phrase_tempo_direction",
                "title": T["p1_title"].format(worse=worse),
                "evidence": T["p1_evidence"].format(
                    worse=worse, better=better, w_val=w_val, b_val=b_val,
                    n=len(up) + len(down)),
            })

    # 2) Harmonik: Anteil unvertraeglicher Key-Wechsel.
    compat = [
        _camelot_compatible(t.get("camelot_before"), t.get("camelot_after"))
        for t in all_transitions
    ]
    compat = [c for c in compat if c is not None]
    if len(compat) >= MIN_PATTERN_SAMPLES:
        bad = compat.count(False)
        share = bad / len(compat)
        if share >= 0.3:
            patterns.append({
                "id": "harmonic_clashes",
                "title": T["p2_title"],
                "evidence": T["p2_evidence"].format(bad=bad, n=len(compat)),
            })

    # 3) Beatmatching: haeufige Tempo-Drifts.
    drifts = [t.get("bpm_drift") for t in all_transitions if t.get("bpm_drift") is not None]
    if len(drifts) >= MIN_PATTERN_SAMPLES:
        heavy = sum(1 for d in drifts if d > 2.0)
        if heavy / len(drifts) >= 0.3:
            patterns.append({
                "id": "tempo_drift",
                "title": T["p3_title"],
                "evidence": T["p3_evidence"].format(heavy=heavy, n=len(drifts)),
            })

    # 4) Energie: Uebergaenge reissen Loecher in den Flow.
    dips = [t.get("energy_dip_pct") for t in all_transitions if t.get("energy_dip_pct") is not None]
    if len(dips) >= MIN_PATTERN_SAMPLES:
        deep = sum(1 for d in dips if d >= 60)
        if deep / len(dips) >= 0.3:
            patterns.append({
                "id": "energy_holes",
                "title": T["p4_title"],
                "evidence": T["p4_evidence"].format(deep=deep, n=len(dips)),
            })

    return patterns


def _transition_name(t: Dict, lang: str = "de") -> str:
    if t.get("track_out") or t.get("track_in"):
        return f"{t.get('track_out') or '?'} → {t.get('track_in') or '?'}"
    return TEXTS.get(lang, TEXTS["de"])["tname"].format(index=t.get("index"))


def _highlights_and_exercises(results: List[Dict], lang: str = "de") -> Dict:
    T = TEXTS.get(lang, TEXTS["de"])
    scored = []
    for r in results:
        for t in _filtered_transitions(r):
            if t.get("quality_score") is None:
                continue
            scored.append({
                "analysisId": r.get("id"),
                "fileName": r.get("fileName"),
                "index": t.get("index"),
                "midSec": t.get("mid_sec"),
                "startSec": t.get("start_sec"),
                "name": _transition_name(t, lang),
                "quality": t.get("quality_score"),
                "phraseBeatsOff": t.get("phrase_beats_off"),
                "feedback": t.get("feedback"),
            })
    if not scored:
        return {"best": None, "worst": None, "exercises": []}

    best = max(scored, key=lambda s: s["quality"])
    worst_sorted = sorted(scored, key=lambda s: s["quality"])

    # Uebungen: die 3 schwaechsten Uebergaenge aus MOEGLICHST verschiedenen Sets.
    exercises = []
    used_sets = set()
    for s in worst_sorted:
        if s["analysisId"] in used_sets and len(worst_sorted) > 3:
            continue
        target = (
            T["ex_target_phrase"]
            if s.get("phraseBeatsOff") is not None and abs(s["phraseBeatsOff"]) >= 4
            else T["ex_target_score"]
        )
        exercises.append({
            "title": T["ex_title"].format(name=s["name"]),
            "description": T["ex_desc"].format(
                file=s["fileName"], quality=s["quality"], target=target),
            "analysisId": s["analysisId"],
            "midSec": s["midSec"],
            "startSec": s["startSec"],
        })
        used_sets.add(s["analysisId"])
        if len(exercises) == 3:
            break

    return {"best": best, "worst": worst_sorted[0], "exercises": exercises}


def build_profile(lang: str = "de") -> Dict:
    results = _load_results()
    timeline = _skill_timeline(results)
    all_transitions = [t for r in results for t in _filtered_transitions(r)]

    return {
        "setsAnalyzed": len(results),
        "transitionsMeasured": len(all_transitions),
        "timeline": timeline,
        "trends": _trends(timeline),
        "patterns": _patterns(all_transitions, lang),
        **_highlights_and_exercises(results, lang),
        "enoughData": len(results) >= 3,
    }
