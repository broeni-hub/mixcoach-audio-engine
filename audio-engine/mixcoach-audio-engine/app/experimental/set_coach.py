from typing import Dict, List


def generate_set_feedback(set_analysis: Dict) -> Dict:
    quality = set_analysis.get("quality", {})
    dramaturgy = set_analysis.get("dramaturgy", {})
    transitions = set_analysis.get("transition_zones", [])
    duration = float(set_analysis.get("duration", 0.0))

    strengths = []
    issues = []
    suggestions = []

    overall = quality.get("overall", 0)

    if overall >= 75:
        strengths.append("Das Set wirkt insgesamt stabil und gut kontrolliert.")
    else:
        issues.append("Das Set hat noch hörbare Schwankungen im Flow.")

    if dramaturgy.get("energy_trend") == "rising":
        strengths.append("Die Energie entwickelt sich nach oben. Gute Set-Dramaturgie.")
    elif dramaturgy.get("energy_trend") == "falling":
        issues.append("Die Energie fällt im Verlauf ab. Das kann das Set gegen Ende schwächer wirken lassen.")
        suggestions.append("Plane gegen Ende bewusst stärkere Tracks oder kürzere Breaks ein.")
    else:
        suggestions.append("Baue mehr gezielte Energiebewegung ein: Intro, Aufbau, Peak, Entspannung.")

    minutes = duration / 60.0 if duration > 0 else 0.0
    transition_density = len(transitions) / max(minutes / 10.0, 1)

    if transition_density < 2:
        issues.append("Es wurden relativ wenige mögliche Übergänge erkannt.")
        suggestions.append("Mehr Wechselpunkte oder klarere Übergangszonen könnten das Set lebendiger machen.")
    elif transition_density > 6:
        issues.append("Es wurden sehr viele mögliche Übergänge erkannt.")
        suggestions.append("Prüfe, ob das Set zu hektisch wirkt oder ob zu oft Energiebrüche entstehen.")
    else:
        strengths.append("Die Übergangsdichte wirkt ausgewogen.")

    if quality.get("energy_flow", 0) < 65:
        issues.append("Der Energieverlauf ist unruhig.")
        suggestions.append("Achte auf weichere Energieübergänge zwischen Tracks.")

    return {
        "overall_score": overall,
        "rating": quality.get("rating"),
        "strengths": strengths,
        "issues": issues,
        "suggestions": suggestions,
    }