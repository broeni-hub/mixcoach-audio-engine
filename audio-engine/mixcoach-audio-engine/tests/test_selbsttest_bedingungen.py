"""Die drei Bedingungen der Live-Schwelle im Selbsttest.

Der wichtigste Test ist test_waechter_faengt_den_fehler_vom_august: er baut
den Fehler nach, der die Fortschrittskurve vom 18. bis 21.08.2026 das
Gegenteil der Wahrheit anzeigen liess, und haelt fest, dass der Waechter
anschlaegt. Ein Waechter, der den Fall nicht faengt, fuer den er gebaut
wurde, ist schlimmer als keiner - er beruhigt.
"""

import pytest

from tools.selbsttest import _steigung


def test_steigung_faellt_bei_fallender_reihe():
    assert _steigung([4.0, 3.0, 2.0, 1.0]) < 0


def test_steigung_steigt_bei_steigender_reihe():
    assert _steigung([1.0, 2.0, 3.0, 4.0]) > 0


def test_steigung_ist_null_bei_flacher_reihe():
    assert _steigung([2.0, 2.0, 2.0, 2.0]) == pytest.approx(0.0)


def test_steigung_braucht_keine_zwei_werte_um_zu_antworten():
    assert _steigung([]) == 0.0
    assert _steigung([1.0]) == 0.0


def test_waechter_faengt_den_fehler_vom_august():
    """Die echte Reihe vom 21.08.2026, mit den zwei Probedateien am Ende.

    Vorne dreizehn eigene Aufnahmen, die von 3,5 auf 1,25 dB fallen; hinten
    die zwei Probedateien mit je einem Uebergang bei 3,4 dB und dazwischen
    MixCoach6 mit 1,1 dB. Der angezeigte Trend (letzte 3 gegen die 3 davor)
    zeigt nach oben, die Reihe insgesamt nach unten - und genau dieser
    Widerspruch ist das Signal.
    """
    reihe = [3.5, 2.8, 3.0, 2.1, 3.6, 3.2, 1.4, 1.95, 0.85, 1.7, 1.85, 1.25,
             2.05, 3.4, 1.1, 3.4]
    letzte_drei = sum(reihe[-3:]) / 3
    davor_drei = sum(reihe[-6:-3]) / 3
    delta = letzte_drei - davor_drei

    assert delta > 0, "der angezeigte Trend zeigt eine Verschlechterung"
    assert _steigung(reihe) < 0, "die ganze Reihe faellt trotzdem"
    assert delta * _steigung(reihe) < 0, "der Waechter schlaegt an"


def test_ohne_die_probedateien_kein_widerspruch():
    """Dieselbe Reihe ohne die zwei Einzel-Uebergangs-Dateien: beide
    Richtungen stimmen ueberein, der Waechter schweigt."""
    reihe = [3.5, 2.8, 3.0, 2.1, 3.6, 3.2, 1.4, 1.95, 0.85, 1.7, 1.85, 1.25,
             2.05, 1.1]
    delta = sum(reihe[-3:]) / 3 - sum(reihe[-6:-3]) / 3
    assert _steigung(reihe) < 0
    assert delta * _steigung(reihe) >= 0, "kein Widerspruch mehr"
