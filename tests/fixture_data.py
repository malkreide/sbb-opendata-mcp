"""Zugriff auf die aufgezeichneten Fixtures unter ``tests/fixtures/``.

Quelle, Datum, Auswahlregel und SHA-256 je Datei stehen in
``tests/fixtures/PROVENANCE.md``, geschrieben von
``scripts/record_fixtures.py``.

Davor hatte diese Suite **keinen einzigen** aufgezeichneten Payload — mit null
Inline-Payloads stand der Server damit auf Platz 41 von 42 der
Portfolio-Rangfolge, und drei seiner zehn Werkzeuge waren trotzdem dauerhaft
kaputt. Die Zahl misst Exposition, nicht Risiko.

Ein fehlender Name ist hier ein Fehler und keine leere Struktur. Ein Loader,
der bei einem Tippfehler ``{}`` zurueckgibt, erzeugt einen Test, der nichts
mehr prueft und trotzdem Erfolg meldet — die teuerste Sorte gruen.
"""

from __future__ import annotations

import copy
import json
from functools import cache
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@cache
def _load(name: str) -> Any:
    path = FIXTURES / name
    if not path.is_file():
        available = sorted(p.name for p in FIXTURES.glob("*.json"))
        raise FileNotFoundError(
            f"Keine Fixture {name!r} unter {FIXTURES}. Vorhanden: {available}. "
            "Neu aufzeichnen mit `python scripts/record_fixtures.py`."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def payload(name: str) -> Any:
    """Die aufgezeichnete Antwort für ``name`` — als Kopie.

    Der Produktivcode bekommt diese Struktur über ``respx`` in die Hand; ein
    Test, der sie verändert, würde sonst dem nächsten die Fixture unter den
    Füssen wegziehen.
    """
    return copy.deepcopy(_load(name))


def records(name: str) -> list[dict[str, Any]]:
    """Die Datensatzzeilen einer aufgezeichneten Antwort."""
    return payload(name)["results"]


def declared_fields(dataset_id: str) -> set[str]:
    """Die Feldnamen, die die Quelle für ``dataset_id`` deklariert.

    Das ist der Vertrag, nicht eine Stichprobe: Ein ``select`` auf ein Feld,
    das hier fehlt, beantwortet die Explore-API mit HTTP 400 — nicht mit
    weniger Spalten.
    """
    fields = _load("dataset_fields.json")
    if dataset_id not in fields:
        raise KeyError(
            f"Für '{dataset_id}' ist keine Felddeklaration aufgezeichnet. "
            f"Vorhanden: {sorted(fields)}. Datensatz in `record_fixtures.py` "
            "unter `used` ergänzen und neu aufzeichnen."
        )
    return set(fields[dataset_id])
