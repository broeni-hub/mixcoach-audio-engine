"""Bestandsaufnahme der Ground Truth: was ist verwertbar, was nicht.

Warum das ein eigenes Modul ist: die Referenzmetrik
(tools/analyze_timing_bias.py) und der Retrain
(app/calibration/retrain_model.py) haben die Frage "gehoert dieses Set in
die Auswertung?" bisher unterschiedlich beantwortet. Der Retrain gruppiert
nach fileName und ueberspringt Aufnahmen ohne Audio; die Metrik zaehlte
jede Ground-Truth-Datei einzeln. Dadurch zaehlt dieselbe Aufnahme in der
Metrik mehrfach (REC001: 14 Dateien) und leere Label-Sitzungen druecken die
Precision, ohne je ins Training eingegangen zu sein.

Dieses Modul ist die EINE Stelle, die das entscheidet. Es kennzeichnet,
loescht nichts und schreibt nichts - der Status wird bei jedem Aufruf aus
dem Dateibestand abgeleitet. Das ist bewusst so: eine eingefrorene Liste
waere nach dem naechsten Label-Durchgang still veraltet, und eine veraltete
Ausschlussliste ist schlimmer als gar keine.

Nur Standardbibliothek - analyze_timing_bias.py laeuft ohne numpy/librosa,
und das muss so bleiben.

    python -m tools.eval.gt_status        # Bestandsaufnahme ausgeben
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

# tools/eval/ liegt zwei Ebenen unter mixcoach-audio-engine/
ENGINE_ROOT = Path(__file__).resolve().parents[2]
PROJEKT_ROOT = ENGINE_ROOT.parents[1]

# Beide Ground-Truth-Staemme (siehe Docstring von analyze_timing_bias.py):
# MIXCOACH_DATA_DIR war mal gesetzt und mal nicht, dadurch sind sie
# auseinandergelaufen. Bewusst NICHT ueber app.paths aufgeloest - die
# Metrik soll auch ohne gesetzte Umgebungsvariable dasselbe messen.
#
# Seit 13.08.2026 sind sie zusammengefuehrt, der zweite liegt unter
# _archiv_2026-08-13/. Der Pfad bleibt hier stehen, damit
# analyze_timing_bias '--mode spec' weiter dieselben Zahlen liefert -
# entfiele er, verschoebe sich der eingefrorene Anker. Geschrieben wird
# dorthin nichts mehr.
ARCHIV = ENGINE_ROOT / "_archiv_2026-08-13"
GT_DIRS = [
    ARCHIV / "ground_truth",
    PROJEKT_ROOT / "daten" / "ground_truth",
]

# Ergebnis- und Audio-Ordner in derselben Reihenfolge, die
# retrain_model._find_result_json/_find_audio benutzt. archived/ gehoert
# dazu: der Aufraeum-Knopf verschiebt Analysen dorthin, ein gelabeltes Set
# darf dadurch nicht aus der Auswertung fallen.
#
# Der Archiv-Ordner traegt die einzigen Kopien von 67 .wav - Audio war nie
# versioniert (.gitignore), es gibt sie nirgends sonst.
RESULT_DIRS = [
    PROJEKT_ROOT / "daten" / "analysis_results",
    PROJEKT_ROOT / "daten" / "analysis_results" / "archived",
    ARCHIV / "analysis_results",
    ARCHIV / "analysis_results" / "archived",
]
AUDIO_SUFFIXES = [".wav", ".mp3", ".flac", ".m4a", ".aiff", ".aif"]

# Ab wie wenigen Handgriffen eine Label-Sitzung als abgebrochen gilt.
# 1 statt 2: die zehn Dateien mit genau EINEM Verdict sind der klare Fall
# (die Engine hatte dort 6-9 Marker gesetzt). Bei 2 kaemen vier weitere
# dazu, die genauso gut bewusst duenn bewertet sein koennen - das waere
# geraten, nicht gemessen.
ABBRUCH_SCHWELLE = 1


@dataclass
class GtDatei:
    """Eine einzelne Ground-Truth-Datei (es gibt sie in zwei Staemmen)."""
    pfad: Path
    stamm: str                 # "daten" oder "engine"
    analysis_id: str
    n_verdicts: int
    n_missed: int
    updated_at: float
    daten: dict = field(repr=False, default_factory=dict)


@dataclass
class Aufnahme:
    """Eine Gruppe von Ground-Truth-Dateien, die dieselbe AUFNAHME meinen.

    Schluessel ist fileName aus dem Ergebnis-JSON, mit der analysisId als
    Rueckfallebene (ohne Ergebnis-JSON gibt es keinen Dateinamen). Genau
    diese Gruppierung benutzt collect_feedback_rows() schon heute.
    """
    schluessel: str
    dateien: list[GtDatei]
    file_name: str | None
    hat_ergebnis: bool
    hat_audio: bool

    @property
    def analysis_ids(self) -> list[str]:
        return sorted({d.analysis_id for d in self.dateien})

    @property
    def n_verdicts(self) -> int:
        """Handgriffe der Gruppe, OHNE Doppelzaehlung ueber die Staemme:
        je analysisId der Stand mit den meisten Verdicts."""
        je_id: dict[str, int] = {}
        for d in self.dateien:
            je_id[d.analysis_id] = max(je_id.get(d.analysis_id, 0), d.n_verdicts)
        return sum(je_id.values())

    @property
    def n_missed(self) -> int:
        je_id: dict[str, int] = {}
        for d in self.dateien:
            je_id[d.analysis_id] = max(je_id.get(d.analysis_id, 0), d.n_missed)
        return sum(je_id.values())

    @property
    def status(self) -> str:
        """verwertbar | ohne_ergebnis | abgebrochen

        Bewusst NICHT an der Audio-Verfuegbarkeit festgemacht, obwohl der
        Retrain daran ueberspringt: Ergebnis-JSON und Ground Truth sind
        versioniert, die Audiodateien nicht. In einem frischen Checkout
        (oder einem git-Worktree) waere sonst schlagartig JEDE Aufnahme
        "unbrauchbar", und die gefilterte Metrik gaebe leere Zahlen aus -
        ein Messfehler, der wie ein Befund aussieht. hat_audio wird
        getrennt gefuehrt und nur als Warnung gemeldet.
        """
        if not self.hat_ergebnis:
            return "ohne_ergebnis"
        if self.n_verdicts <= ABBRUCH_SCHWELLE and self.n_missed == 0:
            return "abgebrochen"
        return "verwertbar"

    @property
    def verwertbar(self) -> bool:
        return self.status == "verwertbar"


def _ergebnis_und_audio(analysis_id: str) -> tuple[dict | None, bool]:
    """(Ergebnis-JSON oder None, ob eine Audiodatei existiert)."""
    ergebnis = None
    for basis in RESULT_DIRS:
        pfad = basis / f"{analysis_id}.json"
        if ergebnis is None and pfad.exists():
            try:
                ergebnis = json.loads(pfad.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                ergebnis = None
    hat_audio = any((basis / f"{analysis_id}{suffix}").exists()
                    for basis in RESULT_DIRS for suffix in AUDIO_SUFFIXES)
    return ergebnis, hat_audio


def lies_gt_dateien() -> tuple[list[GtDatei], list[str]]:
    """Alle Ground-Truth-Dateien beider Staemme. Liefert (Dateien, Hinweise)."""
    hinweise: list[str] = []
    dateien: list[GtDatei] = []
    for gt_dir in GT_DIRS:
        if not gt_dir.is_dir():
            hinweise.append(f"FEHLT: {gt_dir} existiert nicht")
            continue
        stamm = "daten" if "daten" in gt_dir.parts else "engine"
        for pfad in sorted(gt_dir.glob("*.json")):
            try:
                j = json.loads(pfad.read_text(encoding="utf-8"))
            except Exception as fehler:  # noqa: BLE001
                hinweise.append(f"unlesbar: {pfad.name}: {fehler}")
                continue
            verdicts = {k: v for k, v in (j.get("verdicts") or {}).items()
                        if v.get("verdict")}
            dateien.append(GtDatei(
                pfad=pfad, stamm=stamm,
                analysis_id=j.get("analysisId") or pfad.stem,
                n_verdicts=len(verdicts), n_missed=len(j.get("missed") or []),
                updated_at=float(j.get("updatedAt") or 0.0), daten=j,
            ))
    return dateien, hinweise


def aufnahmen() -> tuple[list[Aufnahme], list[str]]:
    """Ground Truth nach AUFNAHME gruppiert (fileName, sonst analysisId)."""
    dateien, hinweise = lies_gt_dateien()

    infos: dict[str, tuple[dict | None, bool]] = {}
    for d in dateien:
        if d.analysis_id not in infos:
            infos[d.analysis_id] = _ergebnis_und_audio(d.analysis_id)

    gruppen: dict[str, list[GtDatei]] = {}
    for d in dateien:
        ergebnis, _ = infos[d.analysis_id]
        schluessel = (ergebnis or {}).get("fileName") or d.analysis_id
        gruppen.setdefault(schluessel, []).append(d)

    out: list[Aufnahme] = []
    for schluessel, gruppe in sorted(gruppen.items()):
        ids = {d.analysis_id for d in gruppe}
        ergebnisse = [infos[i] for i in ids]
        file_name = next((e.get("fileName") for e, _ in ergebnisse
                          if e and e.get("fileName")), None)
        out.append(Aufnahme(
            schluessel=schluessel, dateien=gruppe, file_name=file_name,
            hat_ergebnis=any(e is not None for e, _ in ergebnisse),
            # Audio irgendwo in der Gruppe reicht - genau so entscheidet
            # collect_feedback_rows(), das die naechstbeste Analyse mit
            # Audio nimmt, wenn die kanonische keines hat.
            hat_audio=any(a for _, a in ergebnisse),
        ))
    return out, hinweise


def uebersicht() -> dict:
    """Zahlen fuer den Bericht - eine Zeile je Statusgruppe."""
    gruppen, hinweise = aufnahmen()
    zaehler = Counter(a.status for a in gruppen)

    # Liegt in diesem Checkout ueberhaupt Audio? Wenn nirgends, ist das eine
    # Eigenschaft der Arbeitskopie und keine Aussage ueber die Sets.
    audio_verfuegbar = any(a.hat_audio for a in gruppen)
    if not audio_verfuegbar:
        hinweise.append(
            "In diesem Checkout liegt KEINE Audiodatei (nur Ground Truth und "
            "Ergebnis-JSON sind versioniert). Die Spalte 'Audio' ist damit "
            "ohne Aussage; der Retrain braucht den vollen Datenstamm.")
    else:
        stumm = [a.schluessel for a in gruppen if a.verwertbar and not a.hat_audio]
        if stumm:
            hinweise.append(
                f"{len(stumm)} verwertbare Aufnahme(n) ohne Audio - der Retrain "
                f"ueberspringt sie trotz brauchbarer Labels: {', '.join(stumm[:5])}")

    return {
        "hinweise": hinweise,
        "audio_verfuegbar": audio_verfuegbar,
        "n_dateien": sum(len(a.dateien) for a in gruppen),
        "n_analysis_ids": len({i for a in gruppen for i in a.analysis_ids}),
        "n_aufnahmen": len(gruppen),
        "n_verwertbar": zaehler["verwertbar"],
        "n_ohne_ergebnis": zaehler["ohne_ergebnis"],
        "n_abgebrochen": zaehler["abgebrochen"],
        "n_ohne_audio": sum(1 for a in gruppen if not a.hat_audio),
        "handgriffe_gesamt": sum(a.n_verdicts + a.n_missed for a in gruppen),
        "handgriffe_verwertbar": sum(a.n_verdicts + a.n_missed
                                     for a in gruppen if a.verwertbar),
        "gruppen": gruppen,
    }


def main() -> int:
    u = uebersicht()
    for h in u["hinweise"]:
        print(f"  ! {h}")
    print("=" * 72)
    print("  Ground-Truth-Bestand")
    print("=" * 72)
    print(f"  Dateien in beiden Staemmen        {u['n_dateien']:>4}")
    print(f"  verschiedene analysisId           {u['n_analysis_ids']:>4}")
    print(f"  verschiedene AUFNAHMEN (fileName) {u['n_aufnahmen']:>4}")
    print()
    print(f"  davon verwertbar                  {u['n_verwertbar']:>4}")
    print(f"       ohne Ergebnis-JSON           {u['n_ohne_ergebnis']:>4}"
          f"   (kein Audio auffindbar, nie im Training)")
    print(f"       abgebrochene Label-Sitzung   {u['n_abgebrochen']:>4}"
          f"   (<= {ABBRUCH_SCHWELLE} Handgriff, keine missed)")
    if u["audio_verfuegbar"]:
        print(f"       (nachrichtlich: ohne Audio   {u['n_ohne_audio']:>4})")
    print()
    h_ges, h_ver = u["handgriffe_gesamt"], u["handgriffe_verwertbar"]
    anteil = (h_ges - h_ver) / h_ges * 100 if h_ges else 0.0
    print(f"  Handgriffe gesamt                 {h_ges:>4}")
    print(f"  davon in verwertbaren Aufnahmen   {h_ver:>4}"
          f"   ({100 - anteil:.0f} %)")
    print(f"  ohne Trainingswirkung             {h_ges - h_ver:>4}"
          f"   ({anteil:.0f} %)")
    print()
    print("  Aussortiert:")
    for a in sorted(u["gruppen"], key=lambda x: (x.status, x.schluessel)):
        if a.verwertbar:
            continue
        print(f"    {a.status:<12} {a.schluessel[:44]:<44} "
              f"{a.n_verdicts:>3} verdicts + {a.n_missed:>2} missed"
              f"  ({len(a.analysis_ids)} id)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
