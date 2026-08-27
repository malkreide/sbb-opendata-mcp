# Changelog

Alle relevanten Änderungen an diesem Projekt werden hier dokumentiert.
All notable changes to this project are documented here.

## [Unreleased]

### Behoben — ein Timeout ist kein gebrochener Vertrag

Am 26.8.2026 lief `test_live_search_waedenswil` in das 30-s-Zeitlimit. Der Lauf
wurde `finding`, `live.yml` machte Issue #48 auf und schrieb hinein, der Vertrag
mit `data.sbb.ch` habe sich geaendert. Nachgemessen am 27.8.2026 mit genau
derselben Anfrage: sechs Laeufe, 0.44 bis 0.80 s, HTTP 200. Es hatte sich nichts
geaendert — die Quelle hatte einmal nicht geantwortet, und der Lauf hat darueber
**nichts** festgestellt.

Der Klassifikator kannte den Fall und nannte ihn im eigenen Docstring («ein
Timeout: alles `unknown`»). Nur kam ein Timeout *innerhalb* eines Tests nie dort
an, sondern als Fehlschlag — und ein Fehlschlag heisst `finding`. Genau die
Verwechslung, gegen die die drei Antworten gebaut wurden, nur eine Ebene tiefer.

- `_is_source_unavailable()` zieht die Grenze: Timeout, Verbindungsabbruch, 429
  und 5xx heissen «keine Antwort». HTTP 400 und 404 sind **Antworten** und
  bleiben Befunde — 400 ist die vom 3.8.2026, als die Quelle einen Feldnamen
  wechselte. Ein Werkzeug-Resultat traegt das Ergebnis als
  `upstream_unavailable`.
- `live_attempt()` wiederholt eine ausgebliebene Antwort dreimal (2 s, 5 s) und
  ueberspringt danach mit `SOURCE_UNAVAILABLE` im Grund. Ein `AssertionError`,
  ein 400 und ein 404 werden **nie** wiederholt und nie uebersprungen.
- Der Klassifikator liest den Marker und antwortet `unknown` statt `clear`. Der
  Job bleibt rot, aber es geht kein Issue auf, das einen Vergleich behauptet,
  den es nicht gab, und keines zu, das nie verglichen wurde.

Der bewusste Skip bleibt davon unberuehrt und gruen: Zwei Skips mit
gegensaetzlicher Bedeutung trennen sich nur am Grund, nicht an der Zahl. Beide
Richtungen sind gegengeprobt — «jeder Skip ist ein Ausfall» faellt genauso wie
«kein Skip ist einer».

Nachgemessen statt behauptet: Mit unerreichbar gesetzter Basis-URL uebersprang
die Live-Suite alle sechs Tests, und `scripts/classify_live_run.py` antwortete
`unknown` mit «die Quelle hat bei 6 von 6 Test(s) nicht geantwortet».

### Behoben — die Basis-URL stand zweimal

Aufgefallen bei genau dieser Simulation: Fuenf Live-Tests uebersprangen,
`test_live_list_datasets` lief gruen durch. Das Werkzeug trug die Adresse der
Quelle als zweites Literal und zeigte damit als einziges nicht auf das, was
`BASE_URL` sagt. Solange beide gleich lauten, faellt das nicht auf — und beim
naechsten Umzug faellt es still aus, weil die alte Adresse ja antwortet.
`sbb_list_datasets` nimmt jetzt `BASE_URL`, und ein Test haelt fest, dass das
Literal genau einmal vorkommt.

### Hinzugefuegt

- **Frischehinweise auf `tools/list` und `server/discover`** (SEP-2549, Spec
  `2026-07-28`): `ttlMs` 300000, `cacheScope` `public`. Das SDK setzt beides von
  sich aus auf «sofort veraltet, nie geteilt» — wer nichts übergibt, verhält
  sich also nicht neutral, sondern lässt jeden Client bei jeder Verbindung neu
  auflisten, für eine Liste, die beim Import feststeht und für jeden Aufrufer
  dieselbe ist. `prompts/list` und `resources/list` bleiben ungesetzt: dieser
  Server registriert weder das eine noch das andere.

- **Protokoll-Gate: beide Spec-Aeren gepinnt und geprueft**
  (`tests/test_protocol_version.py`). `mcp` 2.x bedient zwei Aeren ueber
  denselben Server — den `initialize`-Handshake, der bei `2025-11-25`
  deckelt, und den Pro-Request-Envelope, der `2026-07-28` erreicht.
  `LATEST_PROTOCOL_VERSION` ist ein Alias auf die **moderne** Aera; wer nur
  dagegen pinnt, laesst genau die Aera frei wandern, die heutige Clients
  aushandeln. Beide sind jetzt einzeln gepinnt, ein Dependabot-Bump von
  `mcp` kann keine davon still verschieben.

  Ohne gemessenen Teil: dieser Server baut keine ASGI-App, durch die sich ein
  `initialize` schicken liesse. Das Gate haengt deshalb an den SDK-Konstanten —
  die schwaechere Form, im Docstring benannt statt verschwiegen.

  Beide READMEs beschreiben die Aeren; ein Test haelt jede Sprache einzeln
  dagegen — im Portfolio sind EN und DE desselben Repos schon dreimal
  auseinandergelaufen, weil nur eine Fassung nachgezogen wurde.

### Behoben — drei von zehn Werkzeugen waren dauerhaft kaputt

Kein einziger Payload dieser Suite war je von der Quelle geholt worden. Mit
**null** Inline-Payloads stand dieser Server auf Platz 41 von 42 der
Portfolio-Rangfolge — und die Zahl misst Exposition, nicht Risiko.

Beim ersten Vergleich mit `data.sbb.ch` am 2026-08-08 antworteten drei der zehn
Werkzeuge auf jede Anfrage mit einem Fehler:

**1. Die Haltestellensuche wählte sieben Feldnamen, die es nicht gibt.**
`sbb_search_stations` fragte den DiDok-Datensatz nach `bezeichnung_offiziell`,
`uic`, `kanton_kuerzel`, `dst_nr`, `tu_nummer`, `geopos_ost` und `geopos_nord`.
Der Datensatz führt ausschliesslich **englische** Feldnamen —
`designationofficial`, `number`, `cantonabbreviation` und so fort. **Keiner der
sieben existiert.** Die Explore-API beantwortet ein unbekanntes Feld im
`select` mit **HTTP 400**, nicht mit weniger Spalten; jede Haltestellensuche
scheiterte also mit «API-Anfrage fehlgeschlagen».

**2. Die Katalogliste sortierte nach einem Feld, das der Endpunkt nicht kennt.**
`sbb_list_datasets` schickte `order_by=metas.default.title`. Der
Katalog-Endpunkt kennt `title`, aber kein `metas.default.title` —
`ODSQLError: Unknown field`. Damit hat das Werkzeug, mit dem man herausfindet,
welche Datensätze es überhaupt gibt, nie funktioniert. Es sind 61.

**3. Ein Werkzeug fragte einen Datensatz, den es nicht mehr gibt.**
`sbb_get_infrastructure_construction_projects` griff auf `construction-projects`
zu — HTTP 404, und der Katalog führt auch keinen Nachfolger. Das Werkzeug ist
entfernt statt mit einer schöneren Fehlermeldung versehen: Eine Fähigkeit
anzubieten, die es nicht gibt, ist derselbe Fehler wie ein leeres Ergebnis, nur
lauter. Die unbenutzte Konstante `DATASET_ELEVATORS` (`aufzugsstammdaten`, seit
längerem ebenfalls 404) fällt mit weg.

Die verbleibenden **neun** Werkzeuge laufen alle; nachgeprüft, indem jedes
einzeln gegen die Quelle gefahren wurde.

**Nebenbefund:** Die DiDok-Liste schreibt «unbefristet gültig» als `9999-12-31`
— gemessen bei 59'515 von 59'530 Einträgen. Das ist derselbe Füllwert, der in
`swiss-democracy-mcp` als Parteiparole hinausging. Die Haltestellentabelle
zeigt jetzt «unbefristet» statt eines Datums, das keines ist; ein echtes
Ablaufdatum (15 Einträge) bleibt sichtbar.

### Hinzugefuegt — der Vertrag wird aufgezeichnet, nicht nur die Antwort

**`scripts/record_fixtures.py`** holt sechs Antworten von `data.sbb.ch` und
schreibt `tests/fixtures/PROVENANCE.md` mit Quelle, **Aufzeichnungsdatum**,
Auswahlregel und SHA-256 je Datei.

Eine davon ist kein Datenauszug: **`dataset_fields.json`** hält fest, welche
Felder die Quelle je Datensatz deklariert (`fields[].name` unter
`/datasets/<id>`). Genau daran hing der Befund — ein unbekanntes Feld ist hier
kein fehlender Wert, sondern ein Ausfall der ganzen Anfrage. `TestFieldContract`
hält jeden Feldnamen und jeden Sortierschlüssel des Servers gegen diese
Deklaration. Die Namen stehen dafür neu als benannte Konstanten
(`FIELDS_STATIONS`, `ORDER_BY_CATALOG`, …) statt als Literale in den Werkzeugen:
Ein Test kann nur prüfen, was er benennen kann.

**Auswahl nach Merkmal, nicht nach Position.** Die Haltestellen-Fixture ist die
Anfrage des Servers selbst, mit seiner eigenen Feldliste — nur so belegt sie,
dass die Namen stimmen. Die zweite Haltestellen-Fixture enthält Einträge mit
echtem Ablaufdatum; «die ersten N» hätten von 59'530 Zeilen keine der 15
getroffen, um die es geht. Das Skript bricht ab, wenn der Zuschnitt nur einen
Betreiber trifft, wenn er auf eine Seite passt, wenn kein abgelaufener Eintrag
mehr existiert oder wenn der Katalog einen benutzten Datensatz nicht mehr führt.

**`tests/fixture_data.py`** behandelt einen fehlenden Namen als Fehler statt als
leere Struktur.

**Gegenprobe geführt:** Mit zurückgedrehten Feldnamen fallen die beiden neuen
Vertragszusicherungen.

### Behoben — die Live-Suite hing von der Testreihenfolge ab

Der Server hält einen prozessweiten httpx-Client; `pytest-asyncio` gibt jedem
Test einen eigenen Event-Loop. Ein Client, der auf einem inzwischen
geschlossenen Loop entstanden war, meldete beim nächsten Zugriff
`RuntimeError: Event loop is closed` — je nach Reihenfolge fiel derselbe Test
mal und mal nicht. Ein Testlauf, dessen Ausgang von der Reihenfolge abhängt,
wird nach dem zweiten Fehlalarm nicht mehr gelesen. Neu setzt eine
`autouse`-Fixture den Client je Test zurück.

**Und der eigentliche Punkt dazu:** Für zwei der drei kaputten Werkzeuge *gab*
es Live-Tests — `test_live_search_waedenswil` und `test_live_list_datasets`.
Sie hätten die Befunde gefunden. Die CI fährt aber nur `-m "not live"`, und
einen Live-Job gibt es nicht. **Die Abdeckung war da, der Lauf nicht.**

## [0.3.4] — 2026-07-31

### Geaendert

- **Der User-Agent traegt jetzt eine Version.** Bisher sendete der Server
  schlicht `sbb-opendata-mcp` — erkennbar, aber ohne Angabe, welcher Stand da
  anfragt. Damit liess sich ein Problem keiner Release zuordnen. Neu
  traegt den HTTP-Client `sbb-opendata-mcp/<version> (+github.com/malkreide/sbb-opendata-mcp)`.

  Die Version stammt aus `importlib.metadata` und kann nicht getrennt vom
  Paket driften.

### Fixed

- **Der Container band Loopback und war von aussen nicht erreichbar.** Das
  Dockerfile setzt `MCP_HOST=0.0.0.0` und exponiert 8000, aber der Code las
  `MCP_HOST` nicht mehr: die Migration auf mcp 2.x entfernte
  `host=os.environ.get("MCP_HOST", "127.0.0.1")` aus dem Konstruktor und ersetzte
  es durch ein hart verdrahtetes `bind_host = "127.0.0.1"`. Der publizierte Port
  erreichte damit nichts. `MCP_HOST` wird wieder gelesen, zusätzlich `MCP_PORT`
  und ein `--host`-Flag analog zum bestehenden `--port`.

- **Die Host/Origin-Allow-List war toter Code — und von zwei Tests gedeckt
  (SEC-005).** Dieselbe Migration entfernte
  `transport_security=_transport_security()` aus dem Konstruktor, ohne es als
  `run()`-Kwarg wieder anzuhängen. `_transport_security()` blieb stehen, seine
  Unit-Tests blieben grün, und der Server prüfte den Host-Header nie. Testdeckung
  für einen nicht verdrahteten Schutz ist schlechter als keine, weil sie als
  Zusicherung gelesen wird.

  Die Allow-List reist jetzt in `run()`. Der Builder liefert bewusst `None`,
  wenn keine Allow-List ableitbar ist — Nicht-Loopback-Bind ohne
  `MCP_ALLOWED_HOSTS` —, weil der Loopback-Default dort jede echte Anfrage mit
  HTTP 421 abweisen würde; der Aufrufer warnt stattdessen. Bestehende
  Deployments verhalten sich damit unverändert.

- **Der Einstiegspunkt liegt jetzt in `main()`.** Er stand inline im
  `__main__`-Block, weshalb kein Test die Transport-Verdrahtung sehen konnte —
  genau das liess die beiden Regressionen oben durchrutschen. Neue Tests prüfen
  die `run()`-Aufrufe selbst statt nur die Bauteile: dass `host`, `port` und
  `transport_security` ankommen, dass stdio keine davon bekommt, und dass
  `--host` die Umgebung überschreibt. Ein weiterer Test nagelt das Paar
  „Dockerfile setzt `MCP_HOST`" / „Code liest es" zusammen fest.

  Nachgemessen an der echten ASGI-App in drei Szenarien: Container ohne
  Allow-List lässt alles durch und warnt; Container mit `MCP_ALLOWED_HOSTS`
  liefert 200 für den richtigen Hostnamen, 421 für `evil.example.com` **und 421
  für den richtigen Hostnamen auf falschem Port** — nur der letzte Fall
  unterscheidet eine portgenaue Allow-List von einer, die alles erlaubt.

## [0.3.0] — 2026-06-05

Dokumentation und Repository-Struktur an die Konventionen des
[Swiss Public Data MCP Portfolios](https://github.com/malkreide/swiss-public-data-mcp)
(Referenz: [swiss-transport-mcp](https://github.com/malkreide/swiss-transport-mcp))
angeglichen. Keine Code- oder Verhaltensänderung am Server – die 60 Tests bleiben grün.

### Added
- **CI:** `.github/workflows/ci.yml` (GitHub Actions, Test + Lint über Python 3.11/3.12/3.13).
- **Docker:** Multi-Stage, Non-Root `Dockerfile`, `docker-compose.yml` mit Ressourcenlimits
  (`read_only`, `no-new-privileges`, Memory-/CPU-/PID-Limits) und `.dockerignore`.
- **Dokumentation:** `CONTRIBUTING.md` / `CONTRIBUTING.de.md`, `SECURITY.md` / `SECURITY.de.md`,
  `EXAMPLES.md` (Anwendungsfälle nach Zielgruppe) und ein `docs/assets/demo.svg`.
- **Audit:** `audits/RISK-ACCEPTANCES.md` (Risk Acceptance Register für die auf
  Portfolio-/Gateway-Ebene akzeptierten Kontrollen).

### Changed
- **README:** `README.md` / `README.de.md` auf die Portfolio-Struktur umgestellt
  (Portfolio-Header, CI-Badge, Overview, Features, Prerequisites, Quickstart,
  Configuration, Available Tools, Architecture, Project Structure, Safety & Limits,
  Known Limitations, Testing, Author, Credits & Related Projects).
- **Versionsangleich:** `pyproject.toml` und `__init__.py` auf `0.3.0` gehoben
  (zuvor inkonsistent: `0.2.0` / `0.1.0`).

## [0.2.0] — 2026-06-05

Vollständige Remediation des MCP-Audits ([mcp-audit-skill](https://github.com/malkreide/mcp-audit-skill)):
alle 10 Findings (2 High · 4 Medium · 4 Low) behoben, über die PRs #2–#7. Testsuite
von 34 auf 60 Tests gewachsen, `ruff` sauber, reproduzierbarer `uv.lock`.

### Added
- **F-SDK-01:** Alle Tools liefern jetzt MCP-`structuredContent` (die zugrunde
  liegenden Datensätze/Metadaten) zusätzlich zum menschenlesbaren Markdown-Text.
  Additiv und nicht-breaking: der Text-Content bleibt unverändert, programmatische
  Clients erhalten die Daten ohne erneutes Parsen. Tools geben dazu ein
  `CallToolResult` mit `structured_output=False` zurück.

### Fixed
- **F-SEC-05:** Robuste Zahlenkonvertierung (`_to_number`) verhindert, dass eine
  numerische Zeichenkette aus der API (z.B. `"1200"`) beim `{:,}`-Formatieren der
  Nutzfläche einen `ValueError` auslöst und einen gültigen Datensatz als „Fehler"
  erscheinen lässt.

### Changed
- **F-ARCH-01:** `sbb_compare_stations` unterstützt jetzt `response_format`
  (`markdown`/`json`) wie die übrigen Tools.
- **F-OPS-01:** `[project.optional-dependencies] dev` ergänzt, sodass
  `pip install -e ".[dev]"` (wie im README) funktioniert; pytest-Marker `live`
  in `pyproject.toml` registriert (keine `PytestUnknownMarkWarning` mehr).
  `uv.lock` entsprechend aktualisiert.

### Security (Error handling & dependencies)
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

### Security (Transport & Injection)
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
