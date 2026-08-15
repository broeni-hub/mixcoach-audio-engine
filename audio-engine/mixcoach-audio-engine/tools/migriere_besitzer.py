"""Jedem Report und jeder Bewertung einen Besitzer geben (F2.1).

Die Engine kennt heute keinen Nutzer: kein `user_id` an keinem Endpoint,
ein flacher Ergebnisordner. Das Frontend ist ueber Supabase-RLS
(`auth.uid() = user_id`) laengst mandantenfaehig. Beide Modelle lassen
sich nicht gemeinsam hosten.

Der erste Schritt ist der billigste: ein Feld. Mit 51 Reports und einem
Nutzer kostet das Minuten - mit 5000 Reports und fremden Nutzern kostet
es Wochen, und dann steht es zwischen dem Projekt und dem Livegang.

    python -m tools.migriere_besitzer                    # nur Bericht
    python -m tools.migriere_besitzer --write            # schreibt
    python -m tools.migriere_besitzer --besitzer <uid>   # echte auth.uid()
    python -m tools.migriere_besitzer --zurueck --write  # macht es rueckgaengig

Solange Sebastians `auth.uid()` nicht bekannt ist, steht ueberall der
sprechende Platzhalter `local-single-user`. Er ist absichtlich keine
UUID: wer ihn in einem Log oder einer Datei sieht, erkennt sofort, dass
hier noch niemand angemeldet war. Bei der ersten Anmeldung wird er
einmalig umgeschrieben - dafuer `--besitzer` mit der echten uid.

Was NICHT passiert
------------------
Die reportRevision wird NICHT hochgezaehlt. Der Besitzer ist
Engine-seitige Verwaltung; im Browser aendert sich dadurch nichts, was
jemand sehen wuerde. Wuerde die Revision steigen, tauschten alle 67
Reports in jedem Browser ohne sichtbaren Anlass aus. Die naechste echte
Korrektur nimmt das Feld ohnehin mit.

Und: keine Ordnertrennung. `daten/<userId>/analysis_results/` waere die
sauberere Ablage, geht aber durch 26 Dateien, die Trainingskette und das
Archiv. Ein Feld plus Filterung in der API-Schicht reicht fuer eine
geschlossene Beta - die Ablage gehoert in den Auftrag, der sie ohnehin
anfasst.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.paths import DATA_ROOT, GROUND_TRUTH_DIR, RESULTS_DIR

ENGINE_ROOT = Path(__file__).resolve().parents[1]
ARCHIV = ENGINE_ROOT / "_archiv_2026-08-13"

# Sprechend statt UUID - siehe Modul-Docstring.
STANDARD_BESITZER = "local-single-user"

FELD = "userId"


def _ordner() -> list[tuple[str, Path]]:
    """Alles, was einem Besitzer gehoert - inklusive Archiv.

    Das Archiv faellt sonst durchs Raster, und es ist nicht tot: es wird
    von analyze_timing_bias --mode spec gelesen und enthaelt das einzige
    Audio einer Aufnahme (11da05af).
    """
    return [
        ("Reports", RESULTS_DIR),
        ("Reports (archiviert)", RESULTS_DIR / "archived"),
        ("Bewertungen", GROUND_TRUTH_DIR),
        ("Zweitrunde", DATA_ROOT / "relabel"),
        ("Archiv: Reports", ARCHIV / "analysis_results"),
        ("Archiv: Reports (archiviert)", ARCHIV / "analysis_results" / "archived"),
        ("Archiv: Bewertungen", ARCHIV / "ground_truth"),
    ]


def _durchlauf(ordner: Path, besitzer: str, schreiben: bool,
               zurueck: bool) -> dict:
    zahlen = {"gesehen": 0, "geaendert": 0, "schon_gut": 0, "unlesbar": 0,
              "format_unklar": 0}
    if not ordner.exists():
        return zahlen

    for pfad in sorted(ordner.glob("*.json")):
        try:
            roh = pfad.read_bytes()
            daten = json.loads(roh.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            zahlen["unlesbar"] += 1
            continue
        if not isinstance(daten, dict):
            continue

        zahlen["gesehen"] += 1
        ist = daten.get(FELD)
        soll = None if zurueck else besitzer

        if ist == soll or (zurueck and FELD not in daten):
            zahlen["schon_gut"] += 1
            continue

        form = _format_erkennen(roh, daten)
        if form is None:
            zahlen["format_unklar"] += 1

        zahlen["geaendert"] += 1
        if not schreiben:
            continue

        if zurueck:
            daten.pop(FELD, None)
        else:
            daten[FELD] = besitzer
        _schreibe_wie_vorgefunden(pfad, daten, form)
    return zahlen


# Schreibweisen, die im Bestand vorkommen. Durchprobiert wird gegen die
# Originaldatei - was sie exakt nachbaut, ist ihr Format.
_KANDIDATEN = [
    {"indent": i, "ensure_ascii": a, "crlf": c, "schluss": s}
    for i in (None, 1, 2, 4)
    for a in (False, True)
    for c in (False, True)
    for s in ("", "\n")
]


def _bauen(daten: dict, form: dict) -> bytes:
    text = json.dumps(daten, ensure_ascii=form["ensure_ascii"], indent=form["indent"])
    text += form["schluss"]
    if form["crlf"]:
        text = text.replace("\n", "\r\n")
    return text.encode("utf-8")


def _format_erkennen(roh: bytes, unveraendert: dict) -> dict | None:
    """Die Schreibweise der Datei - bewiesen, nicht geraten.

    Wir haben die geparsten Daten und die Originalbytes. Also probieren
    wir die Schreibweisen durch, bis eine die Datei Byte fuer Byte
    nachbaut. Trifft keine zu, geben wir None zurueck und sagen es -
    lieber eine gemeldete Unsicherheit als eine stille Umformatierung.

    Warum der Aufwand: die Umkehrprobe hat es erzwungen. Erst waren es
    182 Dateien, die nach einem Hin und Zurueck anders aussahen (CRLF aus
    der Windows-Zeit, von write_text stillschweigend zu LF gemacht), dann
    noch 113 (die Archiv-Reports stehen mit \\u00f6 statt oe). Beides ist
    inhaltlich nichts und im Diff alles.
    """
    for form in _KANDIDATEN:
        if _bauen(unveraendert, form) == roh:
            return form
    return None


def _schreibe_wie_vorgefunden(pfad: Path, daten: dict, form: dict | None) -> None:
    """Nur das Feld aendern, sonst nichts am Dateiformat."""
    if form is None:
        # Unbekannte Schreibweise: lesbar schreiben und im Bericht zaehlen.
        form = {"indent": 1, "ensure_ascii": False, "crlf": False, "schluss": "\n"}
    pfad.write_bytes(_bauen(daten, form))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--write", action="store_true", help="wirklich schreiben")
    p.add_argument("--besitzer", default=STANDARD_BESITZER,
                   help=f"Besitzer-Kennung (Vorgabe: {STANDARD_BESITZER})")
    p.add_argument("--zurueck", action="store_true",
                   help="das Feld wieder entfernen (macht die Migration rueckgaengig)")
    args = p.parse_args()

    was = "entfernen" if args.zurueck else f"setzen auf '{args.besitzer}'"
    print(f"Besitzer-Feld '{FELD}' {was}\n")

    gesamt = {"gesehen": 0, "geaendert": 0, "schon_gut": 0, "unlesbar": 0,
              "format_unklar": 0}
    for name, ordner in _ordner():
        z = _durchlauf(ordner, args.besitzer, args.write, args.zurueck)
        if z["gesehen"] == 0 and not ordner.exists():
            print(f"  {name:30s} (nicht vorhanden)")
            continue
        print(f"  {name:30s} {z['gesehen']:4d} Dateien, "
              f"{z['geaendert']:4d} zu aendern, {z['schon_gut']:4d} schon gut"
              + (f", {z['unlesbar']} unlesbar" if z["unlesbar"] else ""))
        for k in gesamt:
            gesamt[k] += z[k]

    print(f"\n  {'GESAMT':30s} {gesamt['gesehen']:4d} Dateien, "
          f"{gesamt['geaendert']:4d} zu aendern, {gesamt['schon_gut']:4d} schon gut")

    if not args.write:
        print("\nNur Bericht. Zum Schreiben --write anhaengen.")
    elif args.zurueck:
        print("\nZurueckgenommen. Der Bestand ist wieder wie vor der Migration.")
    else:
        print(f"\nGeschrieben. Rueckgaengig mit: "
              f"python -m tools.migriere_besitzer --zurueck --write")
    return 0


if __name__ == "__main__":
    sys.exit(main())
