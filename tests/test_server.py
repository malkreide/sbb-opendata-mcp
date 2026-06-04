"""
Tests für den SBB Open Data MCP Server.
Drei Kategorien: Unit-Tests (Mock), Integration-Tests (Live API), Smoke-Tests.
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
    ConstructionProjectsInput,
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
    sbb_get_infrastructure_construction_projects,
    sbb_get_passenger_frequency,
    sbb_get_platform_data,
    sbb_get_rail_disruptions,
    sbb_get_real_estate_projects,
    sbb_get_rolling_stock,
    sbb_get_trains_per_segment,
    sbb_list_datasets,
    sbb_search_stations,
)

# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------


def _text(r):
    """Extract the text content from a tool's CallToolResult (str passthrough)."""
    return r.content[0].text if hasattr(r, "content") else r


MOCK_PASSENGER_RECORD = {
    "bahnhof_gare_stazione": "Zürich HB",
    "kt_ct_cantone": "ZH",
    "isb_gi": "SBB",
    "jahr_annee_anno": "2024",
    "dtv_tjm_tgm": 410700.0,
    "dwv_tmjo_tfm": 438300.0,
    "dnwv_tmjno_tmgnl": 349500.0,
    "evu_ef_itf": "SBB, SOB, Thurbo",
    "bemerkungen": "Umfasst auch ZLOE und ZMUS. Ohne SZU.",
    "geopos": {"lon": 8.540212, "lat": 47.378176},
}

MOCK_DISRUPTION_RECORD = {
    "title": "Unterbruch: Zürich HB – Winterthur",
    "description": "Streckensperrung wegen Infrastrukturschaden.",
    "published": "2026-03-08T10:00:00+00:00",
    "startdatetime": "2026-03-08T09:30:00+00:00",
    "enddatetime": "2026-03-08T14:00:00+00:00",
    "link": "https://www.sbb.ch/de/travel-information/rail-traffic-information.html",
    "type": "2",
    "author": "SBB",
}

MOCK_CONSTRUCTION_RECORD = {
    "projektname": "Barrierefreier Bahnzugang Zürich Stadelhofen",
    "projektort": "Zürich",
    "art": "ausbau",
    "ort": "bahnhof",
    "link1_title": "Webseite",
    "link1_url": "https://company.sbb.ch/de/ueber-die-sbb/projekte/projekte-zuerich.html",
    "angebotsschritt": "Ausbauschritt 2035",
}

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
    def test_defaults_to_localhost_with_protection(self, monkeypatch):
        from sbb_opendata_mcp.server import _transport_security

        monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
        monkeypatch.delenv("MCP_ALLOWED_ORIGINS", raising=False)
        ts = _transport_security()
        assert ts.enable_dns_rebinding_protection is True
        assert "127.0.0.1" in ts.allowed_hosts
        assert "localhost" in ts.allowed_hosts

    def test_env_overrides_allowed_hosts_and_origins(self, monkeypatch):
        from sbb_opendata_mcp.server import _transport_security

        monkeypatch.setenv("MCP_ALLOWED_HOSTS", "sbb.example.com, sbb.example.com:*")
        monkeypatch.setenv("MCP_ALLOWED_ORIGINS", "https://sbb.example.com")
        ts = _transport_security()
        assert ts.allowed_hosts == ["sbb.example.com", "sbb.example.com:*"]
        assert ts.allowed_origins == ["https://sbb.example.com"]


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
        # Logs must never go to stdout (stdio JSON-RPC channel).
        assert all(h.stream is sys.stderr for h in stream_handlers)
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
        assert "Zürich HB" in _text(result) or "Bern" in _text(result)
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
        assert "Zürich HB" in _text(result)
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
        assert parsed["results"][0]["bahnhof_gare_stazione"] == "Zürich HB"

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
        assert "Unterbruch" in _text(result) or "Zürich" in _text(result)

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


class TestConstructionProjectsTool:
    @pytest.mark.asyncio
    async def test_markdown_output(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([MOCK_CONSTRUCTION_RECORD]),
        ):
            result = await sbb_get_infrastructure_construction_projects(
                ConstructionProjectsInput(city="Zürich")
            )
        assert "Zürich" in _text(result) or "Bahnzugang" in _text(result)

    @pytest.mark.asyncio
    async def test_json_output(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([MOCK_CONSTRUCTION_RECORD]),
        ):
            result = await sbb_get_infrastructure_construction_projects(
                ConstructionProjectsInput(response_format="json")
            )
        parsed = json.loads(_text(result))
        assert "results" in parsed


class TestPlatformDataTool:
    @pytest.mark.asyncio
    async def test_markdown_output(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([MOCK_PLATFORM_RECORD]),
        ):
            result = await sbb_get_platform_data(PlatformDataInput(station_name="Zürich HB"))
        assert "Zürich HB" in _text(result)
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
        assert "Zürich HB" in _text(result) or "Bern" in _text(result)
        assert "2024" in _text(result)


class TestStationSearchTool:
    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        mock_station = {
            "bezeichnung_offiziell": "Wädenswil",
            "uic": 8503353,
            "kanton_kuerzel": "ZH",
        }
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([mock_station]),
        ):
            result = await sbb_search_stations(StationSearchInput(query="Wädenswil"))
        assert "Wädenswil" in _text(result)
        assert "ZH" in _text(result)

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
        assert result.structuredContent["results"][0]["bahnhof_gare_stazione"] == "Zürich HB"
        assert "pagination" in result.structuredContent

    @pytest.mark.asyncio
    async def test_empty_result_still_structured(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([]),
        ):
            result = await sbb_get_platform_data(PlatformDataInput(station_name="XYZ"))
        assert result.structuredContent["results"] == []

    @pytest.mark.asyncio
    async def test_error_result_flagged_in_structured_content(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            side_effect=ValueError("boom"),
        ):
            result = await sbb_get_rolling_stock(RollingStockInput())
        assert "error" in result.structuredContent
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
