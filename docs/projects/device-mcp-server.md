# device-mcp-server

<ClientOnly>
  <DemoPanel slug="device-mcp-server" />
</ClientOnly>

## What it is

**MCP server for Cisco RoomOS** devices via Webex Cloud API / xAPI: dial, audio/video, camera, standby, presentation, bookings, diagnostics, and UI messages. Token-based auth (no on-device credentials in the MCP process).

## When to use it

- Control RoomOS devices from Cursor or another MCP client
- List devices, place calls, mute, presets, standby, etc.

## Stack and entry points

| Item | Path |
|------|------|
| README | `test/device-mcp-server/README.md` |
| OAuth guide | `test/device-mcp-server/OAUTH_SETUP_GUIDE.md` |
| Built server | `test/device-mcp-server/dist/index.js` |
| Source | `test/device-mcp-server/src/index.ts` |

## Prerequisites

| Need | Detail |
|------|--------|
| Node.js | **18+** |
| Build | `npm install && npm run build` |
| Token | `WEBEX_ACCESS_TOKEN` from root `~/Documents/GitHub/.env` (recommended) |
| Scopes | `spark:xapi_commands`, `spark:xapi_statuses`, `spark-admin:devices_read`, `spark:devices_read` (append to root `WEBEX_SCOPES` if missing) |
| Devices | Webex device IDs for endpoints you control |

## How to run

### Cursor (stdio — default)

1. Workspace root: `~/Documents/GitHub`
2. Build once: `cd test/device-mcp-server && npm install && npm run build`
3. `.cursor/mcp.json` server **roomos**: `node ${workspaceFolder}/test/device-mcp-server/dist/index.js`, `envFile` → root `.env`
4. Reload MCP after token changes

### HTTP MCP (optional)

```bash
cd ~/Documents/GitHub/test/device-mcp-server
TRANSPORT=http npm start
```

Default **PORT** is **3001** unless set. MCP endpoint: `POST /mcp`.

### Root OAuth (recommended)

```bash
cd ~/Documents/GitHub && .venv/bin/python webex_oauth.py
```

Optional folder-only flow: `node oauth-helper.js` in `test/device-mcp-server/`.

## MCP capabilities (summary)

Call, audio, video, camera, standby, presentation, bookings, system, UI, proximity, diagnostics — see README feature list.

## Canonical docs

- `~/Documents/GitHub/test/device-mcp-server/README.md`
- `~/Documents/GitHub/test/device-mcp-server/OAUTH_SETUP_GUIDE.md`
- `~/Documents/GitHub/CLAUDE.md` — Requirements § device-mcp-server
