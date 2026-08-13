"""Welche Rechenvorschrift hat die Werte in einem Report erzeugt?

Das Produktversprechen ruht auf Vergleichbarkeit ueber Zeit: *"Das Abo
rechtfertigt sich nicht durch die Analyse - sondern durch die Entwicklung, die
nur mit Historie sichtbar wird."* Eine Entwicklung sieht man nur, wenn zwei
Zahlen dasselbe bedeuten.

Genau das war bisher nicht gesichert. Am 13.08.2026 nachgezaehlt, auf
Sebastians eigenen 13 Aufnahmen:

    composite_quality_score, Median je Aufnahme
      analysiert am 12.07.        68 - 82
      analysiert ab 17.07.        94 - 97

Das sind keine besseren Uebergaenge. Am 12.07. lief `fit_composite_weights`
zum ersten Mal und hat die Gewichte von Gleichverteilung auf
vocal_overlap 0,42 / beat_alignment 0,49 gesetzt. Derselbe Feldname, zwei
Rechenvorschriften, 25 Punkte Unterschied - ein Fortschritts-Radar darauf
haette dem DJ einen Sprung gezeigt, den er nie gemacht hat.

Deshalb traegt ab jetzt jeder Report eine Versionsnummer. Regel: **wer eine
Rechenvorschrift aendert, erhoeht sie und traegt den Grund unten ein.** Ohne
Eintrag ist eine Aenderung nicht fertig.

Was die Version NICHT abdeckt: Aenderungen an der Erkennung (welcher Uebergang
wo liegt). Die haengen am Modell und stehen dort in `loso_validation`.
"""

from __future__ import annotations

SCORING_VERSION = 3

# Was in welcher Version galt - von neu nach alt, damit der aktuelle Stand
# oben steht.
SCORING_CHANGELOG: dict[int, str] = {
    3: "ab 13.08.2026 - erste Version, die ueberhaupt gestempelt wird. "
       "Inhaltlich wie 2; die Nummer existiert, damit kuenftige Aenderungen "
       "unterscheidbar sind.",
    2: "ab 12.07.2026 - composite_quality_score mit gefitteten Gewichten "
       "(vocal_overlap 0,42 / beat_alignment 0,49 / harmonic_clash 0,09). "
       "Nicht gestempelt, nur rekonstruierbar am Analysedatum.",
    1: "vor 12.07.2026 - composite bei Gleichverteilung der fuenf Dimensionen. "
       "Nicht gestempelt.",
}

# Reports ohne Stempel sind Version 1 oder 2 - welche, sagt nur das
# Analysedatum, und auch das nur ungefaehr. Wer sie vergleicht, muss das
# wissen; deshalb dieser eigene Wert statt eines stillen Default auf 1.
UNSTAMPED = 0


def scoring_stamp() -> dict:
    """Der Block, den die Pipeline in jeden Report schreibt."""
    return {
        "scoringVersion": SCORING_VERSION,
        "scoringNote": SCORING_CHANGELOG[SCORING_VERSION],
    }


def vergleichbar(a: int | None, b: int | None) -> bool:
    """Duerfen zwei Reports gegeneinander gestellt werden?

    Nur bei gleicher, bekannter Version. Zwei ungestempelte Reports gelten
    ausdruecklich als NICHT vergleichbar - sie koennen aus verschiedenen
    Epochen stammen, und das ist der Fall, der den Schaden anrichtet.
    """
    if not a or not b:
        return False
    return a == b
