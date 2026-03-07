# Flight Deck

A file-first knowledge base with Git-backed approval workflows. Edit notes locally, sync with a server, and keep agent changes reviewable via PRs.

## What it does

- **kb-server**: API and workers that manage a Markdown vault, auto-commit to Git, and expose a `current` view (approved content + pending PRs).
- **vault-sync**: Daemon that mirrors the current view to a local folder and pushes your edits back as human-origin commits.

## Get started

1. **Run the server** — [kb-server/README.md](kb-server/README.md)
  Set up the vault, Postgres, and API. Start the API + autosave worker.
2. **Run the sync daemon** — [vault-sync/README.md](vault-sync/README.md)
  Point vault-sync at your kb-server. It pulls notes into a local directory and pushes edits on save.
3. **Edit with Obsidian** — [obsidian.md](https://obsidian.md)
  Open the vault-sync directory as an Obsidian vault. Edit Markdown locally; changes sync automatically.

## Project layout


| Path          | Purpose                                      |
| ------------- | -------------------------------------------- |
| `kb-server/`  | API, Git workflows, current-view composition |
| `vault-sync/` | Local sync daemon (pull + push)              |
| `docs/`       | Architecture, runbooks, product specs        |


## More

- [ARCHITECTURE.md](ARCHITECTURE.md) — Domain boundaries and flows
- [AGENTS.md](AGENTS.md) — Entry point for AI agents
- [docs/](docs/) — Design docs, runbooks, security, reliability

## Docs Checks Before PR

Run these from repo root before opening a PR:

```bash
python3 scripts/docs_lint.py
python3 scripts/generate_context_artifacts.py
python3 scripts/docs_garden.py --output docs/generated/stale-docs-report.md
```
