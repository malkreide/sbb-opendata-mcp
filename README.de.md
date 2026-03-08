# SBB Open Data MCP Server

🇩🇪 Deutsch | [🇬🇧 English](README.md)

Ein [Model Context Protocol (MCP)](https://modelcontextprotocol.io) Server für die offenen Daten der Schweizerischen Bundesbahnen (SBB) via [data.sbb.ch](https://data.sbb.ch). Kein API-Key erforderlich.

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-1.6%2B-purple)](https://modelcontextprotocol.io)

---

## Was ist das?

Dieser Server verbindet KI-Modelle (Claude, GPT-4, Llama u.a.) mit den öffentlichen Daten der SBB – ohne Umwege über Copy-Paste oder manuelle API-Aufrufe. Eine Frage wie *«Wie viele Personen stiegen 2024 täglich in Zürich HB ein und aus?»* wird direkt mit echten Messdaten beantwortet.

Der Server ist modellunabhängig und funktioniert mit jedem MCP-kompatiblen Client.

---

## Verfügbare Tools (10)

| Tool | Beschreibung | Datenaktualisierung |
|------|-------------|---------------------|
| `sbb_get_passenger_frequency` | Ein-/Aussteigende nach Bahnhof und Jahr (DTV/DWV) | Jährlich |
| `sbb_get_rail_disruptions` | Live-Bahnverkehrsmeldungen | Alle 5 Min. |
| `sbb_get_infrastructure_construction_projects` | Infrastruktur-Bauprojekte (Bahnhöfe, Strecken) | Laufend |
| `sbb_get_real_estate_projects` | Immobilien-Bauprojekte der SBB | Täglich |
| `sbb_get_trains_per_segment` | Zugzahlen pro Streckenabschnitt (SBB, BLS, SOB …) | Jährlich |
| `sbb_get_platform_data` | Perrondaten (Länge, Typ, Fläche) | Laufend |
| `sbb_get_rolling_stock` | Rollmaterial (Kapazität, Baujahr) | Laufend |
| `sbb_compare_stations` | Mehrere Bahnhöfe vergleichen (bis 10, multi-Datensatz) | – |
| `sbb_search_stations` | Haltestellen suchen (DiDok-Liste BAV, alle CH) | Laufend |
| `sbb_list_datasets` | Alle ~89 SBB Open Data Datensätze auflisten | – |

Alle Tools unterstützen `response_format: "markdown"` (für Menschen lesbar) und `"json"` (maschinenlesbar) sowie Paginierung.

---

## Installation

### Voraussetzung

[uv](https://github.com/astral-sh/uv) installieren:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Claude Desktop (stdio)

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

Claude Desktop neu starten. Der Server wird automatisch beim ersten Aufruf heruntergeladen.

### Andere MCP-Clients

Funktioniert mit Cursor, Windsurf, VS Code + Continue, LibreChat, Cline und selbst gehosteten Modellen via `mcp-proxy` – gleiche Konfiguration wie oben.

### Cloud-Deployment (Streamable HTTP)

Für Remote-Server (z.B. [Render.com](https://render.com)):

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

# Unit-Tests (ohne Netzwerk)
PYTHONPATH=src pytest tests/ -v -m "not live"

# Live API Smoke Tests
PYTHONPATH=src pytest tests/ -v -m live
```

---

## Beispielabfragen

```
"Wie viele Personen stiegen 2024 täglich in Zürich HB ein und aus?"
→ sbb_get_passenger_frequency(station_name="Zürich HB", year="2024")

"Gibt es aktuell Störungen auf dem Schweizer Bahnnetz?"
→ sbb_get_rail_disruptions(limit=10)

"Vergleiche Zürich HB, Bern und Basel SBB anhand Passagierfrequenz und Perrons."
→ sbb_compare_stations(stations=["Zürich HB", "Bern", "Basel SBB"], year="2024")

"Welche SBB-Bauprojekte laufen in Zürich?"
→ sbb_get_infrastructure_construction_projects(city="Zürich")

"Wie viele Züge fahren täglich auf der Strecke Zürich–Winterthur?"
→ sbb_get_trains_per_segment(line_name="Zürich", operator="SBB", year="2025")

"Welche Bahnhöfe gibt es in Wädenswil?"
→ sbb_search_stations(query="Wädenswil", canton="ZH")
```

---

## Datenbasis und Lizenz

Alle Daten stammen vom [SBB Open Data Portal](https://data.sbb.ch) (OpenDataSoft REST API v2.1).  
Datenlizenz: [NonCommercialAllowed-CommercialAllowed-ReferenceRequired](https://data.sbb.ch/page/licence)

Dieser Server steht unter der **MIT-Lizenz** und ist Teil des Open Source MCP-Portfolios unter [github.com/malkreide](https://github.com/malkreide).

---

## Passung zu anderen MCP-Servern

| Server | Wie SBB Open Data ergänzt |
|--------|--------------------------|
| [swiss-transport-mcp](https://github.com/malkreide/swiss-transport-mcp) | Historische Tiefe: Passagierkontext zu Echtzeit-Fahrplan-Abfragen |
| [swiss-road-mobility-mcp](https://github.com/malkreide/swiss-road-mobility-mcp) | Multimodale Perspektive: Bahn-Hub + Mikromobilität/E-Laden |
| [zurich-opendata-mcp](https://github.com/malkreide/zurich-opendata-mcp) | Cross-Referenz: Zürcher Haltestellen mit städtischen Bevölkerungs- und Schuldaten |

---

## Technische Details

- **Framework:** [FastMCP](https://github.com/modelcontextprotocol/python-sdk) + httpx + Pydantic v2
- **Transport:** stdio (lokal) und Streamable HTTP (Cloud)
- **Python:** 3.11, 3.12, 3.13
- **Tests:** 34 Unit-Tests + 5 Live API Smoke Tests
- **API:** [OpenDataSoft REST v2.1](https://data.sbb.ch/api/explore/v2.1/) — kein API-Key
