"""Laeuft die ganze Kette ab und sagt, was WIRKLICH misst.

Warum es das gibt: am 11.08.2026 sind an einem Tag drei Dinge aufgefallen, die
wie ein Befund aussahen und keiner waren.

  1. MIXCOACH_ENABLE_STEM_SCORING haette nichts bewirkt und nichts gemeldet -
     torch und demucs waren gar nicht installiert, der ImportError lief in ein
     'except Exception: pass'.
  2. fit_composite_weights las per Vorgabe den veralteten Engine-Ordner und
     meldete "zu wenige gelabelte Uebergaenge, Sets muessten neu analysiert
     werden" - obwohl im Datenstamm alles vorlag.
  3. Die Cloud-Synchronisation der Historie scheiterte bei jedem Aufruf, weil
     ein Schluessel fehlte und niemand angemeldet war. Beide Fehler wurden
     verschluckt, die App sah aus als arbeite sie.

Dreimal derselbe Bauplan: ein stiller Ausfall, der sich als Datenproblem
tarnt. In einem Projekt, dessen Markenkern Ehrlichkeit ist, ist der
verschluckte Fehler die teuerste Codezeile - und er trifft nicht den DJ,
sondern den, der das Projekt weiterbaut.

Dieses Skript prueft deshalb nicht, ob der Code laeuft, sondern ob die
Voraussetzungen fuer jede Messung tatsaechlich gegeben sind. Es unterscheidet
streng zwischen "gemessen und Null" und "gar nicht gemessen".

Laeuft ohne Audio, ohne Netz, in Sekunden.

    python -m tools.selbsttest
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.paths import DATA_ROOT, GROUND_TRUTH_DIR, PROJECT_ROOT, RESULTS_DIR  # noqa: E402

OK, WARN, FEHLT = "  ok  ", " WARN ", " FEHLT"
_zaehler = {"ok": 0, "warn": 0, "fehlt": 0}


def sag(status: str, titel: str, detail: str = "", abhilfe: str = "") -> None:
    _zaehler["ok" if status == OK else "warn" if status == WARN else "fehlt"] += 1
    print(f"[{status}] {titel}")
    if detail:
        for zeile in detail.splitlines():
            print(f"          {zeile}")
    if abhilfe and status != OK:
        print(f"          -> {abhilfe}")


def abschnitt(name: str) -> None:
    print()
    print("=" * 74)
    print(f"  {name}")
    print("=" * 74)


# --------------------------------------------------------------------------
def pruefe_datenstamm() -> None:
    abschnitt("1 - Der Datenstamm")

    gesetzt = os.environ.get("MIXCOACH_DATA_DIR")
    if not gesetzt:
        sag(FEHLT, "MIXCOACH_DATA_DIR ist NICHT gesetzt",
            f"app/paths.py faellt auf den Engine-Ordner zurueck:\n{DATA_ROOT}",
            "export MIXCOACH_DATA_DIR=<Projektstamm>/daten - sonst sucht alles "
            "am falschen Ort")
    elif DATA_ROOT == PROJECT_ROOT:
        sag(WARN, "MIXCOACH_DATA_DIR zeigt auf den Engine-Ordner",
            str(DATA_ROOT), "sollte auf daten/ im Projektstamm zeigen")
    else:
        sag(OK, "Datenstamm", str(DATA_ROOT))

    # Der Doppelstamm-Klassiker: Ground Truth an zwei Orten.
    zweiter = PROJECT_ROOT / "ground_truth"
    hier = len(list(GROUND_TRUTH_DIR.glob("*.json"))) if GROUND_TRUTH_DIR.exists() else 0
    dort = len(list(zweiter.glob("*.json"))) if zweiter.exists() and zweiter != GROUND_TRUTH_DIR else 0
    if dort:
        sag(WARN, "Ground Truth liegt an ZWEI Orten",
            f"massgeblich: {hier} Dateien in {GROUND_TRUTH_DIR}\n"
            f"veraltet:    {dort} Dateien in {zweiter}",
            "beim Auswerten bewusst entscheiden, welcher Stand gilt (CLAUDE.md)")
    else:
        sag(OK, "Ground Truth", f"{hier} Dateien, ein Stamm")

    n_json = len(list(RESULTS_DIR.glob("*.json"))) if RESULTS_DIR.exists() else 0
    sag(OK if n_json else FEHLT, "Analyse-Reports", f"{n_json} JSONs in {RESULTS_DIR}",
        "ohne Reports kann nichts ausgewertet werden")


# --------------------------------------------------------------------------
def pruefe_modell() -> None:
    abschnitt("2 - Das Erkennungs-Modell")

    from app.audio.ml_classifier import MODEL_PATH

    if not MODEL_PATH.exists():
        sag(FEHLT, "Modell fehlt", str(MODEL_PATH), "MixCoach-Retrain-Jetzt.command")
        return
    try:
        m = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        sag(FEHLT, "Modell nicht lesbar", str(exc))
        return

    sel = m.get("selection") or {}
    val = m.get("loso_validation") or {}
    sag(OK, "Modell geladen",
        f"Betriebspunkt: min_p={sel.get('min_probability')}, "
        f"gap={sel.get('min_gap_seconds')}s\n"
        f"LOSO: R={val.get('recall')} P={val.get('precision')} F1={val.get('f1')}\n"
        f"trainiert auf: {m.get('trained_on')}")

    backup = MODEL_PATH.with_suffix(".json.backup")
    sag(OK if backup.exists() else WARN, "Rueckfall-Modell",
        "vorhanden" if backup.exists() else "kein .backup",
        "ohne Backup ist ein Retrain nicht umkehrbar")


# --------------------------------------------------------------------------
def pruefe_library() -> None:
    abschnitt("3 - Die Library (Burggraben 2)")

    from app.library.manager import INDEX_PATH, LIBRARY_DIR

    if not INDEX_PATH.exists():
        sag(FEHLT, "Library-Index fehlt", str(INDEX_PATH))
        return
    try:
        tracks = json.loads(INDEX_PATH.read_text(encoding="utf-8")).get("tracks", {})
    except Exception as exc:
        sag(FEHLT, "Index nicht lesbar", str(exc))
        return

    n_fp = len(list((LIBRARY_DIR / "fp").glob("*.npy"))) if (LIBRARY_DIR / "fp").exists() else 0
    n_lm = len(list((LIBRARY_DIR / "lm").glob("*.npz"))) if (LIBRARY_DIR / "lm").exists() else 0
    sag(OK, "Index", f"{len(tracks)} Tracks, {n_fp} Chroma-Fingerprints, {n_lm} Landmark")

    # Stichprobe: loesen die Pfade auf? Ein umgezogener Ordner faellt hier auf,
    # bevor ein Analyselauf still nichts findet.
    stichprobe = list(tracks.values())[:200]
    fehlend = sum(1 for t in stichprobe if not Path(t.get("path", "")).exists())
    if fehlend:
        sag(WARN, "Pfade der Stichprobe",
            f"{fehlend} von {len(stichprobe)} nicht auffindbar",
            "tools/repath_library_index.py - NIE einfach neu scannen "
            "(Track-IDs haengen am Pfad-String, CLAUDE.md)")
    else:
        sag(OK, "Pfade der Stichprobe", f"{len(stichprobe)} von {len(stichprobe)} auffindbar")


# --------------------------------------------------------------------------
def pruefe_stems() -> None:
    abschnitt("4 - Stem-Trennung (der stille Ausfall vom 11.08.)")

    fehlend = []
    for modul in ("torch", "demucs"):
        try:
            __import__(modul)
        except Exception:
            fehlend.append(modul)

    an = os.environ.get("MIXCOACH_ENABLE_STEM_SCORING", "0") != "0"
    if fehlend and an:
        sag(FEHLT, "Schalter ist AN, das Werkzeug fehlt",
            f"nicht installiert: {', '.join(fehlend)}\n"
            "harmonic_clash und vocal_overlap bleiben leer - ununterscheidbar "
            "von 'Schalter aus'",
            "pip install torch demucs")
    elif fehlend:
        sag(OK, "Stem-Trennung aus, Werkzeug fehlt",
            f"nicht installiert: {', '.join(fehlend)} - konsistent, "
            "solange der Schalter aus bleibt")
    elif an:
        sag(OK, "Stem-Trennung an und einsatzbereit", "torch + demucs vorhanden")
    else:
        sag(OK, "Stem-Trennung aus (Vorgabe seit 30.07.2026)",
            "torch + demucs waeren da. Gemessen am 11.08.: die beiden "
            "Stem-Dimensionen haben im Composite-Fit Gewicht 0,000 -\n"
            "das Einschalten kostet ~70 % Analysezeit und bringt nichts.")


# --------------------------------------------------------------------------
def pruefe_messwerte() -> None:
    abschnitt("5 - Was in den Reports wirklich befuellt ist")

    felder = ("quality_score", "composite_quality_score", "loudness_jump_db",
              "energy_dip_pct", "bass_overlap_score")
    zaehler = {f: 0 for f in felder}
    gesamt = 0
    for pfad in RESULTS_DIR.glob("*.json"):
        try:
            d = json.loads(pfad.read_text(encoding="utf-8"))
        except Exception:
            continue
        for t in d.get("setTransitions") or []:
            gesamt += 1
            for f in felder:
                if t.get(f) is not None:
                    zaehler[f] += 1

    if not gesamt:
        sag(WARN, "Keine Uebergaenge in den Reports")
        return

    zeilen = []
    for f in felder:
        anteil = 100 * zaehler[f] / gesamt
        zeilen.append(f"{f:<26} {zaehler[f]:>4}/{gesamt}  {anteil:>3.0f} %")
    duenn = [f for f in felder if zaehler[f] / gesamt < 0.5]
    sag(WARN if duenn else OK, f"Befuellung ueber {gesamt} Uebergaenge",
        "\n".join(zeilen),
        "unter 50 % heisst: der Wert fehlt in der Mehrheit der Uebergaenge "
        "und taugt nicht als Kopfzahl" if duenn else "")


# --------------------------------------------------------------------------
def pruefe_cloud() -> None:
    abschnitt("6 - Historie in der Cloud (Live-Schwelle, Bedingung 2)")

    env = PROJECT_ROOT.parent.parent / "Frontend" / ".env"
    if not env.exists():
        sag(FEHLT, "Frontend/.env fehlt", str(env),
            "aus Frontend/.env.example kopieren und Werte eintragen")
        return

    # NUR Schluesselnamen lesen, nie Werte - die gehoeren in keine Ausgabe.
    namen = set()
    for zeile in env.read_text(encoding="utf-8", errors="replace").splitlines():
        zeile = zeile.strip()
        if zeile and not zeile.startswith("#") and "=" in zeile:
            namen.add(zeile.split("=", 1)[0].strip())

    # Zwei verschiedene Schluessel, zwei verschiedene Wege - am 11.08.2026 habe
    # ich sie verwechselt und den Service-Role-Key als Blocker der Historie
    # gemeldet. Falsch: die sechs analyses-Funktionen laufen ueber
    # context.supabase aus requireSupabaseAuth, und das ist der PUBLISHABLE
    # Key plus das JWT des angemeldeten Nutzers - RLS-gedeckt
    # ("Users manage own analyses" USING auth.uid() = user_id).
    # Der Service-Role-Key umgeht RLS und wird nur von beta.functions.ts und
    # coach-feedback.functions.ts gebraucht.
    fehlend_hist = [k for k in ("SUPABASE_URL", "SUPABASE_PUBLISHABLE_KEY")
                    if k not in namen]
    if fehlend_hist:
        sag(FEHLT, "Schluessel fuer die Historie fehlen",
            f"nicht gesetzt: {', '.join(fehlend_hist)}\n"
            "Ohne sie wirft requireSupabaseAuth, und keine Analyse wird "
            "gespeichert.",
            "Supabase-Projekt -> Project Settings -> API")
    else:
        sag(OK, "Schluessel fuer die Historie gesetzt",
            "SUPABASE_URL + SUPABASE_PUBLISHABLE_KEY (Werte werden nicht "
            "angezeigt).\nDie sechs analyses-Funktionen brauchen nur diese - "
            "sie laufen RLS-gedeckt ueber das JWT des Nutzers.")

    if "SUPABASE_SERVICE_ROLE_KEY" not in namen:
        sag(WARN, "SUPABASE_SERVICE_ROLE_KEY fehlt",
            "Blockiert NICHT die Historie. Betroffen sind nur die "
            "Beta-Anmeldung (beta.functions.ts) und das Fehlerprotokoll in "
            "coach-feedback.functions.ts.",
            "nur eintragen, wenn eine dieser zwei Funktionen gebraucht wird - "
            "der Key umgeht Row Level Security")
    else:
        sag(OK, "SUPABASE_SERVICE_ROLE_KEY gesetzt", "(Wert wird nicht angezeigt)")

    app_tsx = PROJECT_ROOT.parent.parent / "Frontend" / "src" / "routes" / "app.tsx"
    if app_tsx.exists():
        text = app_tsx.read_text(encoding="utf-8", errors="replace")
        if "DEV_BYPASS_AUTH = true" in text:
            sag(FEHLT, "DEV_BYPASS_AUTH steht auf true - DER Blocker",
                "Der Sync-Aufruf steht HINTER einem 'if (DEV_BYPASS_AUTH) return'.\n"
                "Niemand meldet sich an -> kein authorization-Header ->\n"
                "requireSupabaseAuth wirft 'Unauthorized' -> jede der sechs\n"
                "analyses-Funktionen scheitert, und der Fehler wird gefangen.\n"
                "Alles andere fuer die Historie ist fertig und angebunden.",
                "auf false setzen - Preis: Anmeldung wird Pflicht, auch fuer dich")
        else:
            sag(OK, "DEV_BYPASS_AUTH ist aus", "Anmeldung wird verlangt, Sync laeuft")


# --------------------------------------------------------------------------
def main() -> int:
    print()
    print("MixCoach - Selbsttest")
    print("Prueft nicht, ob der Code laeuft, sondern ob die Voraussetzungen")
    print("fuer jede Messung tatsaechlich gegeben sind.")

    for pruefung in (pruefe_datenstamm, pruefe_modell, pruefe_library,
                     pruefe_stems, pruefe_messwerte, pruefe_cloud):
        try:
            pruefung()
        except Exception as exc:
            sag(FEHLT, f"{pruefung.__name__} selbst ist gescheitert",
                f"{type(exc).__name__}: {exc}")

    abschnitt("Ergebnis")
    print(f"  ok: {_zaehler['ok']}   WARN: {_zaehler['warn']}   FEHLT: {_zaehler['fehlt']}")
    print()
    if _zaehler["fehlt"]:
        print("  Jedes FEHLT bedeutet: an dieser Stelle wird NICHT gemessen,")
        print("  auch wenn der Rest des Systems normal aussieht.")
    else:
        print("  Keine stillen Ausfaelle gefunden.")
    print()
    return 1 if _zaehler["fehlt"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
