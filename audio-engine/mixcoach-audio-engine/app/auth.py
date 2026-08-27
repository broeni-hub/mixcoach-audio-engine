"""Zugangskontrolle der Engine (F2, erster Teil).

WARUM ES DIESES MODUL GIBT
--------------------------
Bis zum 27.08.2026 hatte die Engine **keine** Zugangskontrolle: kein
`Depends`, kein `HTTPBearer`, keine Auth-Middleware, CORS auf `*`. 25
Endpoints, einer davon `DELETE /analysis/{analysis_id}`.

Lokal ist das folgenlos - `MixCoach-Start-Mac.command` bindet die Engine an
127.0.0.1, sie ist von aussen gar nicht erreichbar. Genau deshalb ist es nie
aufgefallen. In dem Moment, wo sie gehostet wird, kann jeder, der die Adresse
kennt, jede Analyse lesen und loeschen. Der Befund stand in keinem
Projektdokument, bis er beim Review vom 25.08. auffiel.

DIE ENTSCHEIDUNG, DIE HIER GETROFFEN IST
----------------------------------------
Es gibt genau zwei Betriebsarten, und sie stehen in einer Umgebungsvariablen,
nicht in einer Konstante im Quelltext:

    MIXCOACH_AUTH=aus   keine Pruefung. Fuer den lokalen Betrieb an
                        127.0.0.1. VORGABE, weil das Frontend heute noch
                        keinen Token mitschickt - wer hier scharfstellt,
                        ohne das Frontend nachzuziehen, sperrt Sebastian aus
                        seiner eigenen App aus.
    MIXCOACH_AUTH=an    jeder Endpoint ausser der Freiliste verlangt ein
                        gueltiges Supabase-JWT im Authorization-Header.

**Kein versteckter Schalter.** Am 18.08. hat eine Anmeldung ohne Konto einen
halben Nachmittag gekostet, weil niemand sah, in welchem Zustand sie war.
Deshalb: `/health` nennt die Betriebsart, der Start schreibt sie ins
Protokoll, und der Selbsttest hat einen eigenen Abschnitt dafuer.

WIE GEPRUEFT WIRD
-----------------
Supabase signiert seine Tokens entweder asymmetrisch (ES256/RS256, oeffentliche
Schluessel unter /auth/v1/.well-known/jwks.json) oder symmetrisch (HS256 mit
dem Projekt-JWT-Secret). Beides wird unterstuetzt, und der asymmetrische Weg
ist der Vorzugsweg: er braucht **kein zusaetzliches Geheimnis** auf dem
Server. Nur SUPABASE_URL.

Was NICHT passiert: die Engine holt keine Nutzerdaten und fragt Supabase bei
keinem Aufruf. Sie prueft die Signatur gegen die zwischengespeicherten
oeffentlichen Schluessel und liest `sub`. Ein Netzaufruf faellt nur an, wenn
der Schluesselsatz fehlt oder eine unbekannte `kid` auftaucht.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Optional

import httpx
import jwt
from fastapi import HTTPException, Request
from jwt import PyJWKClient

# Pfade, die auch bei MIXCOACH_AUTH=an ohne Token erreichbar bleiben.
#
# /health muss offen sein: ein Lastverteiler oder ein Neustart-Waechter
# kann sich nicht anmelden, und die Antwort enthaelt nichts Persoenliches.
# Sonst nichts - eine Freiliste, die waechst, ist keine.
OFFENE_PFADE = frozenset({"/health", "/docs", "/openapi.json", "/redoc"})

# Der Nutzer, unter dem lokal gearbeitet wird. Derselbe Wert steht in 51 von
# 56 gespeicherten Reports; er darf sich nicht aendern, sonst findet die App
# ihre eigene Historie nicht mehr.
LOKALER_NUTZER = "local-single-user"

_jwks_client: Optional[PyJWKClient] = None
_jwks_lock = threading.Lock()


def betriebsart() -> str:
    """'an' oder 'aus'. Alles, was nicht 'an' ist, gilt als 'aus'."""
    return "an" if os.getenv("MIXCOACH_AUTH", "aus").strip().lower() == "an" else "aus"


def _supabase_url() -> str:
    url = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
    if not url:
        # Kein stiller Ausfall: ohne URL kann nicht geprueft werden, und
        # "kann nicht pruefen" darf nie "laesst durch" heissen.
        raise HTTPException(
            status_code=503,
            detail=("MIXCOACH_AUTH=an, aber SUPABASE_URL fehlt - die Engine "
                    "kann keine Tokens pruefen und laesst deshalb nichts durch."))
    return url


def _jwks() -> PyJWKClient:
    global _jwks_client
    with _jwks_lock:
        if _jwks_client is None:
            _jwks_client = PyJWKClient(
                f"{_supabase_url()}/auth/v1/.well-known/jwks.json",
                cache_keys=True, lifespan=3600)
        return _jwks_client


def _pruefe_token(token: str) -> dict:
    """Signatur pruefen und die Nutzdaten zurueckgeben. Wirft bei Zweifel."""
    geheimnis = (os.getenv("SUPABASE_JWT_SECRET") or "").strip()
    kopf = jwt.get_unverified_header(token)
    verfahren = kopf.get("alg")

    if verfahren == "HS256":
        if not geheimnis:
            raise HTTPException(
                status_code=503,
                detail=("Token ist HS256-signiert, aber SUPABASE_JWT_SECRET "
                        "fehlt - nicht pruefbar."))
        schluessel = geheimnis
    elif verfahren in ("RS256", "ES256"):
        try:
            schluessel = _jwks().get_signing_key_from_jwt(token).key
        except (httpx.HTTPError, jwt.PyJWKClientError) as fehler:
            raise HTTPException(
                status_code=503,
                detail=f"Schluesselsatz nicht erreichbar: {fehler}") from fehler
    else:
        raise HTTPException(status_code=401,
                            detail=f"Signaturverfahren {verfahren!r} wird nicht akzeptiert.")

    try:
        return jwt.decode(token, schluessel, algorithms=[verfahren],
                          audience="authenticated",
                          options={"require": ["exp", "sub"]})
    except jwt.ExpiredSignatureError as fehler:
        raise HTTPException(status_code=401, detail="Token abgelaufen.") from fehler
    except jwt.InvalidTokenError as fehler:
        # Der Grund gehoert in die Meldung. Am 18.08. hat eine Fehlermeldung,
        # die den falschen Grund nannte, einen Nachmittag gekostet.
        raise HTTPException(status_code=401,
                            detail=f"Token ungueltig: {fehler}") from fehler


async def nutzer(request: Request) -> str:
    """FastAPI-Abhaengigkeit: liefert die Nutzer-ID oder wirft 401.

    Haengt an der ganzen App (main.py), nicht an einzelnen Endpoints. Damit
    ist ein NEUER Endpoint automatisch geschuetzt - eine Liste, die man je
    Endpoint pflegen muss, laeuft frueher oder spaeter auseinander.
    """
    if request.url.path in OFFENE_PFADE:
        return LOKALER_NUTZER
    if betriebsart() == "aus":
        return LOKALER_NUTZER

    kopf = request.headers.get("Authorization") or ""
    if not kopf.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail="Kein Authorization: Bearer <token> mitgeschickt.")

    nutzdaten = _pruefe_token(kopf.split(" ", 1)[1].strip())
    kennung = nutzdaten.get("sub")
    if not kennung:
        raise HTTPException(status_code=401, detail="Token ohne sub.")
    request.state.nutzer = kennung
    return str(kennung)


def cors_urspruenge() -> list[str]:
    """Welche Herkuenfte der Browser benutzen darf.

    Bis zum 27.08.2026 stand hier ["*"]. Fuer eine Engine an 127.0.0.1 ist
    das folgenlos, fuer eine gehostete nicht. Vorgabe sind jetzt die
    localhost-Adressen, unter denen die App wirklich laeuft (Port 8080, siehe
    MixCoach-Start-Mac.command); alles andere wird ausdruecklich eingetragen.
    """
    gesetzt = (os.getenv("MIXCOACH_CORS_ORIGINS") or "").strip()
    if gesetzt:
        return [t.strip() for t in gesetzt.split(",") if t.strip()]
    return [
        "http://localhost:8080", "http://127.0.0.1:8080",
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:3000", "http://127.0.0.1:3000",
    ]


def startmeldung() -> str:
    """Was beim Start im Terminal steht. Der Zustand muss sichtbar sein."""
    if betriebsart() == "an":
        return ("[MixCoach Engine] Zugangskontrolle AN - jeder Endpoint ausser "
                f"{sorted(OFFENE_PFADE)} verlangt ein Supabase-JWT.")
    return ("[MixCoach Engine] Zugangskontrolle AUS - nur fuer den lokalen "
            "Betrieb an 127.0.0.1 gedacht. Vor dem Hosten MIXCOACH_AUTH=an "
            "setzen, sonst kann jeder jede Analyse lesen und loeschen.")
