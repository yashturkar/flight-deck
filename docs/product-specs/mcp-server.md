---
owner: platform
status: draft
last_verified: 2026-03-12
source_of_truth:
  - ../../mcp-server/mcp_server/server.py
  - ../../mcp-server/mcp_server/client.py
  - ../../kb-server/app/api/routes/context.py
related_code:
  - ../../kb-server/app/api/routes/notes.py
related_tests:
  - ../../mcp-server/tests
  - ../../kb-server/tests/test_context_api.py
review_cycle_days: 14
---

# Product Spec: mcp-server

## Purpose

Expose Flight Deck note operations and context retrieval to MCP-capable agents without duplicating backend approval or Git logic.

## User-Visible Behavior

- Provides MCP tools for:
  - finding relevant notes
  - building bounded context bundles
  - listing notes
  - reading notes
  - writing notes as API-origin changes
  - deleting notes as API-origin changes
- Provides a note resource for direct page reads through MCP.
- Defaults reads and retrieval to `view=current`.
- Forces writes to `view=main` and `source=api`.

## Guardrails

- Uses `kb-server` as the only backend authority.
- Must be configured with `KB_SERVER_URL` and `KB_API_KEY`.
- Does not expose `source=human`.
- Does not expose publish or prompt workflows in v1.
- v1 transport is stdio.

## Related Operational Docs

- `../../mcp-server/README.md`
- `../SECURITY.md`
- `../RELIABILITY.md`
- `../../ARCHITECTURE.md`
