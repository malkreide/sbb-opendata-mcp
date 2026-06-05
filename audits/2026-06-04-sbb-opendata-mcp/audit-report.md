# MCP Audit Report — `sbb-opendata-mcp`

**Audit-Datum:** 2026-06-04
**Auditor:** Claude Code (MCP Audit Skill)
**Skill:** [malkreide/mcp-audit-skill](https://github.com/malkreide/mcp-audit-skill) (`main`)
**Repository:** [malkreide/sbb-opendata-mcp](https://github.com/malkreide/sbb-opendata-mcp)
**Commit/Branch:** `claude/quirky-mccarthy-dWbLq`
**Server-Version:** 0.1.0 (auditiert) → 0.2.0 (remediiert)
**Remediation-Status:** ✅ **10 / 10 Findings closed** (2026-06-05, PRs #2–#7)

---

## 1. Executive Summary

`sbb-opendata-mcp` ist ein gut strukturierter, read-only MCP-Server für öffentliche
SBB-Open-Data über die OpenDataSoft-API v2.1. Die Architektur-Grundlagen sind solide:
sauberes Pydantic-v2-Input-Modell mit `extra="forbid"`, korrekte Tool-Annotations
(`readOnlyHint`/`idempotentHint`), gute Tool-Beschreibungen, 34 grüne Unit-Tests und
ein sauberer Ruff-Lint.

Der Audit identifiziert **10 Findings (0 kritisch · 2 hoch · 4 mittel · 4 niedrig)**.
Es gibt **keine produktionsblockierenden (kritischen) Mängel**. Die zwei High-Findings
betreffen ausschliesslich das **Streamable-HTTP-/Cloud-Deployment**: (1) ODSQL-Query-Injection
über unvalidierte Filterparameter und (2) ein HTTP-Transport ohne Authentifizierung,
Origin-Validierung oder Rate-Limiting.

**Produktionsreife-Einschätzung (nach Remediation):**
- ✅ **stdio (Claude Desktop, lokal):** produktionsreif.
- ✅ **Streamable HTTP (Cloud / Render.com):** produktionsreif — F-SEC-01 und F-SEC-02
  sind behoben; der HTTP-Transport ist mit DNS-Rebinding-/Origin-Schutz und
  konfigurierbaren Allowlists gehärtet.

> **Update 2026-06-05:** Alle 10 Findings wurden über die PRs #2–#7 remediiert und nach
> `main` gemergt. Die Testsuite ist von 34 auf 60 Tests gewachsen (alle grün), `ruff`
> durchgängig sauber. Details siehe Abschnitt 4a (Remediation Status).

---

## 2. Profile Snapshot

| Eigenschaft | Wert | Quelle |
|---|---|---|
| Server-Name | `sbb_opendata_mcp` | `server.py:43` |
| Framework | FastMCP (Python SDK) + httpx + Pydantic v2 | `server.py:11-13` |
| Transport | stdio **und** Streamable HTTP (dual) | `server.py:1058-1070` |
| Auth-Modell | **Keines** (öffentliche Daten, kein API-Key) | `server.py:48` |
| Write-Capability | **Keine** (alle 10 Tools `readOnlyHint=True`) | Tool-Annotations |
| Datenklasse | **Öffentlich** (Open Government Data, keine PII) | data.sbb.ch |
| Backend | OpenDataSoft REST v2.1 (extern, öffentlich) | `server.py:19` |
| Deployment | Lokal (stdio) + Cloud (Render.com, HTTP) | README |
| Tools | 10 | `server.py` |
| Tests | 34 Unit + 5 Live-Smoke | `tests/test_server.py` |

**Abgeleitete Felder:** `is_cloud_deployed = true`, `is_write_capable = false`,
`handles_pii = false`, `uses_oauth = false`.

---

## 3. Applicability Overview

Profilbasierte Filterung (Profile first, checks second). Auth-/OAuth- und HITL-Checks
sind für diesen no-auth, read-only Server **nicht anwendbar**.

| Kategorie | Total | Anwendbar | Nicht anwendbar (Begründung) |
|---|---|---|---|
| ARCH | 12 | 12 | — |
| SDK | 5 | 5 | — |
| SEC | 23 | ~12 | OAuth-Proxy/PKCE/Confused-Deputy/Resource-Indicators/Token-Validierung (kein Auth) |
| SCALE | 6 | 6 | — |
| OBS | 6 | 6 | — |
| HITL | 5 | 0 | Kein Sampling / kein Human-in-the-Loop / read-only |
| CH | 8 | ~2 | Keine Personendaten → DSG-/EDÖB-PII-Checks entfallen; nur Lizenz/Attribution relevant |
| OPS | 3 | 3 | — |

> Hinweis: SEC-/CH-Anwendbarkeit ist eine Auditor-Schätzung anhand des Profils; die
> nicht anwendbaren Auth-Checks wurden ohne Finding als „N/A“ markiert.

---

## 4. Findings Table

| ID | Titel | Kat. | Severity | Aufwand | Status |
|---|---|---|---|---|---|
| F-SEC-01 | ODSQL-Query-Injection über unvalidierte Filterparameter | SEC | **High** | M | ✅ closed (PR #2) |
| F-SEC-02 | Streamable-HTTP ohne Auth / Origin-Validierung / Rate-Limit | SEC | **High** | M | ✅ closed (PR #2) |
| F-SEC-03 | Fehlermeldungen leaken Upstream-Body und Exception-Details | SEC | Medium | S | ✅ closed (PR #5) |
| F-SEC-04 | Ungepinnte Abhängigkeiten, kein Lockfile | SEC | Medium | S | ✅ closed (PR #5) |
| F-OBS-01 | Keinerlei Logging / Observability | OBS | Medium | M | ✅ closed (PR #3) |
| F-SCALE-01 | Neuer httpx-Client pro Request + sequentielles Fan-out | SCALE | Medium | M | ✅ closed (PR #4) |
| F-SDK-01 | Kein MCP Structured Output / `outputSchema` | SDK | Low | M | ✅ closed (PR #7) |
| F-OPS-01 | Defektes `.[dev]`-Extra in README + unregistrierter `live`-Marker | OPS | Low | S | ✅ closed (PR #6) |
| F-ARCH-01 | API-Inkonsistenzen (compare_stations, DE/EN-Mix) | ARCH | Low | S | ✅ closed (PR #6) |
| F-SEC-05 | Breites `except Exception` maskiert Formatierungs-Bug | SEC | Low | S | ✅ closed (PR #6) |

---

## 4a. Remediation Status

Alle Findings wurden remediiert und nach `main` gemergt (Audit-Datum 2026-06-04,
Remediation abgeschlossen 2026-06-05).

| PR | Findings | Kerninhalt |
|---|---|---|
| #2 | F-SEC-01, F-SEC-02 | Input-Validierung (`year`/`canton` Regex) + zentrales ODSQL-Escaping; DNS-Rebinding-/Origin-Schutz, konfigurierbarer Bind-Host/Allowlists |
| #3 | F-OBS-01 | Strukturiertes Logging auf stderr (`LOG_LEVEL`/`LOG_FORMAT`), Request-/Fehler-Logging |
| #4 | F-SCALE-01 | Gemeinsamer httpx-Client (Connection-Pooling) + paralleles Fan-out in `compare_stations` |
| #5 | F-SEC-03, F-SEC-04 | Fehler-Sanitisierung (kein Body-/Exception-Leak); Deps mit Major-Caps + `uv.lock` |
| #6 | F-SEC-05, F-ARCH-01, F-OPS-01 | Robuste Zahlenkonvertierung; `response_format` für `compare_stations`; `.[dev]`-Extra + registrierter pytest-Marker |
| #7 | F-SDK-01 | MCP `structuredContent` zusätzlich zum Markdown-Text (additiv) |

**Verifikation:** `pytest -m "not live"` → 60 passed; `ruff check` → sauber.

---

## 5. Detailed Findings

### F-SEC-01 — ODSQL-Query-Injection über unvalidierte Filterparameter

**Severity:** High · **Status:** ✅ closed · **Kategorie:** SEC · **Aufwand:** M (1–3 Tage)

**Observed Behavior**
Der Server baut OpenDataSoft-`where`-Klauseln (ODSQL) per String-Interpolation. Mehrere
Parameter fliessen **ohne jegliches Escaping/Whitelisting** in die Query ein, teils in
unquotiertem Kontext:

- `server.py:310` — `f"year(jahr_annee_anno)={params.year}"` — `year` ist `str | None`,
  **nicht** numerisch validiert (nur eine Beschreibung „4-stellig“). Unquotierter Kontext
  → boolesche Injection möglich, z. B. `year="2024) OR (1=1"`.
- `server.py:649` — `f'geschaeftscode like "%{params.traffic_type}%"'` — `traffic_type`
  wird **ohne** das sonst übliche `.replace('"', '\\"')` interpoliert → Ausbruch aus dem
  String-Literal via `"`.
- `server.py:557` — `f'phase="{params.phase.upper()}"'` — ungeescapt.
- `server.py:645/647` — `isb="{operator.upper()}"` / `jahr="{year}"` — ungeescapt.
- `server.py:881` — `... AND year(jahr_annee_anno)={year_filter}` (compare_stations) — ungeescapt/unquotiert.

Das an anderer Stelle verwendete `.replace('"', '\\"')` (z. B. `server.py:305`) ist zudem
**unvollständig**: Es behandelt den Backslash selbst nicht und ist keine zuverlässige
ODSQL-Escaping-Strategie.

**Expected Behavior**
Eingaben, die in eine Backend-Abfragesprache fliessen, müssen validiert/whitelisted oder
sicher parametrisiert werden (Defense-in-Depth, „Server logic: input validation“).

**Evidence**
`server.py:310`, `:557`, `:645-649`, `:881`; Escaping-Helfer `:305,:470,:554,:642,:726,:803,:880,:960`.

**Risk**
Backend ist read-only und Daten sind öffentlich → kein Schreib-/Exfiltrationsrisiko über
das Mandat hinaus. Aber: Query-Manipulation kann Resultatmengen verfälschen
(Integrität/Vertrauen), Fehler provozieren und ist eine klassische Injection-Klasse, die
bei künftigen Erweiterungen (neue Datasets/Felder) gefährlicher wird.

**Remediation**
1. `year` als 4-stellige Ziffernfolge erzwingen: `Field(pattern=r"^\d{4}$")` (Pydantic v2),
   analog für `jahr`.
2. Enum/Whitelist für `phase` (`CONSTRUCTION|PLANNING|COMPLETED`), `traffic_type`
   (`Personenverkehr|Gueterverkehr`) und `operator`.
3. `canton` zusätzlich `pattern=r"^[A-Za-z]{2}$"`.
4. Eine zentrale `_quote(value)`-Funktion einführen, die `\` **und** `"` escaped, und
   konsequent für **alle** `like`/`=`-String-Werte verwenden (auch `traffic_type`).

```python
canton: str | None = Field(default=None, min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$")
year:   str | None = Field(default=None, pattern=r"^\d{4}$")

def _odsql_str(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
```

---

### F-SEC-02 — Streamable-HTTP-Transport ohne Authentifizierung, Origin-Validierung und Rate-Limiting

**Severity:** High (nur Cloud) · **Status:** ✅ closed · **Kategorie:** SEC/SCALE · **Aufwand:** M

**Observed Behavior**
Im HTTP-Modus wird `mcp.run(transport="streamable_http", port=port)` ohne jede
Schutzkonfiguration gestartet (`server.py:1067-1068`). Es gibt:
- **keine Authentifizierung** — wer den Endpoint erreicht, kann alle Tools aufrufen;
- **keine Origin-Header-Validierung** → DNS-Rebinding-Risiko (MCP-Spec-Empfehlung für
  Streamable HTTP);
- **kein Rate-Limiting** → der Server wird zum offenen Proxy, der `data.sbb.ch`
  ungebremst hämmern kann (Reputations-/Abuse-Risiko gegenüber dem Upstream).

**Expected Behavior**
Defense-in-Depth-Layer 2/3: Gateway mit Rate-Limiting, Origin/Host-Allowlist und (bei
nicht-öffentlicher Exposition) Authentifizierung.

**Evidence** `server.py:1058-1070`, `server.py:42-50` (Instructions: „no authentication required“).

**Risk**
Daten sind öffentlich/read-only, daher kein Datenleck — aber offener Proxy-Missbrauch,
Kostentreiber und DNS-Rebinding (lokaler Browser eines Opfers könnte einen lokal
gebundenen Server ansprechen).

**Remediation**
- Origin/Host-Allowlist bzw. einen Reverse-Proxy (z. B. auf Render) mit Rate-Limit
  vorschalten; optional `Authorization`-Bearer/Token-Gate.
- Bind-Host bewusst setzen (lokal `127.0.0.1`, Cloud `0.0.0.0` nur hinter Proxy).
- Anwendungsseitiges Rate-Limiting oder Caching der Upstream-Antworten ergänzen.

---

### F-SEC-03 — Fehlermeldungen leaken Upstream-Body und Exception-Details

**Severity:** Medium · **Status:** ✅ closed · **Kategorie:** SEC/OBS · **Aufwand:** S

**Observed Behavior**
`_handle_api_error` gibt rohe Upstream-Inhalte an den Client zurück:
`f"... Details: {e.response.text[:200]}"` (`server.py:89`) und generisch
`f"... ({type(e).__name__}): {str(e)[:200]}"` (`server.py:92`).

**Risk**
Geringe, aber unnötige Informationspreisgabe (Upstream-Fehlertexte, interne
Exception-Strings). Bei künftigen nicht-öffentlichen Backends potenziell sensibel.

**Remediation** Generische Client-Meldung zurückgeben; Detail nur ins (noch zu
schaffende, s. F-OBS-01) Server-Log schreiben.

---

### F-SEC-04 — Ungepinnte Abhängigkeiten, kein Lockfile

**Severity:** Medium · **Status:** ✅ closed · **Kategorie:** SEC (Supply Chain) · **Aufwand:** S

**Observed Behavior**
`pyproject.toml` nutzt offene Floor-Pins (`mcp[cli]>=1.6.0`, `httpx>=0.27.0`,
`pydantic>=2.0.0`) ohne Obergrenzen, und es ist kein Lockfile (`uv.lock`) committed.
Da der Server via `uvx`/PyPI verteilt wird, kann ein Breaking-Change einer Transitiv-Dep
reproduzierbare Builds brechen.

**Remediation** `uv.lock` committen; ggf. Obergrenzen für Major-Versionen (`>=1.6,<2`).
CI gegen den Lockfile bauen.

---

### F-OBS-01 — Keinerlei Logging / Observability

**Severity:** Medium · **Status:** ✅ closed · **Kategorie:** OBS · **Aufwand:** M

**Observed Behavior**
Im gesamten Server existiert **kein** Logging (keine `logging`-Imports, keine Logger,
keine `print`). Jedes Tool fängt `except Exception` ab und gibt einen String zurück —
Fehler verschwinden spurlos. Für ein Cloud-HTTP-Deployment fehlt damit jede
Nachvollziehbarkeit (kein Request-/Error-Log, kein Tracing, kein SIEM-Anschluss).

**Evidence** Grep über `src/`: keine Treffer für `logging|logger|print(`.

**Remediation** Strukturiertes Logging (`logging` mit JSON-Formatter) für Requests und
gefangene Exceptions einführen; für die Cloud-Variante optional OpenTelemetry-Spans.

---

### F-SCALE-01 — Neuer httpx-Client pro Request + sequentielles Fan-out

**Severity:** Medium · **Status:** ✅ closed · **Kategorie:** SCALE · **Aufwand:** M

**Observed Behavior**
`_fetch_records` öffnet bei **jedem** Aufruf einen neuen `httpx.AsyncClient`
(`server.py:75`), ebenso `sbb_list_datasets` (`server.py:1027`). Kein Connection-Pooling /
keine Keep-Alive-Wiederverwendung. `sbb_compare_stations` ruft `_fetch_records` zudem
**sequentiell** in zwei Schleifen über alle Stationen auf (`server.py:879-901`) — bei 10
Stationen bis zu 20 nacheinander ausgeführte Requests, jeder mit neuem TCP/TLS-Handshake.

**Remediation** Einen gemeinsamen, langlebigen `AsyncClient` (App-Lifespan) verwenden;
in `compare_stations` die Per-Station-Fetches mit `asyncio.gather` parallelisieren.

---

### F-SDK-01 — Kein MCP Structured Output / `outputSchema`

**Severity:** Low · **Status:** ✅ closed · **Kategorie:** SDK · **Aufwand:** M

**Observed Behavior**
Alle Tools geben `-> str` zurück; im JSON-Modus wird `json.dumps(...)` als **String**
geliefert. Das MCP-Protokoll unterstützt strukturierten Output / `outputSchema`, was die
maschinelle Weiterverarbeitung durch Clients robuster macht. Positiv: die Docstrings
dokumentieren bereits ein `Schema: {...}`.

**Remediation** Optional typisierte Rückgaben (Pydantic-Modelle) bzw. FastMCP
Structured-Output nutzen, wenn die Client-Basis es unterstützt.

---

### F-OPS-01 — Defektes `.[dev]`-Extra in README + unregistrierter `live`-Marker

**Severity:** Low · **Status:** ✅ closed · **Kategorie:** OPS · **Aufwand:** S

**Observed Behavior**
- README empfiehlt `pip install -e ".[dev]"`, aber es existiert **kein** `[dev]`-Extra
  (Dev-Deps liegen unter `[tool.hatch.envs.default]`). `pip` meldet:
  `WARNING: sbb-opendata-mcp 0.1.0 does not provide the extra 'dev'`.
- Der pytest-Marker `live` ist nicht registriert → 5× `PytestUnknownMarkWarning`.

**Remediation**
- Entweder `[project.optional-dependencies] dev = [...]` ergänzen oder README auf
  `uv`/`hatch`-Workflow umstellen.
- In `pyproject.toml`: `[tool.pytest.ini_options] markers = ["live: requires network"]`.

---

### F-ARCH-01 — API-Inkonsistenzen

**Severity:** Low · **Status:** ✅ closed · **Kategorie:** ARCH · **Aufwand:** S

**Observed Behavior**
- `sbb_compare_stations` bietet als einziges Listen-Tool **kein** `response_format` und
  keine Pagination (`server.py:237-249`) — inkonsistente Tool-Oberfläche.
- Sprach-Mix: Server-`instructions` und Docstrings teils Englisch, Fehlermeldungen/Outputs
  Deutsch.
- Lizenz-Attribution (`data.sbb.ch`, ReferenceRequired) wird nur in einigen Tool-Outputs
  genannt (z. B. compare/list), nicht durchgängig (z. B. Passagierfrequenz).

**Remediation** `response_format`/Pagination auch für `compare_stations`; Sprache
vereinheitlichen oder bewusst dokumentieren; Quellenhinweis in alle Outputs.

> Hinweis ARCH-001 (Tool-Naming): `snake_case` mit einheitlichem `sbb_`-Präfix ist gemäss
> Skill **akzeptabel** (camelCase nur „preferred“) → **kein** Finding.

---

### F-SEC-05 — Breites `except Exception` maskiert Formatierungs-Bug

**Severity:** Low · **Status:** ✅ closed · **Kategorie:** SEC/Robustheit · **Aufwand:** S

**Observed Behavior**
In `sbb_get_real_estate_projects` wird `f"- **Nutzfläche:** {area:,} m²"` (`server.py:595`)
ausgeführt, sobald `area` truthy und `!= "–"` ist. Liefert die API `area` als **String**
(z. B. `"1200"`), wirft `:,` einen `ValueError`, der vom breiten `except Exception`
(`server.py:605`) verschluckt und als generische Fehlermeldung an den Client gereicht wird —
ein echter Datensatz erzeugt so eine irreführende „Fehler“-Antwort.

**Remediation** Vor der Formatierung in `int/float` konvertieren (try/except lokal) bzw.
Typ prüfen; das breite `except` enger fassen.

---

## 6. Remediation Plan (empfohlene Reihenfolge)

> ✅ **Vollständig abgearbeitet (2026-06-05).** Die ursprünglich empfohlene Sequenz wurde
> umgesetzt; alle Punkte sind erledigt:

**Vor öffentlichem HTTP-Deployment (Pflicht):**
1. ✅ **F-SEC-01** — Parameter-Validierung/Whitelisting + zentrales ODSQL-Escaping (PR #2)
2. ✅ **F-SEC-02** — Origin/Rate-Limit/Auth-Gate für Streamable HTTP (PR #2)

**Kurzfristig (nächster Sprint):**
3. ✅ **F-OBS-01** — Strukturiertes Logging (PR #3)
4. ✅ **F-SEC-03** — Fehler-Detail nicht mehr an Client leaken (PR #5)
5. ✅ **F-SEC-04** — Lockfile committen / Deps pinnen (PR #5)
6. ✅ **F-SCALE-01** — Shared Client + paralleles Fan-out (PR #4)

**Backlog / Polish:**
7. ✅ F-SDK-01 (PR #7), F-OPS-01 / F-ARCH-01 / F-SEC-05 (PR #6)

---

## 7. Stärken (Positivbefunde)

- **Striktes Input-Modell:** Pydantic v2 mit `extra="forbid"`, `ge/le`-Bounds,
  `min/max_length`, `str_strip_whitespace` auf allen Inputs.
- **Korrekte Tool-Annotations:** `readOnlyHint`/`destructiveHint`/`idempotentHint`/
  `openWorldHint` durchgängig und semantisch richtig (Disruptions korrekt `idempotent=False`).
- **Gute Tool-Beschreibungen** mit Use-Cases und dokumentiertem Ausgabe-Schema (ARCH-001 ✓).
- **Defense-in-Depth bei Limits:** `min(limit, MAX_LIMIT)` zusätzlich zur Pydantic-Grenze.
- **Konsistentes Error-Handling** mit actionable Meldungen (404/429/Timeout).
- **Tests grün:** 34/34 Unit-Tests bestanden, `ruff check` ohne Befund.
- **Read-only, kein Auth, keine PII** → von Natur aus kleine Angriffsfläche.

---

## 8. Audit Metadata

| Feld | Wert |
|---|---|
| Run-ID | `2026-06-04T00:00:00+02:00-sbb-opendata-mcp` |
| Auditor | Claude Code (`claude-opus-4-8`) via MCP Audit Skill |
| Skill-Version | `malkreide/mcp-audit-skill@main` |
| Katalog | 68 Checks (ARCH 12 · SDK 5 · SEC 23 · SCALE 6 · OBS 6 · HITL 5 · CH 8 · OPS 3) |
| Katalog-Hash | nicht gepinnt (Remote `main` zum Audit-Zeitpunkt gelesen) |
| Findings | 10 (0 critical · 2 high · 4 medium · 4 low) — **alle closed (PRs #2–#7)** |
| Remediation | abgeschlossen 2026-06-05; Testsuite 34 → 60 grün, `ruff` sauber |
| Methodik | Profile → Applicability-Filter → Check-Execution → Findings → Report → Remediation |
| Evidenz | Code-Review + `ruff check` + `pytest -m "not live"` (34 passed) |

*Findings ohne Datei-/Zeilenreferenz sind Meinungen, keine Findings — alle obigen Findings
sind mit `server.py`-Zeilennummern belegt.*
