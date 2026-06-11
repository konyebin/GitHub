# GitHub workspace

Personal monorepo at `~/Documents/GitHub` — Webex automation (**wxops**), Vidcast MCP, RoomOS device MCP, scrapers, OCR tools, and side projects. Shared Webex OAuth and Cursor MCP config live at the repo root.

## Documentation site

Browse one page per project folder:

```bash
cd ~/Documents/GitHub/docs
npm install
npm run docs:dev
```

Then open the local URL (usually `http://localhost:5173`). Start at the home page or [workspace setup](docs/shared/root-setup.md) in the site.

## Quick routing

| Need | Folder |
|------|--------|
| Webex Calling admin, CDR, billing | `wxops/` |
| Vidcast recordings / transcripts | `vidcastmcp/` |
| RoomOS devices (Cursor MCP) | `test/device-mcp-server/` |
| Webex OAuth token | `webex_oauth.py` + `.env` at root |
| Website crawl → JSON | `scrapeweb/` |
| Screenshot OCR → Excel | `Lookback/` |

## Agent context

- **Root:** `CLAUDE.md` — fresh install, OAuth, MCP, cross-project routing
- **Per project:** each folder’s `CLAUDE.md` or `README.md`

Human-readable summaries: `docs/` (VitePress).
