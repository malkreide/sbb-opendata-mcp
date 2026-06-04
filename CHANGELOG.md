# Changelog

## [Unreleased]

### Security
- **F-SEC-03:** Fehlermeldungen an den Client geben keine Upstream-Response-Bodies
  oder internen Exception-Strings mehr preis. Details (Body, Exception, Traceback)
  werden serverseitig protokolliert; der Client erhält nur eine bereinigte Meldung.
- **F-SEC-04:** Abhängigkeiten mit Major-Obergrenzen versehen (`mcp[cli]>=1.6.0,<2`,
  `httpx>=0.27.0,<1`, `pydantic>=2.0.0,<3`) und reproduzierbaren `uv.lock` committet.

### Performance
- **F-SCALE-01:** Ein gemeinsamer, langlebiger `httpx.AsyncClient` (Connection-Pooling
  mit Keep-Alive) ersetzt das bisherige Anlegen eines neuen Clients pro Request; der
  Client wird beim Server-Shutdown über einen Lifespan-Hook geschlossen. `compare_stations`
  ruft die Stationen jetzt nebenläufig via `asyncio.gather` ab (vorher 2×N sequentielle
  Requests).

### Observability
- **F-OBS-01:** Strukturiertes Logging ergänzt. Package-Logger `sbb_opendata_mcp`
  mit Handler auf **stderr** (stdout bleibt dem stdio-JSON-RPC-Kanal vorbehalten).
  Konfigurierbar über `LOG_LEVEL` (Default INFO) und `LOG_FORMAT` (`text`/`json`).
  Upstream-Requests/-Responses werden mit Dataset, Statuscode und Dauer geloggt;
  jede in `_handle_api_error` gefangene Exception wird protokolliert (Client erhält
  weiterhin nur eine bereinigte Meldung). Startup-Event mit Transport/Host/Port.

### Security
- **F-SEC-01:** ODSQL-Injection gehärtet. `year`-/`canton`-Parameter werden jetzt per
  Regex (`^\d{4}$` / `^[A-Za-z]{2}$`) validiert, und alle in die `where`-Klausel
  interpolierten String-Werte (inkl. zuvor ungeescapter `operator`, `phase`,
  `traffic_type`) laufen über einen zentralen `_odsql_quote()`-Escaper (Backslash + Quote).
- **F-SEC-02:** Streamable-HTTP-Transport gehärtet. DNS-Rebinding-/Origin-Schutz ist
  aktiviert; Bind-Host und Host/Origin-Allowlists sind über `MCP_HOST`,
  `MCP_ALLOWED_HOSTS` und `MCP_ALLOWED_ORIGINS` konfigurierbar (Default: `127.0.0.1`,
  localhost erlaubt). Fehlerhaften HTTP-Entry-Point korrigiert
  (`transport="streamable-http"`, Port via Settings).

## [0.1.0] — 2026-03-08

### Erstveröffentlichung / Initial Release

**9 Tools:**
- `sbb_get_passenger_frequency` — Passagierfrequenz nach Bahnhof und Jahr
- `sbb_get_rail_disruptions` — Live-Bahnverkehrsmeldungen (alle 5 Min.)
- `sbb_get_infrastructure_construction_projects` — Infrastruktur-Bauprojekte
- `sbb_get_real_estate_projects` — Immobilien-Bauprojekte (tägl. aktualisiert)
- `sbb_get_trains_per_segment` — Zugzahlen pro Streckenabschnitt
- `sbb_get_platform_data` — Perrondaten (Länge, Fläche, Typ)
- `sbb_get_rolling_stock` — Rollmaterial-Daten (Kapazität, Baujahr)
- `sbb_compare_stations` — Mehrere Bahnhöfe vergleichen (kombiniert 2 Datasets)
- `sbb_search_stations` — Haltestellensuche (DiDok-Liste BAV, alle CH-Haltestellen)
- `sbb_list_datasets` — Alle ~89 SBB Open Data Datensätze auflisten

**Technische Merkmale:**
- Kein API-Key erforderlich
- OpenDataSoft REST API v2.1 (data.sbb.ch)
- Dual Transport: stdio (Claude Desktop) + Streamable HTTP (Cloud/Render.com)
- Paginierung für alle Listen-Tools
- Markdown- und JSON-Ausgabeformat
- 34 Unit-Tests + 5 Live API Smoke Tests
