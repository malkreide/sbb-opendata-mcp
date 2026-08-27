#!/usr/bin/env python3
"""Was hat der geplante Live-Lauf festgestellt — clear, finding oder unknown?

WARUM DAS EIN SKRIPT IST UND KEIN YAML-BLOCK
--------------------------------------------
`if: failure()` kennt zwei Antworten: rot und nicht rot. Ein Live-Lauf hat
drei, und die dritte ist die, die zaehlt:

  clear    Die Suite ist gelaufen und war gruen.
  finding  Die Suite ist gelaufen und etwas ist gefallen.
  unknown  Die Suite ist NICHT gelaufen — und niemand weiss, ob der Vertrag
           mit der Quelle noch haelt.

Ein gescheitertes `pip install`, ein Timeout, eine umbenannte Marke: alles
`unknown`, alles sieht unter `if: failure()` aus wie ein gebrochener Vertrag.
Und ein Lauf, in dem jeder Test uebersprungen wurde, sieht unter jedem
Exit-Code-Check aus wie Erfolg.

Diese Einordnung entscheidet, ob ein Issue aufgeht oder zugeht. Sie in einen
`run:`-Block zu schreiben hiesse, den einzigen Teil des Workflows, der etwas
behauptet, an die einzige Stelle zu legen, an der ihn niemand testen kann.
Deshalb steht sie hier, neben ihrem Test.

DER UEBERSPRUNGENE LAUF
-----------------------
Gemessen am 7.8.2026 an `swiss-transport-mcp`: Ohne `TRANSPORT_API_KEY`
ueberspringt die Live-Suite alle sechs Tests, und pytest endet mit 0. Ein
woechentlicher Job haette gemeldet: gruen. Geprueft haette er nichts — und ein
offenes Issue haette er zugemacht, mit einem Vergleich, den es nie gab.

`tests - skipped == 0` ist deshalb `unknown` und nicht `clear`. Ein Secret, das
niemand gesetzt hat, ist kein gruener Vertrag mit der Quelle; es ist gar keiner.

ZWEI SKIPS, GEGENSAETZLICHE BEDEUTUNG
-------------------------------------
Ein Skip heisst nicht immer dasselbe. «Vorbedingung nicht erfuellt» ist eine
Entscheidung im Test und laesst den Rest des Laufs gueltig. «Die Quelle hat
nicht geantwortet» heisst dagegen, dass genau dieser Teil des Vertrags heute
nicht verglichen wurde.

Am 26.8.2026 lief `test_live_search_waedenswil` in das 30-s-Zeitlimit. Der
Fehlschlag wurde `finding`, und `live.yml` machte Issue #48 auf mit dem Satz,
der Vertrag mit der Quelle habe sich geaendert. Nachgemessen am 27.8.2026 mit
derselben Anfrage: sechs Laeufe, 0.44 bis 0.80 s, HTTP 200 — es hatte sich
nichts geaendert. Der Docstring hier nannte den Fall laengst («ein Timeout:
alles `unknown`»); nur kam ein Timeout *innerhalb* eines Tests nie als Timeout
an, sondern als Fehlschlag.

Die Live-Suite schreibt deshalb `SOURCE_UNAVAILABLE` in den Skip-Grund, wenn
die Quelle nach mehreren Versuchen nicht geantwortet hat, und dieser Marker
macht den Lauf `unknown` statt `clear`. Beides ist rot — aber `unknown` macht
kein Issue auf und schliesst keines.

DIE QUELLE IST DAS JUNIT-XML, NICHT DER EXIT-CODE
-------------------------------------------------
Der Exit-Code von pytest sagt 0 fuer «alles gruen» und fuer «alles
uebersprungen» dasselbe. Das XML zaehlt Tests, Fehler, Fehlschlaege und
Uebersprungene getrennt, also wird es gelesen. Fehlt es, ist pytest gar nicht
bis zum Schreiben gekommen — auch das ist `unknown`, und zwar mit Grund.

Aufruf:
    python scripts/classify_live_run.py live-report.xml
    python scripts/classify_live_run.py live-report.xml --pytest-exit 1

Gibt `state=...` und `reason=...` auf stdout aus und haengt beides an
`$GITHUB_OUTPUT` an, wenn die Variable gesetzt ist. Der Exit-Code ist immer 0:
Ueber rot oder gruen entscheidet der Workflow, nicht dieser Reporter.
"""

from __future__ import annotations

import argparse
import os
import xml.etree.ElementTree as ET
from pathlib import Path

CLEAR = "clear"
FINDING = "finding"
UNKNOWN = "unknown"

# Marker, mit dem ein Live-Test sagt: Ich habe uebersprungen, weil die Quelle
# nicht geantwortet hat — nicht, weil eine Vorbedingung fehlte.
#
# Ohne diese Unterscheidung sind beide Skips dasselbe Zeichen mit
# gegensaetzlicher Bedeutung. Ein bewusster Skip ist eine Entscheidung im Test
# und laesst den Rest des Laufs gueltig; ein Ausfall-Skip heisst, dass genau
# dieser Teil des Vertrags heute **nicht** verglichen wurde. Wer beide gleich
# behandelt, muss sich zwischen zwei Fehlern entscheiden: jeden bewussten Skip
# zum Ausfall erklaeren, oder einen echten Ausfall als gruen verbuchen und ein
# offenes Issue mit einem Vergleich schliessen, den es nicht gab.
#
# Die Live-Suite importiert diese Konstante aus diesem Modul, statt den Text
# ein zweites Mal zu schreiben: Zwei Kopien liefen sonst auseinander, und zwar
# still — der Marker stuende noch im Skip-Grund, waehrend hier schon ein
# anderer gesucht wuerde.
SOURCE_UNAVAILABLE = "QUELLE-NICHT-ERREICHBAR"


def classify(report: Path, pytest_exit: int | None = None) -> tuple[str, str]:
    """(state, reason) aus einem JUnit-XML und optional dem pytest-Exit-Code."""
    if not report.is_file():
        return (
            UNKNOWN,
            f"kein Report unter {report} — pytest ist nicht bis zum Schreiben "
            "gekommen" + (f" (Exit {pytest_exit})" if pytest_exit is not None else ""),
        )
    try:
        root = ET.parse(report).getroot()
    except (ET.ParseError, OSError) as exc:
        return UNKNOWN, f"{report} ist nicht lesbar: {exc}"

    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    if not suites:
        return UNKNOWN, f"{report} enthaelt keine testsuite"

    def total(attr: str) -> int:
        return sum(int(s.get(attr) or 0) for s in suites)

    tests, failures, errors, skipped = (
        total("tests"),
        total("failures"),
        total("errors"),
        total("skipped"),
    )
    # `message` ist das Attribut, in das pytest den Skip-Grund schreibt; der
    # Elementtext wiederholt ihn mit Datei und Zeile davor. Gelesen werden
    # beide, damit der Marker auch dann traegt, wenn eine pytest-Version nur
    # noch eines von beiden fuellt.
    unavailable = sum(
        1
        for el in root.iter("skipped")
        if SOURCE_UNAVAILABLE in (el.get("message") or "") or SOURCE_UNAVAILABLE in (el.text or "")
    )

    if failures or errors:
        return (
            FINDING,
            f"{failures} Fehlschlag/Fehlschlaege und {errors} Fehler von {tests} Test(s)",
        )
    if tests == 0:
        return (
            UNKNOWN,
            "null Tests eingesammelt — die Marke oder die Dateien haben sich "
            "bewegt, und ein Erfolg ohne Test ist kein Erfolg",
        )
    # Vor «alles uebersprungen»: Beide Antworten sind `unknown`, aber nur eine
    # von beiden nennt den Grund richtig. Steht die generische zuerst, liest im
    # Job-Log bei einem Totalausfall der Quelle «meist ein fehlendes Secret».
    if unavailable:
        # Nicht `finding`: Es ist nichts gefallen, also gibt es nichts zu
        # melden. Nicht `clear`: Ein Teil des Vertrags wurde heute nicht
        # verglichen, und ein Issue, das darauf zugeht, behauptet mehr als der
        # Lauf hergibt. Sichtbar wird der Ausfall ueber den roten Job.
        return (
            UNKNOWN,
            f"die Quelle hat bei {unavailable} von {tests} Test(s) nicht geantwortet — "
            f"{tests - skipped} Test(s) liefen, der Rest des Vertrags blieb ungeprueft",
        )
    if tests - skipped == 0:
        return (
            UNKNOWN,
            f"alle {tests} Test(s) uebersprungen — meist ein fehlendes Secret oder "
            "eine nicht erfuellte Vorbedingung. Geprueft wurde nichts",
        )
    return CLEAR, f"{tests - skipped} von {tests} Test(s) ausgefuehrt, alle gruen"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="classify_live_run")
    ap.add_argument("report", type=Path, help="Pfad zum JUnit-XML von pytest")
    ap.add_argument("--pytest-exit", type=int, default=None)
    args = ap.parse_args(argv)

    state, reason = classify(args.report, args.pytest_exit)
    print(f"state={state}")
    print(f"reason={reason}")

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"state={state}\n")
            fh.write(f"reason={reason}\n")
    # Immer 0: Ueber rot oder gruen entscheidet der Workflow.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
