# Risk Acceptance Register

Formal record of audit concerns that are **accepted as residual risk** rather
than remediated in this repository, because the appropriate control lives at the
portfolio / MCP-gateway layer. Each acceptance is time-bound by explicit
re-evaluation triggers.

| Field | Value |
|---|---|
| Server | `sbb-opendata-mcp` |
| Audit catalog | mcp-audit-skill (`main`, 68 checks; catalog hash not pinned) |
| Risk owner | Hayal Oezkan ([@malkreide](https://github.com/malkreide)) |
| Decision date | 2026-06-04 |
| Next review | 2026-12-04, or earlier on any trigger below |
| Server profile | read-only · Public Open Data · no PII · `auth_model: none` · no API key · single trusted upstream (`data.sbb.ch`) |

> Note: the formal MCP audit (2026-06-04) raised **10 findings, all remediated
> and closed** by 2026-06-05 (PRs #2–#7). The acceptances below are not audit
> findings but portfolio-level controls that, for a single read-only server, are
> deliberately handled one layer up.

---

## RA-001 — Tool allow-listing via an MCP gateway

| | |
|---|---|
| **Concern** | Per-tool allow-listing across aggregated servers |
| **Status** | `accepted-risk` |
| **Decision** | Accepted at the server level; to be implemented at the gateway. |

**Rationale.** A per-tool allow-list is a property of the MCP host/gateway that
aggregates multiple servers, not of a single server exposing a fixed, fully
read-only tool set. Implementing it here would not constrain a compromised host
and would duplicate a control that belongs one layer up.

**Compensating controls already in place.**
- All 10 tools are read-only (`readOnlyHint`, no write/destructive operations).
- Egress is fixed to the hardcoded `data.sbb.ch` base URL — a tool cannot reach
  arbitrary hosts even if invoked (F-SEC-01).
- Tool definitions are version-controlled and ship from this repository; there is
  no dynamic / remote tool registration.

**Residual risk.** Low. Worst case is unrestricted invocation of read-only,
public-data queries against a single trusted upstream.

---

## RA-002 — Cross-server tool-poisoning detection

| | |
|---|---|
| **Concern** | Pre-flight tool-poisoning / rug-pull detection across servers |
| **Status** | `accepted-risk` |
| **Decision** | Accepted at the server level; cross-server detection belongs to the gateway/host. |

**Rationale.** Tool-poisoning / rug-pull detection across servers is a
supply-chain and host responsibility. This server registers no tools dynamically
or from remote sources; its tool definitions ship from this version-controlled
repository and any change is a reviewed pull request.

**Compensating controls already in place.**
- No dynamic / remote tool registration exists in the codebase.
- Tool definitions, descriptions and annotations are version-controlled; changes
  are reviewable in git history.

**Residual risk.** Low for this server in isolation; the cross-server detection
gap is owned at the portfolio level.

---

## Re-evaluation triggers

Both acceptances above are **void** and the controls must be implemented if the
server ever:

1. gains **write** capability or starts processing **PII**, or
2. registers tools **dynamically** / from remote sources, or
3. is aggregated behind a shared MCP gateway — at which point the controls are
   implemented **there**, and these acceptances are closed.

See [`../SECURITY.md`](../SECURITY.md) for the broader security posture.
