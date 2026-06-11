# test

<ClientOnly>
  <DemoPanel slug="test" />
</ClientOnly>

## What it is

**Experimental and integration code** under `~/Documents/GitHub/test` — not a single app. Notable subprojects:

| Subfolder | Purpose |
|-----------|---------|
| **device-mcp-server** | RoomOS MCP server (Cursor **roomos**) — [dedicated page](/projects/device-mcp-server) |
| **Webex OCR bot** | MVP: screenshots in a Webex space → OCR → Excel row |

## When to use it

- RoomOS / xAPI device control → use **device-mcp-server**, not the test folder root
- Webex space screenshot OCR pipeline → OCR bot README

## Stack and entry points

| Item | Path |
|------|------|
| OCR bot README | `test/README.md` |
| RoomOS MCP | `test/device-mcp-server/` |

## Prerequisites (OCR bot)

| Need | Detail |
|------|--------|
| Python | 3.11+ |
| Tesseract | `brew install tesseract` |
| ngrok | For local Webex webhook dev |
| Packages | `pip install -r requirements.txt` in bot directory |

## How to run (OCR bot)

See `test/README.md` for clone, venv, Webex bot token, and ngrok webhook setup.

## Canonical docs

- `~/Documents/GitHub/test/README.md`
- `~/Documents/GitHub/test/device-mcp-server/README.md` — [device-mcp-server page](/projects/device-mcp-server)
