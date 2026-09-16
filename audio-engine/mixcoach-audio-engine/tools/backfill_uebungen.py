"""Uebungen in die gespeicherten Reports nachtragen (J3).

Ohne Audio, ohne Demucs: alles Noetige steht in den JSON. Dauert Sekunden.

    python -m tools.backfill_uebungen               # nur Bericht
    python -m tools.backfill_uebungen --write       # schreibt
    python -m tools.backfill_uebungen --mit-archiv  # auch archived/

Was passiert
------------
1. Die fest verdrahtete Vorlage ("Transition Review") wird durch Uebungen
   ersetzt, die je eine Zahl aus demselben Report nennen (app/coach/
   uebungen.py). Wo es keine belegte Zahl gibt, bleibt die Liste LEER -
   das ist keine Luecke, sondern das Ergebnis.
2. Beobachtungen kommen in ein eigenes Feld, getrennt von den Uebungen.
3. notMeasured wird aus dem tatsaechlichen Befuellungsstand gebildet statt
   aus einer festen Fuenferliste (B5). Ein Report, dem darueber hinaus
   etwas fehlt, sagt das jetzt auch.
4. Kritik, die als Staerke eingeschoben wurde, faellt aus strengths und
   feedback.worked (seit 16.09.2026, siehe _eingeschobene_kritik).
5. reportRevision zaehlt hoch - ohne das bleibt alles auf der Platte
   liegen und erreicht keinen Browser, der die Analyse schon kennt
   (siehe app/audio/pipeline/scoring_version.py).

Punkt 5 ist der Grund, warum dieser Backfill ueberhaupt ankommt. Bis zum
13.08.2026 ordnete der Korrekturweg nur nach scoringVersion, und Uebungen
sind abgeleiteter Text - sie duerfen die Rechenvorschrift nicht erhoehen.
Ohne die Revision waere dieser Lauf wirkungslos gewesen.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from app.audio.coach_summary import LEER_POSITIV, LEER_VERBESSERUNG
from app.audio.pipeline.scoring_version import naechste_revision, revision_von
from app.audio.segment_keys import camelot_compatibility_score
from app.audio.transition_quality import _feedback, _feedback_en
from app.audio.nicht_gemessen import aus_report as _nicht_gemessen
from app.coach.uebungen import baue
from app.paths import RESULTS_DIR

# Saetze, die auf einer widerlegten Groesse ruhen oder gar keine Zahl nennen.
# Sie stehen in den gespeicherten Reports (289x der Phrasen-Satz, 52x der
# "sitzt"-Satz) und verschwinden mit diesem Lauf.
UNBELEGTE_SAETZE = (
    "Beats neben dem Phrasenstart",
    "beats off the phrase start",
    "Timing, Tempo und Energie passen zusammen",
    "timing, tempo and energy line up",
    "solide, aber nicht herausragend",
    "solid but not outstanding",
    "gleiche die Tempi vor dem Blend an",
    "match tempos before the blend",
    "Es gibt eine auswertbare Struktur",
    "Keine großen Probleme erkannt",
    "Set analysis completed",
    "No major issues detected",
)


def _saetze_neu(uebergaenge: list) -> int:
    """Feedback je Uebergang neu bilden. Liefert, wie viele sich aendern.

    Faithful nachgerechnet, nicht per Textchirurgie: _feedback braucht die
    Camelot-Kompatibilitaet, und die ist eine reine Funktion von
    camelot_before/camelot_after - beides steht im Report. Achtung, das ist
    NICHT harmonic_clash_score: der kommt aus dem Composite-Scoring und ist
    eine andere Groesse, auch wenn der Name aehnlich klingt.
    """
    geaendert = 0
    for t in uebergaenge:
        if not isinstance(t, dict):
            continue
        harmonisch = camelot_compatibility_score(t.get("camelot_before"),
                                                 t.get("camelot_after"))
        mid = t.get("mid_sec")
        if not isinstance(mid, (int, float)):
            continue
        # Im gespeicherten Report sind key_before/key_after flache Strings
        # ("A# Major"), in der Live-Kette dagegen Dicts mit key+camelot.
        # _feedback erwartet die Dict-Form, also hier zusammensetzen.
        vor = {"key": t.get("key_before"), "camelot": t.get("camelot_before")}
        nach = {"key": t.get("key_after"), "camelot": t.get("camelot_after")}

        de = _feedback(float(mid), vor, nach, harmonisch)
        en = _feedback_en(float(mid), vor, nach, harmonisch)
        if t.get("feedback") != de or t.get("feedback_en") != en:
            t["feedback"], t["feedback_en"] = de, en
            geaendert += 1
    return geaendert


def _liste_saeubern(eintraege: list, leer_satz: str, auch_entfernen=None) -> list:
    """Unbelegte Saetze entfernen - und sagen, wenn nichts bleibt."""
    behalten = [s for s in (eintraege or [])
                if not any(m in s for m in UNBELEGTE_SAETZE)
                and not (auch_entfernen and auch_entfernen(s))]
    return behalten or [leer_satz]


# Die drei Saetze, die seit dem 14.08.2026 in das feedback eines Uebergangs
# gelangen - alle drei Kritik, alle maschinell erzeugt. Gebunden an die
# Quellen in tests/test_backfill_staerken.py: aendert jemand den Wortlaut
# dort, schlaegt der Test an, bevor dieses Muster stillschweigend nichts mehr
# findet.
#     app/audio/transition_quality.py  _feedback
#     app/audio/loudness.py            annotate_transitions
#     app/audio/bass_overlap.py        annotate_bass_overlap
KRITIK_MUSTER = re.compile(
    r"Uebergang bei \d{2,3}:\d{2} wechselt harmonisch weit \("
    r"|Achtung: Der neue Track kommt \d+\.\d dB (lauter|leiser)"
    r"|Der neue Track ist \d+\.\d dB (lauter|leiser) - leichter Pegelsprung"
    r"|Beide Baesse liefen im Blend uebereinander \(Overlap"
)


def _eingeschobene_kritik(report: dict):
    """Pruefer: ist dieser Eintrag Kritik, die als Staerke eingeschoben wurde?

    coach_summary setzte bis zum 14.09.2026 den feedback-Text des besten
    "smooth"-Uebergangs als Staerke ein. Dieser Kanal kennt seit dem 14.08.
    nur Kritik - in 12 von 59 Reports stand ein Tadel unter "das lief gut".

    Zwei Wege, beide noetig (gemessen am 16.09.2026):

    1. HERKUNFT - der Eintrag ist wortgleich einem feedback-Text, so wie er im
       ORIGINAL-Report steht. Nicht im neu gebildeten: _saetze_neu bildet nur
       den Harmonie-Satz neu, und "Achtung: Der neue Track kommt 4.2 dB
       leiser" fiele aus dem Vergleich.
    2. SATZMUSTER - in drei Reports vom 12.07. (REC002, REC003, REC013) steht
       der Einschub noch unter strengths, aber nicht mehr im Uebergang: ein
       frueherer Lauf hat das feedback neu gebildet und dabei entfernt, die
       Staerke blieb. Die Herkunft ist dort nicht mehr ablesbar.

    Die echten Staerken ("Die Energie steigt im Verlauf an ...") treffen
    keinen der beiden Wege.
    """
    herkunft = frozenset(
        (t.get("feedback") or "").strip()
        for t in (report.get("setTransitions") or [])
        if isinstance(t, dict) and (t.get("feedback") or "").strip()
    )
    return lambda eintrag: ((eintrag or "").strip() in herkunft
                            or bool(KRITIK_MUSTER.search(eintrag or "")))


def nachziehen(report: dict) -> tuple[dict, list]:
    """Report mit Uebungen versehen. Liefert (neu, was geaendert wurde)."""
    neu = dict(report)
    aenderungen: list = []

    aid = str(report.get("id") or "")
    # Kopie, damit die Saetze im Original erst beim Schreiben landen.
    uebergaenge = [dict(t) if isinstance(t, dict) else t
                   for t in (report.get("setTransitions") or [])]

    saetze = _saetze_neu(uebergaenge)
    if saetze:
        aenderungen.append(f"feedback je Uebergang: {saetze} neu gebildet")
        neu["setTransitions"] = uebergaenge

    kritik = _eingeschobene_kritik(report)
    for feld, leer, weg in (("strengths", LEER_POSITIV, kritik),
                            ("weaknesses", LEER_VERBESSERUNG, None)):
        # Unter weaknesses sind Uebergangs-Saetze richtig - dort nichts entfernen.
        gesaeubert = _liste_saeubern(report.get(feld) or [], leer, weg)
        if gesaeubert != (report.get(feld) or []):
            aenderungen.append(
                f"{feld}: {len(report.get(feld) or [])} -> {len(gesaeubert)}")
            neu[feld] = gesaeubert

    # feedback.worked/improve ist eine ZWEITE Kopie derselben Saetze - der
    # Mapper fuellt sie aus denselben positives/improvements. Genau die
    # rendert das "Coach-Fazit" ganz oben im Report.
    #
    # Der erste Lauf hat sie uebersehen: strengths war sauber, das Fazit
    # zeigte weiter "Uebergang bei 36:43 sitzt: Timing, Tempo und Energie
    # passen zusammen." Aufgefallen ist es erst beim Oeffnen der laufenden
    # App - die Tests waren gruen. Das ist die Lehre aus F1 noch einmal:
    # ein Test belegt die Regel, nicht den Weg durch die Anwendung.
    fb = report.get("feedback")
    if isinstance(fb, dict):
        neu_fb = dict(fb)
        for feld, leer in (("worked", LEER_POSITIV), ("improve", LEER_VERBESSERUNG)):
            gesaeubert = _liste_saeubern(fb.get(feld) or [], leer)
            if feld == "worked":
                # Der Mapper setzt worked = positives[:2]; gezaehlt am 16.09.2026
                # gilt worked == strengths[:2] in 60 von 60 Reports. Faellt ein
                # Einschub weg, rueckt die naechste Staerke nach - getrennt
                # gesaeubert bliebe aus [Einschub, A, B] nur [A].
                gesaeubert = (neu.get("strengths") or [leer])[:2]
            if gesaeubert != (fb.get(feld) or []):
                aenderungen.append(
                    f"feedback.{feld}: {len(fb.get(feld) or [])} -> {len(gesaeubert)}")
                neu_fb[feld] = gesaeubert
        if neu_fb != fb:
            neu["feedback"] = neu_fb

    uebungen, beobachtungen = baue(aid, uebergaenge)

    alt_uebungen = report.get("exercises") or []
    if alt_uebungen != uebungen:
        vorlage = any(not u.get("metric") for u in alt_uebungen)
        aenderungen.append(
            f"exercises: {len(alt_uebungen)}{' (Vorlage)' if vorlage else ''}"
            f" -> {len(uebungen)}")
        neu["exercises"] = uebungen

    if (report.get("observations") or []) != beobachtungen:
        aenderungen.append(f"observations: -> {len(beobachtungen)}")
        neu["observations"] = beobachtungen

    nm = _nicht_gemessen(neu)
    if sorted(report.get("notMeasured") or []) != nm:
        aenderungen.append(
            f"notMeasured: {len(report.get('notMeasured') or [])} -> {len(nm)} Eintraege")
        neu["notMeasured"] = nm

    if aenderungen:
        neu["reportRevision"] = naechste_revision(neu)
        aenderungen.append(
            f"reportRevision: {revision_von(report) or 'fehlt'} -> {neu['reportRevision']}")

    return neu, aenderungen


def durchlauf(ordner: Path, schreiben: bool, laut: bool) -> dict:
    zahlen = {"gesehen": 0, "geaendert": 0, "schon_gut": 0,
              "mit_uebung": 0, "ohne_uebung": 0, "uebungen": 0, "beobachtungen": 0}
    for pfad in sorted(ordner.glob("*.json")):
        try:
            report = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as fehler:
            print(f"  UNLESBAR {pfad.name}: {fehler}")
            continue
        if "setTransitions" not in report:
            continue

        zahlen["gesehen"] += 1
        neu, aenderungen = nachziehen(report)

        anzahl = len(neu.get("exercises") or [])
        zahlen["uebungen"] += anzahl
        zahlen["beobachtungen"] += len(neu.get("observations") or [])
        zahlen["mit_uebung" if anzahl else "ohne_uebung"] += 1

        if not aenderungen:
            zahlen["schon_gut"] += 1
            continue
        zahlen["geaendert"] += 1
        if laut:
            print(f"  {pfad.name}  ({neu.get('fileName')})")
            for a in aenderungen:
                print(f"      {a}")
        if schreiben:
            pfad.write_text(json.dumps(neu, ensure_ascii=False), encoding="utf-8")
    return zahlen


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--write", action="store_true", help="wirklich schreiben")
    p.add_argument("--mit-archiv", action="store_true", help="auch archived/")
    p.add_argument("--leise", action="store_true", help="nur die Zusammenfassung")
    args = p.parse_args()

    ordner = [RESULTS_DIR]
    if args.mit_archiv:
        ordner.append(RESULTS_DIR / "archived")

    gesamt = {k: 0 for k in ("gesehen", "geaendert", "schon_gut", "mit_uebung",
                             "ohne_uebung", "uebungen", "beobachtungen")}
    for o in ordner:
        if not o.exists():
            continue
        print(f"=== {o} ===")
        for k, v in durchlauf(o, args.write, not args.leise).items():
            gesamt[k] += v
        print()

    print(f"Reports gesehen        : {gesamt['gesehen']}")
    print(f"  nachgezogen          : {gesamt['geaendert']}")
    print(f"  schon auf dem Stand  : {gesamt['schon_gut']}")
    print(f"mit mindestens 1 Uebung: {gesamt['mit_uebung']}")
    print(f"ohne jede Uebung       : {gesamt['ohne_uebung']}  (dort ist nichts belegt)")
    print(f"Uebungen gesamt        : {gesamt['uebungen']}")
    print(f"Beobachtungen gesamt   : {gesamt['beobachtungen']}")

    if not args.write:
        print("\nNur Bericht. Zum Schreiben --write anhaengen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
