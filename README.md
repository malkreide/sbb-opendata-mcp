# SBB Open Data MCP Server

**Deutsch** | [English](#english)

Ein Model Context Protocol (MCP) Server für die offenen Daten der Schweizerischen Bundesbahnen (SBB) via [data.sbb.ch](https://data.sbb.ch). Kein API-Key erforderlich.

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-1.6%2B-purple)](https://modelcontextprotocol.io)

---

## Verfügbare Tools (9)

| Tool | Beschreibung | Aktualisierung |
|------|-------------|----------------|
| `sbb_get_passenger_frequency` | Ein-/Aussteigende nach Bahnhof und Jahr | Jährlich |
| `sbb_get_rail_disruptions` | Live-Bahnverkehrsmeldungen | Alle 5 Min. |
| `sbb_get_infrastructure_construction_projects` | Infrastruktur-Bauprojekte | Laufend |
| `sbb_get_real_estate_projects` | Immobilien-Bauprojekte der SBB | Täglich |
| `sbb_get_trains_per_segment` | Zugzahlen pro Streckenabschnitt | Jährlich |
| `sbb_get_platform_data` | Perrondaten (Länge, Typ, Fläche) | Laufend |
| `sbb_get_rolling_stock` | Rollmaterial (Kapazität, Baujahr) | Laufend |
| `sbb_compare_stations` | Mehrere Bahnhöfe vergleichen | – |
| `sbb_search_stations` | Haltestellen suchen (DiDok-Liste BAV) | Laufend |
| `sbb_list_datasets` | Alle ~89 SBB Open Data Datensätze | – |

---

## Installation

### Claude Desktop (stdio)

Voraussetzung: [uv](https://github.com/astral-sh/uv) installiert.

Konfigurationsdatei öffnen:
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

### Andere MCP-Clients (Cursor, Windsurf, VS Code + Continue, LibreChat)

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

### Cloud-Deployment (Streamable HTTP / Render.com)

```bash
git clone https://github.com/malkreide/sbb-opendata-mcp
cd sbb-opendata-mcp
pip install -e .
python -m sbb_opendata_mcp.server --http --port 8000
```

### Lokale Entwicklung

```bash
git clone https://github.com/malkreide/sbb-opendata-mcp
cd sbb-opendata-mcp
pip install -e ".[dev]"

# Tests ausführen
PYTHONPATH=src pytest tests/ -v -m "not live"

# Live API Tests
PYTHONPATH=src pytest tests/ -v -m live
```

---

## Beispielabfragen

```
"Wie viele Personen stiegen 2024 täglich in Zürich HB ein und aus?"
→ sbb_get_passenger_frequency(station_name="Zürich HB", year="2024")

"Gibt es aktuell Störungen auf dem Schweizer Bahnnetz?"
→ sbb_get_rail_disruptions(limit=10)

"Vergleiche die Bahnhöfe Zürich HB, Bern und Basel SBB anhand Passagierfrequenz."
→ sbb_compare_stations(stations=["Zürich HB", "Bern", "Basel SBB"], year="2024")

"Welche SBB-Bauprojekte laufen in Zürich?"
→ sbb_get_infrastructure_construction_projects(city="Zürich")

"Wie viele Züge fahren täglich auf der Strecke Zürich–Winterthur?"
→ sbb_get_trains_per_segment(line_name="Zürich", operator="SBB", year="2025")
```

---

## Datenbasis

Alle Daten stammen vom [SBB Open Data Portal](https://data.sbb.ch) (OpenDataSoft). 
Lizenz: [NonCommercialAllowed-CommercialAllowed-ReferenceRequired](https://data.sbb.ch/page/licence)

Dieses Projekt steht unter der **MIT-Lizenz** und ist Teil der Open Source MCP-Portfolio unter [github.com/malkreide](https://github.com/malkreide).

---

## Passung zu anderen MCP-Servern

| Server | Ergänzung durch SBB Open Data |
|--------|-------------------------------|
| [swiss-transport-mcp](https://github.com/malkreide/swiss-transport-mcp) | Historische Tiefe: Warum ist eine Station wichtig? Passagierkontext zu Echtzeit-Abfragen |
| [swiss-road-mobility-mcp](https://github.com/malkreide/swiss-road-mobility-mcp) | Multimodale Perspektive: Bahn-Hub + Mikromobilität/E-Laden |
| [zurich-opendata-mcp](https://github.com/malkreide/zurich-opendata-mcp) | Cross-referenz: Zürcher Haltestellen mit städtischen Schul-/Bevölkerungsdaten |

---

<a name="english"></a>
## English

An MCP Server for Swiss Federal Railways (SBB) open data via [data.sbb.ch](https://data.sbb.ch). No API key required.

### Available Tools

- **Passenger frequency** by station and year
- **Live rail disruptions** (updated every 5 minutes)
- **Infrastructure construction projects**
- **Real estate projects** (updated daily)
- **Trains per route segment**
- **Platform data** (length, type, area)
- **Rolling stock** (capacity, year built)
- **Station comparison** (multi-dataset, up to 10 stations)
- **Station search** (Swiss DiDok register, all CH stops)
- **List all datasets** (~89 available)

### Quick Start

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

All data: [data.sbb.ch](https://data.sbb.ch) | OpenDataSoft REST API v2.1 | No authentication needed.
