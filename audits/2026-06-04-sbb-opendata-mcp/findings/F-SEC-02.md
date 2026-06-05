## Finding: F-SEC-02 — Streamable HTTP transport without auth / origin validation / rate limiting

**Severity:** high (cloud deployment only)
**Status:** closed (PR #2, 2026-06-05)
**Server:** sbb-opendata-mcp
**Check-Reference:** SEC / SCALE (transport & gateway)
**PDF-Reference:** Sec — Defense-in-Depth (gateway layer)

### Observed Behavior
The HTTP mode starts `mcp.run(transport="streamable_http", port=port)` with no protective
configuration (`server.py:1067-1068`):
- **No authentication** — anyone who can reach the endpoint can invoke all tools.
- **No Origin/Host header validation** → DNS-rebinding risk (MCP spec recommendation for
  Streamable HTTP).
- **No rate limiting** → the server acts as an open proxy that can hammer `data.sbb.ch`.

### Expected Behavior
Defense-in-depth gateway layer: rate limiting, Origin/Host allowlist, and (for non-public
exposure) authentication.

### Evidence
- `src/sbb_opendata_mcp/server.py:1058-1070`
- `src/sbb_opendata_mcp/server.py:42-50` (instructions: "no authentication required")

### Risk Description
Data is public/read-only, so no data leak — but open-proxy abuse, upstream cost/reputation
impact, and DNS-rebinding against a locally bound instance.

### Remediation
- Put a reverse proxy with rate limiting in front (e.g. on Render) and/or an
  `Authorization` bearer gate.
- Validate Origin/Host against an allowlist; bind `127.0.0.1` locally, `0.0.0.0` only behind
  a proxy.
- Add application-side rate limiting or upstream response caching.

### Effort Estimate
M (1–3 days)
