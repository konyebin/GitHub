# scrapeweb

<ClientOnly>
  <DemoPanel slug="scrapeweb" />
</ClientOnly>

## What it is

A **Python BFS web crawler** that extracts structured data from each page (metadata, headings, tables, links, full text) and writes timestamped JSON under `output/`.

## When to use it

- Scrape or extract structured data from a website
- Crawl same-domain (or all domains with `--all-domains`) with depth and page limits

## Stack and entry points

| Item | Path |
|------|------|
| Project context | `scrapeweb/CLAUDE.md` |
| Script | `scrapeweb/src/scraper.py` |
| Output | `scrapeweb/output/` |
| Venv | `scrapeweb/.venv` (Python **3.14**) |

## Prerequisites

| Need | Detail |
|------|--------|
| Python | **3.14** |
| Packages | `requests`, `beautifulsoup4` |

## How to run

```bash
cd ~/Documents/GitHub/scrapeweb
.venv/bin/python3 src/scraper.py
.venv/bin/python3 src/scraper.py --url https://example.com --depth 3 --max-pages 50
```

Common flags: `--depth` (default 2), `--max-pages` (100), `--delay` (0.5s), `--all-domains`.

## Canonical docs

- `~/Documents/GitHub/scrapeweb/CLAUDE.md`
