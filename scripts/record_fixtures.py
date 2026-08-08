#!/usr/bin/env python3
"""Zeichnet die Unit-Test-Fixtures von data.sbb.ch auf.

    python scripts/record_fixtures.py

WARUM ES DAS GIBT. Ein handgeschriebener Mock kodiert die Annahme seines
Autors und kann sie deshalb prinzipiell nicht widerlegen: Produktivcode und
Fixture stammen aus demselben Kopf, derselben Stunde, derselben Lektuere der
Doku. Wo beide irren, irren beide gleich, und die Suite bleibt dauerhaft
gruen.

WAS HIER AUFGEZEICHNET WIRD, ist deshalb zweierlei:

1. **Antworten** — Datensatzauszuege, an denen die Aufbereitung haengt.
2. **Der Vertrag** — die Felddeklaration je Datensatz. Die Explore-v2.1-API
   nennt unter `/datasets/<id>` in `fields[].name`, welche Felder es gibt. Ein
   `select` oder `order_by` auf ein Feld, das dort fehlt, beantwortet sie mit
   **HTTP 400** — nicht mit weniger Spalten. Der Nutzer sieht «API-Anfrage
   fehlgeschlagen».

Punkt 2 ist der Grund, warum es dieses Skript ueberhaupt gibt. Am 2026-08-08
gegen die Quelle gehalten, waren drei von zehn Werkzeugen dauerhaft kaputt:

  * `sbb_search_stations` waehlte sieben **deutsche** Feldnamen aus einem
    Datensatz, der ausschliesslich **englische** fuehrt. Keiner der sieben
    existiert.
  * `sbb_list_datasets` sortierte nach `metas.default.title` — das kennt der
    Katalog-Endpunkt nicht.
  * `sbb_get_infrastructure_construction_projects` fragte den Datensatz
    `construction-projects`, den es nicht mehr gibt (HTTP 404) und fuer den der
    Katalog auch keinen Nachfolger fuehrt.

Kein einziger Payload dieser Suite war je von der Quelle geholt worden, und
mit null Inline-Payloads stand dieser Server auf Platz 41 von 42 der
Portfolio-Rangfolge — die Zahl misst Exposition, nicht Risiko.

Ohne Aufzeichnungsdatum ist «aufgezeichnet» nach zwei Jahren von «ausgedacht»
nicht mehr zu unterscheiden, weil die Datei gleich aussieht. Es steht je Datei
in `tests/fixtures/PROVENANCE.md`.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT / "src"))

# Die Basis-URL und die Datensatz-IDs kommen aus dem Produktivcode, nicht aus
# einer Abschrift. Ein Aufzeichnungsskript, das eine andere Adresse fragt als
# der Server, belegt die falsche Antwort — unauffaellig, weil sie plausibel
# aussieht.
from sbb_opendata_mcp.server import (  # noqa: E402
    BASE_URL,
    DATASET_PASSENGER_FREQUENCY,
    DATASET_PLATFORMS,
    DATASET_RAIL_TRAFFIC,
    DATASET_STATIONS,
    DATASET_TRAINS_PER_SEGMENT,
)

CATALOG = BASE_URL  # .../catalog/datasets

# Je Datensatz: wie viele Zeilen die Fixture behaelt und wonach ausgewaehlt
# wird. Nicht «die ersten N» — die Auswahlregel steht je Eintrag daneben.
RECORDS = 6

# Der Suchbegriff der Haltestellen-Fixture. Wädenswil traegt Umlaut, mehrere
# Betreiber und mehr Treffer als eine Seite fasst: alles drei braucht die
# Fixture, um die Aufbereitung zu belegen.
STATION_QUERY = "Wädenswil"


def record() -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    recorded_at = datetime.now(UTC).strftime("%Y-%m-%d")
    entries: list[dict] = []

    def write(name: str, payload: object, url: str, rule: str) -> None:
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        (FIXTURES / name).write_text(text, encoding="utf-8")
        entries.append(
            {
                "name": name,
                "url": url,
                "rule": rule,
                "bytes": len(text.encode("utf-8")),
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
        )
        print(f"ok  {name:<34} {len(text.encode('utf-8')):>8} B")

    with httpx.Client(timeout=90.0, follow_redirects=True) as c:

        def get(url: str, **params: object) -> dict:
            r = c.get(url, params=params or None)
            r.raise_for_status()
            return r.json()

        # -- 1) Der Vertrag: welche Felder jeder Datensatz deklariert ---------
        used = {
            DATASET_PASSENGER_FREQUENCY,
            DATASET_RAIL_TRAFFIC,
            DATASET_STATIONS,
            DATASET_TRAINS_PER_SEGMENT,
            DATASET_PLATFORMS,
        }
        declared: dict[str, list[str]] = {}
        for ds in sorted(used):
            meta = get(f"{CATALOG}/{ds}")
            names = [f["name"] for f in meta.get("fields", [])]
            if not names:
                raise SystemExit(
                    f"{ds}: keine Felddeklaration — ohne sie laesst sich kein "
                    "`select` mehr gegen die Quelle halten."
                )
            declared[ds] = names
        write(
            "dataset_fields.json",
            declared,
            f"{CATALOG}/<dataset>",
            "die deklarierten Feldnamen (`fields[].name`) je Datensatz, den der "
            "Server benutzt — vollstaendig. Gegen diese Liste haelt der Test "
            "jedes `select` und jedes `order_by`; ein Feld, das hier fehlt, "
            "beantwortet die Quelle mit HTTP 400 und nicht mit weniger Spalten",
        )

        # -- 2) Der Katalog ---------------------------------------------------
        catalog = get(CATALOG, limit=100, order_by="title asc")
        ids = [d["dataset_id"] for d in catalog["results"]]
        missing = sorted(used - set(ids))
        if missing:
            raise SystemExit(
                f"Der Katalog fuehrt {missing} nicht mehr — ein Werkzeug fragt "
                "einen Datensatz, den es nicht gibt. Genau dieser Fall war der "
                "Befund vom 2026-08-08; er gehoert behoben, nicht aufgezeichnet."
            )
        # Ein Katalogeintrag traegt ~16 KB Metadaten; das Werkzeug liest davon
        # vier Angaben. Der Rest wuerde die Datei unlesbar machen, ohne mehr zu
        # belegen — die Auswahl ist deshalb nach VERWENDUNG zugeschnitten und
        # nicht nach Position innerhalb eines Eintrags.
        keep = ("title", "records_count")
        catalog["results"] = [
            {
                "dataset_id": d["dataset_id"],
                "metas": {
                    "default": {k: d.get("metas", {}).get("default", {}).get(k) for k in keep},
                    "dcat": {
                        "accrualperiodicity": d.get("metas", {}).get("dcat", {}).get("accrualperiodicity")
                    },
                },
            }
            for d in catalog["results"][:12]
        ]
        write(
            "catalog.json",
            catalog,
            f"{CATALOG}?limit=100&order_by=title+asc",
            f"die ersten 12 von {len(ids)} Katalogeintraegen, je auf die vier "
            "Angaben gekuerzt, die das Werkzeug liest (`dataset_id`, "
            "`metas.default.title`, `metas.default.records_count`, "
            "`metas.dcat.accrualperiodicity`); `total_count` unveraendert. Der "
            "Sortierschluessel gehoert zur Aufzeichnung: `metas.default.title` "
            "kennt der Katalog-Endpunkt NICHT, `title` schon",
        )

        # -- 3) Haltestellen — die Fixture des Befunds ------------------------
        from sbb_opendata_mcp.server import FIELDS_STATIONS

        stations = get(
            f"{CATALOG}/{DATASET_STATIONS}/records",
            limit=20,
            where=f'designationofficial like "%{STATION_QUERY}%"',
            select=",".join(FIELDS_STATIONS),
        )
        rows = stations["results"]
        if len({r.get("businessorganisationdescriptionde") for r in rows}) < 2:
            raise SystemExit(
                f"'{STATION_QUERY}' liefert nur einen Betreiber — dann belegt "
                "die Fixture die Betreiberspalte nicht. Anderen Ort waehlen."
            )
        if stations["total_count"] <= len(rows):
            raise SystemExit(
                f"'{STATION_QUERY}' passt auf eine Seite — dann prueft die "
                "Fixture den Hinweis auf weitere Treffer nicht."
            )
        write(
            "stations_search.json",
            stations,
            f"{CATALOG}/{DATASET_STATIONS}/records",
            f"Suche nach '{STATION_QUERY}', {len(rows)} von "
            f"{stations['total_count']} Treffern. Die Auswahl ist die Anfrage "
            "des Servers selbst, mit seiner eigenen Feldliste — nur so belegt "
            "die Fixture, dass die Feldnamen stimmen",
        )

        # -- 3b) Ein abgelaufener Eintrag — der Fuellwert-Fall ----------------
        #
        # Die Quelle schreibt «unbefristet gueltig» als 9999-12-31. Von 59'530
        # Eintraegen tragen 15 ein echtes Ablaufdatum. «Die ersten N» haetten
        # keinen davon getroffen; ausgewaehlt wird deshalb nach Merkmal.
        expired = get(
            f"{CATALOG}/{DATASET_STATIONS}/records",
            limit=3,
            where=f'validto < "{recorded_at}"',
            select=",".join(FIELDS_STATIONS),
        )
        if not expired["results"]:
            raise SystemExit(
                "Kein abgelaufener Eintrag mehr in der DiDok-Liste — dann "
                "belegt die Fixture den Unterschied zwischen einem echten "
                "Ablaufdatum und dem Fuellwert 9999-12-31 nicht mehr."
            )
        write(
            "stations_expired.json",
            expired,
            f"{CATALOG}/{DATASET_STATIONS}/records",
            f"{len(expired['results'])} Eintraege mit echtem Ablaufdatum "
            f"(von {expired['total_count']}). Nach Merkmal ausgewaehlt, nicht "
            "nach Position: Fast alle Eintraege tragen den Fuellwert "
            "9999-12-31, und «die ersten N» haetten ausgerechnet die "
            "unauffaelligen getroffen",
        )

        # -- 4) Passagierfrequenz --------------------------------------------
        freq = get(
            f"{CATALOG}/{DATASET_PASSENGER_FREQUENCY}/records",
            limit=RECORDS,
            order_by="jahr_annee_anno desc",
        )
        write(
            "passenger_frequency.json",
            freq,
            f"{CATALOG}/{DATASET_PASSENGER_FREQUENCY}/records",
            f"die {RECORDS} juengsten Zeilen (order_by wie im Server) von {freq['total_count']}",
        )

        # -- 5) Bahnverkehrsmeldungen ----------------------------------------
        disruptions = get(
            f"{CATALOG}/{DATASET_RAIL_TRAFFIC}/records",
            limit=RECORDS,
            order_by="published desc",
        )
        write(
            "rail_disruptions.json",
            disruptions,
            f"{CATALOG}/{DATASET_RAIL_TRAFFIC}/records",
            f"die {RECORDS} juengsten Meldungen von {disruptions['total_count']}",
        )

    _write_provenance(recorded_at, entries)
    print(f"\nPROVENANCE.md geschrieben, Aufzeichnungsdatum {recorded_at}")
    return 0


def _write_provenance(recorded_at: str, entries: list[dict]) -> None:
    lines = [
        "# Herkunft der Fixtures",
        "",
        "**Erzeugt von `scripts/record_fixtures.py`. Nicht von Hand pflegen.**",
        "",
        f"Aufgezeichnet am **{recorded_at}** von `data.sbb.ch`, unveraendert bis",
        "auf die je Datei dokumentierte Auswahl.",
        "",
        "Ohne Datum ist «aufgezeichnet» nach zwei Jahren von «ausgedacht» nicht",
        "mehr zu unterscheiden — die Datei sieht gleich aus, und niemand weiss,",
        "ob sie den Stand von gestern zeigt oder den von vor drei",
        "Schema-Wechseln. Das Datum macht diesen Abstand zu einer lesbaren Zahl.",
        "",
        "## `dataset_fields.json` ist kein Datenauszug, sondern der Vertrag",
        "",
        "Die Explore-v2.1-API deklariert je Datensatz, welche Felder es gibt.",
        "Ein `select` oder `order_by` auf ein Feld, das dort fehlt, beantwortet",
        "sie mit **HTTP 400** — nicht mit weniger Spalten. Der Unterschied ist",
        "der ganze Punkt: Ein fehlendes Feld faellt nicht als Luecke auf,",
        "sondern als Ausfall, und der Nutzer liest «API-Anfrage",
        "fehlgeschlagen». `tests/test_server.py` haelt deshalb jeden Feldnamen,",
        "den der Server verwendet, gegen diese Aufzeichnung.",
        "",
        "**Es sind Ausschnitte, keine Vollabzuege**, und die Auswahlregel steht",
        "je Datei dabei. Eine Fixture belegt damit die *Form* der Antwort und",
        "einen datierten Ausschnitt ihres Inhalts — nicht den Bestand. Aussagen",
        "ueber Vollstaendigkeit gehoeren in Live-Tests (`pytest -m live`).",
        "",
    ]
    for e in entries:
        lines += [
            f"## `{e['name']}`",
            "",
            f"- **Quelle:** `{e['url']}`",
            f"- **Aufgezeichnet:** {recorded_at}",
            f"- **Auswahl:** {e['rule']}",
            f"- **Groesse:** {e['bytes']} B",
            f"- **SHA-256:** `{e['sha256']}`",
            "",
        ]
    (FIXTURES / "PROVENANCE.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(record())
    except httpx.HTTPError as exc:  # ein halber Satz ist schlimmer als keiner
        print(f"FEHLER: Quelle nicht erreichbar: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
