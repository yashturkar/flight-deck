---
owner: platform
status: draft
last_verified: 2026-03-16
source_of_truth:
  - ../../scripts/eval_pr.py
  - ../../kb-server/app/api/routes/notes.py
  - ../../vault-sync/vault_sync/api_client.py
related_code:
  - ../../kb-server/app/services/git_batcher.py
  - ../../vault-sync/vault_sync/sync.py
related_tests:
  - ../../kb-server/tests/test_current_view.py
  - ../../kb-server/tests/test_source_and_delete.py
  - ../../vault-sync/tests/test_api_client.py
  - ../../vault-sync/tests/test_sync.py
review_cycle_days: 14
---

# PR Evaluation Harness

Use `scripts/eval_pr.py` to evaluate a target ref from an isolated worktree rooted
from local `main`.

The harness is meant for reviewing other people's branches without touching your
active checkout. It provisions a temp worktree, temp vault, temp bare remote,
temp SQLite database, and a tmux-backed local stack.

## Prerequisites

- local `main` exists and is up to date enough for comparison
- repo-local virtualenvs already exist:
  - `kb-server/.venv`
  - `vault-sync/.venv`
- `git` and `tmux` are installed

## Default flow

```bash
cd /path/to/flight-deck
python scripts/eval_pr.py <target-ref>
```

Example refs:

```bash
python scripts/eval_pr.py origin/some-branch
python scripts/eval_pr.py my-local-branch
python scripts/eval_pr.py HEAD
```

By default the harness:

- creates a temp git worktree from `main`
- checks out `<target-ref>` inside that worktree
- runs targeted `kb-server` and `vault-sync` tests when those areas changed
- starts `kb-server` in `tmux`
- starts `vault-sync` in `tmux`
- validates current main behavior:
  - API key enforcement using `KB_API_KEY`
  - `source=human` writes commit directly to `main`
  - default API writes batch into `kb-api/YYYY-MM-DD`
  - `view=current` includes pending branch content
  - `vault-sync` pulls `view=current` and pushes local edits with `source=human`

The default `kb-server` test subset intentionally avoids `tests/test_notes_api.py`
because that file is currently failing on `main`; auth behavior is covered by the
harness's own HTTP smoke checks instead.

## Useful flags

```bash
python scripts/eval_pr.py <target-ref> --keep-temp
python scripts/eval_pr.py <target-ref> --tests-only
python scripts/eval_pr.py <target-ref> --e2e-only
python scripts/eval_pr.py <target-ref> --no-sync
python scripts/eval_pr.py <target-ref> --port 8021
python scripts/eval_pr.py <target-ref> --tmux-session-name fd-review
```

## Artifacts and inspection

The script prints:

- temp root
- temp worktree path
- changed files relative to `main`
- interpreter paths
- logs directory
- tmux session name

On failure it keeps the temp root so you can inspect:

- env files
- runtime logs
- worktree contents
- tmux panes

Useful commands after a failed run:

```bash
tmux attach -t <session-name>
tmux capture-pane -pt <session-name>:0.0
tmux capture-pane -pt <session-name>:0.1
```

If you used `--keep-temp`, remove the temp directory yourself after inspection.
