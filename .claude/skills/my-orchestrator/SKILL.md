---
name: my-orchestrator
description: |
  TypeScript MCP meta-orchestrator that lets an LLM discover and understand
  all other MCP servers registered on this machine — without connecting to them
  directly. Exposes ping, list_servers, discover_server, and discover_all tools.
allowed-tools: Bash, Read, Edit, Write
argument-hint: [start|add-server|rebuild]
---

# My Orchestrator Skill

MCP meta-server for discovering all other MCP servers on this machine.

**Project path:** `~/Documents/GitHub/my-orchestrator/`

---

## Quick-start

```bash
cd ~/Documents/GitHub/my-orchestrator

# Start the server (stdio transport — used by Claude/MCP clients)
npx tsx src/index.ts
```

---

## MCP config registration

Add to your MCP client config (e.g. Cursor `mcp.json`, Claude Code settings):

```json
{
  "command": "npx",
  "args": ["tsx", "/Users/konyebin/Documents/GitHub/my-orchestrator/src/index.ts"]
}
```

---

## Tools exposed

| Tool | What it does |
|---|---|
| `ping` | Health check — returns `"Pong: <message>"` |
| `list_servers` | Lists all servers in the registry with their command + args |
| `discover_server` | Reads a specific server's README (first 2000 chars) |
| `discover_all` | Reads all server READMEs at once (first 1000 chars each) |

---

## Stack

| Item | Detail |
|---|---|
| Runtime | Node.js (CommonJS — do not switch to ESM without updating imports) |
| Language | TypeScript |
| Dev runner | `tsx` (no build step) |
| Key deps | `@modelcontextprotocol/sdk`, `zod` |
| Entry point | `src/index.ts` — single file, all tools defined here |
| Module type | `"type": "commonjs"` in package.json |

---

## Adding a new MCP server to the registry

Edit the `serverRegistry` object in `src/index.ts`:

```typescript
serverRegistry['my-new-server'] = {
  readmePath: '/absolute/path/to/server/README.md',
  command: 'node',
  args: ['/absolute/path/to/server/dist/index.js']
};
```

- Paths must be absolute and correct — `discover_server` will error if the README doesn't exist
- Placeholder paths in the file use `xxx` — replace with the actual username

---

## Setup (first time)

```bash
cd ~/Documents/GitHub/my-orchestrator
npm install
```

No build step needed — `tsx` runs TypeScript directly.

---

## Gotchas

- `"type": "commonjs"` — don't switch to ESM without updating all imports
- `tsx` is the dev runner; there's no compiled `dist/` output configured
- README paths in the registry must be absolute — relative paths will fail when started from a different working directory
- `discover_all` can be slow if many servers are registered; use `discover_server` for targeted lookups
