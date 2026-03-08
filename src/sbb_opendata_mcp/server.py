"""
SBB Open Data MCP Server
Provides access to Swiss Federal Railways (SBB) open data via the OpenDataSoft API v2.1.
No API key required. Data from data.sbb.ch.
"""

import json
from enum import StrEnum
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://data.sbb.ch/api/explore/v2.1/catalog/datasets"
DEFAULT_TIMEOUT = 30.0
DEFAULT_LIMIT = 20
MAX_LIMIT = 100

# Dataset IDs
DATASET_PASSENGER_FREQUENCY = "passagierfrequenz"
DATASET_RAIL_TRAFFIC = "rail-traffic-information"
DATASET_CONSTRUCTION_INFRA = "construction-projects"
DATASET_CONSTRUCTION_REALESTATE = "bauprojekte-immobilien"
DATASET_TRAINS_PER_SEGMENT = "zugzahlen"
DATASET_TRAINS_PER_MONTH = "zugzahlen_pro_monat"
DATASET_PLATFORMS = "perron"
DATASET_ROLLING_STOCK = "rollmaterial"
DATASET_STATION_USERS = "anzahl-sbb-bahnhofbenutzer"
DATASET_STATIONS = "dienststellen-gemass-opentransportdataswiss"
DATASET_ELEVATORS = "aufzugsstammdaten"
DATASET_LINES = "linie"

# ---------------------------------------------------------------------------
# Server init
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "sbb_opendata_mcp",
    instructions=(
        "SBB Open Data MCP Server: Access Swiss Federal Railways open data. "
        "Covers passenger frequency, live rail disruptions, infrastructure construction, "
        "real estate projects, trains per segment, platform data, rolling stock, and more. "
        "All data from data.sbb.ch — no authentication required."
    ),
)

# ---------------------------------------------------------------------------
# Shared API client
# ---------------------------------------------------------------------------


async def _fetch_records(
    dataset_id: str,
    where: str | None = None,
    order_by: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    select: str | None = None,
) -> dict[str, Any]:
    """Shared HTTP fetch for any SBB dataset via OpenDataSoft v2.1 API."""
    url = f"{BASE_URL}/{dataset_id}/records"
    params: dict[str, Any] = {"limit": min(limit, MAX_LIMIT), "offset": offset}
    if where:
        params["where"] = where
    if order_by:
        params["order_by"] = order_by
    if select:
        params["select"] = select

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        response = client.build_request("GET", url, params=params)
        r = await client.send(response)
        r.raise_for_status()
        return r.json()


def _handle_api_error(e: Exception) -> str:
    """Consistent, actionable error messages for all tools."""
    if isinstance(e, httpx.HTTPStatusError):
        if e.response.status_code == 404:
            return "Fehler: Datensatz oder Ressource nicht gefunden. Bitte Dataset-ID und Parameter prüfen."
        if e.response.status_code == 429:
            return "Fehler: Rate-Limit erreicht. Bitte kurz warten und erneut versuchen."
        return f"Fehler: API-Anfrage fehlgeschlagen (HTTP {e.response.status_code}). Details: {e.response.text[:200]}"
    if isinstance(e, httpx.TimeoutException):
        return "Fehler: Anfrage hat Zeitlimit überschritten (30s). Bitte erneut versuchen."
    return f"Fehler: Unerwarteter Fehler ({type(e).__name__}): {str(e)[:200]}"


def _pagination_meta(total: int, limit: int, offset: int) -> dict[str, Any]:
    """Reusable pagination metadata block."""
    returned = min(limit, max(0, total - offset))
    return {
        "total_count": total,
        "returned": returned,
        "offset": offset,
        "has_more": total > offset + returned,
        "next_offset": offset + returned if total > offset + returned else None,
    }


# ---------------------------------------------------------------------------
# Input models (Pydantic v2)
# ---------------------------------------------------------------------------


class ResponseFormat(StrEnum):
    MARKDOWN = "markdown"
    JSON = "json"


class PassengerFrequencyInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    station_name: str | None = Field(
        default=None,
        description="Bahnhofsname (teilweise Übereinstimmung möglich), z.B. 'Zürich HB', 'Bern', 'Winterthur'",
    )
    canton: str | None = Field(
        default=None,
        description="Kantonskürzel (2 Buchstaben), z.B. 'ZH', 'BE', 'AG'",
        min_length=2,
        max_length=2,
    )
    year: str | None = Field(
        default=None,
        description="Jahr (4-stellig), z.B. '2024', '2023'. Ohne Angabe: aktuellste Daten aller Jahre.",
    )
    limit: int = Field(default=20, ge=1, le=100, description="Maximale Anzahl Resultate (1–100)")
    offset: int = Field(default=0, ge=0, description="Offset für Paginierung")
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Ausgabeformat: 'markdown' (lesbar) oder 'json' (maschinenlesbar)",
    )


class RailDisruptionsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    limit: int = Field(default=20, ge=1, le=100, description="Maximale Anzahl Meldungen (1–100)")
    offset: int = Field(default=0, ge=0, description="Offset für Paginierung")
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Ausgabeformat: 'markdown' oder 'json'",
    )


class ConstructionProjectsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    city: str | None = Field(
        default=None,
        description="Stadt/Ort filtern, z.B. 'Zürich', 'Basel', 'Bern'",
    )
    project_type: str | None = Field(
        default=None,
        description="Projektart filtern: 'ausbau', 'bahnhof', 'strecke', etc.",
    )
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class RealEstateProjectsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    city: str | None = Field(
        default=None,
        description="Stadt filtern, z.B. 'Zürich', 'Bern', 'Luzern'",
    )
    phase: str | None = Field(
        default=None,
        description="Projektphase: 'CONSTRUCTION', 'PLANNING', 'COMPLETED'",
    )
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class TrainsPerSegmentInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    line_name: str | None = Field(
        default=None,
        description="Streckenbezeichnung (Teilübereinstimmung), z.B. 'Zürich', 'Basel - Bern'",
    )
    operator: str | None = Field(
        default=None,
        description="Infrastrukturbetreiberin: 'SBB', 'BLS', 'SOB', 'DB', etc.",
    )
    year: str | None = Field(
        default=None,
        description="Jahr, z.B. '2025', '2024'",
    )
    traffic_type: str | None = Field(
        default=None,
        description="Verkehrstyp: 'Personenverkehr' oder 'Gueterverkehr'",
    )
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class PlatformDataInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    station_name: str | None = Field(
        default=None,
        description="Bahnhofsname, z.B. 'Zürich HB', 'Bern', 'Basel SBB'",
    )
    platform_type: str | None = Field(
        default=None,
        description="Perrontyp: 'Mittelperron', 'Aussenperron', 'Inselperron'",
    )
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class RollingStockInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    vehicle_type: str | None = Field(
        default=None,
        description="Fahrzeugtyp, z.B. 'IC 2000', 'FV-Dosto', 'TGV', 'RABe 511'",
    )
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class CompareStationsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    stations: list[str] = Field(
        description="Liste von Bahnhofsnamen zum Vergleich, z.B. ['Zürich HB', 'Bern', 'Basel SBB']",
        min_length=2,
        max_length=10,
    )
    year: str | None = Field(
        default=None,
        description="Vergleichsjahr, z.B. '2024'. Ohne Angabe: aktuellste verfügbare Daten.",
    )


class StationSearchInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(
        description="Suchbegriff für Bahnhofs-/Haltestellenname, z.B. 'Zürich', 'Wädenswil'",
        min_length=2,
    )
    canton: str | None = Field(
        default=None,
        description="Kantonskürzel, z.B. 'ZH', 'BE', 'AG'",
        min_length=2,
        max_length=2,
    )
    limit: int = Field(default=20, ge=1, le=100)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool(
    name="sbb_get_passenger_frequency",
    annotations={
        "title": "SBB Passagierfrequenz nach Bahnhof",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def sbb_get_passenger_frequency(params: PassengerFrequencyInput) -> str:
    """Ruft Passagierfrequenzdaten (Ein-/Aussteigende) für SBB-Bahnhöfe ab.

    Datensatz wird jährlich aktualisiert. Enthält Tagesschnitt (DTV),
    Werktagesschnitt (DWV) und Nicht-Werktages-Schnitt (DNWV) pro Bahnhof und Jahr.

    Args:
        params (PassengerFrequencyInput): Filterparameter:
            - station_name (Optional[str]): Bahnhofsname (Teilsuche)
            - canton (Optional[str]): Kantonskürzel, z.B. 'ZH'
            - year (Optional[str]): Jahr, z.B. '2024'
            - limit (int): Max. Resultate (1–100), Standard 20
            - offset (int): Offset für Paginierung
            - response_format (str): 'markdown' oder 'json'

    Returns:
        str: Passagierfrequenzdaten mit DTV/DWV-Werten und Paginierungsinfo.
             Schema: {station, year, daily_avg, workday_avg, non_workday_avg, canton, operator}
    """
    try:
        conditions = []
        if params.station_name:
            escaped = params.station_name.replace('"', '\\"')
            conditions.append(f'bahnhof_gare_stazione like "%{escaped}%"')
        if params.canton:
            conditions.append(f'kt_ct_cantone="{params.canton.upper()}"')
        if params.year:
            conditions.append(f"year(jahr_annee_anno)={params.year}")

        where = " AND ".join(conditions) if conditions else None
        data = await _fetch_records(
            DATASET_PASSENGER_FREQUENCY,
            where=where,
            order_by="jahr_annee_anno desc",
            limit=params.limit,
            offset=params.offset,
        )

        results = data.get("results", [])
        total = data.get("total_count", 0)
        pagination = _pagination_meta(total, params.limit, params.offset)

        if params.response_format == ResponseFormat.JSON:
            return json.dumps({"pagination": pagination, "results": results}, ensure_ascii=False, indent=2)

        if not results:
            return "Keine Passagierfrequenzdaten gefunden. Bitte Suchparameter anpassen."

        lines = ["## SBB Passagierfrequenz\n"]
        lines.append(f"*Resultate: {pagination['returned']} von {pagination['total_count']}*\n")
        lines.append("| Bahnhof | Jahr | Tagesschnitt (DTV) | Werktag (DWV) | Nicht-Werktag | Kanton |")
        lines.append("|---------|------|-------------------|---------------|---------------|--------|")

        for r in results:
            dtv = f"{int(r.get('dtv_tjm_tgm', 0)):,}".replace(",", "'") if r.get("dtv_tjm_tgm") else "–"
            dwv = f"{int(r.get('dwv_tmjo_tfm', 0)):,}".replace(",", "'") if r.get("dwv_tmjo_tfm") else "–"
            dnwv = f"{int(r.get('dnwv_tmjno_tmgnl', 0)):,}".replace(",", "'") if r.get("dnwv_tmjno_tmgnl") else "–"
            lines.append(
                f"| {r.get('bahnhof_gare_stazione', '–')} "
                f"| {r.get('jahr_annee_anno', '–')} "
                f"| {dtv} "
                f"| {dwv} "
                f"| {dnwv} "
                f"| {r.get('kt_ct_cantone', '–')} |"
            )

        if results[0].get("bemerkungen"):
            lines.append(f"\n*Hinweis: {results[0]['bemerkungen']}*")

        if pagination["has_more"]:
            lines.append(f"\n*Weitere Resultate verfügbar. Nächster Offset: {pagination['next_offset']}*")

        return "\n".join(lines)

    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="sbb_get_rail_disruptions",
    annotations={
        "title": "SBB Bahnverkehrsstörungen (Live)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def sbb_get_rail_disruptions(params: RailDisruptionsInput) -> str:
    """Ruft aktuelle Bahnverkehrsstörungen und -meldungen ab (alle 5 Minuten aktualisiert).

    Enthält Titel, Beschreibung, Ursache, Start-/Endzeitpunkt und betroffene Linien.
    Ideal für Echtzeit-Monitoring und Kommunikation bei Ereignissen.

    Args:
        params (RailDisruptionsInput): Parameter:
            - limit (int): Max. Meldungen (1–100), Standard 20
            - offset (int): Offset für Paginierung
            - response_format (str): 'markdown' oder 'json'

    Returns:
        str: Liste aktueller Störungsmeldungen mit Zeitfenstern und Beschreibungen.
             Schema: {title, description, published, start, end, type, author}
    """
    try:
        data = await _fetch_records(
            DATASET_RAIL_TRAFFIC,
            order_by="published desc",
            limit=params.limit,
            offset=params.offset,
        )

        results = data.get("results", [])
        total = data.get("total_count", 0)
        pagination = _pagination_meta(total, params.limit, params.offset)

        if params.response_format == ResponseFormat.JSON:
            return json.dumps({"pagination": pagination, "results": results}, ensure_ascii=False, indent=2)

        if not results:
            return "Keine aktuellen Störungsmeldungen gefunden."

        lines = ["## SBB Bahnverkehrsmeldungen (Live, alle 5 Min.)\n"]
        lines.append(f"*{pagination['returned']} von {pagination['total_count']} Meldungen*\n")

        for r in results:
            title = r.get("title", "Keine Überschrift")
            published = r.get("published", "")
            if published:
                published = published[:16].replace("T", " ")
            start = (r.get("startdatetime") or "")[:16].replace("T", " ")
            end = (r.get("enddatetime") or "")[:16].replace("T", " ")
            desc = r.get("description", "")
            # Strip HTML tags simply
            desc_clean = desc.replace("<br />", "\n  ").replace("<br>", "\n  ")

            lines.append(f"### 🚨 {title}")
            lines.append(f"- **Publiziert:** {published}")
            if start:
                lines.append(f"- **Zeitraum:** {start} – {end or 'offen'}")
            if desc_clean:
                lines.append(f"- **Details:** {desc_clean[:300]}")
            link = r.get("link")
            if link:
                lines.append(f"- **Mehr Info:** [SBB Website]({link})")
            lines.append("")

        if pagination["has_more"]:
            lines.append(f"*Weitere Meldungen verfügbar. Nächster Offset: {pagination['next_offset']}*")

        return "\n".join(lines)

    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="sbb_get_infrastructure_construction_projects",
    annotations={
        "title": "SBB Infrastruktur-Bauprojekte",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def sbb_get_infrastructure_construction_projects(params: ConstructionProjectsInput) -> str:
    """Ruft laufende SBB-Infrastruktur-Bauprojekte (Bahnhöfe, Strecken, Ausbau) ab.

    Enthält Projektname, Ort, Projektart, Angebotsschritt und Links zu Projektseiten.
    Geeignet für Stadtplanung, Kommunikation und Raumplanung.

    Args:
        params (ConstructionProjectsInput): Parameter:
            - city (Optional[str]): Ortsfilter, z.B. 'Zürich', 'Basel'
            - project_type (Optional[str]): Projektart, z.B. 'ausbau'
            - limit (int): Max. Resultate
            - offset (int): Paginierung
            - response_format (str): 'markdown' oder 'json'

    Returns:
        str: Liste Infrastruktur-Bauprojekte mit Ort, Art und Projektlinks.
             Schema: {name, location, type, category, link}
    """
    try:
        conditions = []
        if params.city:
            escaped = params.city.replace('"', '\\"')
            conditions.append(f'projektort like "%{escaped}%"')
        if params.project_type:
            escaped = params.project_type.replace('"', '\\"')
            conditions.append(f'art like "%{escaped}%"')

        where = " AND ".join(conditions) if conditions else None
        data = await _fetch_records(
            DATASET_CONSTRUCTION_INFRA,
            where=where,
            limit=params.limit,
            offset=params.offset,
        )

        results = data.get("results", [])
        total = data.get("total_count", 0)
        pagination = _pagination_meta(total, params.limit, params.offset)

        if params.response_format == ResponseFormat.JSON:
            return json.dumps({"pagination": pagination, "results": results}, ensure_ascii=False, indent=2)

        if not results:
            return "Keine Infrastruktur-Bauprojekte mit diesen Filterkriterien gefunden."

        lines = ["## SBB Infrastruktur-Bauprojekte\n"]
        lines.append(f"*{pagination['returned']} von {pagination['total_count']} Projekten*\n")

        for r in results:
            name = r.get("projektname", "Unbekannt")
            ort = r.get("projektort", "–")
            art = r.get("art", "–")
            ort_typ = r.get("ort", "–")
            link = r.get("link1_url", "")
            angebotsschritt = r.get("angebotsschritt", "")

            lines.append(f"### 🏗️ {name}")
            lines.append(f"- **Ort:** {ort}")
            lines.append(f"- **Projekttyp:** {art} / {ort_typ}")
            if angebotsschritt:
                lines.append(f"- **Angebotsschritt:** {angebotsschritt}")
            if link:
                lines.append(f"- **Mehr Info:** [{r.get('link1_title', 'Projektseite')}]({link})")
            lines.append("")

        if pagination["has_more"]:
            lines.append(f"*Weitere Projekte verfügbar. Nächster Offset: {pagination['next_offset']}*")

        return "\n".join(lines)

    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="sbb_get_real_estate_projects",
    annotations={
        "title": "SBB Immobilien-Bauprojekte",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def sbb_get_real_estate_projects(params: RealEstateProjectsInput) -> str:
    """Ruft laufende SBB-Immobilien-Bauprojekte (Wohn- und Geschäftsbauten) ab.

    Täglich aktualisiert. Enthält Projektname, Stadt, Bauphase, Nutzfläche,
    Baudaten und Beschreibungen (DE/FR/IT/EN).

    Args:
        params (RealEstateProjectsInput): Parameter:
            - city (Optional[str]): Stadt, z.B. 'Zürich', 'Bern', 'Luzern'
            - phase (Optional[str]): Projektphase, z.B. 'CONSTRUCTION', 'PLANNING'
            - limit (int): Max. Resultate
            - offset (int): Paginierung
            - response_format (str): 'markdown' oder 'json'

    Returns:
        str: Immobilien-Bauprojekte mit Baustart, Einzug und Nutzfläche.
             Schema: {title, city, phase, start_of_construction, move_in, area_m2, description}
    """
    try:
        conditions = []
        if params.city:
            escaped = params.city.replace('"', '\\"')
            conditions.append(f'city like "%{escaped}%"')
        if params.phase:
            conditions.append(f'phase="{params.phase.upper()}"')

        where = " AND ".join(conditions) if conditions else None
        data = await _fetch_records(
            DATASET_CONSTRUCTION_REALESTATE,
            where=where,
            limit=params.limit,
            offset=params.offset,
        )

        results = data.get("results", [])
        total = data.get("total_count", 0)
        pagination = _pagination_meta(total, params.limit, params.offset)

        if params.response_format == ResponseFormat.JSON:
            return json.dumps({"pagination": pagination, "results": results}, ensure_ascii=False, indent=2)

        if not results:
            return "Keine Immobilien-Bauprojekte mit diesen Filterkriterien gefunden."

        lines = ["## SBB Immobilien-Bauprojekte\n"]
        lines.append(f"*{pagination['returned']} von {pagination['total_count']} Projekten*\n")

        for r in results:
            title = r.get("titlede") or r.get("titleen", "Unbekannt")
            city = r.get("city", "–")
            phase = r.get("phase", "–")
            start = r.get("startofconstruction", "–")
            move_in = r.get("moveinto", "–")
            area = r.get("mainusefulareastotal", "–")
            lead = r.get("leadde") or r.get("leaden", "")

            phase_emoji = {"CONSTRUCTION": "🔨", "PLANNING": "📐", "COMPLETED": "✅"}.get(phase, "🏢")

            lines.append(f"### {phase_emoji} {title} ({city})")
            lines.append(f"- **Phase:** {phase}")
            lines.append(f"- **Baustart:** {start}  |  **Einzug:** {move_in}")
            if area and area != "–":
                lines.append(f"- **Nutzfläche:** {area:,} m²".replace(",", "'"))
            if lead:
                lines.append(f"- **Beschreibung:** {lead[:200]}...")
            lines.append("")

        if pagination["has_more"]:
            lines.append(f"*Weitere Projekte verfügbar. Nächster Offset: {pagination['next_offset']}*")

        return "\n".join(lines)

    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="sbb_get_trains_per_segment",
    annotations={
        "title": "SBB Züge pro Streckenabschnitt",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def sbb_get_trains_per_segment(params: TrainsPerSegmentInput) -> str:
    """Ruft Anzahl Züge pro Streckenabschnitt und Verkehrstyp ab.

    Deckt SBB, BLS, SOB, DB und weitere Infrastrukturbetreiberinnen ab.
    Enthält Personenverkehr und Güterverkehr, Trassenkilometer und Stromverbrauch.

    Args:
        params (TrainsPerSegmentInput): Parameter:
            - line_name (Optional[str]): Streckenbezeichnung (Teilsuche)
            - operator (Optional[str]): Infrastrukturbetreiberin, z.B. 'SBB', 'BLS'
            - year (Optional[str]): Jahr, z.B. '2025'
            - traffic_type (Optional[str]): 'Personenverkehr' oder 'Gueterverkehr'
            - limit (int): Max. Resultate
            - offset (int): Paginierung
            - response_format (str): 'markdown' oder 'json'

    Returns:
        str: Zugzahlen pro Streckenabschnitt mit Operator und Traffiktyp.
             Schema: {segment, line, operator, year, train_count, traffic_type, track_km}
    """
    try:
        conditions = []
        if params.line_name:
            escaped = params.line_name.replace('"', '\\"')
            conditions.append(f'strecke_bezeichnung like "%{escaped}%"')
        if params.operator:
            conditions.append(f'isb="{params.operator.upper()}"')
        if params.year:
            conditions.append(f'jahr="{params.year}"')
        if params.traffic_type:
            conditions.append(f'geschaeftscode like "%{params.traffic_type}%"')

        where = " AND ".join(conditions) if conditions else None
        data = await _fetch_records(
            DATASET_TRAINS_PER_SEGMENT,
            where=where,
            order_by="anzahl_zuege desc",
            limit=params.limit,
            offset=params.offset,
            select="strecke_bezeichnung,isb,jahr,geschaeftscode,anzahl_zuege,trassenkilometer,bp_von_abschnitt_bezeichnung,bp_bis_abschnitt_bezeichnung",
        )

        results = data.get("results", [])
        total = data.get("total_count", 0)
        pagination = _pagination_meta(total, params.limit, params.offset)

        if params.response_format == ResponseFormat.JSON:
            return json.dumps({"pagination": pagination, "results": results}, ensure_ascii=False, indent=2)

        if not results:
            return "Keine Zugzahlen-Daten mit diesen Filterkriterien gefunden."

        lines = ["## SBB Zugzahlen pro Streckenabschnitt\n"]
        lines.append(f"*{pagination['returned']} von {pagination['total_count']} Abschnitten*\n")
        lines.append("| Strecke | Von → Bis | Züge | Typ | Betreiber | Jahr |")
        lines.append("|---------|-----------|------|-----|-----------|------|")

        for r in results:
            strecke = r.get("strecke_bezeichnung", "–")[:40]
            von = r.get("bp_von_abschnitt_bezeichnung", "–")
            bis = r.get("bp_bis_abschnitt_bezeichnung", "–")
            zuege = int(r.get("anzahl_zuege", 0)) if r.get("anzahl_zuege") else "–"
            typ = r.get("geschaeftscode", "–")
            isb = r.get("isb", "–")
            jahr = r.get("jahr", "–")
            lines.append(f"| {strecke} | {von} → {bis} | {zuege} | {typ} | {isb} | {jahr} |")

        if pagination["has_more"]:
            lines.append(f"\n*Weitere Abschnitte verfügbar. Nächster Offset: {pagination['next_offset']}*")

        return "\n".join(lines)

    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="sbb_get_platform_data",
    annotations={
        "title": "SBB Perrondaten",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def sbb_get_platform_data(params: PlatformDataInput) -> str:
    """Ruft Perrondaten (Länge, Fläche, Typ) für SBB-Bahnhöfe ab.

    Enthält Perronlänge (m), Netto-/Bruttofläche (m²), Perrontyp und
    Angaben zur schienenfreien Zugänglichkeit.

    Args:
        params (PlatformDataInput): Parameter:
            - station_name (Optional[str]): Bahnhofsname, z.B. 'Zürich HB'
            - platform_type (Optional[str]): Perrontyp, z.B. 'Mittelperron'
            - limit (int): Max. Resultate
            - offset (int): Paginierung
            - response_format (str): 'markdown' oder 'json'

    Returns:
        str: Perrondaten mit Länge, Fläche und Typ.
             Schema: {station, platform_nr, type, length_m, gross_area_m2, net_area_m2, accessible}
    """
    try:
        conditions = []
        if params.station_name:
            escaped = params.station_name.replace('"', '\\"')
            conditions.append(f'bps_name like "%{escaped}%"')
        if params.platform_type:
            escaped = params.platform_type.replace('"', '\\"')
            conditions.append(f'perrontyp like "%{escaped}%"')

        where = " AND ".join(conditions) if conditions else None
        data = await _fetch_records(
            DATASET_PLATFORMS,
            where=where,
            order_by="bps_name",
            limit=params.limit,
            offset=params.offset,
        )

        results = data.get("results", [])
        total = data.get("total_count", 0)
        pagination = _pagination_meta(total, params.limit, params.offset)

        if params.response_format == ResponseFormat.JSON:
            return json.dumps({"pagination": pagination, "results": results}, ensure_ascii=False, indent=2)

        if not results:
            return "Keine Perrondaten mit diesen Filterkriterien gefunden."

        lines = ["## SBB Perrondaten\n"]
        lines.append(f"*{pagination['returned']} von {pagination['total_count']} Perrons*\n")
        lines.append("| Bahnhof | Perron | Typ | Länge (m) | Fläche netto (m²) | Schienenfrei |")
        lines.append("|---------|--------|-----|-----------|-------------------|--------------|")

        for r in results:
            station = r.get("bps_name", "–")
            p_nr = r.get("p_nr", "–")
            p_typ = r.get("perrontyp", "–")
            p_len = r.get("p_lange", "–")
            net = r.get("perronflach_netto_m2", "–")
            accessible = r.get("z_schienenfrei", "–")
            lines.append(f"| {station} | {p_nr} | {p_typ} | {p_len} | {net} | {accessible} |")

        if pagination["has_more"]:
            lines.append(f"\n*Weitere Perrons verfügbar. Nächster Offset: {pagination['next_offset']}*")

        return "\n".join(lines)

    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="sbb_get_rolling_stock",
    annotations={
        "title": "SBB Rollmaterial",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def sbb_get_rolling_stock(params: RollingStockInput) -> str:
    """Ruft technische Daten zum SBB-Rollmaterial (Züge, Triebzüge, Wagen) ab.

    Enthält Fahrzeugtyp, Sitzplatzkapazität (1./2. Kl.), Baujahr, Länge und Gewicht.

    Args:
        params (RollingStockInput): Parameter:
            - vehicle_type (Optional[str]): Fahrzeugtyp, z.B. 'IC 2000', 'TGV', 'FV-Dosto'
            - limit (int): Max. Resultate
            - offset (int): Paginierung
            - response_format (str): 'markdown' oder 'json'

    Returns:
        str: Rollmaterial-Daten mit Kapazität, Baujahr und technischen Kennzahlen.
             Schema: {vehicle_type, built_year, seats_1st, seats_2nd, total_seats, length_mm, weight_t}
    """
    try:
        conditions = []
        if params.vehicle_type:
            escaped = params.vehicle_type.replace('"', '\\"')
            conditions.append(f'fahrzeug_typ like "%{escaped}%"')

        where = " AND ".join(conditions) if conditions else None
        data = await _fetch_records(
            DATASET_ROLLING_STOCK,
            where=where,
            limit=params.limit,
            offset=params.offset,
            select="fahrzeug_typ,objekt,baudatum_fahrzeug,sitzplatze_1_kl_total_zug,sitzplatze_2_kl_total_zug,sitzplatze_pro_zug_total,lange_uber_zug,eigengewicht_tara",
        )

        results = data.get("results", [])
        total = data.get("total_count", 0)
        pagination = _pagination_meta(total, params.limit, params.offset)

        if params.response_format == ResponseFormat.JSON:
            return json.dumps({"pagination": pagination, "results": results}, ensure_ascii=False, indent=2)

        if not results:
            return "Kein Rollmaterial mit diesem Fahrzeugtyp gefunden."

        lines = ["## SBB Rollmaterial\n"]
        lines.append(f"*{pagination['returned']} von {pagination['total_count']} Fahrzeugen*\n")
        lines.append("| Typ | Nr. | Baujahr | Plätze 1. Kl. | Plätze 2. Kl. | Total | Länge (mm) |")
        lines.append("|-----|-----|---------|---------------|---------------|-------|------------|")

        for r in results:
            typ = r.get("fahrzeug_typ", "–")
            nr = r.get("objekt", "–")
            bj = str(r.get("baudatum_fahrzeug", "–"))[:4] if r.get("baudatum_fahrzeug") else "–"
            s1 = r.get("sitzplatze_1_kl_total_zug", "–")
            s2 = r.get("sitzplatze_2_kl_total_zug", "–")
            total_s = r.get("sitzplatze_pro_zug_total", "–")
            laenge = r.get("lange_uber_zug", "–")
            lines.append(f"| {typ} | {nr} | {bj} | {s1} | {s2} | {total_s} | {laenge} |")

        if pagination["has_more"]:
            lines.append(f"\n*Weitere Fahrzeuge verfügbar. Nächster Offset: {pagination['next_offset']}*")

        return "\n".join(lines)

    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="sbb_compare_stations",
    annotations={
        "title": "SBB Bahnhöfe vergleichen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def sbb_compare_stations(params: CompareStationsInput) -> str:
    """Vergleicht mehrere SBB-Bahnhöfe anhand Passagierfrequenz und Perrondaten.

    Kombiniert drei Datensätze (Passagierfrequenz, Bahnhofnutzer, Perrons) zu einem
    kompakten Vergleich. Nützlich für Planungsentscheide, Präsentationen und
    Standortanalysen.

    Args:
        params (CompareStationsInput): Parameter:
            - stations (list[str]): Liste von Bahnhofsnamen (2–10), z.B. ['Zürich HB', 'Bern']
            - year (Optional[str]): Vergleichsjahr, z.B. '2024'

    Returns:
        str: Tabellarischer Vergleich der Bahnhöfe mit Passagierfrequenz und Perron-Kennzahlen.
    """
    try:
        results_by_station: dict[str, dict] = {s: {"name": s} for s in params.stations}
        year_filter = params.year or "2024"

        # Fetch passenger frequency for all stations
        for station in params.stations:
            escaped = station.replace('"', '\\"')
            where = f'bahnhof_gare_stazione like "%{escaped}%" AND year(jahr_annee_anno)={year_filter}'
            data = await _fetch_records(
                DATASET_PASSENGER_FREQUENCY, where=where, order_by="dtv_tjm_tgm desc", limit=1
            )
            if data.get("results"):
                r = data["results"][0]
                results_by_station[station].update(
                    {
                        "matched_name": r.get("bahnhof_gare_stazione"),
                        "year": r.get("jahr_annee_anno"),
                        "dtv": r.get("dtv_tjm_tgm"),
                        "dwv": r.get("dwv_tmjo_tfm"),
                        "canton": r.get("kt_ct_cantone"),
                    }
                )

        # Fetch platform counts for all stations
        for station in params.stations:
            escaped = station.replace('"', '\\"')
            where = f'bps_name like "%{escaped}%"'
            data = await _fetch_records(DATASET_PLATFORMS, where=where, limit=50)
            if data.get("results"):
                perrons = data["results"]
                total_length = sum(r.get("p_lange", 0) or 0 for r in perrons)
                results_by_station[station].update(
                    {
                        "platform_count": len(perrons),
                        "total_platform_length_m": int(total_length),
                    }
                )

        lines = [f"## Bahnhofvergleich ({year_filter})\n"]
        lines.append("| Bahnhof | Kanton | DTV (tägl.) | DWV (werktags) | Perrons | Gesamtlänge (m) |")
        lines.append("|---------|--------|-------------|----------------|---------|-----------------|")

        for station, info in results_by_station.items():
            name = info.get("matched_name") or station
            canton = info.get("canton", "–")
            dtv = f"{int(info['dtv']):,}".replace(",", "'") if info.get("dtv") else "–"
            dwv = f"{int(info['dwv']):,}".replace(",", "'") if info.get("dwv") else "–"
            pc = info.get("platform_count", "–")
            pl = f"{info.get('total_platform_length_m', '–'):,}".replace(",", "'") if info.get("total_platform_length_m") else "–"
            lines.append(f"| {name} | {canton} | {dtv} | {dwv} | {pc} | {pl} |")

        lines.append("\n*Quellen: SBB Passagierfrequenz + Perrondaten | data.sbb.ch*")
        return "\n".join(lines)

    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="sbb_search_stations",
    annotations={
        "title": "SBB Haltestellen suchen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def sbb_search_stations(params: StationSearchInput) -> str:
    """Sucht Bahnhöfe und Haltestellen der Schweiz (DiDok-Liste des BAV).

    Deckt alle öV-Haltestellen ab (nicht nur SBB). Enthält UIC-Nummern,
    Koordinaten, Kantone und Betreiberinformationen.

    Args:
        params (StationSearchInput): Parameter:
            - query (str): Suchbegriff (mind. 2 Zeichen), z.B. 'Wädenswil', 'Zürich'
            - canton (Optional[str]): Kantonskürzel, z.B. 'ZH'
            - limit (int): Max. Resultate
            - response_format (str): 'markdown' oder 'json'

    Returns:
        str: Haltestellenliste mit UIC, Kanton und Koordinaten.
             Schema: {name, uic, canton, operator, coordinates}
    """
    try:
        escaped = params.query.replace('"', '\\"')
        conditions = [f'bezeichnung_offiziell like "%{escaped}%"']
        if params.canton:
            conditions.append(f'kanton_kuerzel="{params.canton.upper()}"')

        where = " AND ".join(conditions)
        data = await _fetch_records(
            DATASET_STATIONS,
            where=where,
            limit=params.limit,
            offset=0,
            select="bezeichnung_offiziell,uic,kanton_kuerzel,dst_nr,tu_nummer,geopos_ost,geopos_nord",
        )

        results = data.get("results", [])
        total = data.get("total_count", 0)

        if params.response_format == ResponseFormat.JSON:
            return json.dumps({"total_count": total, "results": results}, ensure_ascii=False, indent=2)

        if not results:
            return f"Keine Haltestellen für '{params.query}' gefunden."

        lines = [f"## Haltestellen: '{params.query}'\n"]
        lines.append(f"*{len(results)} von {total} Resultaten*\n")
        lines.append("| Bezeichnung | UIC | Kanton |")
        lines.append("|-------------|-----|--------|")

        for r in results:
            name = r.get("bezeichnung_offiziell", "–")
            uic = r.get("uic", "–")
            kt = r.get("kanton_kuerzel", "–")
            lines.append(f"| {name} | {uic} | {kt} |")

        if total > params.limit:
            lines.append(f"\n*{total - params.limit} weitere Resultate – Suchbegriff präzisieren.*")

        return "\n".join(lines)

    except Exception as e:
        return _handle_api_error(e)


@mcp.tool(
    name="sbb_list_datasets",
    annotations={
        "title": "SBB Open Data Datensätze auflisten",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def sbb_list_datasets() -> str:
    """Listet alle verfügbaren SBB Open Data Datensätze (data.sbb.ch) auf.

    Gibt Dataset-ID, Titel, Anzahl Datensätze und Aktualisierungsfrequenz zurück.
    Nützlich zur Übersicht und Entdeckung neuer Datensätze.

    Returns:
        str: Vollständige Liste aller SBB Open Data Datensätze.
             Schema: {dataset_id, title, records_count, update_frequency, themes}
    """
    try:
        url = "https://data.sbb.ch/api/explore/v2.1/catalog/datasets"
        params = {"limit": 100, "order_by": "metas.default.title asc"}

        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()

        results = data.get("results", [])
        total = data.get("total_count", 0)

        lines = [f"## SBB Open Data – {total} Datensätze (data.sbb.ch)\n"]
        lines.append("| Dataset ID | Titel | Datensätze | Aktualisierung |")
        lines.append("|------------|-------|------------|----------------|")

        for d in results:
            ds_id = d.get("dataset_id", "–")
            meta = d.get("metas", {}).get("default", {})
            title = meta.get("title", ds_id)[:50]
            records = meta.get("records_count", "–")
            freq = d.get("metas", {}).get("dcat", {}).get("accrualperiodicity") or "–"
            lines.append(f"| `{ds_id}` | {title} | {records} | {freq} |")

        lines.append("\n*Quelle: data.sbb.ch | API: OpenDataSoft v2.1 | Kein API-Key erforderlich*")
        return "\n".join(lines)

    except Exception as e:
        return _handle_api_error(e)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    transport = "streamable_http" if "--http" in sys.argv else "stdio"
    port = 8000
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])

    if transport == "streamable_http":
        mcp.run(transport="streamable_http", port=port)
    else:
        mcp.run()
