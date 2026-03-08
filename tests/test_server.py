"""
Tests für den SBB Open Data MCP Server.
Drei Kategorien: Unit-Tests (Mock), Integration-Tests (Live API), Smoke-Tests.
"""

import json
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
    ResponseFormat,
    RollingStockInput,
    StationSearchInput,
    TrainsPerSegmentInput,
    _handle_api_error,
    _pagination_meta,
    sbb_compare_stations,
    sbb_get_infrastructure_construction_projects,
    sbb_get_passenger_frequency,
    sbb_get_platform_data,
    sbb_get_rail_disruptions,
    sbb_get_rolling_stock,
    sbb_get_trains_per_segment,
    sbb_list_datasets,
    sbb_search_stations,
)

# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------

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
        assert "nicht gefunden" in result.lower()

    def test_handle_api_error_429(self):
        mock_resp = AsyncMock()
        mock_resp.status_code = 429
        mock_resp.text = "Rate limit"
        error = httpx.HTTPStatusError("429", request=AsyncMock(), response=mock_resp)
        result = _handle_api_error(error)
        assert "rate-limit" in result.lower() or "limit" in result.lower()

    def test_handle_api_error_timeout(self):
        error = httpx.TimeoutException("Timeout")
        result = _handle_api_error(error)
        assert "zeitlimit" in result.lower() or "timeout" in result.lower()

    def test_handle_api_error_generic(self):
        result = _handle_api_error(ValueError("something went wrong"))
        assert "fehler" in result.lower()


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
        assert "Zürich HB" in result
        assert "410" in result or "DTV" in result or "Passagier" in result

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
        parsed = json.loads(result)
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
        assert "keine" in result.lower() or "not found" in result.lower() or "gefunden" in result.lower()

    @pytest.mark.asyncio
    async def test_pagination_info_shown(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([MOCK_PASSENGER_RECORD] * 5, total=100),
        ):
            result = await sbb_get_passenger_frequency(PassengerFrequencyInput(limit=5))
        assert "100" in result or "weitere" in result.lower()


class TestRailDisruptionsTool:
    @pytest.mark.asyncio
    async def test_markdown_output(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([MOCK_DISRUPTION_RECORD]),
        ):
            result = await sbb_get_rail_disruptions(RailDisruptionsInput())
        assert "Unterbruch" in result or "Zürich" in result

    @pytest.mark.asyncio
    async def test_json_output(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([MOCK_DISRUPTION_RECORD]),
        ):
            result = await sbb_get_rail_disruptions(RailDisruptionsInput(response_format="json"))
        parsed = json.loads(result)
        assert "results" in parsed

    @pytest.mark.asyncio
    async def test_no_disruptions(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([]),
        ):
            result = await sbb_get_rail_disruptions(RailDisruptionsInput())
        assert "keine" in result.lower()


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
        assert "Zürich" in result or "Bahnzugang" in result

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
        parsed = json.loads(result)
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
        assert "Zürich HB" in result
        assert "420" in result or "Mittelperron" in result

    @pytest.mark.asyncio
    async def test_json_output(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([MOCK_PLATFORM_RECORD]),
        ):
            result = await sbb_get_platform_data(PlatformDataInput(response_format="json"))
        parsed = json.loads(result)
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
        assert "IC 2000" in result

    @pytest.mark.asyncio
    async def test_seat_capacity_shown(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([MOCK_ROLLING_STOCK_RECORD]),
        ):
            result = await sbb_get_rolling_stock(RollingStockInput())
        assert "600" in result or "480" in result or "120" in result


class TestTrainsPerSegmentTool:
    @pytest.mark.asyncio
    async def test_markdown_output(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([MOCK_TRAIN_SEGMENT_RECORD]),
        ):
            result = await sbb_get_trains_per_segment(TrainsPerSegmentInput(operator="SBB", year="2025"))
        assert "SBB" in result or "Zürich" in result or "245" in result

    @pytest.mark.asyncio
    async def test_json_output(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([MOCK_TRAIN_SEGMENT_RECORD]),
        ):
            result = await sbb_get_trains_per_segment(TrainsPerSegmentInput(response_format="json"))
        parsed = json.loads(result)
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
        assert "Zürich HB" in result or "Bern" in result
        assert "2024" in result


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
        assert "Wädenswil" in result
        assert "ZH" in result

    @pytest.mark.asyncio
    async def test_no_results(self):
        with patch(
            "sbb_opendata_mcp.server._fetch_records",
            new_callable=AsyncMock,
            return_value=mock_api_response([]),
        ):
            result = await sbb_search_stations(StationSearchInput(query="XYZNOTEXIST"))
        assert "keine" in result.lower() or "not found" in result.lower()


# ---------------------------------------------------------------------------
# Live API Smoke Tests (require network)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.live
async def test_live_zurich_hb_frequency():
    """Live-Test: Passagierfrequenz Zürich HB 2024."""
    result = await sbb_get_passenger_frequency(
        PassengerFrequencyInput(station_name="Zürich HB", year="2024")
    )
    assert "Zürich HB" in result
    assert "2024" in result
    assert "410" in result  # ca. 410'000 DTV


@pytest.mark.asyncio
@pytest.mark.live
async def test_live_rail_disruptions():
    """Live-Test: Aktuelle Bahnverkehrsmeldungen."""
    result = await sbb_get_rail_disruptions(RailDisruptionsInput(limit=5))
    assert isinstance(result, str)
    assert len(result) > 50


@pytest.mark.asyncio
@pytest.mark.live
async def test_live_list_datasets():
    """Live-Test: Alle Datensätze auflisten."""
    result = await sbb_list_datasets()
    assert "passagierfrequenz" in result.lower()
    assert "SBB" in result


@pytest.mark.asyncio
@pytest.mark.live
async def test_live_compare_zurich_bern():
    """Live-Test: Vergleich Zürich HB vs. Bern."""
    result = await sbb_compare_stations(
        CompareStationsInput(stations=["Zürich HB", "Bern"], year="2024")
    )
    assert "Zürich HB" in result or "Bern" in result


@pytest.mark.asyncio
@pytest.mark.live
async def test_live_search_waedenswil():
    """Live-Test: Haltestellensuche Wädenswil."""
    result = await sbb_search_stations(StationSearchInput(query="Wädenswil", canton="ZH"))
    assert "Wädenswil" in result
