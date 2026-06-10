# my-orchestrator

<ClientOnly>
  <DemoPanel slug="my-orchestrator" />
</ClientOnly>

## What it is

A **TypeScript MCP meta-server** that lists registered MCP servers on the machine and exposes tools to read their READMEs (`discover_server`, `discover_all`) without connecting to each server directly.

## When to use it

- Discover what MCP servers are available locally
- Preview another server's capabilities from its README

## Stack and entry points

| Item | Path |
|------|------|
| Project context | `my-orchestrator/CLAUDE.md` |
| Server | `my-orchestrator/src/index.ts` |
| Registry | Hardcoded `serverRegistry` in `index.ts` |

## Prerequisites

| Need | Detail |
|------|--------|
| Node.js | Current LTS |
| Install | `npm install` in `my-orchestrator/` |

## How to run

```bash
cd ~/Documents/GitHub/my-orchestrator
npm install
npx tsx src/index.ts
```

**MCP tools:** `ping`, `list_servers`, `discover_server`, `discover_all`.

**Claude Code registration (example):**

```json
{ "command": "npx", "args": ["tsx", "/Users/konyebin/Documents/GitHub/my-orchestrator/src/index.ts"] }
```

Update `serverRegistry` paths before use (placeholders may still say `xxx`).

## Canonical docs

- `~/Documents/GitHub/my-orchestrator/CLAUDE.md`
- `~/Documents/GitHub/my-orchestrator/README.md`
