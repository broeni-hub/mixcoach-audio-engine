def weighted_overall_score(
    tempo_score: float,
    harmonic_score: int,
    phrase_score: int,
    energy_score: int,
    transition_timing_score: int,
):

    weights = {
        "tempo": 0.30,
        "harmonic": 0.25,
        "phrase": 0.18,
        "energy": 0.12,
        "transition_timing": 0.15,
    }

    overall = round(
    tempo_score * weights["tempo"]
    + harmonic_score * weights["harmonic"]
    + phrase_score * weights["phrase"]
    + energy_score * weights["energy"]
    + transition_timing_score * weights["transition_timing"],
    2,
)

    breakdown = {
        "tempo": {
            "score": round(tempo_score, 2),
            "weight": weights["tempo"],
            "impact": "high",
        },
        "harmonic": {
            "score": harmonic_score,
            "weight": weights["harmonic"],
            "impact": "high",
        },
        "phrase": {
            "score": phrase_score,
            "weight": weights["phrase"],
            "impact": "medium",
        },
        "energy": {
            "score": energy_score,
            "weight": weights["energy"],
            "impact": "low",
        },
        "transition_timing": {
            "score": transition_timing_score,
            "weight": weights["transition_timing"],
            "impact": "medium",
},
    }

    return overall, breakdown