# Bugbot / PR review focus (GitHub)

When reviewing PRs in this monorepo, prioritize:

## Secrets and credentials

- No `.env`, tokens, `WEBEX_ACCESS_TOKEN`, client secrets, or PATs in diffs
- No hardcoded OAuth codes or refresh tokens in scripts or docs

## MCP and launchers

- [`wxops/scripts/run-mcp-stdio.sh`](../wxops/scripts/run-mcp-stdio.sh) must **not** `source` root `.env` (WEBEX_SCOPES breaks bash)
- [`.cursor/mcp.json`](./mcp.json) paths must use `${workspaceFolder}` and remain stdio for local dev
- Changes to `mcp_server.py` should keep tool schemas backward compatible

## wxops / Webex

- Device deletes must append to [`devices_deleted.csv`](../devices_deleted.csv), not overwrite
- MAC must be captured before phone delete (reassign-device-by-mac skill)
- Do not commit camp0093 personIds as "new secrets" — they are lab IDs, but flag accidental production org IDs

## Docs and demos

- [`docs/public/demos/`](../docs/public/demos/) — no live API keys in client-side JS
- GitHub Pages base path `/GitHub/` must stay consistent in VitePress config

## Shell scripts

- Hooks under `.cursor/hooks/` must be executable and fail safely
- Prefer `set -euo pipefail` in new bash scripts

## check-back-intelligence

- No customer PDFs or PII in git
- Output xlsx paths only in docs, not committed customer data
