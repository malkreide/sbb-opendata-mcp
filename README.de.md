# 🚆 sbb-opendata-mcp

🇨🇭 **Teil des [Swiss Public Data MCP Portfolios](https://github.com/malkreide/swiss-public-data-mcp)**

[![PyPI](https://img.shields.io/pypi/v/sbb-opendata-mcp)](https://pypi.org/project/sbb-opendata-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple)](https://modelcontextprotocol.io/)
[![Data Source](https://img.shields.io/badge/Data-data.sbb.ch-red)](https://data.sbb.ch/)
![CI](https://github.com/malkreide/sbb-opendata-mcp/actions/workflows/ci.yml/badge.svg)

> MCP-Server, der KI-Modelle mit den offenen Daten der Schweizerischen Bundesbahnen (SBB) verbindet – Passagierfrequenz, Live-Störungen, Infrastruktur- & Immobilienprojekte, Zugzahlen, Perrondaten, Rollmaterial und Haltestellensuche von [data.sbb.ch](https://data.sbb.ch/). **Kein API-Key erforderlich.**

[🇬🇧 English Version](README.md)

### Demo

![Demo: Claude fragt SBB-Passagierfrequenz ab](docs/assets/demo.svg)

---

## Überblick

**sbb-opendata-mcp** gibt KI-Assistenten wie Claude direkten Zugriff auf öffentliche
SBB-Daten – ohne Umwege über Copy-Paste oder manuelle API-Aufrufe. Eine Frage wie
*«Wie viele Personen stiegen 2024 täglich in Zürich HB ein und aus?»* wird direkt mit
echten Messdaten beantwortet.

Das SBB-Open-Data-Portal spricht die OpenDataSoft-REST-API (v2.1). Dieser Server
übersetzt sie in sauberes Markdown und JSON für das KI-Modell und liefert zusätzlich
MCP-`structuredContent` parallel zum lesbaren Text, sodass programmatische Clients die
zugrunde liegenden Datensätze ohne erneutes Parsen verarbeiten können. Der Server ist
modellunabhängig und funktioniert mit jedem MCP-kompatiblen Client.

**Anker-Demo-Abfrage:** *«Vergleiche Zürich HB, Bern und Basel SBB anhand Passagierfrequenz und Perronkapazität.»*
→ [Weitere Anwendungsfälle nach Zielgruppe](EXAMPLES.md) →

---

## Funktionen

- 📊 **Passagierfrequenz** – Ein-/Aussteigende nach Bahnhof und Jahr (Tagesschnitte)
- 🚨 **Live-Störungen** – Bahnverkehrsmeldungen, alle 5 Minuten aktualisiert
- 🏗️ **Infrastrukturprojekte** – Bahnhof- und Streckenbau
- 🏢 **Immobilienprojekte** – Immobilienentwicklung der SBB (täglich aktualisiert)
- 🚆 **Zugzahlen pro Abschnitt** – Zugzahlen pro Strecke (SBB, BLS, SOB …)
- 🛤️ **Perrondaten** – Länge, Typ, Fläche, schienenfreier Zugang
- 🚃 **Rollmaterial** – Kapazität und Baujahr
- 🔁 **Bahnhofvergleich** – bis zu 10 Bahnhöfe über mehrere Datensätze
- 🔍 **Haltestellensuche** – DiDok-Register des BAV (ganze Schweiz)
- 📦 **Datenkatalog** – alle ~89 SBB-Open-Data-Datensätze auflisten
- 🔑 **Kein API-Key** – alle Daten sind öffentlich und frei nutzbar
- ☁️ **Dual-Transport** – stdio für Claude Desktop, Streamable HTTP für die Cloud

---

## Voraussetzungen

- Python 3.11+
- Kein API-Key – alle Daten stammen vom öffentlichen Portal [data.sbb.ch](https://data.sbb.ch)

[uv](https://github.com/astral-sh/uv) installieren (empfohlen):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Installation

Von [PyPI](https://pypi.org/project/sbb-opendata-mcp/):

```bash
pip install sbb-opendata-mcp
```

Oder mit `uvx` (ohne permanente Installation):

```bash
uvx sbb-opendata-mcp
```

Für die lokale Entwicklung als editierbare Installation aus einem Klon:

```bash
git clone https://github.com/malkreide/sbb-opendata-mcp.git
cd sbb-opendata-mcp
pip install -e ".[dev]"
```

---

## Schnellstart

```bash
# Server starten (stdio-Modus für Claude Desktop)
sbb-opendata-mcp
```

Direkt in Claude Desktop ausprobieren:

> *«Wie viele Personen stiegen 2024 täglich in Zürich HB ein und aus?»*
> *«Gibt es aktuell Störungen auf dem Schweizer Bahnnetz?»*

---

## Konfiguration

### Umgebungsvariablen

Für den Betrieb über stdio braucht der Server keine Konfiguration. Die folgenden
Variablen steuern den optionalen Streamable-HTTP-Transport, das Logging und die
Observability.

| Variable | Wirkung | Standard |
|---|---|---|
| `MCP_HOST` | Bind-Host für den HTTP-Transport. Lokal `127.0.0.1` belassen; `0.0.0.0` nur in einer kontrollierten Container-/Cloud-Umgebung. | `127.0.0.1` |
| `MCP_PORT` | Port für den HTTP-Transport. | `8000` |
| `MCP_ALLOWED_HOSTS` | Kommagetrennte Host-Allow-List für den DNS-Rebinding-Schutz (z.B. `your-app.onrender.com,your-app.onrender.com:*`). | nur localhost |
| `MCP_ALLOWED_ORIGINS` | Kommagetrennte Browser-Origin-Allow-List (z.B. `https://your-app.onrender.com`). | _(keine)_ |
| `LOG_LEVEL` | Log-Detailgrad (`DEBUG`/`INFO`/`WARNING`/…). | `INFO` |
| `LOG_FORMAT` | `json` für strukturierte Logs; sonst lesbarer Text. Immer auf stderr. | `text` |

> 🔒 Der DNS-Rebinding-/Origin-Schutz ist **immer aktiv**; localhost ist freigegeben,
> damit die lokale HTTP-Entwicklung funktioniert. Logs gehen auf **stderr** – stdout
> ist dem stdio-JSON-RPC-Kanal vorbehalten.

### Claude-Desktop-Konfiguration

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

**Pfade der Konfigurationsdatei:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Claude Desktop neu starten – der Server wird beim ersten Aufruf automatisch heruntergeladen.

### Andere MCP-Clients

Funktioniert mit Cursor, Windsurf, VS Code + Continue, LibreChat, Cline und selbst
gehosteten Modellen via `mcp-proxy` – gleiche Konfiguration wie oben.

### Cloud-Deployment (Streamable HTTP)

Für die Nutzung via **claude.ai im Browser** oder Remote-Server (z.B. [Render.com](https://render.com)). Der Cloud-Transport ist **Streamable HTTP** (Endpunkt `/mcp`).

**Docker (empfohlen):**

```bash
# Build + Run mit expliziten Ressourcenlimits (siehe docker-compose.yml)
docker compose up --build
# → http://127.0.0.1:8000/mcp
```

Das Image ist ein Multi-Stage-Build und läuft als **Non-Root**-Benutzer;
`docker-compose.yml` ergänzt `read_only`, `no-new-privileges` und Memory-/CPU-/PID-Limits.

**Manuell / Render.com:**

```bash
pip install -e .

# Öffentlich binden (hinter einem Reverse-Proxy mit Rate-Limit) und
# DNS-Rebinding-/Origin-Schutz für den eigenen Hostnamen konfigurieren:
export MCP_HOST=0.0.0.0
export MCP_ALLOWED_HOSTS="your-app.onrender.com,your-app.onrender.com:*"
export MCP_ALLOWED_ORIGINS="https://your-app.onrender.com"
python -m sbb_opendata_mcp.server --http --port 8000
```

> ⚠️ **Binding:** Bei einem Netzwerk-Transport bindet der Server standardmässig an
> `127.0.0.1`, sodass ein lokal gestarteter Server **nicht** dem ganzen Netzwerk
> ausgesetzt ist. Setzen Sie `MCP_HOST=0.0.0.0` **nur** in einer Container-/Cloud-
> Umgebung, in der das Binden an alle Interfaces beabsichtigt ist (das Docker-Image
> tut dies für Sie), und stellen Sie den Server hinter einen Reverse-Proxy mit
> Rate-Limiting (sowie Authentifizierung, falls der Endpunkt nicht öffentlich sein
> soll). Siehe [`SECURITY.de.md`](SECURITY.de.md).

---

## Verfügbare Tools

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

Alle Tools unterstützen `response_format: "markdown"` (lesbar) und `"json"`
(maschinenlesbar) sowie Paginierung. Zusätzlich liefert jedes Tool MCP-`structuredContent`
(die zugrunde liegenden Datensätze/Metadaten) parallel zum gerenderten Text.

### Beispiel-Anwendungsfälle

| Abfrage | Tool |
|---|---|
| *«Wie viele Personen stiegen 2024 täglich in Zürich HB ein und aus?»* | `sbb_get_passenger_frequency` |
| *«Gibt es aktuell Störungen auf dem Schweizer Bahnnetz?»* | `sbb_get_rail_disruptions` |
| *«Vergleiche Zürich HB, Bern und Basel SBB»* | `sbb_compare_stations` |
| *«Welche SBB-Bauprojekte laufen in Zürich?»* | `sbb_get_infrastructure_construction_projects` |
| *«Wie viele Züge fahren jährlich auf der Strecke Zürich–Winterthur?»* | `sbb_get_trains_per_segment` |
| *«Welche Haltestellen gibt es in Wädenswil?»* | `sbb_search_stations` |

→ [Weitere Anwendungsfälle nach Zielgruppe](EXAMPLES.md)

---

## Architektur

```
┌─────────────────┐     ┌───────────────────────────┐     ┌──────────────────────────┐
│   Claude / KI   │────▶│   SBB Open Data MCP       │────▶│       data.sbb.ch        │
│   (MCP-Host)    │◀────│   (MCP-Server)            │◀────│                          │
└─────────────────┘     │                           │     │  OpenDataSoft REST v2.1  │
                        │  10 Tools                 │     │  (öffentlich, kein Key)  │
                        │  Stdio | Streamable HTTP  │     │                          │
                        │                           │     │  passagierfrequenz       │
                        │  Gemeinsamer httpx-Client │     │  rail-traffic-information │
                        │  (gepoolt, Lifespan)      │     │  construction-projects   │
                        │  ODSQL-Escaping + Pydantic │    │  perron · rollmaterial   │
                        │  Validierung              │     │  zugzahlen · dienststellen│
                        └───────────────────────────┘     └──────────────────────────┘
```

---

## Projektstruktur

```
sbb-opendata-mcp/
├── src/sbb_opendata_mcp/
│   ├── __init__.py
│   └── server.py                   # FastMCP-Server, alle 10 Tool-Definitionen
├── tests/
│   └── test_server.py              # Unit- + Live-API-Smoke-Tests
├── audits/                         # MCP-Best-Practice-Audit-Evidenz
├── docs/assets/demo.svg            # README-Demo-Asset
├── .github/workflows/ci.yml        # GitHub Actions (Python 3.11/3.12/3.13)
├── Dockerfile                      # Multi-Stage, Non-Root-Runtime-Image
├── docker-compose.yml              # Lokaler Run mit Ressourcenlimits
├── claude_desktop_config.json      # Beispiel-Claude-Desktop-Konfiguration
├── pyproject.toml
├── CHANGELOG.md
├── CONTRIBUTING.de.md
├── SECURITY.de.md
├── EXAMPLES.md
├── LICENSE
├── README.de.md                    # Diese Datei (Deutsch)
└── README.md                       # Englische Version
```

---

## Sicherheit & Grenzen

- **Rein lesend:** Alle 10 Tools führen nur lesende HTTP-GET-Anfragen aus – upstream wird nichts geschrieben, geändert oder gelöscht.
- **Keine Personendaten:** Abfragen sind transient und werden nicht gespeichert. Das Portal liefert aggregierte Statistiken, Infrastruktur- und Betriebsmetadaten. Es werden keine PII verarbeitet oder gespeichert.
- **Kein API-Key:** Die Daten sind öffentlich und frei. Es gibt keine Authentifizierung und kein zu verwaltendes Secret.
- **Injection-gehärtet:** `year`/`canton` werden per Regex validiert, und jeder in eine ODSQL-`where`-Klausel interpolierte Wert wird über einen zentralen Helfer escaped.
- **Datenaktualität:** Echtzeit-Tools (Störungen) spiegeln den Upstream zum Abfragezeitpunkt; statistische Datensätze werden jährlich/täglich aktualisiert (siehe Tool-Tabelle).
- **Nutzungsbedingungen:** Die Daten stehen unter der [data.sbb.ch-Lizenz](https://data.sbb.ch/page/licence) (NonCommercialAllowed-CommercialAllowed-ReferenceRequired).
- **Keine Garantien:** Dieser Server ist ein Community-Projekt und nicht mit der SBB verbunden. Die Verfügbarkeit hängt von der Upstream-API ab.

Die vollständige Sicherheitslage finden Sie in [`SECURITY.de.md`](SECURITY.de.md).

---

## Bekannte Einschränkungen

- **Passagierfrequenz:** Jährlich aktualisiert; das jüngste vollständige Jahr kann einige Monate nachhinken.
- **Bahnstörungen:** Liefert alle aktuellen Schweizer Bahnmeldungen → `limit` und Paginierung nutzen.
- **Zugzahlen pro Abschnitt:** Jahresaggregate, nicht in Echtzeit.
- **Haltestellensuche:** Deckt das gesamte DiDok-Register (alle Betreiber) ab, nicht nur SBB.
- **Kein eigenes Rate-Limiting:** Ein öffentliches HTTP-Deployment hinter einen Reverse-Proxy mit Rate-Limit stellen.

---

## Tests

Es ist kein API-Key erforderlich.

```bash
# Unit-Tests (ohne Netzwerk)
PYTHONPATH=src pytest tests/ -m "not live"

# Live-API-Smoke-Tests (benötigen Netzwerkzugriff auf data.sbb.ch)
PYTHONPATH=src pytest tests/ -m live
```

---

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md)

---

## Beitragen

Siehe [CONTRIBUTING.de.md](CONTRIBUTING.de.md)

---

## Lizenz

MIT-Lizenz — siehe [LICENSE](LICENSE)

---

## Autor

Hayal Oezkan · [github.com/malkreide](https://github.com/malkreide)

---

## Credits & verwandte Projekte

- **Daten:** [data.sbb.ch](https://data.sbb.ch/) – Schweizerische Bundesbahnen (SBB) Open Data, OpenDataSoft REST API v2.1
- **Protokoll:** [Model Context Protocol](https://modelcontextprotocol.io/) – Anthropic / Linux Foundation
- **Verwandt:**
  - [swiss-transport-mcp](https://github.com/malkreide/swiss-transport-mcp) – Echtzeit-Fahrpläne, Reisen & Störungen (opentransportdata.swiss)
  - [swiss-road-mobility-mcp](https://github.com/malkreide/swiss-road-mobility-mcp) – Mikromobilität & E-Laden
  - [zurich-opendata-mcp](https://github.com/malkreide/zurich-opendata-mcp) – MCP-Server für Open Data der Stadt Zürich
- **Portfolio:** [Swiss Public Data MCP Portfolio](https://github.com/malkreide/swiss-public-data-mcp)
