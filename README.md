# SBB Open Data MCP Server

[🇩🇪 Deutsch](README.de.md) | 🇬🇧 English

An [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server for Swiss Federal Railways (SBB) open data via [data.sbb.ch](https://data.sbb.ch). No API key required.

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-1.6%2B-purple)](https://modelcontextprotocol.io)

---

## What is this?

This server connects AI models (Claude, GPT-4, Llama, etc.) directly to public SBB data — no copy-pasting or manual API calls required. A question like *"How many passengers passed through Zürich HB every day in 2024?"* is answered with real measured data.

The server is model-agnostic and works with any MCP-compatible client.

---

## Available Tools (10)

| Tool | Description | Data Update |
|------|-------------|-------------|
| `sbb_get_passenger_frequency` | Boardings/alightings by station and year (daily avg.) | Annual |
| `sbb_get_rail_disruptions` | Live rail traffic messages | Every 5 min. |
| `sbb_get_infrastructure_construction_projects` | Infrastructure construction (stations, lines) | Ongoing |
| `sbb_get_real_estate_projects` | SBB real estate development projects | Daily |
| `sbb_get_trains_per_segment` | Train counts per route segment (SBB, BLS, SOB …) | Annual |
| `sbb_get_platform_data` | Platform data (length, type, area) | Ongoing |
| `sbb_get_rolling_stock` | Rolling stock (capacity, year built) | Ongoing |
| `sbb_compare_stations` | Compare up to 10 stations (multi-dataset) | – |
| `sbb_search_stations` | Search stops (Swiss DiDok register, all CH) | Ongoing |
| `sbb_list_datasets` | List all ~89 SBB open datasets | – |

All tools support `response_format: "markdown"` (human-readable) and `"json"` (machine-readable), plus pagination.

---

## Installation

### Prerequisites

Install [uv](https://github.com/astral-sh/uv):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Claude Desktop (stdio)

Open the config file:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "sbb-opendata": {
      "command": "uvx",
      "args": ["sbb-opendata-mcp"]
    }
  }
}
```

Restart Claude Desktop. The server is downloaded automatically on first use.

### Other MCP Clients

Works with Cursor, Windsurf, VS Code + Continue, LibreChat, Cline and self-hosted models via `mcp-proxy` — same configuration as above.

### Cloud Deployment (Streamable HTTP)

For remote servers (e.g. [Render.com](https://render.com)):

```bash
git clone https://github.com/malkreide/sbb-opendata-mcp
cd sbb-opendata-mcp
pip install -e .
python -m sbb_opendata_mcp.server --http --port 8000
```

### Local Development

```bash
git clone https://github.com/malkreide/sbb-opendata-mcp
cd sbb-opendata-mcp
pip install -e ".[dev]"

# Unit tests (no network required)
PYTHONPATH=src pytest tests/ -v -m "not live"

# Live API smoke tests
PYTHONPATH=src pytest tests/ -v -m live
```

---

## Example Queries

```
"How many people boarded at Zürich HB daily in 2024?"
→ sbb_get_passenger_frequency(station_name="Zürich HB", year="2024")

"Are there any current disruptions on the Swiss rail network?"
→ sbb_get_rail_disruptions(limit=10)

"Compare Zürich HB, Bern and Basel SBB by passenger frequency and platform capacity."
→ sbb_compare_stations(stations=["Zürich HB", "Bern", "Basel SBB"], year="2024")

"Which SBB construction projects are active in Zürich?"
→ sbb_get_infrastructure_construction_projects(city="Zürich")

"How many trains run daily on the Zürich–Winterthur route?"
→ sbb_get_trains_per_segment(line_name="Zürich", operator="SBB", year="2025")

"Which stops exist in Wädenswil?"
→ sbb_search_stations(query="Wädenswil", canton="ZH")
```

---

## Data & License

All data is sourced from the [SBB Open Data Portal](https://data.sbb.ch) (OpenDataSoft REST API v2.1).  
Data license: [NonCommercialAllowed-CommercialAllowed-ReferenceRequired](https://data.sbb.ch/page/licence)

This server is released under the **MIT License** and is part of the open source MCP portfolio at [github.com/malkreide](https://github.com/malkreide).

---

## Relationship to Other MCP Servers

| Server | How SBB Open Data Complements It |
|--------|----------------------------------|
| [swiss-transport-mcp](https://github.com/malkreide/swiss-transport-mcp) | Historical depth: passenger context for real-time timetable queries |
| [swiss-road-mobility-mcp](https://github.com/malkreide/swiss-road-mobility-mcp) | Multimodal view: rail hub + micromobility/EV charging |
| [zurich-opendata-mcp](https://github.com/malkreide/zurich-opendata-mcp) | Cross-reference: Zurich stops combined with city population and school data |

---

## Technical Details

- **Framework:** [FastMCP](https://github.com/modelcontextprotocol/python-sdk) + httpx + Pydantic v2
- **Transport:** stdio (local) and Streamable HTTP (cloud)
- **Python:** 3.11, 3.12, 3.13
- **Tests:** 34 unit tests + 5 live API smoke tests
- **API:** [OpenDataSoft REST v2.1](https://data.sbb.ch/api/explore/v2.1/) — no authentication needed
