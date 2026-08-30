"""Tracknamen aus der Tracklist des DJs statt aus dem Fingerabdruck (A3).

WARUM ES DIESES MODUL GIBT
--------------------------
Am 27.08.2026 gemessen, getrennt nach eigenen und fremden Sets:

    Uebergaenge mit Tracknamen    eigenes Set 56 %    fremdes Set 0 %

Null Prozent, nicht "wenige". Das ist keine Panne, sondern Bauart: der
Fingerabdruck-Index kennt 6113 Tracks - Sebastians. Ein fremder DJ spielt
fremde Tracks, also greift der Abgleich gar nicht.

Im Report steht dann neunmal "Uebergang 7" statt "Amelie Lens -> FJAAK".
Genau dieser Satz ist in PRODUKTVISION.md das Versprechen, und ohne ihn ist
der Report fuer einen Fremden kaum zu lesen.

DER WEG DRUMHERUM
-----------------
Die Tracks fremd zu fingerprinten hiesse: der DJ laedt seine Sammlung hoch.
Fuer einen ersten Test ist das eine unmoegliche Bitte. Aber fast jeder DJ hat
eine TRACKLIST - aus der rekordbox-History, aus Notizen, aus dem
Set-Beschreibungstext. Die kostet ihn eine Datei, keine 300.

ZWEI FAELLE, UND SIE SIND VERSCHIEDEN VIEL WERT
-----------------------------------------------
1. MIT ZEITEN ("00:00 Track A / 05:42 Track B / ..."). Jeder Uebergang wird
   der Trackgrenze zugeordnet, die zeitlich am naechsten liegt. Robust auch
   dann, wenn die Engine einen Uebergang uebersehen hat oder einen zu viel
   gefunden hat.

2. NUR REIHENFOLGE ("Track A / Track B / ..."). Dann geht die Zuordnung nur,
   wenn die Zahlen zusammenpassen: n Tracks brauchen n-1 Uebergaenge. Passt
   es nicht, wird NICHTS zugeordnet.

   Das ist der Kern dieses Moduls. Nach Position zu raten, wenn ein Uebergang
   fehlt, verschiebt ALLE folgenden Namen um eins - und dann steht unter
   jedem Uebergang ein falscher, aber selbstbewusster Trackname. Das ist
   derselbe Fehler wie die Sekundenangabe, die wir gerade durch ein Fenster
   ersetzt haben: lieber keine Angabe als eine falsche.

Woher ein Name stammt, steht in `detection`: "fingerprint" (gemessen) oder
"tracklist" (vom DJ genannt). Der Unterschied gehoert in den Report - das
eine hat das Werkzeug erkannt, das andere hat der Mensch behauptet.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

# "01:23", "1:23:45", "1.23" am Zeilenanfang, optional mit Trenner danach.
_ZEIT = re.compile(r"^\s*\[?(\d{1,2})[:.](\d{2})(?:[:.](\d{2}))?\]?\s*[-–—.)\]]?\s*")
# Fuehrende Nummerierung: "1.", "01)", "12 -"
_NUMMER = re.compile(r"^\s*\d{1,2}\s*[.)\-–]\s+")


def _zeit_und_titel(zeile: str) -> Tuple[Optional[float], str]:
    """(Sekunden oder None, Titel) aus einer Tracklist-Zeile."""
    treffer = _ZEIT.match(zeile)
    if treffer:
        a, b, c = treffer.group(1), treffer.group(2), treffer.group(3)
        # "1:23:45" = h:m:s, "05:42" = m:s
        sek = (int(a) * 3600 + int(b) * 60 + int(c)) if c else (int(a) * 60 + int(b))
        return float(sek), zeile[treffer.end():].strip()
    return None, _NUMMER.sub("", zeile).strip()


def lesen(text: str) -> List[Dict]:
    """Eine Tracklist als Liste von {'sec': float|None, 'titel': str}.

    Leerzeilen und offensichtliche Ueberschriften fallen weg. Reihenfolge
    bleibt, wie sie dasteht - sie ist die eigentliche Information.
    """
    raus: List[Dict] = []
    for zeile in (text or "").splitlines():
        if not zeile.strip():
            continue
        sek, titel = _zeit_und_titel(zeile)
        # Nur wirklich leere Zeilen fallen weg. Eine Mindestlaenge waere
        # gegriffen: es gibt Tracks, die "U" oder "9" heissen, und einen
        # Namen wegzuwerfen ist schlimmer als eine Muellzeile mitzunehmen -
        # die faellt beim Zuordnen ohnehin auf.
        if not titel:
            continue
        raus.append({"sec": sek, "titel": titel})
    return raus


def zuordnen(transitions: List[Dict], tracks: List[Dict]) -> Dict:
    """Haengt track_out/track_in an die Uebergaenge. Liefert einen Bericht.

    Aendert nichts, wo bereits ein Fingerabdruck-Treffer steht - gemessen
    schlaegt genannt.
    """
    bericht = {"tracks": len(tracks), "uebergaenge": len(transitions or []),
               "zugeordnet": 0, "weg": None, "grund": None}
    if len(tracks) < 2 or not transitions:
        bericht["grund"] = "zu wenige Angaben"
        return bericht

    mit_zeit = [t for t in tracks if t["sec"] is not None]
    offen = [t for t in (transitions or []) if not t.get("track_in") and not t.get("track_out")]

    if len(mit_zeit) >= 2:
        bericht["weg"] = "zeiten"
        # Jeder Uebergang bekommt die Trackgrenze, die zeitlich am naechsten
        # liegt. Die Grenze zwischen Track i und i+1 ist der Startzeitpunkt
        # von Track i+1.
        grenzen = [(t["sec"], mit_zeit[i - 1]["titel"], t["titel"])
                   for i, t in enumerate(mit_zeit) if i > 0]
        for u in offen:
            anker = u.get("start_sec")
            if not isinstance(anker, (int, float)):
                anker = u.get("mid_sec")
            if not isinstance(anker, (int, float)):
                continue
            sek, raus_titel, rein_titel = min(grenzen, key=lambda g: abs(g[0] - anker))
            u["track_out"] = raus_titel
            u["track_in"] = rein_titel
            u["detection"] = "tracklist"
            bericht["zugeordnet"] += 1
        return bericht

    # Nur Reihenfolge: die Zahlen muessen zusammenpassen, sonst nichts.
    if len(tracks) != len(transitions) + 1:
        bericht["weg"] = "reihenfolge"
        bericht["grund"] = (
            f"{len(tracks)} Tracks brauchen {len(tracks)-1} Uebergaenge, "
            f"gefunden wurden {len(transitions)} - ohne Zeiten laesst sich das "
            f"nicht sicher zuordnen. Nach Position zu raten wuerde ALLE "
            f"folgenden Namen um eins verschieben.")
        return bericht

    bericht["weg"] = "reihenfolge"
    for i, u in enumerate(transitions):
        if u.get("track_in") or u.get("track_out"):
            continue
        u["track_out"] = tracks[i]["titel"]
        u["track_in"] = tracks[i + 1]["titel"]
        u["detection"] = "tracklist"
        bericht["zugeordnet"] += 1
    return bericht
