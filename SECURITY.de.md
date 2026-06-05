# Sicherheitsrichtlinie & Sicherheitslage

[🇬🇧 English Version](SECURITY.md)

`sbb-opendata-mcp` wurde gegen den internen MCP-Best-Practice-Audit-Katalog
([mcp-audit-skill](https://github.com/malkreide/mcp-audit-skill)) gehärtet. Alle
10 Findings (2 hoch · 4 mittel · 4 niedrig) wurden behoben – den vollständigen
Bericht finden Sie unter [`audits/`](audits/), die Härtungshistorie in
[`CHANGELOG.md`](CHANGELOG.md).

## Schwachstelle melden

Bitte eröffnen Sie ein privates Security Advisory im GitHub-Repository oder
kontaktieren Sie die in `README.md` genannte verantwortliche Person. Erstellen Sie
für ausnutzbare Schwachstellen **keine** öffentlichen Issues.

## Zusammenfassung der Sicherheitslage

Dies ist ein **rein lesender**, **PII-freier** MCP-Server für **öffentliche Open
Data** – **ohne Authentifizierung und ohne API-Key**. Alle 10 Tools fragen
ausschliesslich das SBB-Open-Data-Portal (`data.sbb.ch`) ab. Bereits umgesetzte
Härtungsmassnahmen:

| Bereich | Kontrolle |
|---|---|
| Egress | Alle Anfragen gehen an die fest verdrahtete `data.sbb.ch`-Basis-URL (OpenDataSoft v2.1); kein benutzergesteuerter Host (F-SEC-01) |
| Injection | `year`/`canton` per Regex validiert; jeder in eine ODSQL-`where`-Klausel interpolierte String wird über ein zentrales `_odsql_quote()` escaped (F-SEC-01) |
| Binding | Der Streamable-HTTP-Transport bindet standardmässig an `127.0.0.1` (F-SEC-02) |
| Transport | DNS-Rebinding-/Origin-Schutz immer aktiv; Host- & Origin-Allow-Lists über `MCP_ALLOWED_HOSTS` / `MCP_ALLOWED_ORIGINS` (F-SEC-02) |
| Input | Pydantic-v2-Strict-Validierung (`extra="forbid"`, Bounds, `min/max_length`) auf jedem Tool-Input |
| Secrets | Keine erforderlich – kein API-Key; `.gitignore` schützt `.env`, keine hartcodierten Secrets |
| Abhängigkeiten | `mcp`/`httpx`/`pydantic` auf aktuelle Major-Versionen begrenzt + committeter `uv.lock` (F-SEC-04) |
| Fehler | Upstream-Antworten & Exception-Strings werden nach stderr geloggt, niemals an das Modell weitergegeben (F-SEC-03) |
| Stdout | Reserviert für den JSON-RPC-Stream; Logging fest auf stderr (F-OBS-01) |
| Tool-Integrität | Tool-Definitionen sind versionskontrolliert und werden aus diesem Repo ausgeliefert; keine dynamische / entfernte Tool-Registrierung |

Den vollständigen Bericht finden Sie unter [`audits/`](audits/), die
Härtungshistorie in `CHANGELOG.md`.

## Den HTTP-Transport sicher betreiben (keine eingebaute Auth)

Der Server hat **keine eigene Authentifizierung**. Wenn Sie den Streamable-HTTP-
Transport (`--http`) betreiben, ist der DNS-Rebinding-/Origin-Schutz aktiv, aber
es ist keine Benutzeridentität an eine Session gebunden. Daher:

- **Exponieren Sie eine No-Auth-Instanz nicht direkt im öffentlichen Internet.**
  Stellen Sie einen authentifizierenden Reverse-Proxy (OAuth2-Proxy, mTLS oder die
  Zugriffskontrolle Ihrer Plattform) mit Rate-Limiting davor oder beschränken Sie
  ihn auf ein vertrauenswürdiges Netz.
- Behalten Sie für die lokale Nutzung `MCP_HOST=127.0.0.1`; binden Sie `0.0.0.0`
  nur in einer kontrollierten Container-/Cloud-Umgebung (siehe Deployment in
  `README.md`).
- Beschränken Sie `MCP_ALLOWED_HOSTS` / `MCP_ALLOWED_ORIGINS` auf die Hosts/Origins,
  denen Sie tatsächlich vertrauen, bevor Sie öffentlich gehen.

## Akzeptierte Risiken (Kontrollen auf Portfolio-Ebene)

Einige wenige Audit-Belange sind **bewusst nicht** innerhalb dieses Servers
implementiert. Es handelt sich um portfolioweite Belange, die am besten auf einer
MCP-Gateway-/Host-Ebene durchgesetzt werden; das Restrisiko ist hier gering, da der
Server rein lesend ist und nur einen einzigen vertrauenswürdigen Open-Data-Anbieter
erreicht. Diese sind im
[Risk Acceptance Register](audits/RISK-ACCEPTANCES.md) dokumentiert:

- **Tool-Allow-Listing** gehört zum MCP-Host/-Gateway, das mehrere Server
  aggregiert, nicht zu einem einzelnen Server mit festem, rein lesendem Tool-Set.
- **Serverübergreifende Tool-Poisoning-Erkennung** ist ein Lieferketten-/Host-
  Belang; dieser Server registriert keine Tools dynamisch oder aus entfernten Quellen.

## Re-Evaluierungs-Auslöser

Diese Akzeptanzen sollten neu bewertet werden, falls der Server jemals:

- **Schreib**-Funktionalität erhält oder beginnt, **PII** zu verarbeiten, oder
- Tools **dynamisch** / aus entfernten Quellen registriert, oder
- hinter einem gemeinsamen MCP-Gateway aggregiert wird (dann die Kontrollen dort umsetzen).
