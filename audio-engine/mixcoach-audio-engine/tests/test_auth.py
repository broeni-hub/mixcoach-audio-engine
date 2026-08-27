"""Zugangskontrolle der Engine (app/auth.py).

Bis zum 27.08.2026 hatte die Engine keine: 25 Endpoints offen, darunter
DELETE /analysis/{id}, CORS auf "*". Lokal folgenlos, weil an 127.0.0.1
gebunden - und genau deshalb nie aufgefallen.

Der wichtigste Test ist test_ein_neuer_endpoint_ist_von_selbst_geschuetzt:
die Pruefung haengt an der ganzen App, nicht an einzelnen Endpoints. Faellt
er, ist jemand auf eine Liste je Endpoint umgestiegen - und die laeuft
auseinander.

Der zweitwichtigste ist test_lokal_bleibt_alles_wie_es_war: wer die
Zugangskontrolle einbaut und dabei Sebastian aus seiner eigenen App
aussperrt, hat den Fehler vom 18.08. wiederholt.
"""

import time

import jwt
import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app

client = TestClient(app)
GEHEIMNIS = "test-geheimnis-nur-fuer-diese-datei"


@pytest.fixture
def auth_an(monkeypatch):
    monkeypatch.setenv("MIXCOACH_AUTH", "an")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", GEHEIMNIS)
    monkeypatch.setenv("SUPABASE_URL", "https://beispiel.supabase.co")


def _token(**abweichend) -> str:
    nutzdaten = {"sub": "nutzer-4711", "aud": "authenticated",
                 "exp": int(time.time()) + 3600}
    nutzdaten.update(abweichend)
    return jwt.encode(nutzdaten, GEHEIMNIS, algorithm="HS256")


def _kopf(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# --- Die Vorgabe: lokal aendert sich nichts -------------------------------


def test_lokal_bleibt_alles_wie_es_war(monkeypatch):
    """Vorgabe ist 'aus'. Das Frontend schickt heute keinen Token - wer hier
    scharfstellt, ohne es nachzuziehen, sperrt den Nutzer aus."""
    monkeypatch.delenv("MIXCOACH_AUTH", raising=False)
    assert auth.betriebsart() == "aus"
    assert client.get("/health").status_code == 200
    assert client.get("/analysis").status_code == 200


def test_health_nennt_die_betriebsart(monkeypatch):
    """Ein Zustand, den man nicht abfragen kann, ist einer, ueber den man
    raet - siehe die Anmeldung am 18.08."""
    monkeypatch.delenv("MIXCOACH_AUTH", raising=False)
    assert client.get("/health").json()["auth"] == "aus"
    monkeypatch.setenv("MIXCOACH_AUTH", "an")
    assert client.get("/health").json()["auth"] == "an"


def test_nur_genau_an_schaltet_ein(monkeypatch):
    for wert in ("", "1", "true", "ja", "AN ", "An"):
        monkeypatch.setenv("MIXCOACH_AUTH", wert)
        erwartet = "an" if wert.strip().lower() == "an" else "aus"
        assert auth.betriebsart() == erwartet, f"{wert!r}"


# --- Eingeschaltet --------------------------------------------------------


def test_ohne_token_kein_zugang(auth_an):
    antwort = client.get("/analysis")
    assert antwort.status_code == 401
    assert "Authorization" in antwort.json()["detail"]


def test_mit_gueltigem_token_zugang(auth_an):
    assert client.get("/analysis", headers=_kopf(_token())).status_code == 200


def test_health_bleibt_offen(auth_an):
    """Ein Neustart-Waechter kann sich nicht anmelden."""
    assert client.get("/health").status_code == 200


def test_abgelaufener_token_wird_abgewiesen(auth_an):
    alt = _token(exp=int(time.time()) - 60)
    antwort = client.get("/analysis", headers=_kopf(alt))
    assert antwort.status_code == 401
    assert "abgelaufen" in antwort.json()["detail"].lower()


def test_falsche_signatur_wird_abgewiesen(auth_an):
    fremd = jwt.encode({"sub": "x", "aud": "authenticated",
                        "exp": int(time.time()) + 60},
                       "ein-anderes-geheimnis", algorithm="HS256")
    assert client.get("/analysis", headers=_kopf(fremd)).status_code == 401


def test_token_ohne_sub_wird_abgewiesen(auth_an):
    ohne = jwt.encode({"aud": "authenticated", "exp": int(time.time()) + 60},
                      GEHEIMNIS, algorithm="HS256")
    assert client.get("/analysis", headers=_kopf(ohne)).status_code == 401


def test_none_verfahren_wird_abgewiesen(auth_an):
    """Der aelteste JWT-Angriff: alg=none. Muss scheitern."""
    boese = jwt.encode({"sub": "x", "aud": "authenticated",
                        "exp": int(time.time()) + 60}, key="", algorithm="none")
    assert client.get("/analysis", headers=_kopf(boese)).status_code == 401


def test_kein_geheimnis_heisst_nicht_durchlassen(monkeypatch):
    """'Kann nicht pruefen' darf nie 'laesst durch' heissen."""
    monkeypatch.setenv("MIXCOACH_AUTH", "an")
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://beispiel.supabase.co")
    antwort = client.get("/analysis", headers=_kopf(_token()))
    assert antwort.status_code == 503
    assert antwort.status_code != 200


# --- Die Eigenschaft, auf die es ankommt ----------------------------------


def test_ein_neuer_endpoint_ist_von_selbst_geschuetzt(auth_an):
    """Die Pruefung haengt an der App, nicht an einzelnen Endpoints."""
    @app.get("/frisch-dazugekommen")
    def frisch():                                    # pragma: no cover
        return {"ok": True}

    try:
        assert client.get("/frisch-dazugekommen").status_code == 401
        assert client.get("/frisch-dazugekommen",
                          headers=_kopf(_token())).status_code == 200
    finally:
        app.router.routes = [r for r in app.router.routes
                             if getattr(r, "path", "") != "/frisch-dazugekommen"]


def test_die_messwerkzeuge_bekommen_keine_ausnahme(auth_an):
    """In main.py stand, der Relabel- und der Uebungs-Router gehoerten bei
    F2 'in dieselbe Ausnahme'. Sie bekommen keine: beide zeigen echte
    Analysen, und gehostet koennte sonst jeder fremde Sets ansehen."""
    for pfad in ("/relabel/irgendeine-id", "/uebungen-bewertung/abend1"):
        assert client.get(pfad).status_code == 401, pfad


def test_die_freiliste_bleibt_kurz():
    """Eine Freiliste, die waechst, ist keine."""
    assert auth.OFFENE_PFADE == {"/health", "/docs", "/openapi.json", "/redoc"}


# --- CORS -----------------------------------------------------------------


def test_cors_ist_nicht_mehr_offen_fuer_alle(monkeypatch):
    monkeypatch.delenv("MIXCOACH_CORS_ORIGINS", raising=False)
    urspruenge = auth.cors_urspruenge()
    assert "*" not in urspruenge
    assert "http://localhost:8080" in urspruenge, "die App laeuft auf 8080"


def test_cors_laesst_sich_setzen(monkeypatch):
    monkeypatch.setenv("MIXCOACH_CORS_ORIGINS",
                       "https://mixcoach.app, https://beta.mixcoach.app")
    assert auth.cors_urspruenge() == ["https://mixcoach.app",
                                      "https://beta.mixcoach.app"]
