"""Spec `2026-07-28` nativ: was der Server selbst beitragen muss.

`mcp` 2.x spricht die Revision von sich aus — Envelope, `server/discover`,
`resultType`. Drei Dinge liefert das SDK aber nur, wenn der Server sie angibt,
und ohne Angabe sieht die Antwort trotzdem gueltig aus:

* **`serverInfo.version`.** Ab `2026-07-28` stempelt das SDK `serverInfo` als
  `_meta["io.modelcontextprotocol/serverInfo"]` auf jedes Resultat. Ohne
  `version=` stand dort bei jeder Antwort `"version": ""`.
* **`title` auf dem Werkzeug.** Anzeige-Reihenfolge ist `title`, dann
  `annotations.title`, dann `name`. Der Server setzte nur das mittlere.
* **`outputSchema`.** Die Werkzeuge lieferten `structuredContent` ohne Schema;
  ein Client sah ein Objekt und musste raten, was darin steht.

Geprueft ueber einen echten `Client`: der validiert `structuredContent` selbst
gegen das gelistete `outputSchema` und wirft bei Abweichung. Ein Blick auf
`mcp._tool_manager` waere auch dann gruen, wenn das Schema auf dem Weg zum
Draht verlorenginge.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import httpx
import pytest
from mcp import Client
from mcp.server.mcpserver import MCPServer

from sbb_opendata_mcp import __version__
from sbb_opendata_mcp.server import (
    BASE_URL,
    DATASET_PASSENGER_FREQUENCY,
    DATASET_RAIL_TRAFFIC,
    DATASET_STATIONS,
    PROJECT_URL,
    mcp,
)
from tests.fixture_data import payload

# `auto` fuehrt ein echtes `server/discover` und landet in der modernen Aera;
# ein fest gepinnter Modus uebersprange es und kennte kein `serverInfo`.
MODES = {"legacy": "2025-11-25", "auto": "2026-07-28"}

# Aufgezeichnet, wo es eine Aufzeichnung gibt (tests/fixtures/PROVENANCE.md).
# Fuer die uebrigen vier Datensaetze genuegt ein leerer Datensatz: das Schema
# typisiert die Zeilen der Quelle bewusst nicht (`dict[str, Any]`), ihr Inhalt
# traegt zu den Zusicherungen hier also nichts bei — der Umschlag schon.
RECORDED = {
    DATASET_PASSENGER_FREQUENCY: "passenger_frequency.json",
    DATASET_RAIL_TRAFFIC: "rail_disruptions.json",
    DATASET_STATIONS: "stations_search.json",
}
UNRECORDED = {"total_count": 1, "results": [{}]}

# Jedes Werkzeug mit Argumenten, die eine Antwort mit Inhalt ergeben.
CALLS: dict[str, dict[str, Any]] = {
    "sbb_get_passenger_frequency": {"params": {"station_name": "Aarau"}},
    "sbb_get_rail_disruptions": {"params": {}},
    "sbb_get_real_estate_projects": {"params": {}},
    "sbb_get_trains_per_segment": {"params": {}},
    "sbb_get_platform_data": {"params": {}},
    "sbb_get_rolling_stock": {"params": {}},
    "sbb_compare_stations": {"params": {"stations": ["Aarau", "Bern"]}},
    "sbb_search_stations": {"params": {"query": "Wädenswil"}},
    "sbb_list_datasets": {},
}


def _answer(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if request.url.copy_with(query=None) == httpx.URL(BASE_URL):
        return httpx.Response(200, json=payload("catalog.json"))
    dataset = path.rsplit("/records", 1)[0].rsplit("/", 1)[-1]
    body = payload(RECORDED[dataset]) if dataset in RECORDED else UNRECORDED
    return httpx.Response(200, json=body)


def _source(handler) -> Any:
    """Ersetzt data.sbb.ch fuer alle Werkzeuge, auch `sbb_list_datasets`,
    das nicht ueber `_fetch_records` geht."""
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def _get_client() -> httpx.AsyncClient:
        return client

    return patch("sbb_opendata_mcp.server._get_client", _get_client)


# ---------------------------------------------------------------------------
# serverInfo
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", sorted(MODES))
async def test_server_info_nennt_die_paketversion(mode: str) -> None:
    async with Client(mcp, mode=mode) as client:
        info = client.server_info
        assert client.protocol_version == MODES[mode]

    assert info is not None
    assert info.version == __version__, (
        f"serverInfo.version ist {info.version!r}; ab 2026-07-28 steht das auf jeder Antwort"
    )
    assert info.title
    assert info.website_url == PROJECT_URL


async def test_ohne_angabe_bleibt_die_version_leer() -> None:
    """Negativkontrolle: das SDK hat keinen eigenen Default. Bekommt es einen,
    prueft der Test oben nicht mehr, dass wir die Version setzen."""
    async with Client(MCPServer("kontrolle"), mode="auto") as client:
        assert client.server_info is not None
        assert client.server_info.version == ""


# ---------------------------------------------------------------------------
# Werkzeug-Titel
# ---------------------------------------------------------------------------


async def test_jedes_werkzeug_traegt_title_und_annotations_title_gleich() -> None:
    """Beide, weil Clients vor `2025-06-18` nur `annotations.title` kennen —
    und gleich, weil zwei Titel fuer dasselbe Werkzeug einer zu viel sind."""
    async with Client(mcp, mode="2026-07-28") as client:
        tools = (await client.list_tools()).tools

    for tool in tools:
        assert tool.title, f"{tool.name} hat keinen title"
        assert tool.annotations is not None and tool.annotations.title == tool.title, tool.name


# ---------------------------------------------------------------------------
# outputSchema
# ---------------------------------------------------------------------------


async def test_jedes_werkzeug_deklariert_ein_output_schema() -> None:
    async with Client(mcp, mode="2026-07-28") as client:
        tools = (await client.list_tools()).tools

    assert {t.name for t in tools} == set(CALLS), "CALLS deckt nicht mehr jedes Werkzeug ab"
    missing = sorted(t.name for t in tools if not t.output_schema)
    assert not missing, f"ohne outputSchema: {missing}"
    for tool in tools:
        assert tool.output_schema["type"] == "object", tool.name


@pytest.mark.parametrize("mode", sorted(MODES))
@pytest.mark.parametrize("name", sorted(CALLS))
async def test_das_resultat_haelt_sein_schema(name: str, mode: str) -> None:
    """Der Client prueft `structuredContent` gegen das gelistete Schema und
    wirft `RuntimeError`, wenn es abweicht — dieser Test braucht dafuer keine
    eigene Zusicherung. Er faellt, sobald ein Werkzeug etwas anderes baut, als
    es deklariert."""
    with _source(_answer):
        async with Client(mcp, mode=mode) as client:
            result = await client.call_tool(name, CALLS[name])

    assert not result.is_error, result.content
    assert result.structured_content


async def test_der_server_haelt_sich_selbst_an_das_schema() -> None:
    """Gegenprobe: eine Quelle, deren Antwort nicht ins Schema passt.

    Das SDK validiert vor dem Versand. Kommt die Abweichung trotzdem als
    Erfolg heraus, ist das Schema nur Deko — dann waere die Deklaration eine
    Behauptung, die niemand prueft."""

    def _broken(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"total_count": "viele", "results": []})

    with _source(_broken):
        async with Client(mcp, mode="2026-07-28") as client:
            result = await client.call_tool("sbb_list_datasets", {})

    assert result.is_error


async def test_ein_fehlerresultat_ist_vom_schema_ausgenommen() -> None:
    """Fehler tragen `{error, upstream_unavailable}` statt des Umschlags. Das
    darf das Schema nicht brechen — die Spec nimmt `isError` aus, und die
    Unterscheidung «Quelle hat nicht geantwortet» muss den Client erreichen."""

    def _down(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, request=request)

    with _source(_down):
        async with Client(mcp, mode="2026-07-28") as client:
            result = await client.call_tool("sbb_list_datasets", {})

    assert result.is_error
    assert result.structured_content == {
        "error": result.content[0].text,
        "upstream_unavailable": True,
    }
