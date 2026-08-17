def generate_recommendations(
    tempo_score: float,
    harmonic_score: int,
    phrase_score: int,
    energy_score: int,
):
    recommendations = []

    if tempo_score < 80:
        recommendations.append(
            "Tempo differs significantly. Use tempo sync or choose a closer BPM."
        )

    if harmonic_score < 80:
        recommendations.append(
            "Keys are not harmonically compatible. Consider another transition."
        )

    if phrase_score < 80:
        recommendations.append(
            "Align the transition with the beginning of an 8-bar phrase."
        )

    if energy_score < 70:
        recommendations.append(
            "Energy levels differ considerably. Consider a smoother build-up."
        )

    if not recommendations:
        recommendations.append("Excellent mix candidate.")

    return recommendations