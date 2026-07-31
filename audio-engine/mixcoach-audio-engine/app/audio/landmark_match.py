"""Spektral-Peak-/Landmark-Fingerprinting (Shazam-Prinzip) - KOMPLEMENTAER
zum Chroma-Matching in library_match.py.

Warum ergaenzend: das Chroma-Verfahren (Harmonieverlauf) erkennt tonale
Tracks sehr gut, scheitert aber strukturell an harmonisch STATISCHER Musik
(Minimal/Techno mit konstanter Harmonie) - dort ist die zeitliche Chroma-
Ableitung Rauschen, echte Tracks scoren wie Zufall (gemessen 2026-07-15:
4 von 40 Benchmark-Tracks, alle mit NULL Grobsuche-Peaks). Landmark-Hashing
nutzt stattdessen markante Zeit-Frequenz-PEAKS - die sind auch bei statischer
Harmonie einzigartig pro Aufnahme.

Voraussetzung/Grenze: robust gegen TEMPO-Stretch (Zeit-Deltas werden im
Offset-Histogramm mit Toleranz gebinnt), aber NICHT gegen echtes Pitch-
Shifting (Vinyl-Pitch verschiebt die Frequenz-Bins). DJ-Sets mit Keylock/
Master-Tempo (nur Tempo, Tonhoehe erhalten) sind abgedeckt; reine Vinyl-
Pitch-Sets sind eine bekannte Grenze fuer v1.

Speicherformat je Track (kompakt, fuer den Index):
    hashes:  uint32-Array gepackter (f1,f2,dt)-Hashes
    frames:  int64-Array der Anker-Frames (parallel zu hashes)

Frames waren bis 2026-07-30 uint16. Das deckt nur Frame-Index 65535 ab,
bei HOP=512/SR=22050 also 1521.7 s = 25:22 Audio. Fuer Library-Tracks
reicht das (build_landmark_index kappt bei 360 s = Frame 15502), aber
fingerprint() laeuft auch ueber GANZE MIXES - jede Aufnahme in
daten/analysis_results ist 28-120 min lang, lief also ueber: unter
numpy 2 mit OverflowError, unter numpy 1 still modulo 65536. Der stille
Fall war der gefaehrlichere - umgeklappte Anker-Frames haetten das
Offset-Histogramm in match() fuer alles nach 25:22 verschmiert.

int64 statt uint32, obwohl schon uint32 reichen wuerde (4.3e9 Frames =
27 Jahre): Frames gehen ausschliesslich als DIFFERENZ in match() ein,
und die ist legitim negativ (Track startet vor dem Mix-Ausschnitt) -
ein vorzeichenbehafteter Typ ist hier der richtige, und er nimmt der
Rechnung die Unsigned-Wrap-Falle. Kostet nach npz-Kompression nur
+1.7 % Dateigroesse (gemessen an 25 Library-.npz), weil die fuehrenden
Nullbytes wegkomprimieren.

Bestehende .npz in daten/library/lm/ brauchen KEINE Migration: sie
liefern weiterhin uint16-Frames, und match() hebt beide Seiten vor der
Subtraktion explizit nach int64. Der gemischte Fall (uint16 von Platte,
int64 im Speicher) ist der Normalfall, nicht der Ausnahmefall.
"""

from __future__ import annotations

import time as _time
from collections import defaultdict

import numpy as np

N_FFT = 2048
HOP = 512                      # ~23ms bei 22050 Hz
SR = 22050
PEAKS_PER_FRAME = 3            # dichteste Peaks je Zeitschritt
FANOUT = 5                     # Ziel-Peaks je Anker
TARGET_DT_MIN, TARGET_DT_MAX = 1, 30   # Frames Abstand Anker->Ziel (~0.02-0.7s)
OFFSET_BIN = 5                 # Frames pro Offset-Histogramm-Bin (Stretch-Toleranz)
FREQ_BINS = N_FFT // 2 + 1     # 1025

# Hash-Packung: f1 (11 bit) | f2 (11 bit) | dt (5 bit, 1..30 passt in 5 bit).
_F_BITS, _DT_BITS = 11, 5
_F_MASK = (1 << _F_BITS) - 1
_DT_MASK = (1 << _DT_BITS) - 1


def _pack(f1: int, f2: int, dt: int) -> int:
    return ((f1 & _F_MASK) << (_F_BITS + _DT_BITS)) | ((f2 & _F_MASK) << _DT_BITS) | (dt & _DT_MASK)


def constellation(waveform: np.ndarray, sr: int = SR) -> list[tuple[int, int]]:
    """(frame, freq_bin) der lokalen Spektral-Peaks - die 'Konstellation'."""
    import librosa
    S = np.abs(librosa.stft(waveform, n_fft=N_FFT, hop_length=HOP))
    logS = np.log1p(S)
    peaks: list[tuple[int, int]] = []
    for f in range(logS.shape[1]):
        col = logS[:, f]
        if col.max() < 1e-3:
            continue
        idx = np.where((col[1:-1] > col[:-2]) & (col[1:-1] > col[2:]))[0] + 1
        if len(idx) == 0:
            continue
        strongest = idx[np.argsort(col[idx])[-PEAKS_PER_FRAME:]]
        for b in strongest:
            peaks.append((f, int(b)))
    return peaks


def fingerprint(waveform: np.ndarray, sr: int = SR) -> dict[str, np.ndarray]:
    """Kompakter Landmark-Fingerprint fuer die Index-Ablage."""
    peaks = constellation(waveform, sr)
    hashes, frames = _hash_arrays(peaks)
    return {"hashes": hashes.astype(np.uint32), "frames": frames.astype(np.int64)}


def _hash_arrays(peaks: list[tuple[int, int]]) -> tuple[np.ndarray, np.ndarray]:
    by_frame: dict[int, list[int]] = defaultdict(list)
    for fr, b in peaks:
        by_frame[fr].append(b)
    hashes: list[int] = []
    frames: list[int] = []
    for fr in sorted(by_frame):
        for b1 in by_frame[fr]:
            targets = 0
            for dt in range(TARGET_DT_MIN, TARGET_DT_MAX + 1):
                if targets >= FANOUT:
                    break
                for b2 in by_frame.get(fr + dt, []):
                    hashes.append(_pack(b1, b2, dt))
                    frames.append(fr)
                    targets += 1
                    if targets >= FANOUT:
                        break
    # frames als int64: Anker-Frames muessen die volle Mix-Laenge tragen
    # (>25:22, siehe Modul-Docstring). hashes bleiben uint32 - sie sind auf
    # 27 bit gepackt und wachsen nicht mit der Laufzeit.
    return np.asarray(hashes, dtype=np.uint32), np.asarray(frames, dtype=np.int64)


# Uebervolle Mix-Hash-Buckets kappen: ein Hash, der im Mix hunderte Male
# vorkommt (tieffrequentes Dauerrauschen), traegt keine Ortsinformation,
# blaeht aber das Offset-Histogramm massiv auf. Standard-Praxis bei
# Landmark-Verfahren. Der Wert begrenzt zugleich die Worst-Case-Laufzeit.
MAX_BUCKET = 64


def prepare_mix(mix_fp: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Mix-Fingerprint einmal nach Hash sortieren (fuer den searchsorted-
    Join in match) - bei vielen Track-Vergleichen gegen denselben Mix
    spart das das wiederholte Sortieren. Enthaelt zusaetzlich die
    EINDEUTIGEN Hash-Werte fuer den billigen Screen (siehe screen_score)."""
    order = np.argsort(mix_fp["hashes"], kind="stable")
    hashes = np.asarray(mix_fp["hashes"])[order]
    return {"hashes": hashes,
            "frames": np.asarray(mix_fp["frames"])[order],
            "unique_hashes": np.unique(hashes),
            "_sorted": np.True_}


def screen_score(mix_unique_hashes: np.ndarray, track_fp: dict[str, np.ndarray]) -> int:
    """Billiger Vorfilter-Score: Anzahl EINDEUTIGER Hash-Werte, die Mix und
    Track teilen (kein Offset-Histogramm, keine Gruppen-Expansion). Rein
    empirisch ~195x guenstiger als match() (1.7ms vs. 332ms/Track,
    2026-07-16) - kann darum ueber die GANZE Library laufen, bevor der
    teure volle Abgleich nur auf die vielversprechendsten Kandidaten
    angewendet wird. Analog zum Screen-Vorfilter in library_match.py."""
    return int(np.intersect1d(mix_unique_hashes, np.unique(track_fp["hashes"]),
                              assume_unique=True).size)


def match(mix_fp: dict[str, np.ndarray], track_fp: dict[str, np.ndarray]) -> dict:
    """Gleicht Mix- gegen Track-Fingerprint ab. Rueckgabe:
        peak    - Hoehe des staerksten Offset-Bins (Anzahl kohaerenter Hashes)
        offset_frames - geschaetzter Versatz (Track-Anfang im Mix), in Frames
        n_shared - Gesamtzahl gemeinsamer Hashes (diffus + kohaerent)
        dominance - peak / zweitstaerkster Bin (Schaerfe des Einrastens)
    Ein hoher, DOMINANTER peak bei einem Offset = Track laeuft dort;
    diffuse gemeinsame Hashes ohne klaren Peak = Zufall.

    Vektorisiert (Sortier-Join + arithmetische Gruppen-Expansion) - die
    urspruengliche Python-Doppelschleife brauchte MINUTEN pro Vergleich
    (bei haeufigen Hashes Milliarden Iterationen; ein 8-Mix-Benchmark
    haette ~40h gebraucht, gemessen abgebrochen 2026-07-15)."""
    if mix_fp.get("_sorted"):
        mh, mf = mix_fp["hashes"], mix_fp["frames"]
    else:
        prepared = prepare_mix(mix_fp)
        mh, mf = prepared["hashes"], prepared["frames"]
    th = np.asarray(track_fp["hashes"])
    tf = np.asarray(track_fp["frames"])
    if len(th) == 0 or len(mh) == 0:
        return {"peak": 0, "offset_frames": 0, "n_shared": 0, "dominance": 0.0}

    left = np.searchsorted(mh, th, side="left")
    right = np.searchsorted(mh, th, side="right")
    counts = right - left
    counts = np.minimum(counts, MAX_BUCKET)  # uebervolle Buckets kappen
    keep = counts > 0
    if not keep.any():
        return {"peak": 0, "offset_frames": 0, "n_shared": 0, "dominance": 0.0}

    k = counts[keep]
    starts = left[keep]
    total = int(k.sum())
    # Gruppen-Expansion ohne Python-Schleife: fuer Gruppe i die Indizes
    # starts[i] .. starts[i]+k[i]-1.
    within = np.arange(total) - np.repeat(np.cumsum(k) - k, k)
    idx = np.repeat(starts, k) + within
    # Die beiden .astype(np.int64) BITTE STEHEN LASSEN. mf kommt aus einem
    # frisch gerechneten Mix-Fingerprint (int64), tf meist aus einer alten
    # .npz mit uint16-Frames (siehe Modul-Docstring). In genau dieser
    # Paarung waeren die Casts zwar entbehrlich (numpy promotet int64-uint16
    # selbst nach int64), aber sie sind das, was die Rechnung UNABHAENGIG
    # von den Operanden-Typen macht: treffen zwei gleiche unsigned Typen
    # aufeinander - zwei Fingerprints von Platte, oder haetten wir statt
    # int64 uint32 gewaehlt -, bleibt die Differenz unsigned, und der
    # legitim NEGATIVE Fall (Track startet vor dem Mix-Ausschnitt) klappt
    # still auf einen riesigen positiven Wert um: uint16(10)-uint16(20)
    # = 65526. Das waere ein falscher Offset-Bin, kein Fehler.
    delta = (mf[idx].astype(np.int64) - np.repeat(tf[keep].astype(np.int64), k)) // OFFSET_BIN

    bins, bin_counts = np.unique(delta, return_counts=True)
    top = int(np.argmax(bin_counts))
    peak = int(bin_counts[top])
    # Dominanz = Peak ueber dem RAUSCH-BODEN (Mittel der uebrigen Bins), NICHT
    # Peak/zweitbester: bei dichten Offset-Histogrammen (viele gemeinsame
    # Hashes durch Kollisionen im 27-bit-Raum) sind benachbarte Bins fast
    # gleich hoch -> peak/second ~1, obwohl der echte Offset klar ueber dem
    # diffusen Boden liegt (gemessen an Boratto: peak 15700, Boden ~1000 ->
    # echte Dominanz ~15, waehrend peak/second nur 1.05 war, 2026-07-15).
    floor = (total - peak) / max(1, len(bin_counts) - 1)
    return {
        "peak": peak,
        "offset_frames": int(bins[top]) * OFFSET_BIN,
        "n_shared": total,
        "dominance": peak / max(1.0, floor),
    }


def frames_to_seconds(frames: int) -> float:
    return frames * HOP / SR


# Mindest-Offset-Peak UND Mindest-Dominanz (Peak / Rausch-Boden), ab denen
# ein Landmark-Treffer akzeptiert wird. BEWUSST KONSERVATIV: am Subset-
# Benchmark (2026-07-15, 50 Fremd-Tracks) gemessen liegen echte Fremd-Tracks
# durchweg bei Peak<=5250 / Dominanz<=8.7; der klar trennbare Zielfall
# (Boratto: 15700 / 18.6) liegt weit darueber. Century/void_23/orisa sind
# NICHT sicher trennbar (echt kaum ueber bzw. sogar unter dem besten Fremd-
# Track) - ein aggressiverer Schwellenwert wuerde die Precision-1.0-
# Eigenschaft brechen (Vision-Saeule "radikale Ehrlichkeit"). Diese
# Schwellen holen daher nur die extremsten harmonisch-statischen Faelle
# sicher, ohne Fehlalarme. Bei voller Library (6113) steigt das Fremd-Maximum
# tendenziell -> vor Produktivschaltung an echtem Full-Scale-Index nachmessen.
LANDMARK_MIN_PEAK = 8000
LANDMARK_MIN_DOMINANCE = 10.0
GAP_MIN_SECONDS = 60.0        # nur echte Luecken fuellen, keine Mini-Restspalten
GAP_OVERLAP_TOLERANCE = 0.5   # so viel Ueberlapp mit Chroma-Treffern ist ok (Blend)

# VERWORFEN (2026-07-16): ein zweistufiger Screen wie in library_match.py
# (screen_score = Anzahl gemeinsamer EINDEUTIGER Hashes, ~195x guenstiger
# als match()) wurde versucht, aber GEMESSEN FALSCH befunden - Boratto
# (der einzige sicher trennbare Zielfall, Dominanz 18.6) lag im Screen auf
# Rang 2773 von 6113, weit ausserhalb jeder sinnvollen Top-K-Grenze (Rang
# 500 brauchte Score 12478, Boratto hatte nur 8667). Rohe Hash-ANZAHL
# korreliert nicht mit einem echten Treffer - "lautere"/dichtere Fremd-
# Tracks erzeugen durch Zufalls-Kollisionen im 27-bit-Hash-Raum mehr
# geteilte Hashes als der leisere, aber echte Treffer. screen_score() bleibt
# im Modul (als Werkzeug fuer kuenftige Experimente), wird hier aber NICHT
# mehr verwendet - ein schneller, aber nachweislich falscher Filter ist
# schlechter als ein langsamer, korrekter (Vision-Saeule "radikale
# Ehrlichkeit").
#
# Stattdessen: Zeitbudget als harte Sicherheits-Obergrenze GEGEN
# PATHOLOGISCHE FAELLE (z.B. eine kaputte/riesige Library) - bewusst
# GROSSZUEGIG, kein primaeres Latenz-Werkzeug: bei willkuerlicher Abbruch-
# Reihenfolge wuerde ein KNAPPES Budget einen Treffer an schlechter Rang-
# Position (wie Boratto, Rang 2773 von 6113 im verworfenen Screen) einfach
# zufaellig verpassen - kein echter Fix, nur eine andere Form von Zufall.
# Der gemessene Normalfall bei einer echten Luecke liegt bei ~2000s (6113
# Tracks * ~330ms) - das Budget deckt das grosszuegig ab. DESHALB ist
# gap_fill() NICHT im Live-Analyse-Pfad verdrahtet (siehe pipeline.py) -
# fuer eine Live-Antwort ist auch der Normalfall hier zu langsam. Ein
# echter, GEMESSEN validierter Vorfilter ist ein offener Folge-Schritt.
LANDMARK_TIME_BUDGET_SECONDS = 2400.0


def _uncovered_spans(covered: list[tuple[float, float]], set_len_seconds: float) -> list[tuple[float, float]]:
    """Zeitspannen von [0, set_len], die von KEINEM Chroma-Treffer belegt
    sind - sortiert nach Start."""
    if not covered:
        return [(0.0, set_len_seconds)]
    merged = sorted(covered)
    spans = []
    cursor = 0.0
    for cs, ce in merged:
        if cs > cursor:
            spans.append((cursor, cs))
        cursor = max(cursor, ce)
    if cursor < set_len_seconds:
        spans.append((cursor, set_len_seconds))
    return spans


def gap_fill(mix_fp: dict, landmark_index: dict[str, dict],
             chroma_matches: list[dict], set_len_seconds: float) -> list[dict]:
    """Landmark-Treffer NUR in Zeitluecken, die der Chroma-Matcher leer
    liess. Chroma bleibt primaer (Precision), Landmark hebt den Recall bei
    harmonisch statischen Tracks. Rueckgabe: zusaetzliche Treffer im
    library_match-Format (start/end/score/id/title/artist/path).

    Kostenschranke: kein match()-Aufruf, wenn ueberhaupt keine Luecke
    >= GAP_MIN_SECONDS existiert (haeufigster Fall: Chroma deckt das ganze
    Set ab) - ein einzelner match()-Aufruf kostet ~190ms bei realistischer
    Groesse, ueber 6113 Tracks ungefiltert ~19 Minuten PRO SET (gemessen
    2026-07-15).

    FRUEHER gab es hier zusaetzlich einen Dauer-Vorfilter (Track laenger
    als die Luecke -> ueberspringen). Der war FALSCH und wurde entfernt: er
    ging von "der ganze Track muss in die Luecke passen" aus, aber Tracks
    werden im Set nur TEILWEISE gespielt (dieselbe Annahme wie in
    library_match.py/MIN_OVERLAP_SHARE) - er hat dadurch echte Treffer
    verworfen, wenn der Track laenger als sein gespielter Ausschnitt war
    (gefunden am Boratto-Fall: Track ~400s, gespielter Ausschnitt nur 262s -
    der Vorfilter schloss ihn faelschlich aus, 2026-07-16). Half nebenbei
    auch kaum gegen die Laufzeit (die meisten Library-Tracks sind kuerzer
    als eine typische Luecke, der Filter liess sie also ohnehin durch) - die
    verbleibende Kosten-Frage (mehrminuetiges Matching bei einer echten
    Erkennungsluecke) ist als offener Folge-Punkt dokumentiert, nicht durch
    einen falschen Vorfilter kaschiert."""
    covered = [(m["start"], m["end"]) for m in chroma_matches]
    gaps = [g for g in _uncovered_spans(covered, set_len_seconds)
            if g[1] - g[0] >= GAP_MIN_SECONDS]
    if not gaps:
        return []

    mix_sorted = prepare_mix(mix_fp)

    def in_gap(start: float, end: float) -> bool:
        span = max(1.0, end - start)
        for cs, ce in covered:
            if min(end, ce) - max(start, cs) > GAP_OVERLAP_TOLERANCE * span:
                return False
        return True

    # Volle Suche ueber die Library, hart begrenzt durch ein Zeitbudget
    # (nicht durch eine Kandidaten-Heuristik - siehe LANDMARK_TIME_BUDGET_
    # SECONDS-Docstring oben). Wird das Budget ueberschritten, bricht die
    # Suche ehrlich ab (moeglicherweise unvollstaendiger Recall fuer DIESE
    # Luecke), statt unbegrenzt weiterzulaufen ODER durch einen falschen
    # Vorfilter Genauigkeit vorzutaeuschen.
    deadline = _time.monotonic() + LANDMARK_TIME_BUDGET_SECONDS
    cands: list[dict] = []
    for tid, tfp in landmark_index.items():
        if _time.monotonic() > deadline:
            break
        dur = float(tfp.get("duration") or 0.0)
        if dur < GAP_MIN_SECONDS:
            continue  # Track kann nie GAP_MIN_SECONDS liefern - unabhaengig
            # von der Luecken-Groesse (Tracks werden nur TEILWEISE gespielt,
            # ein laengerer Track KANN in eine kuerzere Luecke passen -
            # siehe Docstring oben, deshalb keine obere Dauer-Schranke hier).
        res = match(mix_sorted, tfp)
        if res["peak"] < LANDMARK_MIN_PEAK or res["dominance"] < LANDMARK_MIN_DOMINANCE:
            continue
        start = max(0.0, frames_to_seconds(res["offset_frames"]))
        end = min(set_len_seconds, start + dur)
        if end - start < GAP_MIN_SECONDS or not in_gap(start, end):
            continue
        cands.append({"id": tid, "title": tfp.get("title"), "artist": tfp.get("artist"),
                      "path": tfp.get("path"), "start": start, "end": end,
                      "score": float(res["peak"]), "source": "landmark"})

    # Greedy nach Peak: kein Track doppelt, Landmark-Treffer untereinander
    # nicht stark ueberlappend.
    accepted: list[dict] = []
    for c in sorted(cands, key=lambda x: -x["score"]):
        span = max(1.0, c["end"] - c["start"])
        if all(min(c["end"], a["end"]) - max(c["start"], a["start"]) <= GAP_OVERLAP_TOLERANCE * span
               for a in accepted):
            accepted.append(c)
    return accepted
