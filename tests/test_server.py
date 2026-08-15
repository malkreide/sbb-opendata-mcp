"""
Tests für den SBB Open Data MCP Server.
Drei Kategorien: Unit-Tests (Mock), Integration-Tests (Live API), Smoke-Tests.

Die Antworten der Datensätze, an denen die Befunde vom 2026-08-08 hängen, sind
**aufgezeichnet, nicht ausgedacht**: Quelle, Datum, Auswahlregel und SHA-256 je
Datei stehen in `tests/fixtures/PROVENANCE.md`, neu aufzeichnen mit
`python scripts/record_fixtures.py`.

Der wichtigste Test dieser Datei ist `test_every_field_the_server_uses_exists`.
Die Explore-API beantwortet ein unbekanntes Feld in `select` oder `order_by`
mit **HTTP 400**, nicht mit weniger Spalten — drei von zehn Werkzeugen waren
deshalb dauerhaft kaputt, ohne dass ein Test es gemerkt hätte.

Er prüft aber gegen die Aufzeichnung, nicht gegen die Quelle, und kann deren
Veralterung nicht bemerken. Das tut nur sein Gegenstück
`test_live_the_recording_still_matches_the_source` (`-m live`).
"""

import json
import logging
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import httpx

from sbb_opendata_mcp.server import (
    CompareStationsInput,
    PassengerFrequencyInput,
    PlatformDataInput,
    RailDisruptionsInput,
    RealEstateProjectsInput,
    ResponseFormat,
    RollingStockInput,
    StationSearchInput,
    TrainsPerSegmentInput,
    _handle_api_error,
    _pagination_meta,
    _to_number,
    sbb_compare_stations,
    sbb_get_passenger_frequency,
    sbb_get_platform_data,
    sbb_get_rail_disruptions,
    sbb_get_real_estate_projects,
    sbb_get_rolling_stock,
    sbb_get_trains_per_segment,
    sbb_list_datasets,
    sbb_search_stations,
)

# `tests/` ist ein Paket (`__init__.py`), also legt pytest das Repo-Wurzel-
# verzeichnis auf den Pfad und nicht `tests/` selbst. Der Import muss
# deshalb ueber das Paket laufen — sonst faellt die Sammlung unter dem
# CI-Kommando `PYTHONPATH=src pytest tests/`, waehrend sie lokal mit einem
# grosszuegigeren PYTHONPATH durchgeht.
from tests.fixture_data import declared_fields, payload, records


@pytest.fixture(autouse=True)
def _fresh_shared_client():
    """Jeder Test bekommt einen httpx-Client auf seinem eigenen Event-Loop.

    Der Server hält einen prozessweiten Client. `pytest-asyncio` gibt jedem
    Test einen eigenen Loop, und ein Client, der auf einem inzwischen
    geschlossenen Loop entstanden ist, meldet beim nächsten Zugriff
    `RuntimeError: Event loop is closed` — je nach Testreihenfolge.

    Das ist kein Schönheitsfehler: Die Live-Suite hat dadurch je nach
    Reihenfolge unterschiedliche Ergebnisse geliefert, und ein Testlauf, dessen
    Ausgang von der Reihenfolge abhängt, wird nach dem zweiten Fehlalarm nicht
    mehr gelesen. Genau diese Tests hätten zwei der drei Befunde gefunden.
    """
    import sbb_opendata_mcp.server as _srv

    _srv._client = None
    yield
    _srv._client = None


# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------


def _text(r):
    """Extract the text content from a tool's CallToolResult (str passthrough)."""
    return r.content[0].text if hasattr(r, "content") else r


# Aufgezeichnet, nicht ausgedacht — siehe tests/fixtures/PROVENANCE.md.
MOCK_PASSENGER_RECORD = records("passenger_frequency.json")[0]
MOCK_DISRUPTION_RECORD = records("rail_disruptions.json")[0]
STATIONS_SEARCH = payload("stations_search.json")
STATIONS_EXPIRED = payload("stations_expired.json")
CATALOG = payload("catalog.json")

MOCK_PLATFORM_RECORD = {
    "bps_name": "Zürich HB",
    "p_nr": "1/2",
    "perrontyp": "Mittelperron",
    "p_lange": 420,
    "perronflach_netto_m2": 3100.5,
    "perronflach_brutto_m2": 4200.0,
    "z_schienenfrei": "ja",
    "linie": 700,
    "km": 0.0,
}

MOCK_ROLLING_STOCK_RECORD = {
    "fahrzeug_typ": "IC 2000",
    "objekt": "001",
    "baudatum_fahrzeug": "1997-05-01",
    "sitzplatze_1_kl_total_zug": 120,
    "sitzplatze_2_kl_total_zug": 480,
    "sitzplatze_pro_zug_total": 600,
    "lange_uber_zug": 325000,
    "eigengewicht_tara": 420.0,
}

MOCK_TRAIN_SEGMENT_RECORD = {
    "strecke_bezeichnung": "Zürich HB - Winterthur",
    "isb": "SBB",
    "jahr": "2025",
    "geschaeftscode": "Personenverkehr",
    "anzahl_zuege": 245.0,
    "trassenkilometer": 28.5,
    "bp_von_abschnitt_bezeichnung": "Zürich HB",
    "bp_bis_abschnitt_bezeichnung": "Winterthur",
}


def mock_api_response(records: list, total: int | None = None) -> dict:
    return {"total_count": total or len(records), "results": records}


# ---------------------------------------------------------------------------
# Unit Tests: Helper functions
# ---------------------------------------------------------------------------


class TestHelperFunctions:
    def test_pagination_meta_basic(self):
        meta = _pagination_meta(total=100, limit=20, offset=0)
        assert meta["total_count"] == 100
        assert meta["returned"] == 20
        assert meta["has_more"] is True
        assert meta["next_offset"] == 20

    def test_pagination_meta_last_page(self):
        meta = _pagination_meta(total=25, limit=20, offset=20)
        assert meta["returned"] == 5
        assert meta["has_more"] is False
        assert meta["next_offset"] is None

    def test_pagination_meta_empty(self):
        meta = _pagination_meta(total=0, limit=20, offset=0)
        assert meta["returned"] == 0
        assert meta["has_more"] is False

    def test_handle_api_error_404(self):
        mock_resp = AsyncMock()
        mock_resp.status_code = 404
        mock_resp.text = "Not found"
        error = httpx.HTTPStatusError("404", request=AsyncMock(), response=mock_resp)
        result = _handle_api_error(error)
        assert "nicht gefunden" in _text(result).lower()

    def test_handle_api_error_429(self):
        mock_resp = AsyncMock()
        mock_resp.status_code = 429
        mock_resp.text = "Rate limit"
        error = httpx.HTTPStatusError("429", request=AsyncMock(), response=mock_resp)
        result = _handle_api_error(error)
        assert "rate-limit" in _text(result).lower() or "limit" in _text(result).lower()

    def test_handle_api_error_timeout(self):
        error = httpx.TimeoutException("Timeout")
        result = _handle_api_error(error)
        assert "zeitlimit" in _text(result).lower() or "timeout" in _text(result).lower()

    def test_handle_api_error_generic(self):
        result = _handle_api_error(ValueError("something went wrong"))
        assert "fehler" in _text(result).lower()

    # --- F-SEC-03: client messages must not leak upstream/internal details ---

    def test_http_error_does_not_leak_upstream_body(self):
        mock_resp = AsyncMock()
        mock_resp.status_code = 500
        mock_resp.text = "SECRET-STACKTRACE-internal.host:5432"
        error = httpx.HTTPStatusError("500", request=AsyncMock(), response=mock_resp)
        result = _handle_api_error(error)
        assert "SECRET-STACKTRACE" not in _text(result)
        assert "500" in _text(result)  # the status code itself is fine to surface

    def test_generic_error_does_not_leak_exception_string(self):
        result = _handle_api_error(ValueError("super-secret-internal-detail"))
        assert "super-secret-internal-detail" not in _text(result)
        assert "ValueError" not in _text(result)


# ---------------------------------------------------------------------------
# Unit Tests: Input models
# ---------------------------------------------------------------------------


class TestInputModels:
    def test_passenger_frequency_defaults(self):
        p = PassengerFrequencyInput()
        assert p.limit == 20
        assert p.offset == 0
        assert p.response_format == ResponseFormat.MARKDOWN

    def test_passenger_frequency_valid(self):
        p = PassengerFrequencyInput(station_name="Zürich HB", year="2024", canton="ZH")
        assert p.station_name == "Zürich HB"
        assert p.canton == "ZH"

    def test_passenger_frequency_canton_stripped(self):
        p = PassengerFrequencyInput(station_name="  Bern  ")
        assert p.station_name == "Bern"

    def test_compare_stations_min_length(self):
        with pytest.raises(Exception):
            CompareStationsInput(stations=["Zürich HB"])  # min 2

    def test_compare_stations_max_length(self):
        with pytest.raises(Exception):
            CompareStationsInput(stations=[f"Station {i}" for i in range(11)])  # max 10

    def test_station_search_min_length(self):
        with pytest.raises(Exception):
            StationSearchInput(query="Z")  # min 2 chars

    def test_rail_disruptions_limit_bounds(self):
        with pytest.raises(Exception):
            RailDisruptionsInput(limit=0)

    def test_trains_segment_valid(self):
        p = TrainsPerSegmentInput(operator="SBB", year="2025", traffic_type="Personenverkehr")
        assert p.operator == "SBB"

    def test_response_format_enum(self):
        p = RailDisruptionsInput(response_format="json")
        assert p.response_format == ResponseFormat.JSON

    # --- F-SEC-01: input validation hardening ---

    def test_year_must_be_four_digits(self):
        PassengerFrequencyInput(year="2024")  # valid
        for bad in ["2024 OR 1=1", "2024) OR (1=1", "24", "abcd", "20245"]:
            with pytest.raises(Exception):
                PassengerFrequencyInput(year=bad)

    def test_trains_year_must_be_four_digits(self):
        with pytest.raises(Exception):
            TrainsPerSegmentInput(year='2025" OR "1"="1')

    def test_compare_year_must_be_four_digits(self):
        with pytest.raises(Exception):
            CompareStationsInput(stations=["Zürich HB", "Bern"], year="2024 OR 1=1")

    def test_canton_must_be_two_letters(self):
        PassengerFrequencyInput(canton="ZH")  # valid
        for bad in ['Z"', "Z1", "12"]:
            with pytest.raises(Exception):
                PassengerFrequencyInput(canton=bad)


class TestOdsqlQuote:
    def test_escapes_double_quote(self):
        from sbb_opendata_mcp.server import _odsql_quote

        assert _odsql_quote('a"b') == 'a\\"b'

    def test_escapes_backslash_before_quote(self):
        from sbb_opendata_mcp.server import _odsql_quote

        # Backslash escaped first so a trailing escape cannot be neutralised.
        assert _odsql_quote('a\\"b') == 'a\\\\\\"b'

    def test_plain_value_unchanged(self):
        from sbb_opendata_mcp.server import _odsql_quote

        assert _odsql_quote("Zürich HB") == "Zürich HB"


class TestTransportSecurity:
    """SEC-005, inbound half.

    These tests used to cover only the builder. It was never called: the
    migration to mcp 2.x dropped ``transport_security=_transport_security()``
    from the constructor without re-adding it as a ``run()`` kwarg, so the
    allow-list became dead code while these tests stayed green. Coverage of a
    protection that is not wired is worse than no coverage, because it reads as
    assurance. ``TestTransportSecurityIsWired`` below closes that.
    """

    def test_defaults_to_localhost_with_protection(self, monkeypatch):
        from sbb_opendata_mcp.server import _transport_security

        monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
        monkeypatch.delenv("MCP_ALLOWED_ORIGINS", raising=False)
        ts = _transport_security("127.0.0.1")
        assert ts is not None
        assert ts.enable_dns_rebinding_protection is True
        assert "127.0.0.1" in ts.allowed_hosts
        assert "localhost" in ts.allowed_hosts

    def test_env_overrides_allowed_hosts_and_origins(self, monkeypatch):
        from sbb_opendata_mcp.server import _transport_security

        monkeypatch.setenv("MCP_ALLOWED_HOSTS", "sbb.example.com, sbb.example.com:*")
        monkeypatch.setenv("MCP_ALLOWED_ORIGINS", "https://sbb.example.com")
        ts = _transport_security()
        assert ts is not None
        assert ts.allowed_hosts == ["sbb.example.com", "sbb.example.com:*"]
        assert ts.allowed_origins == ["https://sbb.example.com"]

    def test_wildcard_bind_without_allowlist_stays_off(self, monkeypatch):
        """0.0.0.0 with no MCP_ALLOWED_HOSTS: the reachable name is unknown here.

        Returning the loopback default would reject every real request with
        HTTP 421 — the failure this whole change exists to prevent. So the
        protection stays off and the caller warns, which leaves the SDK's own
        behaviour for a non-loopback bind unchanged.
        """
        from sbb_opendata_mcp.server import _transport_security

        monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
        assert _transport_security("0.0.0.0") is None

    def test_wildcard_bind_with_allowlist_is_protected(self, monkeypatch):
        from sbb_opendata_mcp.server import _transport_security

        monkeypatch.setenv("MCP_ALLOWED_HOSTS", "sbb.example.com")
        ts = _transport_security("0.0.0.0")
        assert ts is not None
        assert ts.allowed_hosts == ["sbb.example.com"]


class TestBindHost:
    """The container asks for 0.0.0.0 via MCP_HOST; the code must read it."""

    def test_defaults_to_loopback(self, monkeypatch):
        from sbb_opendata_mcp.server import _bind_host

        monkeypatch.delenv("MCP_HOST", raising=False)
        assert _bind_host() == "127.0.0.1"

    def test_mcp_host_is_honoured(self, monkeypatch):
        """The regression this guards: the Dockerfile sets MCP_HOST=0.0.0.0 and
        publishes 8000. A hardcoded loopback bind means the published port
        reaches nothing inside the container."""
        from sbb_opendata_mcp.server import _bind_host

        monkeypatch.setenv("MCP_HOST", "0.0.0.0")
        assert _bind_host() == "0.0.0.0"

    def test_the_dockerfile_still_sets_it(self):
        """Pins the pair. If the Dockerfile stops setting MCP_HOST, reading it is
        pointless; if the code stops reading it, the container breaks. Either
        drift should be a deliberate edit, not a silent one."""
        import pathlib
        import re

        dockerfile = (pathlib.Path(__file__).resolve().parents[1] / "Dockerfile").read_text()
        assert re.search(r"MCP_HOST\s*=\s*0\.0\.0\.0", dockerfile)


class TestTransportSecurityIsWired:
    """The allow-list must reach the transport, not merely be constructible."""

    def test_run_receives_the_transport_security(self, monkeypatch):
        """Guards the actual regression.

        The builder and its unit tests survived the migration untouched; what
        vanished was the single kwarg that connected them to the server. So the
        assertion is on the call itself.
        """
        import sbb_opendata_mcp.server as srv

        monkeypatch.setenv("MCP_ALLOWED_HOSTS", "sbb.example.com")
        monkeypatch.setenv("MCP_HOST", "0.0.0.0")
        captured: dict = {}
        monkeypatch.setattr(type(srv.mcp), "run", lambda self, **kw: captured.update(kw))

        srv.main(["sbb-opendata-mcp", "--http"])

        assert captured["transport"] == "streamable-http"
        assert captured["host"] == "0.0.0.0"
        assert captured["transport_security"] is not None
        assert captured["transport_security"].allowed_hosts == ["sbb.example.com"]

    def test_stdio_gets_no_transport_kwargs(self, monkeypatch):
        """stdio has no listener, so a bind or allow-list there would be noise."""
        import sbb_opendata_mcp.server as srv

        captured: dict = {}
        monkeypatch.setattr(type(srv.mcp), "run", lambda self, **kw: captured.update(kw))

        srv.main(["sbb-opendata-mcp"])

        assert captured == {}

    def test_cli_host_overrides_the_environment(self, monkeypatch):
        import sbb_opendata_mcp.server as srv

        monkeypatch.setenv("MCP_HOST", "0.0.0.0")
        monkeypatch.setenv("MCP_ALLOWED_HOSTS", "sbb.example.com")
        captured: dict = {}
        monkeypatch.setattr(type(srv.mcp), "run", lambda self, **kw: captured.update(kw))

        srv.main(["sbb-opendata-mcp", "--http", "--host", "127.0.0.1", "--port", "9001"])

        assert captured["host"] == "127.0.0.1"
        assert captured["port"] == 9001


class TestLogging:
    """F-OBS-01: structured logging / observability."""

    def _capture(self):
        """Attach a list-collecting handler to the package logger."""
        from sbb_opendata_mcp.server import logger

        records: list[logging.LogRecord] = []
        handler = logging.Handler()
        handler.emit = records.append
        logger.addHandler(handler)
        prev_level = logger.level
        logger.setLevel(logging.DEBUG)
        return logger, handler, records, prev_level

    def test_configure_logging_idempotent_and_stderr(self):
        from sbb_opendata_mcp.server import configure_logging, logger

        before = len(logger.handlers)
        configure_logging()  # already configured at import — must not duplicate
        assert len(logger.handlers) == before
        stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
        assert stream_handlers, "expected a stream handler"
        # Logs must never go to stdout (stdio JSON-RPC channel). Test runners
        # (e.g. pytest) attach their own capture StreamHandlers to this logger,
        # so assert on intent rather than on every handler: nothing targets
        # stdout, and the handler we configured targets stderr.
        assert all(getattr(h, "stream", None) is not sys.stdout for h in stream_handlers)
        assert any(getattr(h, "stream", None) is sys.stderr for h in stream_handlers)
        assert logger.propagate is False

    def test_json_formatter_outputs_valid_json(self):
        from sbb_opendata_mcp.server import _JsonFormatter

        rec = logging.LogRecord("sbb_opendata_mcp", logging.INFO, __file__, 1, "hello", None, None)
        rec.fields = {"dataset": "perron", "status": 200}
        parsed = json.loads(_JsonFormatter().format(rec))
        assert parsed["msg"] == "hello"
        assert parsed["level"] == "INFO"
        assert parsed["dataset"] == "perron"
        assert parsed["status"] == 200

    def test_handle_api_error_logs_http_status(self):
        logger, handler, records, prev = self._capture()
        try:
            mock_resp = AsyncMock()
            mock_resp.status_code = 429
            mock_resp.text = "rate limit"
            err = httpx.HTTPStatusError("429", request=AsyncMock(), response=mock_resp)
            _handle_api_error(err)
        finally:
            logger.removeHandler(handler)
            logger.setLevel(prev)
        assert any(r.getMessage() == "upstream_http_error" for r in records)

    def test_handle_api_error_logs_generic_at_error_level(self):
        logger, handler, records, prev = self._capture()
        try:
            _handle_api_error(ValueError("boom"))
        finally:
            logger.removeHandler(handler)
            logger.setLevel(prev)
        assert any(r.levelno >= logging.ERROR for r in records)

    @pytest.mark.asyncio
    async def test_fetch_records_logs_response(self):
        logger, handler, records, prev = self._capture()
        try:

            class _Resp:
                status_code = 200

                def raise_for_status(self):
                    return None

                def json(self):
                    return {"total_count": 3, "results": []}

            class _Client:
                async def get(self, *a, **k):
                    return _Resp()

            from sbb_opendata_mcp import server

            with patch.object(server, "_get_client", AsyncMock(return_value=_Client())):
                await server._fetch_records("perron", limit=5)
        finally:
            logger.removeHandler(handler)
            logger.setLevel(prev)
        msgs = [r.getMessage() for r in records]
        assert "upstream_response" in msgs


class TestSharedClient:
    """F-SCALE-01: shared httpx client + concurrent fan-out."""

    @pytest.mark.asyncio
    async def test_get_client_returns_singleton(self):
        from sbb_opendata_mcp import server

        await server._aclose_client()
        try:
            c1 = await server._get_client()
            c2 = await server._get_client()
            assert c1 is c2
            assert isinstance(c1, httpx.AsyncClient)
            assert c1.is_closed is False
        finally:
            await server._aclose_client()

    @pytest.mark.asyncio
    async def test_aclose_client_closes_and_recreates(self):
        from sbb_opendata_mcp import server

        c1 = await server._get_client()
        await server._aclose_client()
        assert c1.is_closed is True
        c2 = await server._get_client()
        assert c2 is not c1
        await server._aclose_client()

    @pytest.mark.asyncio
    async def test_compare_stations_fans_out_concurrently(self):
        """All per-station fetches should be in flight at once, not serialized."""
        import asyncio

        in_flight = 0
        peak = 0

        async def slow_fetch(dataset_id, **kwargs):
            nonlocal in_flight, peak
            in_flight += 1
            peak = max(peak, in_flight)
            await asyncio.sleep(0.02)
            in_flight -= 1
            if "passagier" in dataset_id:
                return mock_api_response([MOCK_PASSENGER_RECORD])
            return mock_api_response([MOCK_PLATFORM_RECORD])

        with patch("sbb_opendata_mcp.server._fetch_records", side_effect=slow_fetch):
            result = await sbb_compare_stations(
                CompareStationsInput(stations=["Zürich HB", "Bern", "Basel SBB"], year="2024")
            )
        assert MOCK_PASSENGER_RECORD["bahnhof_gare_stazione"] in _text(result)
        # 3 stations running concurrently → peak well above 1.
        assert peak >= 3


# ---------------------------------------------------------------------------
# Unit Tests: Tool outputs (mocked API)
# ---------------------------------------------------------------------------


class TestPassengerFrequencyTool:
    @pytest.mark.asyncio
    async def test_markdown_output(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([MOCK_PASSENGER_RECORD]),
        ):
            result = await sbb_get_passenger_frequency(
                PassengerFrequencyInput(station_name="Zürich HB", year="2024")
            )
        assert MOCK_PASSENGER_RECORD["bahnhof_gare_stazione"] in _text(result)
        assert "410" in _text(result) or "DTV" in _text(result) or "Passagier" in _text(result)

    @pytest.mark.asyncio
    async def test_json_output(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([MOCK_PASSENGER_RECORD]),
        ):
            result = await sbb_get_passenger_frequency(
                PassengerFrequencyInput(station_name="Zürich HB", response_format="json")
            )
        parsed = json.loads(_text(result))
        assert "results" in parsed
        assert "pagination" in parsed
        assert parsed["results"][0]["bahnhof_gare_stazione"] == MOCK_PASSENGER_RECORD["bahnhof_gare_stazione"]

    @pytest.mark.asyncio
    async def test_empty_results(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([]),
        ):
            result = await sbb_get_passenger_frequency(
                PassengerFrequencyInput(station_name="NichtExistierendXYZ")
            )
        assert (
            "keine" in _text(result).lower()
            or "not found" in _text(result).lower()
            or "gefunden" in _text(result).lower()
        )

    @pytest.mark.asyncio
    async def test_pagination_info_shown(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([MOCK_PASSENGER_RECORD] * 5, total=100),
        ):
            result = await sbb_get_passenger_frequency(PassengerFrequencyInput(limit=5))
        assert "100" in _text(result) or "weitere" in _text(result).lower()


class TestRailDisruptionsTool:
    @pytest.mark.asyncio
    async def test_markdown_output(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([MOCK_DISRUPTION_RECORD]),
        ):
            result = await sbb_get_rail_disruptions(RailDisruptionsInput())
        assert MOCK_DISRUPTION_RECORD["title"][:20] in _text(result)

    @pytest.mark.asyncio
    async def test_json_output(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([MOCK_DISRUPTION_RECORD]),
        ):
            result = await sbb_get_rail_disruptions(RailDisruptionsInput(response_format="json"))
        parsed = json.loads(_text(result))
        assert "results" in parsed

    @pytest.mark.asyncio
    async def test_no_disruptions(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([]),
        ):
            result = await sbb_get_rail_disruptions(RailDisruptionsInput())
        assert "keine" in _text(result).lower()


class TestPlatformDataTool:
    @pytest.mark.asyncio
    async def test_markdown_output(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([MOCK_PLATFORM_RECORD]),
        ):
            result = await sbb_get_platform_data(PlatformDataInput(station_name="Zürich HB"))
        assert MOCK_PLATFORM_RECORD["bps_name"] in _text(result)
        assert "420" in _text(result) or "Mittelperron" in _text(result)

    @pytest.mark.asyncio
    async def test_json_output(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([MOCK_PLATFORM_RECORD]),
        ):
            result = await sbb_get_platform_data(PlatformDataInput(response_format="json"))
        parsed = json.loads(_text(result))
        assert "results" in parsed


class TestRollingStockTool:
    @pytest.mark.asyncio
    async def test_markdown_output(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([MOCK_ROLLING_STOCK_RECORD]),
        ):
            result = await sbb_get_rolling_stock(RollingStockInput(vehicle_type="IC 2000"))
        assert "IC 2000" in _text(result)

    @pytest.mark.asyncio
    async def test_seat_capacity_shown(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([MOCK_ROLLING_STOCK_RECORD]),
        ):
            result = await sbb_get_rolling_stock(RollingStockInput())
        assert "600" in _text(result) or "480" in _text(result) or "120" in _text(result)


class TestTrainsPerSegmentTool:
    @pytest.mark.asyncio
    async def test_markdown_output(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([MOCK_TRAIN_SEGMENT_RECORD]),
        ):
            result = await sbb_get_trains_per_segment(TrainsPerSegmentInput(operator="SBB", year="2025"))
        assert "SBB" in _text(result) or "Zürich" in _text(result) or "245" in _text(result)

    @pytest.mark.asyncio
    async def test_json_output(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([MOCK_TRAIN_SEGMENT_RECORD]),
        ):
            result = await sbb_get_trains_per_segment(TrainsPerSegmentInput(response_format="json"))
        parsed = json.loads(_text(result))
        assert "results" in parsed


class TestCompareStationsTool:
    @pytest.mark.asyncio
    async def test_two_stations(self):
        freq_resp = mock_api_response([MOCK_PASSENGER_RECORD])
        plat_resp = mock_api_response([MOCK_PLATFORM_RECORD, MOCK_PLATFORM_RECORD])

        call_count = 0

        async def mock_fetch(dataset_id, **kwargs):
            nonlocal call_count
            call_count += 1
            if "passagier" in dataset_id:
                return freq_resp
            return plat_resp

        with patch("sbb_opendata_mcp.server._fetch_records", side_effect=mock_fetch):
            result = await sbb_compare_stations(
                CompareStationsInput(stations=["Zürich HB", "Bern"], year="2024")
            )
        assert MOCK_PASSENGER_RECORD["bahnhof_gare_stazione"] in _text(result)
        assert "2024" in _text(result)


class TestStationSearchTool:
    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=STATIONS_SEARCH,
        ):
            result = await sbb_search_stations(StationSearchInput(query="Wädenswil"))
        first = STATIONS_SEARCH["results"][0]
        # Aus der Fixture abgeleitet. Die erfundene Vorgaengerin trug die drei
        # deutschen Feldnamen, die es in diesem Datensatz nicht gibt — mit ihr
        # bestand der Test, waehrend jede echte Anfrage HTTP 400 lieferte.
        assert first["designationofficial"] in _text(result)
        assert str(first["number"]) in _text(result)
        assert first["cantonabbreviation"] in _text(result)
        assert first["businessorganisationdescriptionde"] in _text(result)

    @pytest.mark.asyncio
    async def test_no_results(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([]),
        ):
            result = await sbb_search_stations(StationSearchInput(query="XYZNOTEXIST"))
        assert "keine" in _text(result).lower() or "not found" in _text(result).lower()


class TestToNumber:
    """F-SEC-05: robust numeric coercion."""

    def test_numbers_and_numeric_strings(self):
        assert _to_number(1200) == 1200.0
        assert _to_number(1200.5) == 1200.5
        assert _to_number("1200") == 1200.0

    def test_non_numeric_returns_none(self):
        for bad in (None, "–", "n/a", "", True, False):
            assert _to_number(bad) is None


class TestRealEstateTool:
    """F-SEC-05: a numeric-string area must not trigger a formatting error."""

    @pytest.mark.asyncio
    async def test_area_as_string_does_not_error(self):
        record = {
            "titlede": "Wohnüberbauung Test",
            "city": "Zürich",
            "phase": "CONSTRUCTION",
            "mainusefulareastotal": "1200",  # string from API used to crash {:,}
        }
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([record]),
        ):
            result = await sbb_get_real_estate_projects(RealEstateProjectsInput(city="Zürich"))
        assert "Fehler" not in _text(result)
        assert "1'200" in _text(result)  # formatted with thousands separator


class TestCompareStationsFormat:
    """F-ARCH-01: compare_stations supports response_format like other tools."""

    @pytest.mark.asyncio
    async def test_json_output(self):
        async def mock_fetch(dataset_id, **kwargs):
            if "passagier" in dataset_id:
                return mock_api_response([MOCK_PASSENGER_RECORD])
            return mock_api_response([MOCK_PLATFORM_RECORD])

        with patch("sbb_opendata_mcp.server._fetch_records", side_effect=mock_fetch):
            result = await sbb_compare_stations(
                CompareStationsInput(stations=["Zürich HB", "Bern"], year="2024", response_format="json")
            )
        parsed = json.loads(_text(result))
        assert parsed["year"] == "2024"
        assert len(parsed["stations"]) == 2


class TestStructuredOutput:
    """F-SDK-01: tools return structuredContent alongside human-readable text."""

    @pytest.mark.asyncio
    async def test_markdown_mode_still_includes_structured_content(self):
        from mcp.types import CallToolResult

        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([MOCK_PASSENGER_RECORD]),
        ):
            result = await sbb_get_passenger_frequency(
                PassengerFrequencyInput(station_name="Zürich HB", year="2024")
            )
        # Human-readable markdown is preserved (non-breaking) ...
        assert isinstance(result, CallToolResult)
        assert "## SBB Passagierfrequenz" in result.content[0].text
        # ... and the underlying records are exposed as structured content.
        assert (
            result.structured_content["results"][0]["bahnhof_gare_stazione"]
            == MOCK_PASSENGER_RECORD["bahnhof_gare_stazione"]
        )
        assert "pagination" in result.structured_content

    @pytest.mark.asyncio
    async def test_empty_result_still_structured(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([]),
        ):
            result = await sbb_get_platform_data(PlatformDataInput(station_name="XYZ"))
        assert result.structured_content["results"] == []

    @pytest.mark.asyncio
    async def test_error_result_flagged_in_structured_content(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            side_effect=ValueError("boom"),
        ):
            result = await sbb_get_rolling_stock(RollingStockInput())
        assert "error" in result.structured_content
        assert "Fehler" in result.content[0].text


# ---------------------------------------------------------------------------
# Live API Smoke Tests (require network)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.live
async def test_live_zurich_hb_frequency():
    """Live-Test: Passagierfrequenz Zürich HB 2024."""
    result = await sbb_get_passenger_frequency(PassengerFrequencyInput(station_name="Zürich HB", year="2024"))
    assert "Zürich HB" in _text(result)
    assert "2024" in _text(result)
    assert "410" in _text(result)  # ca. 410'000 DTV


@pytest.mark.asyncio
@pytest.mark.live
async def test_live_rail_disruptions():
    """Live-Test: Aktuelle Bahnverkehrsmeldungen."""
    result = await sbb_get_rail_disruptions(RailDisruptionsInput(limit=5))
    assert isinstance(_text(result), str)
    assert len(_text(result)) > 50


@pytest.mark.asyncio
@pytest.mark.live
async def test_live_list_datasets():
    """Live-Test: Alle Datensätze auflisten."""
    result = await sbb_list_datasets()
    assert "passagierfrequenz" in _text(result).lower()
    assert "SBB" in _text(result)


@pytest.mark.asyncio
@pytest.mark.live
async def test_live_compare_zurich_bern():
    """Live-Test: Vergleich Zürich HB vs. Bern."""
    result = await sbb_compare_stations(CompareStationsInput(stations=["Zürich HB", "Bern"], year="2024"))
    assert "Zürich HB" in _text(result) or "Bern" in _text(result)


@pytest.mark.asyncio
@pytest.mark.live
async def test_live_search_waedenswil():
    """Live-Test: Haltestellensuche Wädenswil."""
    result = await sbb_search_stations(StationSearchInput(query="Wädenswil", canton="ZH"))
    assert "Wädenswil" in _text(result)


# ---------------------------------------------------------------------------
# Der Vertrag: jedes Feld, das der Server verwendet, muss die Quelle führen
# ---------------------------------------------------------------------------


def fields_the_server_uses() -> list[tuple[str, tuple[str, ...]]]:
    """(Datensatz, verwendete Feldnamen) — Sortierschlüssel ohne asc/desc.

    Eine Liste, zwei Prüfungen: `TestFieldContract` hält sie gegen die
    aufgezeichnete Deklaration, `test_live_the_recording_still_matches_the_source`
    gegen die Quelle von heute. Als zwei Kopien wuerden ausgerechnet die beiden
    Tests auseinanderlaufen, die Auseinanderlaufen bemerken sollen.
    """
    from sbb_opendata_mcp.server import (
        DATASET_PASSENGER_FREQUENCY,
        DATASET_PLATFORMS,
        DATASET_RAIL_TRAFFIC,
        DATASET_STATIONS,
        DATASET_TRAINS_PER_SEGMENT,
        FIELDS_STATIONS,
        FIELDS_TRAINS_PER_SEGMENT,
        ORDER_BY_COMPARE_STATIONS,
        ORDER_BY_PASSENGER_FREQUENCY,
        ORDER_BY_PLATFORMS,
        ORDER_BY_RAIL_TRAFFIC,
        ORDER_BY_TRAINS_PER_SEGMENT,
    )

    return [
        (DATASET_STATIONS, FIELDS_STATIONS),
        (DATASET_STATIONS, ("designationofficial", "cantonabbreviation", "validto")),
        (DATASET_TRAINS_PER_SEGMENT, FIELDS_TRAINS_PER_SEGMENT),
        (DATASET_TRAINS_PER_SEGMENT, (ORDER_BY_TRAINS_PER_SEGMENT.split()[0],)),
        (DATASET_PASSENGER_FREQUENCY, (ORDER_BY_PASSENGER_FREQUENCY.split()[0],)),
        (DATASET_PASSENGER_FREQUENCY, (ORDER_BY_COMPARE_STATIONS.split()[0],)),
        (DATASET_RAIL_TRAFFIC, (ORDER_BY_RAIL_TRAFFIC.split()[0],)),
        (DATASET_PLATFORMS, (ORDER_BY_PLATFORMS.split()[0],)),
    ]


class TestFieldContract:
    """Warum es diese Klasse gibt.

    Die Explore-v2.1-API beantwortet ein unbekanntes Feld in `select` oder
    `order_by` mit **HTTP 400** — nicht mit weniger Spalten. Ein Feldname, der
    nicht mehr stimmt, fällt deshalb nicht als Lücke auf, sondern als Ausfall,
    und der Nutzer liest «API-Anfrage fehlgeschlagen».

    Genau das war der Zustand: Die Haltestellensuche wählte sieben **deutsche**
    Feldnamen aus einem Datensatz, der ausschliesslich **englische** führt —
    keiner der sieben existierte, und jede Suche scheiterte. Die Katalogliste
    sortierte nach `metas.default.title`, das der Katalog-Endpunkt nicht kennt.
    Beides seit jeher, beides von keinem Test bemerkt, weil die erfundenen
    Payloads die erfundenen Namen trugen.

    Die Quelle deklariert ihre Felder selbst (`fields[].name` unter
    `/datasets/<id>`). Diese Deklaration ist aufgezeichnet, und hier wird jeder
    Feldname des Servers dagegen gehalten.
    """

    def test_every_field_the_server_uses_exists(self):
        problems: list[str] = []
        for dataset, fields in fields_the_server_uses():
            available = declared_fields(dataset)
            for f in fields:
                if f not in available:
                    problems.append(f"{dataset}: '{f}' gibt es nicht")
        assert not problems, (
            "Feldnamen, die die Quelle nicht führt — die API antwortet darauf "
            "mit HTTP 400:\n  " + "\n  ".join(problems)
        )

    def test_the_german_field_names_really_are_gone(self):
        """Die Gegenprobe zum Befund, als Zusicherung.

        Ohne diesen Test bestünde der obige auch dann, wenn jemand die
        Felddeklaration versehentlich vom falschen Datensatz aufzeichnet.
        """
        from sbb_opendata_mcp.server import DATASET_STATIONS

        available = declared_fields(DATASET_STATIONS)
        for gone in (
            "bezeichnung_offiziell",
            "uic",
            "kanton_kuerzel",
            "dst_nr",
            "tu_nummer",
            "geopos_ost",
            "geopos_nord",
        ):
            assert gone not in available, (
                f"'{gone}' gibt es im DiDok-Datensatz wieder — dann ist der "
                "Befund vom 2026-08-08 überholt und diese Datei gehört geprüft."
            )

    def test_the_catalog_sort_key_is_not_a_dataset_field(self):
        """`metas.default.title` war der Sortierschlüssel und existiert nicht."""
        from sbb_opendata_mcp.server import ORDER_BY_CATALOG

        assert ORDER_BY_CATALOG.split()[0] == "title"
        assert "metas" not in ORDER_BY_CATALOG


@pytest.mark.asyncio
@pytest.mark.live
async def test_live_the_recording_still_matches_the_source():
    """Die Gegenseite zu `TestFieldContract`: hält die Aufzeichnung noch?

    `TestFieldContract` hält den Server gegen `dataset_fields.json` — also
    gegen eine Aufzeichnung. Wechselt die Quelle einen Feldnamen, wird die
    Aufzeichnung still falsch: Der Offline-Test bleibt grün, weil er gegen
    dieselbe veraltete Datei prüft, und die Werkzeuge kassieren produktiv
    HTTP 400. Genau dieser Zustand bestand am 2026-08-03, und keine der
    Zusicherungen dieser Datei konnte ihn widerlegen — eine Aufzeichnung kann
    ihre eigene Veralterung nicht bemerken.

    Nur dieser Test fragt die Quelle. Er läuft in `.github/workflows/live.yml`,
    nicht in der CI der Pull Requests.
    """
    from sbb_opendata_mcp.server import BASE_URL

    datasets = sorted({ds for ds, _ in fields_the_server_uses()})

    live: dict[str, set[str]] = {}
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        for ds in datasets:
            response = await client.get(f"{BASE_URL}/{ds}")
            response.raise_for_status()
            names = {f["name"] for f in response.json().get("fields", [])}
            assert names, (
                f"{ds}: Die Quelle deklariert keine Felder. Ohne Deklaration "
                "lässt sich kein `select` mehr gegen sie halten — erst die "
                "Quelle abfragen, dann einordnen."
            )
            live[ds] = names

    # 1. Produktiv kaputt: Ein Feld, das der Server verwendet, führt die Quelle
    #    heute nicht mehr. Jede Anfrage damit endet in HTTP 400.
    broken = [
        f"{ds}: '{field}'"
        for ds, fields in fields_the_server_uses()
        for field in fields
        if field not in live[ds]
    ]
    assert not broken, (
        "Feldnamen, die der Server verwendet und die die Quelle NICHT MEHR "
        "führt. Die Explore-API beantwortet sie mit HTTP 400 — diese Werkzeuge "
        "sind produktiv kaputt:\n  " + "\n  ".join(broken)
    )

    # 2. Aufzeichnung veraltet: Ein Feld ist aus der Deklaration verschwunden.
    #    Der Server verwendet es (noch) nicht, aber jeder Offline-Test prüft ab
    #    jetzt gegen eine Fiktion.
    vanished = [f"{ds}: '{field}'" for ds in datasets for field in sorted(declared_fields(ds) - live[ds])]
    assert not vanished, (
        "Felder aus `tests/fixtures/dataset_fields.json`, die die Quelle nicht "
        "mehr führt. Der Server verwendet sie nicht, aber die Aufzeichnung ist "
        "damit überholt und die Offline-Tests prüfen gegen einen Stand, den es "
        "nicht mehr gibt. Neu aufzeichnen: `python scripts/record_fixtures.py`"
        "\n  " + "\n  ".join(vanished)
    )


class TestStationValidity:
    """Ein Füllwert, der wie ein Datum aussieht.

    Die DiDok-Liste schreibt «unbefristet gültig» als `9999-12-31`. Gemessen am
    2026-08-08 tragen 59'515 von 59'530 Einträgen genau diesen Wert — dieselbe
    Form, die in `swiss-democracy-mcp` als Parteiparole hinausging.
    """

    @pytest.mark.asyncio
    async def test_the_sentinel_is_not_printed_as_a_date(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=STATIONS_SEARCH,
        ):
            result = await sbb_search_stations(StationSearchInput(query="Wädenswil"))
        assert any(r["validto"] == "9999-12-31" for r in STATIONS_SEARCH["results"]), (
            "Fixture ohne Füllwert — dann prüft dieser Test nichts"
        )
        assert "9999-12-31" not in _text(result)
        assert "unbefristet" in _text(result)

    @pytest.mark.asyncio
    async def test_a_real_expiry_date_survives(self):
        """Die Gegenprobe: ein echtes Ablaufdatum darf nicht verschwinden.

        Nur 15 von 59'530 Einträgen tragen eines. «Die ersten N» hätten keinen
        davon getroffen; die Fixture ist deshalb nach Merkmal ausgewählt.
        """
        expired = [r for r in STATIONS_EXPIRED["results"] if r["validto"] != "9999-12-31"]
        assert expired, "Fixture ohne echtes Ablaufdatum — Auswahlregel prüfen"
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=STATIONS_EXPIRED,
        ):
            result = await sbb_search_stations(StationSearchInput(query="Bahnhof"))
        assert expired[0]["validto"] in _text(result)
