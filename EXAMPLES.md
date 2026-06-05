# Use Cases & Examples — sbb-opendata-mcp

Real-world queries by audience. **Kein API-Key erforderlich** – alle Tools greifen direkt auf das öffentliche SBB-Open-Data-Portal [data.sbb.ch](https://data.sbb.ch) zu.

## 🏫 Bildung & Schule
Lehrpersonen, Schulbehörden, Fachreferent:innen

**Bahnhof als Unterrichtsthema**
«Wie viele Personen stiegen 2024 täglich in Zürich HB ein und aus – und wie verteilt sich das auf Werktage und Wochenende?»
→ `sbb_get_passenger_frequency(station_name="Zürich HB", year="2024")`
Warum nützlich: Liefert echte Messdaten für Statistik-, Geografie- oder Mathematikprojekte rund um den öffentlichen Verkehr.

**Bahnhöfe vergleichen lassen**
«Vergleiche Zürich HB, Bern und Basel SBB anhand Passagierfrequenz und Perronkapazität.»
→ `sbb_compare_stations(stations=["Zürich HB", "Bern", "Basel SBB"], year="2024")`
Warum nützlich: Erlaubt einen anschaulichen Datenvergleich grosser Schweizer Bahnhöfe als Grundlage für Präsentationen und Diskussionen im Unterricht.

## 👨‍👩‍👧 Eltern & Schulgemeinde
Elternräte, interessierte Erziehungsberechtigte

**Haltestellen am Wohnort finden**
«Welche Bahnhöfe und Haltestellen gibt es in Wädenswil?»
→ `sbb_search_stations(query="Wädenswil", canton="ZH")`
Warum nützlich: Eltern können rasch prüfen, welche öV-Haltestellen sich am Wohnort oder in Schulnähe befinden.

**Barrierefreiheit und Perrondaten**
«Welche Perrons hat der Bahnhof Bern und wie lang sind sie?»
→ `sbb_get_platform_data(station_name="Bern")`
Warum nützlich: Gibt Familien mit Kinderwagen oder eingeschränkter Mobilität konkrete Informationen zu Perronlänge, Typ und schienenfreier Zugänglichkeit.

## 🗳️ Bevölkerung & öffentliches Interesse
Allgemeine Öffentlichkeit, politisch und gesellschaftlich Interessierte

**Aktuelle Störungen prüfen**
«Gibt es aktuell Störungen auf dem Schweizer Bahnnetz?»
→ `sbb_get_rail_disruptions(limit=10)`
Warum nützlich: Bietet einen schnellen, alle 5 Minuten aktualisierten Überblick über laufende Bahnverkehrsmeldungen direkt aus offizieller Quelle.

**Bauprojekte in der eigenen Region**
«Welche SBB-Infrastruktur-Bauprojekte laufen in Zürich?»
→ `sbb_get_infrastructure_construction_projects(city="Zürich")`
Warum nützlich: Macht laufende Bahnhof- und Streckenprojekte transparent – relevant für Anwohnerinnen, Raumplanung und politische Diskussionen.

**Immobilienentwicklung der SBB**
«Welche Immobilien-Bauprojekte der SBB befinden sich in Luzern in der Bauphase?»
→ `sbb_get_real_estate_projects(city="Luzern", phase="CONSTRUCTION")`
Warum nützlich: Zeigt, wie die SBB ihre Areale entwickelt – nützlich für Standort- und Wohnraumfragen.

## 🤖 KI-Interessierte & Entwickler:innen
MCP-Enthusiast:innen, Forscher:innen, Prompt Engineers, öffentliche Verwaltung

**Streckenauslastung analysieren**
«Wie viele Züge fahren jährlich auf der Strecke Zürich–Winterthur, und wer betreibt die Infrastruktur?»
→ `sbb_get_trains_per_segment(line_name="Zürich", operator="SBB", year="2025")`
Warum nützlich: Liefert belastbare Kennzahlen pro Streckenabschnitt für Mobilitäts- und Infrastrukturanalysen.

**Cross-Domain-Analyse (Multi-Server)**
«Welche Bahnhöfe gibt es in Zürich und was sagen die städtischen Open-Data dazu?»
→ `sbb_search_stations(query="Zürich", canton="ZH")`
→ `zurich_search_datasets(query="verkehr")` *(via [zurich-opendata-mcp](https://github.com/malkreide/zurich-opendata-mcp))*
Warum nützlich: Demonstriert die Stärke des Model Context Protocols, wenn nationale Bahndaten und lokale Stadtverwaltungsdaten verknüpft werden.

**Datenkatalog erkunden**
«Welche SBB-Open-Data-Datensätze gibt es überhaupt?»
→ `sbb_list_datasets()`
Warum nützlich: Entwickler:innen verschaffen sich rasch einen Überblick über alle ~89 verfügbaren Datensätze, ihre IDs und Aktualisierungsfrequenzen.

## 🔧 Technische Referenz: Tool-Auswahl nach Anwendungsfall

| Ich möchte… | Tool(s) | Auth nötig? |
|---|---|---|
| Ein-/Aussteigende eines Bahnhofs nach Jahr abfragen | `sbb_get_passenger_frequency` | Nein |
| Aktuelle Bahnverkehrsstörungen prüfen | `sbb_get_rail_disruptions` | Nein |
| Infrastruktur-Bauprojekte (Bahnhöfe, Strecken) finden | `sbb_get_infrastructure_construction_projects` | Nein |
| Immobilien-Bauprojekte der SBB ansehen | `sbb_get_real_estate_projects` | Nein |
| Zugzahlen pro Streckenabschnitt analysieren | `sbb_get_trains_per_segment` | Nein |
| Perrondaten (Länge, Typ, Fläche) abrufen | `sbb_get_platform_data` | Nein |
| Rollmaterial (Kapazität, Baujahr) nachschlagen | `sbb_get_rolling_stock` | Nein |
| Mehrere Bahnhöfe miteinander vergleichen | `sbb_compare_stations` | Nein |
| Eine Haltestelle über den Namen suchen | `sbb_search_stations` | Nein |
| Den Open-Data-Katalog auflisten | `sbb_list_datasets` | Nein |
