# Current Status

- Control Tower bootstrap is initialized and graph-backed memory is enabled through `.control-tower/state/decision-graph/`.
- Latest curated import is Scout session `019d12f8-d138-79f0-b22b-8cfd6b0f85da`, which established repo context for Tower.
- Repository state at import time: `main` matched `origin/main`; the only untracked area was `.control-tower/`.
- Canonical repo conventions are grounded from `AGENTS.md`: code behavior is canonical, tests break doc ties, durable docs live under `docs/`, `main` is approved content, `kb-api/*` carries pending API or agent changes, `view=current` is read-only composed state, and `source=human` writes commit directly to the base branch.
- Recent confirmed repo evolution on `main`:
  - `7c47d50`: local pre-commit docs checks and stale-doc autofix support.
  - `258552c`: context rollout plan moved from active to completed and auth/reliability docs were aligned.
  - `2beef5b`: git auth fixes.
  - `3848563`: API key auth added for `/notes` endpoints.
- The previously observed `docs/PLANS.md` drift is resolved on `main`: `docs/exec-plans/active/` now exists again with `.gitkeep` and `README.md`. This matches the minimal recommended fix and keeps agent navigation aligned with the documented path.
- Active PR lines are now grounded from GitHub and remote refs:
  - PR `#6`: `feat/actor-aware-git-identities` -> `main` and PR `#8`: `feat/hashed-api-key-auth` -> `feat/actor-aware-git-identities` form a two-branch auth stack. Relative to `origin/main`, the branches are ahead by 5 and 10 commits respectively; `feat/hashed-api-key-auth` is 5 commits ahead of its parent branch.
  - PR `#9`: `yashom7/revup/main/retrieval-layer` -> `main` and PR `#10`: `yashom7/revup/main/mcp-adapter` -> `yashom7/revup/main/retrieval-layer` form a two-branch retrieval/MCP stack. Relative to `origin/main`, the branches are ahead by 1 and 2 commits respectively; `mcp-adapter` is 1 commit ahead of `retrieval-layer`.
  - PR `#13`: `feat/pr-eval-harness` -> `main` is a standalone line ahead of `origin/main` by 3 commits.
- Open PR anomaly: PR `#12` targets `main` from `main` while describing admin UI and `.env` setup work. Tower should treat it as review-state noise until a non-`main` head branch or replacement PR is identified.
