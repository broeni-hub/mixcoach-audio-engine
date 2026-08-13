"""Die zwei Ergebnis- und Ground-Truth-Staemme zu einem zusammenfuehren (F1.1).

Ausgangslage (13.08.2026 ausgezaehlt):

    daten/ground_truth/                    45 Dateien   <- maszgeblich
    audio-engine/.../ground_truth/         24 Dateien   <- alle 24 namensgleich,
                                                          18 byteidentisch,
                                                          6 abweichend
    daten/analysis_results/                50 Reports   <- maszgeblich
    audio-engine/.../analysis_results/     93 Reports   <- 30 auch in daten,
                                                          63 nur hier

Der als veraltet gefuehrte Ordner ist NICHT nur veraltet: in den 6
abweichenden Ground-Truth-Dateien steckt Handarbeit, die im maszgeblichen
Stamm fehlt (z.B. a5ee0fde: missed 119.39 gibt es nur dort). Deshalb wird
zusammengefuehrt und nicht ueberschrieben, und deshalb wird nichts
geloescht, sondern archiviert.

    python -m tools.staemme_zusammenfuehren            # nur Bericht
    python -m tools.staemme_zusammenfuehren --write    # schreibt

Was dieses Skript NICHT entscheidet
-----------------------------------
Widersprechende `verdicts`. Wenn dieselbe Uebergangsnummer in beiden
Staemmen ein anderes Urteil traegt, ist das Sebastians Bewertung, nicht
eine Rechenaufgabe. Solche Faelle kommen nach daten/ground_truth/
KONFLIKTE.md, und bis zur Entscheidung gilt der Stand aus daten/.

Was dieses Skript bewusst NICHT anfasst
---------------------------------------
`audioPath`. Der Auftrag sagt "den Verweis korrigieren, falls einer ins
Leere zeigt" - das beruht auf einer falschen Annahme: das Feld enthaelt
keinen Dateipfad, sondern eine API-Route (`/analysis/<id>/audio`, siehe
ein beliebiger Report). Sie ergibt sich aus der id und kann gar nicht ins
Leere zeigen. Die Audiodateien liegen daneben als <id>.wav und sind
gitignoriert (.gitignore:33) - sie werden weder kopiert noch verschoben.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.paths import GROUND_TRUTH_DIR, RESULTS_DIR

ENGINE_ROOT = Path(__file__).resolve().parents[1]
ENGINE_GT = ENGINE_ROOT / "ground_truth"
ENGINE_RESULTS = ENGINE_ROOT / "analysis_results"
ARCHIV = ENGINE_ROOT / "_archiv_2026-08-13"
KONFLIKTE = GROUND_TRUTH_DIR / "KONFLIKTE.md"

# missed-Zeiten gelten als dieselbe Angabe, wenn sie sich um weniger als das
# unterscheiden. Bewusst eng: hier wird nur Datei-Rauschen entdoppelt, keine
# inhaltliche Entscheidung getroffen.
MISSED_TOLERANZ = 0.01

# Ab diesem Abstand gelten zwei missed-Angaben aus VERSCHIEDENEN Staemmen als
# sicher verschiedene Uebergaenge. Darunter werden sie im Bericht angezeigt -
# nicht zusammengefasst. Sebastians Entscheidung vom 13.08.: volle Union, die
# Naehe wird nur sichtbar gemacht. Beispiel a156bceb: 1297.48 (daten) und
# 1310.8 (engine) liegen 13,3 s auseinander und sind sehr wahrscheinlich
# derselbe Uebergang, einmal praeziser nachgetragen.
NAHE_HINWEIS_S = 30.0


def _lade(pfad: Path) -> dict | None:
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _entdoppeln(werte: list[float]) -> list[float]:
    """Sortiert, und Werte innerhalb MISSED_TOLERANZ zaehlen als einer."""
    raus: list[float] = []
    for w in sorted(float(x) for x in werte):
        if not raus or w - raus[-1] > MISSED_TOLERANZ:
            raus.append(w)
    return raus


def _nahe_paare(a: list[float], b: list[float]) -> list[tuple[float, float]]:
    """Paare aus verschiedenen Staemmen, die naeher als NAHE_HINWEIS_S liegen,
    ohne identisch zu sein - reine Anzeige, keine Zusammenfassung."""
    paare = []
    for x in a:
        for y in b:
            if MISSED_TOLERANZ < abs(x - y) < NAHE_HINWEIS_S:
                paare.append((x, y))
    return paare


def ground_truth_zusammenfuehren() -> tuple[dict[str, dict], dict]:
    """Fuer jede namensgleiche Datei den vereinigten Stand berechnen.

    Liefert {dateiname: zusammengefuehrter Inhalt} und einen Bericht.
    Geschrieben wird hier nichts.
    """
    bericht: dict = {"zusammengefuehrt": [], "unveraendert": [], "nur_engine": [],
                     "konflikte": [], "nahe_paare": []}
    ergebnis: dict[str, dict] = {}

    engine_dateien = sorted(ENGINE_GT.glob("*.json")) if ENGINE_GT.exists() else []
    for e_pfad in engine_dateien:
        name = e_pfad.name
        d_pfad = GROUND_TRUTH_DIR / name
        engine = _lade(e_pfad)
        if engine is None:
            continue

        if not d_pfad.exists():
            # Gibt es im maszgeblichen Stamm nicht - unveraendert uebernehmen.
            ergebnis[name] = engine
            bericht["nur_engine"].append(name)
            continue

        daten = _lade(d_pfad)
        if daten is None:
            continue
        if d_pfad.read_bytes() == e_pfad.read_bytes():
            bericht["unveraendert"].append(name)
            continue

        neu = dict(daten)  # daten/ ist die Grundlage, siehe Modul-Docstring

        # --- missed: volle Vereinigung beider Seiten ---
        m_d = [float(x) for x in (daten.get("missed") or [])]
        m_e = [float(x) for x in (engine.get("missed") or [])]
        vereint = _entdoppeln(m_d + m_e)
        if vereint != _entdoppeln(m_d):
            neu["missed"] = vereint
        for x, y in _nahe_paare(m_d, m_e):
            bericht["nahe_paare"].append((name, x, y, round(abs(x - y), 2)))

        # --- verdicts: gleich -> uebernehmen, verschieden -> nicht raten ---
        v_d = daten.get("verdicts") or {}
        v_e = engine.get("verdicts") or {}
        zusammen = dict(v_d)
        for index, urteil_e in v_e.items():
            if index not in v_d:
                zusammen[index] = urteil_e          # nur im Engine-Stamm
            elif v_d[index] != urteil_e:
                bericht["konflikte"].append({
                    "datei": name, "index": index,
                    "daten": v_d[index], "engine": urteil_e,
                    "updatedAt_daten": daten.get("updatedAt"),
                    "updatedAt_engine": engine.get("updatedAt"),
                })
                # daten/ gilt weiter - siehe Modul-Docstring.
        if zusammen != v_d:
            neu["verdicts"] = zusammen

        # --- updatedAt: der spaetere gewinnt ---
        u_d, u_e = daten.get("updatedAt"), engine.get("updatedAt")
        if isinstance(u_d, (int, float)) and isinstance(u_e, (int, float)):
            neu["updatedAt"] = max(u_d, u_e)

        if neu != daten:
            ergebnis[name] = neu
            bericht["zusammengefuehrt"].append(name)
        else:
            bericht["unveraendert"].append(name)

    return ergebnis, bericht


def _version(report: dict) -> tuple[int, str, str]:
    """Rangfolge fuer 'welcher Stand gewinnt': erst scoringVersion (ohne
    Stempel = 0, siehe scoring_version.UNSTAMPED), dann mapperVersion, dann
    createdAt. Genau in dieser Reihenfolge, weil nur die scoringVersion
    aussagt, nach welcher Rechenvorschrift die Zahlen entstanden sind."""
    sv = report.get("scoringVersion")
    return (int(sv) if isinstance(sv, int) else 0,
            str(report.get("mapperVersion") or ""),
            str(report.get("createdAt") or ""))


def reports_einordnen() -> dict:
    """Welcher Engine-Report gehoert in den Datenstamm, welcher ins Archiv?"""
    bericht: dict = {"daten_gewinnt": [], "engine_gewinnt": [],
                     "uebernehmen": [], "archivieren": []}

    gt_ids = {p.stem for p in GROUND_TRUTH_DIR.glob("*.json")}
    if ENGINE_GT.exists():
        gt_ids |= {p.stem for p in ENGINE_GT.glob("*.json")}

    for e_pfad in sorted(ENGINE_RESULTS.glob("*.json")):
        aid = e_pfad.stem
        engine = _lade(e_pfad)
        if engine is None:
            continue
        d_pfad = RESULTS_DIR / f"{aid}.json"

        if d_pfad.exists():
            daten = _lade(d_pfad)
            if daten is None:
                continue
            if _version(engine) > _version(daten):
                bericht["engine_gewinnt"].append(aid)
            else:
                bericht["daten_gewinnt"].append(aid)
            continue

        # Nur im Engine-Stamm: mit Ground Truth gehoert er in den Datenstamm.
        if aid in gt_ids:
            bericht["uebernehmen"].append(aid)
        else:
            bericht["archivieren"].append(aid)

    return bericht


def konflikte_schreiben(konflikte: list[dict]) -> None:
    zeilen = [
        "# Widersprechende Bewertungen aus der Stamm-Zusammenfuehrung",
        "",
        f"Erzeugt am {datetime.now(timezone.utc).strftime('%d.%m.%Y')} von "
        "`tools/staemme_zusammenfuehren.py`.",
        "",
        "Dieselbe Uebergangsnummer traegt in den beiden Staemmen ein anderes",
        "Urteil. Das ist eine Bewertung, keine Rechenaufgabe - deshalb steht",
        "sie hier statt im Ergebnis. **Bis zur Entscheidung gilt der Stand aus",
        "`daten/`.** Wer entscheidet, traegt das Urteil dort ein und streicht",
        "den Eintrag hier.",
        "",
        f"Offen: **{len(konflikte)}**",
        "",
    ]
    nach_datei: dict[str, list[dict]] = {}
    for k in konflikte:
        nach_datei.setdefault(k["datei"], []).append(k)

    for datei, eintraege in sorted(nach_datei.items()):
        e0 = eintraege[0]
        zeilen += [f"## `{datei}`", ""]
        for feld, wert in (("daten/", e0["updatedAt_daten"]),
                           ("engine/", e0["updatedAt_engine"])):
            if isinstance(wert, (int, float)):
                stand = datetime.fromtimestamp(wert).strftime("%d.%m.%Y %H:%M")
                zeilen.append(f"- zuletzt geaendert {feld}: {stand}")
        zeilen.append("")
        zeilen.append("| Uebergang | Stand `daten/` (gilt) | Stand `engine/` |")
        zeilen.append("|---|---|---|")
        for k in sorted(eintraege, key=lambda x: int(x["index"]) if str(x["index"]).isdigit() else 0):
            d = json.dumps(k["daten"], ensure_ascii=False)
            e = json.dumps(k["engine"], ensure_ascii=False)
            zeilen.append(f"| {k['index']} | `{d}` | `{e}` |")
        zeilen.append("")

    KONFLIKTE.write_text("\n".join(zeilen), encoding="utf-8")


def archiv_liesmich(anzahl_reports: int, anzahl_gt: int) -> None:
    ARCHIV.mkdir(parents=True, exist_ok=True)
    (ARCHIV / "LIESMICH.md").write_text(
        "\n".join([
            "# Zweiter Stamm, archiviert am 13.08.2026",
            "",
            "Hier lag bis zum 13.08.2026 ein zweiter Satz Ergebnisse und",
            "Bewertungen, parallel zum maszgeblichen Stamm in `daten/`.",
            "Entstanden ist er, weil `MIXCOACH_DATA_DIR` nicht gesetzt war:",
            "`app/paths.py` faellt dann auf den Engine-Ordner zurueck, und die",
            "App legt Library, Ergebnisse und Ground Truth am falschen Ort ab.",
            "",
            f"Inhalt: {anzahl_reports} Analyse-Reports, {anzahl_gt} Bewertungen.",
            "",
            "**Der Inhalt ist nicht verloren, sondern eingearbeitet.** Die",
            "abweichenden Bewertungen wurden mit `daten/ground_truth/`",
            "vereinigt (`tools/staemme_zusammenfuehren.py`); widersprechende",
            "Urteile stehen in `daten/ground_truth/KONFLIKTE.md` und warten auf",
            "eine Entscheidung.",
            "",
            "Dieser Ordner wird nicht mehr gelesen. Er bleibt liegen, damit die",
            "Zusammenfuehrung nachpruefbar ist. Wer ihn loeschen will, sollte",
            "vorher KONFLIKTE.md abgearbeitet haben.",
            "",
            "Die Audiodateien (`*.wav`) waren nie versioniert (.gitignore) und",
            "sind hier nicht mitgezogen worden.",
        ]), encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--write", action="store_true",
                   help="Zusammenfuehrung schreiben (ohne: nur Bericht)")
    # Bewusst ein ZWEITER Schalter, nicht Teil von --write.
    #
    # Das Verschieben ist der gefaehrliche Teil: fuenf Werkzeuge lesen den
    # zweiten Stamm direkt - tools/analyze_timing_bias.py:69 (die
    # Referenzmetrik selbst!), app/calibration/retrain_model.py:37
    # (LEGACY_RESULTS_DIR, dort liegt das Audio), tools/selbsttest.py:79,
    # tools/predictions_from_analyses.py:37 und tools/eval/gt_status.py:40.
    # Wer zuerst verschiebt und dann misst, kann nicht mehr unterscheiden, ob
    # die Zusammenfuehrung oder der fehlende Ordner die Zahl bewegt hat.
    #
    # Reihenfolge deshalb: --write, messen, Leser umstellen, --archivieren.
    p.add_argument("--archivieren", action="store_true",
                   help="zusaetzlich den zweiten Stamm ins Archiv verschieben "
                        "(erst nachdem die fuenf Leser umgestellt sind)")
    args = p.parse_args()

    print(f"Maszgeblich : {GROUND_TRUTH_DIR.parent}")
    print(f"Zweiter Stamm: {ENGINE_ROOT}\n")

    gt_neu, gt_bericht = ground_truth_zusammenfuehren()
    r_bericht = reports_einordnen()

    print("=== Ground Truth ===")
    print(f"  byteidentisch, nichts zu tun : {len(gt_bericht['unveraendert'])}")
    print(f"  zusammengefuehrt             : {len(gt_bericht['zusammengefuehrt'])}")
    print(f"  nur im zweiten Stamm         : {len(gt_bericht['nur_engine'])}")
    for name in gt_bericht["zusammengefuehrt"]:
        print(f"    + {name}")
    if gt_bericht["nahe_paare"]:
        print(f"\n  HINWEIS - nahe missed-Paare (beide bleiben, volle Union):")
        for name, x, y, abstand in gt_bericht["nahe_paare"]:
            print(f"    {name}: {x} (daten) vs {y} (engine) - {abstand} s auseinander")
    print(f"\n  WIDERSPRUECHE (gehen nach KONFLIKTE.md): {len(gt_bericht['konflikte'])}")
    for k in gt_bericht["konflikte"]:
        print(f"    {k['datei']} Uebergang {k['index']}")

    print("\n=== Analyse-Reports ===")
    print(f"  in beiden, daten/ gewinnt : {len(r_bericht['daten_gewinnt'])}")
    print(f"  in beiden, engine gewinnt : {len(r_bericht['engine_gewinnt'])}")
    print(f"  nur engine, MIT Bewertung -> uebernehmen : {len(r_bericht['uebernehmen'])}")
    for aid in r_bericht["uebernehmen"]:
        print(f"    + {aid}")
    print(f"  nur engine, ohne Bewertung -> Archiv     : {len(r_bericht['archivieren'])}")

    if not args.write:
        print("\nNur Bericht. Zum Schreiben --write anhaengen.")
        return 0

    for name, inhalt in gt_neu.items():
        ziel = GROUND_TRUTH_DIR / name
        # Zeilenenden der Vorlage behalten. Die Dateien stammen aus der
        # Windows-Zeit und tragen CRLF; mit LF neu geschrieben gilt in git
        # JEDE Zeile als geaendert - aus einem zusaetzlichen missed-Wert
        # werden 331 Diff-Zeilen, und niemand kann mehr nachsehen, was
        # wirklich passiert ist. Ausserdem haengt der Schluessel des
        # Feature-Caches am Byte-Inhalt dieser Dateien
        # (retrain_model._gt_stamp): andere Zeilenenden heisst unnoetiger
        # Neuaufbau ueber das echte Audio.
        roh = ziel.read_bytes() if ziel.exists() else b""
        zeilenende = "\r\n" if b"\r\n" in roh else "\n"
        text = json.dumps(inhalt, ensure_ascii=False, indent=1)
        if roh.endswith(b"\n"):
            text += "\n"
        ziel.write_text(text, encoding="utf-8", newline=zeilenende)
    if gt_bericht["konflikte"]:
        konflikte_schreiben(gt_bericht["konflikte"])
        print(f"\nKonflikte notiert -> {KONFLIKTE}")

    for aid in r_bericht["uebernehmen"]:
        shutil.copy2(ENGINE_RESULTS / f"{aid}.json", RESULTS_DIR / f"{aid}.json")

    print(f"\nZusammengefuehrt. Der zweite Stamm liegt unveraendert an seinem Platz.")
    if not args.archivieren:
        print("Zum Verschieben --archivieren anhaengen - vorher die fuenf Leser "
              "umstellen (siehe --help).")
        return 0

    ARCHIV.mkdir(parents=True, exist_ok=True)
    for unterordner, quelle in (("analysis_results", ENGINE_RESULTS),
                                ("ground_truth", ENGINE_GT)):
        if quelle.exists():
            ziel = ARCHIV / unterordner
            if ziel.exists():
                print(f"  {ziel} gibt es schon - nicht angefasst.")
                continue
            shutil.move(str(quelle), str(ziel))
    archiv_liesmich(len(list((ARCHIV / "analysis_results").glob("*.json"))),
                    len(list((ARCHIV / "ground_truth").glob("*.json"))))

    print(f"\nGeschrieben. Zweiter Stamm liegt jetzt unter {ARCHIV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
