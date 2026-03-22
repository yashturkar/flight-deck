# Active Tasks

- Track the currently active PR lines as grounded branch stacks rather than generic branches ahead of `main`:
- Auth stack: PR `#6` `feat/actor-aware-git-identities` -> `main`, then PR `#8` `feat/hashed-api-key-auth` -> `feat/actor-aware-git-identities`.
- Retrieval stack: PR `#9` `yashom7/revup/main/retrieval-layer` -> `main`, then PR `#10` `yashom7/revup/main/mcp-adapter` -> `yashom7/revup/main/retrieval-layer`.
- Standalone line: PR `#13` `feat/pr-eval-harness` -> `main`.
- Triage PR `#12` as an anomaly: it is open with `main` as both head and base while describing admin UI work, so Tower should seek owner clarification instead of treating it as a normal active branch.
