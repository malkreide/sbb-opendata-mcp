# Changelog

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
