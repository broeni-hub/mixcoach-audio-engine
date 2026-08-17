"""Ein Job schreibt dorthin, wohin er beim Absenden zeigte.

Der Fehler, gegen den das steht, ist schwer zu sehen und teuer:

Der Executor in job_manager lebt prozessweit und ueberdauert jeden
einzelnen Test. conftest.py biegt job_manager.RESULTS_DIR per monkeypatch
in einen tmp-Ordner um und nimmt den Patch beim Teardown zurueck. Laeuft
der Job-Thread dann noch - unter Last passiert das, wenn ein Test in
seinen Timeout laeuft -, las er beim SCHREIBEN den wiederhergestellten
Wert und legte die Analyse im echten Datenstamm ab.

Am 15.08.2026 genau so passiert (caf8ee17, mix.wav). Am 31.07. waren 62
solcher Dateien aufgelaufen und haben eine Verteilungsmessung um 1,8
Beats verschoben. Der Fehler faellt nicht auf, weil das Ergebnis wie ein
Befund aussieht.
"""

import json
from pathlib import Path

from app.jobs import job_manager


def test_zielordner_wird_beim_absenden_festgehalten(tmp_path, monkeypatch):
    """Der Kern: nach dem Absenden darf ein Wechsel von RESULTS_DIR die
    schon laufende Analyse nicht mehr umlenken."""
    gepatcht = tmp_path / "waehrend_des_tests"
    gepatcht.mkdir()
    echt = tmp_path / "echter_datenstamm"
    echt.mkdir()

    monkeypatch.setattr(job_manager, "RESULTS_DIR", gepatcht)

    gesehen = {}

    def falscher_lauf(job_id, ziel_ordner=None):
        # Das macht der echte Thread auch: er schreibt erst spaeter.
        # Zwischenzeitlich ist der Patch schon zurueckgenommen.
        monkeypatch.setattr(job_manager, "RESULTS_DIR", echt)
        gesehen["ziel"] = ziel_ordner

    monkeypatch.setattr(job_manager, "_run_job", falscher_lauf)
    # Der echte Executor wuerde asynchron laufen - hier direkt ausfuehren,
    # damit der Test nicht auf einen Thread wartet.
    monkeypatch.setattr(job_manager._executor, "submit",
                        lambda fn, *args: fn(*args))

    job_manager.create_job(str(tmp_path / "x.wav"), "x.wav", 123)

    assert gesehen["ziel"] == gepatcht, (
        "Der Job muss in den Ordner schreiben, der beim Absenden galt - "
        "nicht in den, der beim Schreiben zufaellig eingestellt ist.")


def test_retry_haelt_den_zielordner_ebenso_fest():
    """retry_job() sendet ueber denselben Weg ab - beide Stellen zaehlen."""
    quelle = Path(job_manager.__file__).read_text(encoding="utf-8")
    absendungen = quelle.count("_executor.submit(_run_job, job.job_id, RESULTS_DIR)")
    assert absendungen == 2, (
        f"Es gibt {absendungen} Absendungen mit festgehaltenem Ordner, "
        "erwartet sind 2 (create_job und retry_job). Wer eine dritte "
        "hinzufuegt, muss den Ordner ebenso mitgeben.")


def test_ohne_angabe_gilt_weiter_der_globale_ordner(tmp_path, monkeypatch):
    """Rueckwaertskompatibel: ein Aufruf ohne Ordner nimmt RESULTS_DIR.

    Wichtig fuer den Betrieb - dort ist der Wert ueber die Laufzeit
    konstant, und niemand soll ihn durchreichen muessen.
    """
    ziel = tmp_path / "global"
    ziel.mkdir()
    monkeypatch.setattr(job_manager, "RESULTS_DIR", ziel)

    job = job_manager.Job(job_id="j1", file_name="x.wav", file_size=1,
                          temp_path=str(tmp_path / "fehlt.wav"))
    monkeypatch.setitem(job_manager._jobs, "j1", job)

    # Die Datei fehlt, der Lauf scheitert also frueh - uns interessiert
    # nur, dass er ohne TypeError startet und den Job als failed markiert.
    job_manager._run_job("j1")
    assert job.status == "failed"


def test_ergebnis_landet_im_uebergebenen_ordner(tmp_path, monkeypatch):
    """Und das Ergebnis liegt danach wirklich dort - nicht nur der Wert
    stimmt, sondern die Datei."""
    ziel = tmp_path / "hierhin"
    ziel.mkdir()
    woanders = tmp_path / "nicht_hierhin"
    woanders.mkdir()
    monkeypatch.setattr(job_manager, "RESULTS_DIR", woanders)

    job = job_manager.Job(job_id="j2", file_name="s.wav", file_size=1,
                          temp_path=str(tmp_path / "s.wav"))
    Path(job.temp_path).write_bytes(b"nicht wirklich audio")
    monkeypatch.setitem(job_manager._jobs, "j2", job)

    monkeypatch.setattr(job_manager, "load_audio_file",
                        lambda **kw: object())
    monkeypatch.setattr(job_manager, "analyze_set",
                        lambda audio, progress=None: {"tempo": {}})
    monkeypatch.setattr(job_manager, "map_set_analysis_to_frontend_result",
                        lambda filename, analysis: {"id": "abc123", "fileName": filename})

    job_manager._run_job("j2", ziel)

    assert (ziel / "abc123.json").exists(), "Ergebnis nicht im uebergebenen Ordner"
    assert not (woanders / "abc123.json").exists(), "Ergebnis im falschen Ordner gelandet"
    assert json.loads((ziel / "abc123.json").read_text())["id"] == "abc123"
