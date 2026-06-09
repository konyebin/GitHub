---
name: scrapeweb
description: |
  Recursively crawl a website via BFS (breadth-first search), extract rich
  structured data from each page, and save results to timestamped JSON files.
  Extracts headings, text blocks, links, images, tables, open graph, metadata,
  and more from every page visited.
allowed-tools: Bash, Read, Glob
argument-hint: [url] [--depth N] [--max-pages N]
---

# Scrapeweb Skill

Crawls a URL and saves structured JSON output for every page visited.

**Project path:** `~/Documents/GitHub/scrapeweb/`

---

## Quick-start

```bash
cd ~/Documents/GitHub/scrapeweb

# Interactive — prompts for URL
.venv/bin/python3 src/scraper.py

# With URL
.venv/bin/python3 src/scraper.py --url https://example.com

# Custom depth + page cap
.venv/bin/python3 src/scraper.py --url https://example.com --depth 3 --max-pages 50

# Follow external links too
.venv/bin/python3 src/scraper.py --url https://example.com --all-domains
```

---

## CLI flags

| Flag | Default | Description |
|---|---|---|
| `--url` | (prompted) | Starting URL |
| `--depth` | 2 | Max crawl depth from start URL |
| `--max-pages` | 100 | Hard cap on total pages crawled |
| `--delay` | 0.5s | Politeness delay between requests |
| `--output` | `./output` | Output directory |
| `--all-domains` | off | Follow links to external domains |

---

## Output

Each crawl writes one file: `output/<domain>_<timestamp>_crawl.json`

Each page record contains:

```
url, title, meta, open_graph, twitter_card,
headings, text_blocks, lists, blockquotes, code_blocks,
links, images, tables, full_text
```

Output files are **never overwritten** — every run creates a new timestamped file.

---

## Stack

| Item | Detail |
|---|---|
| Language | Python 3.14 |
| HTTP | `requests` (stream=True — do not remove) |
| Parsing | `beautifulsoup4` (receives raw bytes for charset detection) |
| Venv | `.venv/` — always use it |
| Entry point | `src/scraper.py` — single file, no modules |

---

## Setup (first time)

```bash
cd ~/Documents/GitHub/scrapeweb
python3.14 -m venv .venv
.venv/bin/pip install requests beautifulsoup4
```

---

## Key conventions & gotchas

- **Same-domain only by default** — use `--all-domains` to follow external links
- `stream=True` on requests is intentional — prevents UnicodeDecodeError on redirect bodies; do not remove
- BeautifulSoup receives raw bytes so it can detect charset from `<meta charset>` itself
- Text block deduplication uses direct child text only to avoid parent/child repetition
- Non-HTML resources (PDF, JS, CSS, images) are automatically skipped via `SKIP_EXTENSIONS`
- `.venv` uses Python 3.14 — do not mix with system Python or other venvs
- Results land in `output/` inside the project; `my_results/` is for manually organised copies
