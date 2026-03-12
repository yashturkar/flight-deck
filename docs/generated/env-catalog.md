---
owner: platform
status: generated
last_verified: 2026-03-12
source_of_truth:
  - ../../kb-server/.env.example
  - ../../kb-server/app/core/config.py
  - ../../vault-sync/vault_sync/config.py
related_code:
  - ../../scripts/generate_context_artifacts.py
related_tests:
  - ../../kb-server/tests
  - ../../vault-sync/tests
review_cycle_days: 7
---

# Environment Catalog (Generated)

Generated on `2026-03-12` from settings and env sources.

## kb-server `.env.example`

| Variable | Example Default |
| --- | --- |
| `VAULT_PATH` | `/Users/yashturkar/Downloads/flightdeck/vault` |
| `DATABASE_URL` | `postgresql://kb:kb@localhost:5432/kb` |
| `KB_API_KEY` | `<redacted>` |
| `GIT_REMOTE` | `origin` |
| `GIT_BRANCH` | `main` |
| `GIT_PUSH_ENABLED` | `true` |
| `GIT_USER_AUTHOR_NAME` | `` |
| `GIT_USER_AUTHOR_EMAIL` | `` |
| `GIT_USER_COMMITTER_NAME` | `` |
| `GIT_USER_COMMITTER_EMAIL` | `` |
| `GIT_USER_SSH_COMMAND` | `` |
| `GIT_AGENT_AUTHOR_NAME` | `` |
| `GIT_AGENT_AUTHOR_EMAIL` | `` |
| `GIT_AGENT_COMMITTER_NAME` | `` |
| `GIT_AGENT_COMMITTER_EMAIL` | `` |
| `GIT_AGENT_SSH_COMMAND` | `` |
| `GIT_AGENT_HTTPS_TOKEN` | `<redacted>` |
| `AUTOSAVE_DEBOUNCE_SECONDS` | `30` |
| `GIT_PULL_INTERVAL_SECONDS` | `60` |
| `GIT_BATCH_DEBOUNCE_SECONDS` | `10` |
| `GIT_BATCH_BRANCH_PREFIX` | `kb-api` |
| `GITHUB_TOKEN` | `<redacted>` |
| `GITHUB_AGENT_TOKEN` | `<redacted>` |
| `GITHUB_REPO` | `owner/repo` |
| `QUARTZ_BUILD_COMMAND` | `` |
| `QUARTZ_WEBHOOK_URL` | `` |
| `API_HOST` | `0.0.0.0` |
| `API_PORT` | `8000` |

## kb-server Settings Defaults

| Field | Default Expression |
| --- | --- |
| `vault_path` | `Path("/srv/flightdeck/vault")` |
| `database_url` | `"postgresql://kb:kb@localhost:5432/kb"` |
| `kb_api_key` | `""` |
| `git_remote` | `"origin"` |
| `git_branch` | `"main"` |
| `git_push_enabled` | `True` |
| `git_user_author_name` | `""` |
| `git_user_author_email` | `""` |
| `git_user_committer_name` | `""` |
| `git_user_committer_email` | `""` |
| `git_user_ssh_command` | `""` |
| `git_agent_author_name` | `""` |
| `git_agent_author_email` | `""` |
| `git_agent_committer_name` | `""` |
| `git_agent_committer_email` | `""` |
| `git_agent_ssh_command` | `""` |
| `git_agent_https_token` | `""  # PAT used for agent git push over HTTPS` |
| `git_batch_debounce_seconds` | `10` |
| `git_batch_branch_prefix` | `"kb-api"` |
| `github_token` | `""` |
| `github_agent_token` | `""` |
| `github_repo` | `""  # e.g., "owner/repo"` |
| `autosave_debounce_seconds` | `30` |
| `git_pull_interval_seconds` | `60` |
| `quartz_build_command` | `""` |
| `quartz_webhook_url` | `""` |
| `api_host` | `"0.0.0.0"` |
| `api_port` | `8000` |

## vault-sync Settings Defaults

| Field | Default Expression |
| --- | --- |
| `kb_server_url` | `"http://localhost:8000"` |
| `kb_api_key` | `""` |
| `sync_dir` | `Path.home() / "vault-sync"` |
| `sync_debounce_seconds` | `2.0` |
| `sync_pull_interval_seconds` | `30.0` |

Do not edit manually. Regenerate with `python3 scripts/generate_context_artifacts.py`.