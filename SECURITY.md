# Security Policy & Posture

[🇩🇪 Deutsche Version](SECURITY.de.md)

`sbb-opendata-mcp` was hardened against the internal MCP best-practice audit
catalogue ([mcp-audit-skill](https://github.com/malkreide/mcp-audit-skill)). All
10 findings (2 high · 4 medium · 4 low) were remediated — see
[`audits/`](audits/) for the full report and [`CHANGELOG.md`](CHANGELOG.md) for
the hardening history.

## Reporting a vulnerability

Please open a private security advisory on the GitHub repository, or contact the
maintainer listed in `README.md`. Do not file public issues for exploitable
vulnerabilities.

## Posture summary

This is a **read-only**, **no-PII**, **public-open-data** MCP server with **no
authentication and no API key**. All 10 tools only query the SBB Open Data portal
(`data.sbb.ch`). Hardening already in place:

| Area | Control |
|---|---|
| Egress | All requests target the hardcoded `data.sbb.ch` base URL (OpenDataSoft v2.1); no user-controllable host (F-SEC-01) |
| Injection | `year`/`canton` validated by regex; every string interpolated into an ODSQL `where` clause is escaped via a central `_odsql_quote()` (F-SEC-01) |
| Binding | The Streamable HTTP transport defaults to `127.0.0.1` (F-SEC-02) |
| Transport | DNS-rebinding / Origin protection always on; host & origin allow-lists via `MCP_ALLOWED_HOSTS` / `MCP_ALLOWED_ORIGINS` (F-SEC-02) |
| Input | Pydantic v2 strict validation (`extra="forbid"`, bounds, `min/max_length`) on every tool input |
| Secrets | None required — no API key; `.gitignore` guards `.env`, no hardcoded secrets |
| Dependencies | `mcp`/`httpx`/`pydantic` capped to their current majors + committed `uv.lock` (F-SEC-04) |
| Errors | Upstream bodies & exception strings logged to stderr, never forwarded to the model (F-SEC-03) |
| Stdout | Reserved for the JSON-RPC stream; logging pinned to stderr (F-OBS-01) |
| Tool integrity | Tool definitions are version-controlled and shipped from this repo; no dynamic / remote tool registration |

See [`audits/`](audits/) for the full report and `CHANGELOG.md` for the
hardening history.

## Running the HTTP transport safely (no built-in auth)

The server has **no authentication of its own**. When you run the Streamable
HTTP transport (`--http`), DNS-rebinding / Origin protection is enabled, but no
user identity is bound to a session. Therefore:

- **Do not expose a no-auth instance directly to the public internet.** Put it
  behind an authenticating reverse proxy (OAuth2 proxy, mTLS, or your platform's
  access control) that also enforces rate limiting, or restrict it to a trusted
  network.
- Keep the default `MCP_HOST=127.0.0.1` for local use; only bind `0.0.0.0`
  inside a controlled container/cloud environment (see Deployment in `README.md`).
- Scope `MCP_ALLOWED_HOSTS` / `MCP_ALLOWED_ORIGINS` to the hosts/origins you
  actually trust before going public.

## Accepted risks (portfolio-level controls)

A small number of audit concerns are **not** implemented inside this server by
design. They are portfolio-wide concerns best enforced at an MCP gateway / host
layer, and the residual risk here is low because the server is read-only and only
reaches a single trusted public-data provider. These are recorded in the
[Risk Acceptance Register](audits/RISK-ACCEPTANCES.md):

- **Tool allow-listing** belongs to the MCP host/gateway that aggregates multiple
  servers, not to a single server exposing a fixed, read-only tool set.
- **Cross-server tool-poisoning detection** is a supply-chain / host concern; this
  server registers no tools dynamically or from remote sources.

## Re-evaluation triggers

These acceptances should be revisited if the server ever:

- gains **write** capability or starts processing **PII**, or
- registers tools **dynamically** / from remote sources, or
- is aggregated behind a shared MCP gateway (then implement the controls there).
