"""Library-Fingerprinting: erkennt, WELCHER Track WANN im Set laeuft.

Idee: Jeder Track wird als grobe Chroma-Sequenz (Harmonieverlauf ueber die
Zeit) gespeichert - ein "Fingerabdruck". Beim Set-Vergleich wird der
Fingerabdruck per FFT-Kreuzkorrelation ueber das ganze Set geschoben,
in mehreren Tempo-Varianten (DJs pitchen +-8%). Wo er stark einrastet,
laeuft der Track. Aus den Zeitspannen aufeinanderfolgender Tracks ergeben
sich Uebergaenge nahezu exakt - inklusive echter Tracknamen.

Robust gegen: Tempo-Anpassung (Stretch-Suche), EQ/Blends an den Raendern
(Score mittelt ueber die ganze Track-Laenge), Lautstaerke (Frames sind
normalisiert). Nicht abgedeckt (v1): Tonart-Pitching ohne Master-Tempo.
"""

from __future__ import annotations

import numpy as np

# 512er-Hop -> Faktor 16 -> effektiv 8192 Samples pro Frame (ca. 2.7 fps bei 22050 Hz)
FP_DECIMATE = 16
STRETCHES = (0.92, 0.94, 0.96, 0.98, 1.0, 1.02, 1.04, 1.06, 1.08)
MIN_OVERLAP_SECONDS = 90.0   # absolute Untergrenze gemeinsamer Spielzeit
MIN_OVERLAP_SHARE = 0.15     # Grobsuche: kleiner Anteil reicht (Tracks werden nur TEILWEISE gespielt)
MIN_PLAYED_SECONDS = 90.0    # so lange muss ein Track nachweislich im Set laufen
PLAY_SIM_THRESHOLD = 0.22    # ab dieser (geglaetteten) Frame-Aehnlichkeit gilt: laeuft
PLAY_GAP_SECONDS = 15.0      # kurze Einbrueche (EQ/Blend) unterbrechen den Lauf nicht
TOP_OFFSETS = 8              # so viele Grob-Kandidaten werden pro Track verfolgt
MIN_SCORE = 0.32             # Fenster-Score-Schwelle. Urspruenglich 0.40 an EINER Aufnahme (REC001)
# kalibriert ("echte ~0.54-0.72, Fremde <=0.23"). Der Synth-Mix-Benchmark
# (tools/benchmark_fingerprint.py, 2026-07-14) zeigte echte Treffer bei
# 0.34-0.44, die 0.40 knapp verfehlten (korrekt lokalisiert, nur unter der
# Schwelle) - Fremd-Tracks lagen weiterhin klar darunter; darum zunaechst
# auf 0.30 gesenkt. Am ECHTEN Set MixCoach2 (2026-07-17, Sebastians
# Ground Truth) produzierte 0.30 dann einen realen Fehlalarm EXAKT auf der
# Schwelle ("Atjazz - In Code", Score 0.30, laut DJ lief dort durchgehend
# Rana - der falsche Treffer zerteilte Ranas Spanne und blockierte die
# Segment-Verlaengerung). 0.32 eliminiert genau diesen Fall und laesst die
# gemessenen echten Grenz-Treffer (0.34+) unangetastet.
PRE_SCORE = 0.10             # Grobsuche-Schwelle, ab der feinjustiert wird
PEAK_MIN_DISTANCE_SECONDS = 45.0  # Mindestabstand zwischen zwei Grob-Kandidaten derselben Tempo-Variante
MAX_BLEND_OVERLAP = 120.0    # laengere Ueberlappung wird als Blend-Ende gekappt

# --- Geschaetzte Uebergaenge in Erkennungs-Luecken ---
# Deckt der Fingerprint nur Teile beider Tracks ab, bleibt zwischen "Track A
# erkannt" und "Track B erkannt" oft eine unerkannte Luecke. Ist sie groesser
# als GAP_ESTIMATE_SECONDS, ist die genaue Uebergangsposition IN der Luecke
# unsicher - der Trackwechsel selbst aber eine gemessene Tatsache (zwei
# verschiedene Fingerprints). Frueher wurde ein solcher Uebergang komplett
# verschwiegen (zwei benannte Tracks OHNE Marker dazwischen); jetzt wird er
# gesetzt und ehrlich als "Position geschaetzt" markiert (Vision: radikale
# Ehrlichkeit - lieber den sicheren Wechsel mit Unsicherheits-Hinweis zeigen
# als ihn verstecken).
GAP_ESTIMATE_SECONDS = 30.0  # ab hier ist die Position in der Luecke unsicher
LARGE_GAP_SECONDS = 120.0    # so grosse Luecken koennen einen unerkannten Track enthalten
ESTIMATE_WINDOW = 15.0       # +/- Fenster um die geschaetzte Luecken-Mitte (Listen/Anzeige)

# Zweistufige Suche bei grossen Libraries: ein billiger Vorfilter
# (Screen) waehlt Kandidaten, nur die bekommen die volle FFT-Pruefung.
SCREEN_POOL = 8              # zusaetzliche Verdichtung fuer den Vorfilter
SCREEN_TEMPLATE_FRAMES = 20  # ~60s Track-Mitte als Suchschablone
SCREEN_STRETCHES = (0.93, 1.0, 1.07)
# Gemessen am Synth-Mix-Benchmark (tools/benchmark_fingerprint.py, 8 Mixes,
# 40 Ground-Truth-Tracks, 6113er-Library, 2026-07-14): der Median-Rang
# echter Tracks im Screen ist 4, aber die Verteilung hat einen langen
# Schwanz (p90=575, max=1741). Bei K=250 ueberlebten nur 85% der echten
# Tracks den Vorfilter - nachweislich verlorene Treffer, die die volle
# Pruefung bestanden haetten (z.B. Score 0.55 bei Rang 282). K=2000 behielt
# im Benchmark 100%. Kostet ~8x Matching-Zeit (~8s -> ~60s pro Set), was
# gegen den Vision-Anspruch "nahezu exakte Erkennung" nachrangig ist;
# Tempo-Optimierung ist ein eigener Roadmap-Punkt (A5).
SCREEN_TOP_K = 2000
SCREEN_MIN_LIBRARY = 400     # darunter lohnt der Vorfilter nicht


def decimate_chroma(chroma: np.ndarray, factor: int = FP_DECIMATE) -> np.ndarray:
    """Feines Chroma (12 x N) -> grobes, frame-normalisiertes Chroma (12 x N//factor)."""
    n = chroma.shape[1] // factor
    if n == 0:
        return np.zeros((12, 0))
    coarse = chroma[:, : n * factor].reshape(12, n, factor).mean(axis=2)
    norms = np.linalg.norm(coarse, axis=0, keepdims=True)
    return coarse / np.maximum(norms, 1e-9)


def _whiten(coarse: np.ndarray) -> np.ndarray:
    """Zeitliche Ableitung der Chroma-Sequenz, frame-normalisiert.

    Tonale Musik korreliert ueberall hoch (gleiche Tonart = aehnliche
    Frames) - die AENDERUNG der Harmonie ueber die Zeit ist dagegen pro
    Track einzigartig. Erst dadurch trennt der Score echte Treffer (~0.6)
    sauber von Fremd-Tracks (~0.1).
    """
    d = np.diff(coarse, axis=1)
    norms = np.linalg.norm(d, axis=0, keepdims=True)
    return d / np.maximum(norms, 1e-9)


def _stretch_time(chroma: np.ndarray, factor: float) -> np.ndarray:
    """Chroma zeitlich strecken/stauchen (Tempo-Varianten), Frames re-normalisieren."""
    n = chroma.shape[1]
    new_n = max(4, int(round(n * factor)))
    old_x = np.arange(n)
    new_x = np.linspace(0, n - 1, new_n)
    out = np.vstack([np.interp(new_x, old_x, chroma[b]) for b in range(12)])
    norms = np.linalg.norm(out, axis=0, keepdims=True)
    return out / np.maximum(norms, 1e-9)


def _prepare_set(set_coarse: np.ndarray) -> dict:
    """Set einmal vorbereiten: Whitening + FFT-Cache pro Transformlaenge."""
    white = _whiten(set_coarse)
    return {"white": white, "ffts": {}}


def _set_fft(prepared: dict, nfft: int) -> np.ndarray:
    cached = prepared["ffts"].get(nfft)
    if cached is None:
        cached = np.fft.rfft(prepared["white"], nfft, axis=1)
        prepared["ffts"][nfft] = cached
    return cached


def _refine_match(set_white: np.ndarray, track_coarse: np.ndarray,
                  stretch0: float, start_frame0: int, min_overlap: int) -> dict | None:
    """Feinjustierung um einen Grobtreffer: Tempo in 0.25%-Schritten,
    Offset in +-6 Frames. Noetig, weil das grobe 2%-Raster bei langen
    Tracks um viele Frames driftet und den Score echter Treffer zerstoert.
    Zufallstreffer profitieren von der Justierung praktisch nicht."""
    m = set_white.shape[1]
    best = None
    for ds in np.arange(-0.0175, 0.01751, 0.0025):
        stretch = stretch0 + ds
        tw = _whiten(_stretch_time(track_coarse, stretch))
        n = tw.shape[1]
        required = max(min_overlap, int(MIN_OVERLAP_SHARE * n))
        for dj in range(-6, 7):
            start = start_frame0 + dj
            a = max(0, start)
            b = min(m, start + n)
            if b - a < required:
                continue
            seg_set = set_white[:, a:b]
            seg_trk = tw[:, a - start: b - start]
            score = float((seg_set * seg_trk).sum() / (b - a))
            if best is None or score > best["score"]:
                best = {"score": round(score, 4), "stretch": round(stretch, 4),
                        "start_frame": start, "n": n}
    return best


def _played_window(set_white: np.ndarray, track_white: np.ndarray,
                   start_frame: int, fps: float):
    """Findet das tatsaechlich GESPIELTE Teilstueck des Tracks im Set.

    DJs spielen selten den ganzen Track (Uebergang alle 2-4 Minuten bei
    6-9-Minuten-Tracks). Bewertet wird deshalb nur das laengste Stueck,
    in dem die Frame-Aehnlichkeit anhaltend hoch ist - das liefert
    zugleich exakte Ein-/Ausstiegszeiten.
    Rueckgabe: (set_start_frame, set_end_frame, fenster_score) oder None.
    """
    m = set_white.shape[1]
    n = track_white.shape[1]
    a = max(0, start_frame)
    b = min(m, start_frame + n)
    if b - a < int(MIN_PLAYED_SECONDS * fps):
        return None
    contrib = (set_white[:, a:b] * track_white[:, a - start_frame: b - start_frame]).sum(axis=0)
    k = max(3, int(5 * fps))
    smooth = np.convolve(contrib, np.ones(k) / k, mode="same")

    active = smooth >= PLAY_SIM_THRESHOLD
    # aktive Laeufe sammeln, kurze Luecken (EQ/Blend-Einbrueche) verschmelzen
    runs = []
    run_start = None
    for i, flag in enumerate(np.append(active, False)):
        if flag and run_start is None:
            run_start = i
        elif not flag and run_start is not None:
            runs.append([run_start, i])
            run_start = None
    if not runs:
        return None
    max_gap = int(PLAY_GAP_SECONDS * fps)
    merged = [runs[0]]
    for r in runs[1:]:
        if r[0] - merged[-1][1] <= max_gap:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    best_run = max(merged, key=lambda r: r[1] - r[0])
    r0, r1 = best_run
    if (r1 - r0) < int(MIN_PLAYED_SECONDS * fps):
        return None
    score = float(contrib[r0:r1].mean())
    return a + r0, a + r1, round(score, 4)


def match_track(set_coarse: np.ndarray, track_coarse: np.ndarray, fps: float,
                prepared: dict | None = None) -> dict | None:
    """Bester Treffer eines Tracks im Set - oder None, wenn nicht ueberzeugend.

    Vektorisiert: alle Tempo-Varianten und alle 12 Chroma-Baender laufen
    in EINEM FFT-Batch; die Set-FFT wird ueber alle Tracks wiederverwendet.
    """
    min_overlap = int(MIN_OVERLAP_SECONDS * fps)
    if set_coarse.shape[1] < min_overlap + 1 or track_coarse.shape[1] < min_overlap + 1:
        return None

    if prepared is None:
        prepared = _prepare_set(set_coarse)
    m = prepared["white"].shape[1]

    # Alle Stretch-Varianten bauen (gewhitent, zeitlich gespiegelt fuer
    # Korrelation-per-Faltung) und auf gemeinsame Laenge bringen.
    variants = [_whiten(_stretch_time(track_coarse, s))[:, ::-1] for s in STRETCHES]
    lengths = [v.shape[1] for v in variants]
    n_max = max(lengths)
    size_max = m + n_max - 1
    nfft = 1 << (size_max - 1).bit_length()

    stack = np.zeros((len(variants), 12, n_max))
    for i, v in enumerate(variants):
        stack[i, :, : v.shape[1]] = v

    fa = _set_fft(prepared, nfft)                      # (12, nfft/2+1)
    fb = np.fft.rfft(stack, nfft, axis=2)              # (V, 12, nfft/2+1)
    corr = np.fft.irfft(fa[None] * fb, nfft, axis=2).sum(axis=1)  # (V, size)

    candidates_all: list = []
    for v_idx, (stretch, n) in enumerate(zip(STRETCHES, lengths)):
        size = m + n - 1
        idx = np.arange(size)
        overlap = np.minimum(np.minimum(idx + 1, size - idx), min(m, n))
        # Rand-Artefakte verhindern: ein echter Treffer muss einen
        # nennenswerten Teil des Tracks im Set gespielt haben.
        required = max(min_overlap, int(MIN_OVERLAP_SHARE * n))
        valid = overlap >= required
        if not valid.any():
            continue
        scores = np.where(valid, corr[v_idx, :size] / np.maximum(overlap, 1), -1.0)
        # Top-Offsets dieser Tempo-Variante einsammeln (lokale Maxima mit
        # Mindestabstand) - bei Teil-Plays gewinnt global oft der falsche.
        work = scores.copy()
        min_dist = max(1, int(PEAK_MIN_DISTANCE_SECONDS * fps))
        for _ in range(3):
            j = int(np.argmax(work))
            peak = float(work[j])
            if peak <= PRE_SCORE:
                break
            candidates_all.append((peak, stretch, j - n + 1))
            work[max(0, j - min_dist): j + min_dist] = -1.0

    if not candidates_all:
        return None

    # Die besten Grob-Kandidaten verfolgen: feinjustieren (2%-Raster
    # driftet bei langen Tracks) und jeweils das GESPIELTE Fenster suchen.
    candidates_all.sort(key=lambda c: -c[0])
    best_hit = None
    for coarse_score, stretch, start_frame in candidates_all[:TOP_OFFSETS]:
        refined = _refine_match(prepared["white"], track_coarse,
                                stretch, start_frame,
                                int(MIN_OVERLAP_SECONDS * fps))
        use_stretch, use_start = ((refined["stretch"], refined["start_frame"])
                                  if refined is not None and refined["score"] >= coarse_score
                                  else (stretch, start_frame))
        track_white = _whiten(_stretch_time(track_coarse, use_stretch))
        window = _played_window(prepared["white"], track_white, use_start, fps)
        if window is None:
            continue
        w0, w1, wscore = window
        if best_hit is None or wscore > best_hit["score"]:
            best_hit = {
                "score": wscore,
                "stretch": use_stretch,
                "start": w0 / fps,
                "end": w1 / fps,
                "track_offset": max(0.0, (w0 - use_start) / fps),
            }
    if best_hit is None or best_hit["score"] < MIN_SCORE:
        return None
    return best_hit


def _pool(coarse: np.ndarray, factor: int) -> np.ndarray:
    n = coarse.shape[1] // factor
    if n == 0:
        return coarse[:, :0]
    pooled = coarse[:, : n * factor].reshape(12, n, factor).mean(axis=2)
    norms = np.linalg.norm(pooled, axis=0, keepdims=True)
    return pooled / np.maximum(norms, 1e-9)


def _screen_score(set_pooled_white: np.ndarray, track_coarse: np.ndarray) -> float:
    """Billiger Vorfilter: beste mittlere Aehnlichkeit einer kurzen,
    stark verdichteten Schablone aus der Track-Mitte. Kein FFT."""
    pooled = _pool(track_coarse, SCREEN_POOL)
    if pooled.shape[1] < SCREEN_TEMPLATE_FRAMES + 6:
        return float("inf")  # zu kurz fuer den Filter -> immer voll pruefen
    m = set_pooled_white.shape[1]
    if m < SCREEN_TEMPLATE_FRAMES + 2:
        return float("inf")

    windows = np.lib.stride_tricks.sliding_window_view(
        set_pooled_white, SCREEN_TEMPLATE_FRAMES, axis=1,
    )  # (12, M-T+1, T)

    best = -1.0
    for stretch in SCREEN_STRETCHES:
        t = _whiten(_stretch_time(pooled, stretch))
        n = t.shape[1]
        # 3 Schablonen (vorne/Mitte/hinten): DJs spielen oft nur einen Teil.
        for pos in (0.2, 0.5, 0.8):
            a = int(pos * n) - SCREEN_TEMPLATE_FRAMES // 2
            a = max(0, min(n - SCREEN_TEMPLATE_FRAMES, a))
            tpl = t[:, a: a + SCREEN_TEMPLATE_FRAMES]
            if tpl.shape[1] < SCREEN_TEMPLATE_FRAMES:
                continue
            scores = np.einsum("bwt,bt->w", windows, tpl) / SCREEN_TEMPLATE_FRAMES
            best = max(best, float(scores.max()))
    return best


def _prefilter_candidates(set_coarse: np.ndarray, fingerprints: list[dict]) -> list[dict]:
    """Stufe 1 (nur bei grossen Libraries): billiger Vorfilter waehlt die
    aussichtsreichsten Kandidaten fuer die teure FFT-Vollpruefung.

    Tracks, die _screen_score NICHT bewerten kann (zu kurz -> inf), werden
    IMMER durchgelassen (die volle FFT-Pruefung entscheidet dann). Frueher
    schob das Minus-Sortierschluessel (`-inf`) genau diese Tracks ans ENDE
    und schnitt sie damit weg - das exakte Gegenteil der Absicht "zu kurz
    fuer den Filter -> immer voll pruefen". Ist das ganze SET zu kurz zum
    Screenen, geben ALLE Tracks inf zurueck -> gar kein Vorfilter (korrekt).
    """
    if len(fingerprints) <= SCREEN_MIN_LIBRARY:
        return list(fingerprints)

    set_pooled = _whiten(_pool(set_coarse, SCREEN_POOL))
    always_keep: list[dict] = []
    scored: list[tuple[float, dict]] = []
    for fp in fingerprints:
        s = _screen_score(set_pooled, np.asarray(fp["chroma"], dtype=np.float64))
        if not np.isfinite(s):
            always_keep.append(fp)
        else:
            scored.append((s, fp))

    scored.sort(key=lambda item: -item[0])
    budget = max(0, SCREEN_TOP_K - len(always_keep))
    return always_keep + [fp for _, fp in scored[:budget]]


def match_library(set_chroma_fine: np.ndarray, fingerprints: list[dict],
                  sample_rate: int, hop_length: int = 512) -> list[dict]:
    """Alle Library-Tracks gegen das Set matchen.

    fingerprints: [{"id","title","artist","chroma": ndarray 12xN (grob, normiert)}]
    Liefert akzeptierte, zeitlich sortierte Treffer (jeder Track max. einmal,
    Ueberlappung untereinander begrenzt).
    """
    fps = sample_rate / (hop_length * FP_DECIMATE)
    set_coarse = decimate_chroma(set_chroma_fine)
    set_len = set_coarse.shape[1] / fps
    prepared = _prepare_set(set_coarse)

    pool = _prefilter_candidates(set_coarse, fingerprints)

    candidates = []
    for fp in pool:
        hit = match_track(set_coarse, np.asarray(fp["chroma"], dtype=np.float64), fps,
                          prepared=prepared)
        if hit is not None:
            hit.update({"id": fp.get("id"), "title": fp.get("title"),
                        "artist": fp.get("artist"), "path": fp.get("path")})
            candidates.append(hit)

    # Greedy nach Score: kein Track doppelt, Spannen duerfen sich nur im
    # Blend-Rahmen ueberlappen (sonst widersprechen sich zwei Treffer).
    accepted: list[dict] = []
    for cand in sorted(candidates, key=lambda c: -c["score"]):
        span = max(1.0, cand["end"] - cand["start"])
        clash = 0.0
        for a in accepted:
            clash = max(clash, min(cand["end"], a["end"]) - max(cand["start"], a["start"]))
        if clash > min(MAX_BLEND_OVERLAP, 0.5 * span):
            continue
        accepted.append(cand)

    accepted.sort(key=lambda c: c["start"])
    # Auf Set-Grenzen kappen (erster/letzter Track ragt oft hinaus).
    for a in accepted:
        a["start"] = max(0.0, a["start"])
        a["end"] = min(set_len, a["end"])
    return accepted


# Segment-Zweitpass: Annahme-Regeln, kalibriert an den 4 realen
# MixCoach2-Luecken mit Sebastians Ground-Truth-Tracklist (2026-07-17):
#   echte Tracks gewannen ihr Segment mit 0.453-0.686 und 1.6-2.3x Abstand
#   zum Zweitplatzierten (Bashmore 0.504/1.59x, Rana 0.686/1.71x,
#   Trago 0.453/2.34x); der einzige unentscheidbare Fall (Dalfie, Rang 2,
#   0.273 hinter 0.299 = 1.09x) wird von BEIDEN Regeln korrekt abgelehnt -
#   lieber ehrlich "unbekannt" als ein falscher Trackname.
SEGMENT_MIN_SCORE = 0.35
SEGMENT_MIN_MARGIN = 1.25
SEGMENT_MIN_GAP_SECONDS = 120.0  # kuerzere Luecken sind meist nur Blend-Raender


def _best_segment_match(set_coarse: np.ndarray, a: float, b: float, fps: float,
                        fingerprints: list[dict]) -> tuple[dict, dict, float] | None:
    """Bester Library-Treffer INNERHALB des Zeitfensters [a, b] (Sekunden).
    Rueckgabe (hit, fp, second_score) oder None, wenn kein Kandidat die
    Annahme-Regeln (SEGMENT_MIN_SCORE + SEGMENT_MIN_MARGIN) erfuellt. Der
    Margin-Check (Abstand zum Zweitplatzierten) schuetzt die Precision:
    lieber ehrlich unbenannt als ein knapper Fehlname."""
    a_f, b_f = int(a * fps), int(b * fps)
    seg = set_coarse[:, a_f:b_f]
    if seg.shape[1] < int(MIN_PLAYED_SECONDS * fps):
        return None
    prepared = _prepare_set(seg)
    pool = _prefilter_candidates(seg, fingerprints)
    scored: list[tuple[float, dict, dict]] = []
    for fp in pool:
        hit = match_track(seg, np.asarray(fp["chroma"], dtype=np.float64), fps,
                          prepared=prepared)
        if hit is not None:
            scored.append((hit["score"], hit, fp))
    if not scored:
        return None
    scored.sort(key=lambda x: -x[0])
    best_score, best_hit, best_fp = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0
    if best_score < SEGMENT_MIN_SCORE:
        return None
    if second_score > 0 and best_score / second_score < SEGMENT_MIN_MARGIN:
        return None
    return best_hit, best_fp, second_score


def rematch_from_boundaries(set_chroma_fine: np.ndarray, boundaries: list[float],
                            fingerprints: list[dict], sample_rate: int,
                            hop_length: int = 512) -> list[dict]:
    """Nachmatchen anhand VOM DJ korrigierter Uebergangsgrenzen.

    Das ist die Vision-Daten-Schleife in Reinform: die Korrekturen im
    Report ("Uebergang startet woanders" / "hier fehlte einer") liefern die
    EXAKTEN Track-Grenzen. Zwischen zwei aufeinanderfolgenden Grenzen laeuft
    genau ein Track - dieses praezise Segment gewinnt der echte Track auch
    dann, wenn der automatische Zweitpass an unsauberen Luecken-Grenzen
    scheiterte (gemessen 2026-07-17: Bashmore verfehlte die automatische
    Luecke 3:05-8:15 komplett - sie enthielt ~40% Fremdmaterial -, gewann
    aber sein korrigiertes Segment 2:27-6:30 mit Rang 1 / Score 0.504).

    boundaries: sortierte Uebergangszeitpunkte in Sekunden (korrigierte +
    nachgemeldete, OHNE die als Fehlalarm verworfenen). Rueckgabe: Treffer
    je Segment im library_match-Format (nur die, die die Annahme-Regeln
    erfuellen; jeder Track hoechstens einmal, staerkster Score gewinnt)."""
    fps = sample_rate / (hop_length * FP_DECIMATE)
    set_coarse = decimate_chroma(set_chroma_fine)
    set_len = set_coarse.shape[1] / fps

    edges = [0.0] + sorted(t for t in boundaries if 0.0 < t < set_len) + [set_len]
    hits: list[dict] = []
    for a, b in zip(edges[:-1], edges[1:]):
        if b - a < MIN_PLAYED_SECONDS:
            continue
        res = _best_segment_match(set_coarse, a, b, fps, fingerprints)
        if res is None:
            continue
        hit, fp, _ = res
        hits.append({
            "id": fp.get("id"), "title": fp.get("title"),
            "artist": fp.get("artist"), "path": fp.get("path"),
            "start": max(a, a + hit["start"]), "end": min(b, a + hit["end"]),
            "score": hit["score"], "stretch": hit.get("stretch"),
            "source": "rematch",
        })

    # Kein Track doppelt: bei Kollision gewinnt der staerkere Score.
    best_by_path: dict[str, dict] = {}
    for h in hits:
        p = h.get("path")
        if p not in best_by_path or h["score"] > best_by_path[p]["score"]:
            best_by_path[p] = h
    return sorted(best_by_path.values(), key=lambda m: m["start"])


def fill_gaps_by_segment(set_chroma_fine: np.ndarray, accepted: list[dict],
                         fingerprints: list[dict], sample_rate: int,
                         hop_length: int = 512) -> list[dict]:
    """Zweitpass: unbenannte Zeitluecken einzeln nachmatchen.

    Der Voll-Set-Matcher muss ein anhaltendes Fenster IRGENDWO im ganzen
    Set finden - auf schwierigem Material (lange EQ-Kills, Loops, statische
    Passagen) verliert er Tracks, die ein auf die LUECKE begrenzter
    Vergleich klar gewinnt (gemessen 2026-07-17 an MixCoach2: 3 der 4
    unbenannten Luecken-Tracks gewannen ihr Segment mit Rang 1 und
    deutlichem Abstand, obwohl der Voll-Match sie komplett verfehlte).

    Precision-Schutz: ein Segment-Treffer wird NUR akzeptiert, wenn er die
    Mindest-Score-Schwelle erreicht UND mit klarem Abstand vor dem
    Zweitplatzierten liegt (SEGMENT_MIN_SCORE/SEGMENT_MIN_MARGIN) - sonst
    bleibt die Luecke ehrlich unbenannt.

    Rueckgabe: die KOMPLETTE, zeitlich sortierte Treffer-Liste (uebernommene
    + neue Segment-Treffer; Fenster-Fortsetzungen desselben Tracks werden in
    den bestehenden Treffer hineinverlaengert statt dupliziert).
    """
    fps = sample_rate / (hop_length * FP_DECIMATE)
    set_coarse = decimate_chroma(set_chroma_fine)
    set_len = set_coarse.shape[1] / fps

    # Luecken zwischen akzeptierten Treffern (inkl. Set-Anfang/-Ende) -
    # mit Nachbar-Treffern, damit Fenster-Fortsetzungen erkennbar sind.
    ordered = sorted(accepted, key=lambda x: x["start"])
    gaps: list[tuple[float, float, dict | None, dict | None]] = []
    cursor = 0.0
    left: dict | None = None
    for m in ordered:
        if m["start"] - cursor >= SEGMENT_MIN_GAP_SECONDS:
            gaps.append((cursor, m["start"], left, m))
        cursor = max(cursor, m["end"])
        left = m
    if set_len - cursor >= SEGMENT_MIN_GAP_SECONDS:
        gaps.append((cursor, set_len, left, None))
    if not gaps:
        return list(ordered)

    taken_paths = {m.get("path") for m in ordered}
    merged: list[dict] = [dict(m) for m in ordered]
    for a, b, left_m, right_m in gaps:
        res = _best_segment_match(set_coarse, a, b, fps, fingerprints)
        if res is None:
            continue
        best_hit, best_fp, _ = res
        best_path = best_fp.get("path")
        start = max(a, a + best_hit["start"])
        end = min(b, a + best_hit["end"])

        # Derselbe Track wie der Luecken-Nachbar? Dann ist das die
        # FORTSETZUNG eines zu frueh abgebrochenen Fensters (real gemessen:
        # Rana lief 11:09-17:45, der Voll-Match fand nur 11:24-14:07 - das
        # Segment 15:34-17:48 gewann Rana mit 0.686) -> Spanne verlaengern
        # statt Duplikat anlegen. Ein NICHT angrenzender Duplikat-Treffer
        # bleibt verboten (derselbe Track laeuft nicht zweimal im Set).
        if best_path in taken_paths:
            neighbor = None
            if left_m is not None and left_m.get("path") == best_path:
                neighbor = left_m
            elif right_m is not None and right_m.get("path") == best_path:
                neighbor = right_m
            if neighbor is None:
                continue
            for m in merged:
                if m.get("path") == best_path:
                    m["start"] = min(m["start"], start)
                    m["end"] = max(m["end"], end)
                    m["score"] = max(m["score"], best_hit["score"])
                    break
            continue

        merged.append({
            "id": best_fp.get("id"), "title": best_fp.get("title"),
            "artist": best_fp.get("artist"), "path": best_path,
            "start": start, "end": end,
            "score": best_hit["score"],
            "stretch": best_hit.get("stretch"),
            "source": "segment",
        })
        taken_paths.add(best_path)

    merged.sort(key=lambda m: m["start"])
    return merged


def transitions_from_matches(matches: list[dict]) -> list[dict]:
    """Aus den Track-Zeitspannen die Uebergaenge ableiten.

    Blend-Start = der neue Track wird hoerbar (Start seiner Spanne).
    Blend-Ende = der alte Track verschwindet (Ende seiner Spanne).

    Bei einer Luecke (unerkannter Abschnitt zwischen zwei erkannten Tracks)
    ist der Trackwechsel trotzdem sicher (zwei verschiedene Fingerprints) -
    nur die genaue Position IST unsicher. Statt den Uebergang zu verschweigen
    (frueher: kein Marker zwischen zwei benannten Tracks) wird er in die
    Luecken-Mitte gesetzt und mit position_estimated=True ehrlich als
    geschaetzt markiert; sehr grosse Luecken werden zusaetzlich als moeglicher
    unerkannter Zwischentrack gekennzeichnet.
    """
    transitions = []
    for prev, nxt in zip(matches, matches[1:]):
        gap = nxt["start"] - prev["end"]
        common = {
            "from_title": prev.get("title"),
            "from_artist": prev.get("artist"),
            "to_title": nxt.get("title"),
            "to_artist": nxt.get("artist"),
            "confidence": min(prev["score"], nxt["score"]),
        }
        if gap > GAP_ESTIMATE_SECONDS:
            # Luecke: Trackwechsel sicher, Position geschaetzt (Luecken-Mitte).
            mid = (prev["end"] + nxt["start"]) / 2.0
            half = min(gap / 2.0, ESTIMATE_WINDOW)
            transitions.append({
                **common,
                "blend_start": round(mid - half, 2),
                "mid": round(mid, 2),
                "blend_end": round(mid + half, 2),
                "position_estimated": True,
                "gap_seconds": round(gap, 1),
                "possible_unrecognized_track": gap > LARGE_GAP_SECONDS,
            })
            continue
        # Angrenzend/ueberlappend: exakte Fingerprint-Grenze (wie bisher).
        blend_start = max(prev["start"], nxt["start"])
        blend_end = min(prev["end"] + 5.0, blend_start + MAX_BLEND_OVERLAP)
        blend_end = max(blend_end, blend_start + 4.0)
        transitions.append({
            **common,
            "blend_start": round(blend_start, 2),
            "mid": round((blend_start + blend_end) / 2.0, 2),
            "blend_end": round(blend_end, 2),
            "position_estimated": False,
            "gap_seconds": round(max(gap, 0.0), 1),
            "possible_unrecognized_track": False,
        })
    return transitions


def merge_with_fingerprints(zones: list[dict], fp_transitions: list[dict],
                            matches: list[dict], tolerance: float = 105.0) -> list[dict]:
    """ML-Zonen mit Fingerprint-Uebergaengen zusammenfuehren.

    - Fingerprint-Uebergaenge sind massgeblich: nahe ML-Zonen werden auf
      die exakten Zeiten korrigiert, fehlende ergaenzt.
    - ML-Zonen MITTEN in einem erkannten Track sind Fehlalarme -> raus.
    - ML-Zonen in nicht zugeordneten Abschnitten bleiben (Fallback).
    """
    merged: list[dict] = []
    used: set[int] = set()

    for ft in fp_transitions:
        base: dict = {"score": 1.0, "signals": 3}
        for i, z in enumerate(zones):
            if i not in used and abs(float(z["time"]) - ft["mid"]) <= tolerance:
                base = dict(z)
                used.add(i)
                break
        base.update({
            "time": ft["mid"],
            "blend_start": ft["blend_start"],
            "blend_end": ft["blend_end"],
            "type": "fingerprint",
            "confidence": ft["confidence"],
            "from_title": ft.get("from_title"),
            "from_artist": ft.get("from_artist"),
            "to_title": ft.get("to_title"),
            "to_artist": ft.get("to_artist"),
            "position_estimated": ft.get("position_estimated", False),
            "gap_seconds": ft.get("gap_seconds"),
            "possible_unrecognized_track": ft.get("possible_unrecognized_track", False),
        })
        merged.append(base)

    for i, z in enumerate(zones):
        if i in used:
            continue
        t = float(z["time"])
        inside_track = any(m["start"] + 45.0 < t < m["end"] - 45.0 for m in matches)
        if not inside_track:
            merged.append(z)

    merged.sort(key=lambda z: float(z["time"]))
    return merged
