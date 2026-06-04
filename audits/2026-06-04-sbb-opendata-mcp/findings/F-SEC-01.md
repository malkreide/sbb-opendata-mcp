## Finding: F-SEC-01 — ODSQL Query Injection via unvalidated filter parameters

**Severity:** high
**Status:** open
**Server:** sbb-opendata-mcp
**Check-Reference:** SEC (input validation / injection)
**PDF-Reference:** Sec — Server logic: input validation

### Observed Behavior
ODSQL `where` clauses are built by f-string interpolation. Several parameters reach the
query with **no escaping/whitelisting**, partly in unquoted context:

- `server.py:310` — `f"year(jahr_annee_anno)={params.year}"`; `year` is `str | None` and is
  **not** validated as numeric → boolean injection, e.g. `year="2024) OR (1=1"`.
- `server.py:649` — `f'geschaeftscode like "%{params.traffic_type}%"'`; `traffic_type` is
  interpolated **without** the `.replace('"', '\\"')` used elsewhere → string-literal breakout.
- `server.py:557` — `phase="{phase.upper()}"`; `server.py:645/647` — `isb=...`, `jahr=...`;
  `server.py:881` — `... year(jahr_annee_anno)={year_filter}` (compare_stations). All unescaped.

The `.replace('"', '\\"')` helper used on other fields is also incomplete (does not escape
the backslash itself).

### Expected Behavior
Inputs flowing into a backend query language must be validated/whitelisted or safely
escaped (defense-in-depth at the server-logic layer).

### Evidence
- `src/sbb_opendata_mcp/server.py:310`, `:557`, `:645-649`, `:881`
- Incomplete escaping: `:305, :470, :554, :642, :726, :803, :880, :960`

### Risk Description
Backend is read-only and data is public, so no write/exfiltration beyond mandate. But query
manipulation can falsify result sets (integrity), provoke errors, and is an injection class
that becomes more dangerous as datasets/fields grow.

### Remediation
```python
canton: str | None = Field(default=None, min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$")
year:   str | None = Field(default=None, pattern=r"^\d{4}$")

def _odsql_str(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
```
Add enums/whitelists for `phase`, `traffic_type`, `operator`; route every string value
through `_odsql_str` (including `traffic_type`).

### Effort Estimate
M (1–3 days)
