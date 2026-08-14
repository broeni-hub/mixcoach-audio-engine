from typing import Dict, List

# Was dasteht, wenn nichts Belegtes dasteht. Bewusst zwei verschiedene
# Saetze: "nichts hervorzuheben" und "nichts anzumahnen" sind nicht
# dasselbe, und derselbe Text an zwei Stellen liest sich wie ein Fehler.
LEER_POSITIV = ("Zu diesem Set laesst sich aus den vorhandenen Messungen "
                "nichts Konkretes hervorheben.")
LEER_VERBESSERUNG = ("Zu diesem Set laesst sich aus den vorhandenen Messungen "
                     "nichts Konkretes anmahnen.")


def generate_coach_summary(set_analysis: Dict) -> Dict:
    quality = set_analysis.get("quality", {})
    rule_findings = set_analysis.get("rule_findings", [])
    dramaturgy = set_analysis.get("dramaturgy", {})

    raw_overall = quality.get("overall")
    overall = float(raw_overall) if raw_overall is not None else None
    rating = quality.get("rating", "unknown")

    summary = _summary_text(overall, rating)
    positives = _build_positives(set_analysis)
    improvements = _build_improvements(rule_findings, dramaturgy)

    # Phase 2: konkretes Feedback aus der Uebergangs-Bewertung.
    transitions = set_analysis.get("transitions_detailed", [])
    rough = [t for t in transitions if t.get("label") == "rough"]
    smooth = [t for t in transitions if t.get("label") == "smooth"]

    for t in sorted(rough, key=lambda x: x.get("quality_score") or 0)[:2]:
        if t.get("feedback"):
            improvements.insert(0, t["feedback"])

    if smooth:
        best = max(smooth, key=lambda x: x.get("quality_score") or 0)
        if best.get("feedback"):
            positives.insert(0, best["feedback"])

    # Bleibt eine Liste leer, wird das gesagt - nicht gefuellt. Seit dem
    # 14.08.2026 kommt das haeufiger vor: die Uebergangs-Saetze aus
    # phrase_beats_off und bpm_drift sind entfallen (transition_quality.
    # _feedback), und was uebrig bleibt, ist weniger Text. Das ist richtig
    # so - ein Allgemeinplatz sieht aus wie ein Befund.
    if not positives:
        positives = [LEER_POSITIV]
    if not improvements:
        improvements = [LEER_VERBESSERUNG]

    return {
        "overall_score": overall,
        "rating": rating,
        "summary": summary,
        "positives": positives,
        "improvements": improvements,
    }


def _summary_text(score, rating: str) -> str:
    if score is None:
        return (
            "Die Uebergaenge konnten nicht bewertet werden - "
            "entweder wurden keine erkannt oder die Segmente waren zu kurz fuer eine Messung."
        )

    if score >= 85:
        return f"Starkes Set. Die Analyse bewertet es mit {score}/100 ({rating})."

    if score >= 70:
        return f"Gutes Set mit kleinen Baustellen. Score: {score}/100 ({rating})."

    if score >= 55:
        return f"Solides Grundgerüst, aber der Flow kann klarer werden. Score: {score}/100 ({rating})."

    return f"Das Set braucht Arbeit. Score: {score}/100 ({rating})."


def _build_positives(set_analysis: Dict) -> List[str]:
    positives = []

    quality = set_analysis.get("quality", {})
    dramaturgy = set_analysis.get("dramaturgy", {})

    if quality.get("energy_flow", 0) >= 70:
        positives.append("Der Energiefluss wirkt überwiegend stabil.")

    if dramaturgy.get("energy_trend") == "rising":
        positives.append("Die Energie steigt im Verlauf an. Gute Dramaturgie.")

    if quality.get("transition_density", 0) >= 70:
        positives.append("Die Übergangsdichte wirkt brauchbar.")

    # Frueher stand hier "Es gibt eine auswertbare Struktur, auf der MixCoach
    # weiter aufbauen kann." - ein Satz, der nichts misst und immer passt.
    # Wenn nichts belegt ist, sagt das generate_coach_summary am Ende
    # ausdruecklich, statt die Liste zu fuellen.
    return positives


def _build_improvements(rule_findings: List[Dict], dramaturgy: Dict) -> List[str]:
    improvements = []

    for finding in rule_findings:
        message = finding.get("message")
        if message and message not in improvements:
            improvements.append(message)

    if dramaturgy.get("energy_trend") == "stable":
        improvements.append("Mehr bewusste Energiebewegung einbauen: Aufbau, Peak und kurze Entspannung.")

    # Frueher: "Keine großen Probleme erkannt. Feintuning bei Übergängen und
    # Track-Auswahl lohnt sich trotzdem." Das klang nach einem Befund, war
    # aber nur der Fall "es wurde nichts gefunden" - siehe _build_positives.
    return improvements