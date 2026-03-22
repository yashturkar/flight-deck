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
python3 scripts/eval_pr.py <target-ref>
```

Example refs:

```bash
python3 scripts/eval_pr.py origin/some-branch
python3 scripts/eval_pr.py my-local-branch
python3 scripts/eval_pr.py HEAD
```

Symbolic refs such as `HEAD` are resolved in your current checkout before the temp
worktree is created, so the harness evaluates the commit you asked for rather than
the temp worktree's initial `main` HEAD.

By default the harness:

- creates a temp git worktree from `main`
- resolves `<target-ref>` to a commit in your current checkout, then checks out that commit inside the temp worktree
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
python3 scripts/eval_pr.py <target-ref> --keep-temp
python3 scripts/eval_pr.py <target-ref> --tests-only
python3 scripts/eval_pr.py <target-ref> --e2e-only
python3 scripts/eval_pr.py <target-ref> --no-sync
python3 scripts/eval_pr.py <target-ref> --port 8021
python3 scripts/eval_pr.py <target-ref> --tmux-session-name fd-review
```

## Recommended review flow

For a normal review pass:

```bash
git fetch origin
python3 scripts/eval_pr.py origin/<branch-name>
```

For a quicker check when you only want test feedback:

```bash
python3 scripts/eval_pr.py origin/<branch-name> --tests-only
```

For debugging a runtime issue and keeping the temp environment around:

```bash
python3 scripts/eval_pr.py origin/<branch-name> --keep-temp
```

## Artifacts and inspection

The script prints:

- temp root
- temp worktree path
- changed files relative to `main`
- interpreter paths
- logs directory
- tmux session name

On failure it keeps the temp root and any harness-created worktree/tmux session so
you can inspect:

- env files
- runtime logs
- worktree contents
- tmux panes

If the requested tmux session name already exists, the harness stops before
starting services and leaves that pre-existing session untouched.

Useful commands after a failed run:

```bash
tmux attach -t <session-name>
tmux capture-pane -pt <session-name>:0.0
tmux capture-pane -pt <session-name>:0.1
```

`--keep-temp` uses the same preservation behavior after a successful run. Remove the
temp directory and any preserved worktree/tmux session yourself after inspection.
