#!/usr/bin/env python3
"""Tests fuer scripts/classify_live_run.py — die drei Antworten eines Live-Laufs.

Die Einordnung entscheidet, ob ein Issue aufgeht oder zugeht. Genau deshalb
steht sie in einem Skript und nicht in einem `run:`-Block: So kann jemand sie
gegen die Faelle halten, aus denen sie entstanden ist.

Der wichtigste Fall ist `test_alle_uebersprungen_ist_nicht_gruen`. Gemessen am
7.8.2026 an `swiss-transport-mcp`: Ohne `TRANSPORT_API_KEY` ueberspringt die
Live-Suite alle sechs Tests und pytest endet mit 0. Ein Job, der das als gruen
bucht, schliesst ein offenes Issue mit einem Vergleich, den es nie gab.

Nur Standardbibliothek, kein Netz.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import classify_live_run as clr  # noqa: E402


def write(tmp: Path, xml: str) -> Path:
    path = tmp / "live-report.xml"
    path.write_text(xml, encoding="utf-8")
    return path


def suite(
    tests: int, failures: int = 0, errors: int = 0, skipped: int = 0, reasons: list[str] | None = None
) -> str:
    """Ein JUnit-XML wie pytest es schreibt; `reasons` fuellt die Skip-Gruende."""
    cases = "".join(
        f'<testcase classname="t" name="test_{i}">'
        f'<skipped type="pytest.skip" message="{r}">t.py:1: {r}</skipped>'
        "</testcase>"
        for i, r in enumerate(reasons or [])
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<testsuites><testsuite name="pytest" tests="{tests}" failures="{failures}" '
        f'errors="{errors}" skipped="{skipped}">{cases}</testsuite></testsuites>'
    )


class ClassifyTest(unittest.TestCase):
    def _state(self, xml: str) -> tuple[str, str]:
        with tempfile.TemporaryDirectory() as tmp:
            return clr.classify(write(Path(tmp), xml))

    def test_alles_gruen_ist_clear(self):
        state, reason = self._state(suite(tests=3))
        self.assertEqual(state, clr.CLEAR)
        self.assertIn("3 von 3", reason)

    def test_ein_fehlschlag_ist_ein_finding(self):
        state, _ = self._state(suite(tests=3, failures=1))
        self.assertEqual(state, clr.FINDING)

    def test_ein_fehler_ist_ein_finding(self):
        state, _ = self._state(suite(tests=3, errors=1))
        self.assertEqual(state, clr.FINDING)

    def test_alle_uebersprungen_ist_nicht_gruen(self):
        """swiss-transport-mcp ohne TRANSPORT_API_KEY: 6 von 6 uebersprungen."""
        state, reason = self._state(suite(tests=6, skipped=6))
        self.assertEqual(state, clr.UNKNOWN)
        self.assertIn("uebersprungen", reason)

    def test_teilweise_uebersprungen_ist_gruen(self):
        """Ein einzelner Skip ist eine Entscheidung im Test, kein Ausfall."""
        state, reason = self._state(suite(tests=6, skipped=5))
        self.assertEqual(state, clr.CLEAR)
        self.assertIn("1 von 6", reason)

    def test_ein_bewusster_skip_bleibt_gruen(self):
        """Die Gegenprobe zum Ausfall-Skip: ein Grund ohne Marker aendert nichts.

        Ohne diesen Test koennte die Regel darunter auch «jeder Skip ist
        unknown» lauten und bliebe gruen — dann waere jede bewusste
        Vorbedingung ein Ausfall.
        """
        state, reason = self._state(suite(tests=6, skipped=1, reasons=["kein TRANSPORT_API_KEY gesetzt"]))
        self.assertEqual(state, clr.CLEAR)
        self.assertIn("5 von 6", reason)

    def test_ausfall_skip_ist_nicht_gruen(self):
        """26.8.2026: `test_live_search_waedenswil` lief ins 30-s-Zeitlimit.

        Der Lauf wurde `finding`, `live.yml` machte Issue #48 auf und schrieb
        hinein, der Vertrag mit der Quelle habe sich geaendert. Nachgemessen am
        27.8.2026: dieselbe Anfrage, sechs Laeufe, 0.44 bis 0.80 s, HTTP 200.
        Es hatte sich nichts geaendert.

        Ueberspringt der Test stattdessen, darf daraus weder ein Befund noch
        ein Freispruch werden: Genau dieser Teil des Vertrags wurde heute nicht
        verglichen.
        """
        state, reason = self._state(
            suite(
                tests=6,
                skipped=1,
                reasons=[f"{clr.SOURCE_UNAVAILABLE}: data.sbb.ch hat in 3 Versuchen nicht geantwortet"],
            )
        )
        self.assertEqual(state, clr.UNKNOWN)
        self.assertIn("nicht geantwortet", reason)
        self.assertIn("1 von 6", reason)

    def test_totalausfall_nennt_die_quelle_und_nicht_das_secret(self):
        """Beides `unknown` — aber nur eine der beiden Begruendungen stimmt.

        Simuliert am 27.8.2026 mit unerreichbarer Basis-URL: alle sechs Tests
        uebersprangen. Stuende die generische Regel zuerst, laese im Job-Log
        «meist ein fehlendes Secret», waehrend die Quelle weg war.
        """
        state, reason = self._state(suite(tests=6, skipped=6, reasons=[clr.SOURCE_UNAVAILABLE] * 6))
        self.assertEqual(state, clr.UNKNOWN)
        self.assertIn("nicht geantwortet", reason)
        self.assertNotIn("Secret", reason)

    def test_ein_fehlschlag_schlaegt_den_ausfall_skip(self):
        """Ein echter Befund neben einem Ausfall bleibt ein Befund.

        Etwas ist gefallen, also ist etwas festgestellt — das gehoert gemeldet,
        auch wenn ein anderer Test keine Antwort bekam.
        """
        state, _ = self._state(suite(tests=6, failures=1, skipped=1, reasons=[clr.SOURCE_UNAVAILABLE]))
        self.assertEqual(state, clr.FINDING)

    def test_ausfall_skip_wird_auch_ohne_message_attribut_erkannt(self):
        """Der Marker steht im Attribut UND im Elementtext; eines genuegt."""
        xml = (
            '<testsuites><testsuite tests="6" failures="0" errors="0" skipped="1">'
            f'<testcase classname="t" name="a"><skipped>t.py:1: {clr.SOURCE_UNAVAILABLE}</skipped></testcase>'
            "</testsuite></testsuites>"
        )
        state, _ = self._state(xml)
        self.assertEqual(state, clr.UNKNOWN)

    def test_null_tests_ist_kein_erfolg(self):
        """Die Marke umbenannt, die Dateien verschoben — pytest meldet trotzdem 0."""
        state, reason = self._state(suite(tests=0))
        self.assertEqual(state, clr.UNKNOWN)
        self.assertIn("null Tests", reason)

    def test_ein_fehlschlag_schlaegt_uebersprungene(self):
        state, _ = self._state(suite(tests=6, skipped=5, failures=1))
        self.assertEqual(state, clr.FINDING)

    def test_mehrere_testsuites_werden_summiert(self):
        xml = (
            "<testsuites>"
            '<testsuite tests="2" failures="0" errors="0" skipped="2"/>'
            '<testsuite tests="3" failures="0" errors="0" skipped="0"/>'
            "</testsuites>"
        )
        state, _ = self._state(xml)
        self.assertEqual(state, clr.CLEAR)

    def test_eine_einzelne_testsuite_ohne_huelle(self):
        xml = '<testsuite tests="2" failures="0" errors="0" skipped="0"/>'
        state, _ = self._state(xml)
        self.assertEqual(state, clr.CLEAR)


class MissingReportTest(unittest.TestCase):
    """Kein Report heisst: pytest kam nicht bis zum Schreiben. Nie clear."""

    def test_fehlender_report_ist_unknown(self):
        state, reason = clr.classify(Path("/nonexistent/live-report.xml"), pytest_exit=4)
        self.assertEqual(state, clr.UNKNOWN)
        self.assertIn("Exit 4", reason)

    def test_kaputtes_xml_ist_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(Path(tmp), "<testsuite tests=")
            state, _ = clr.classify(path)
        self.assertEqual(state, clr.UNKNOWN)

    def test_xml_ohne_testsuite_ist_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write(Path(tmp), "<irgendwas/>")
            state, _ = clr.classify(path)
        self.assertEqual(state, clr.UNKNOWN)


class GithubOutputTest(unittest.TestCase):
    """Der Workflow liest state und reason ueber $GITHUB_OUTPUT."""

    def test_beide_werte_werden_angehaengt(self):
        import os

        with tempfile.TemporaryDirectory() as tmp:
            report = write(Path(tmp), suite(tests=2))
            out = Path(tmp) / "gh-output"
            out.write_text("", encoding="utf-8")
            os.environ["GITHUB_OUTPUT"] = str(out)
            try:
                rc = clr.main([str(report)])
            finally:
                del os.environ["GITHUB_OUTPUT"]
            written = out.read_text(encoding="utf-8")
        self.assertEqual(rc, 0)
        self.assertIn("state=clear", written)
        self.assertIn("reason=", written)


class GithubOutputZeilenTest(unittest.TestCase):
    """Ein Grund mit Zeilenumbruch darf kein zweites Output nachschieben.

    `key=value` endet in `$GITHUB_OUTPUT` an der ersten neuen Zeile; was
    danach steht, liest der Runner als eigenen Output. Der Reportpfad kommt
    vom Aufrufer und steht woertlich im Grund — ein Umbruch darin schoebe
    sonst ein `state=clear` nach und faerbte den roten Lauf gruen.
    """

    def test_umbruch_im_grund_schiebt_kein_zweites_output_nach(self):
        import os

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "gh-output"
            out.write_text("", encoding="utf-8")
            os.environ["GITHUB_OUTPUT"] = str(out)
            try:
                clr.main([str(Path(tmp) / "live-report.xml") + "\nstate=clear"])
            finally:
                del os.environ["GITHUB_OUTPUT"]
            zeilen = [z for z in out.read_text(encoding="utf-8").splitlines() if z]
        self.assertEqual([z for z in zeilen if z.startswith("state=")], ["state=unknown"])
        self.assertEqual(len(zeilen), 2)


if __name__ == "__main__":
    unittest.main()
