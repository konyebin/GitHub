# Check Back Customer Adoption Intelligence

Track whether Webex customers are **using what they pay for** — provisioned vs entitled licenses, adoption health (G/Y/R), and per-account business insight slides.

```text
PDFs + screenshots  →  populate CLI  →  Check Back .xlsx  →  dashboard
```

The **dashboard only reads Excel/CSV**. It does not ingest PDFs or images directly. Run `populate` first for each customer.

---

## Install (standalone)

Clone this repo anywhere. No parent monorepo or special folder layout required.

```bash
git clone https://github.com/konyebin/check-back-intelligence.git
cd check-back-intelligence

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

**Requirements:** Python 3.12+ (3.11+ usually works), a modern browser. Optional: `cloudflared` for the Webex bot tunnels.

### First run

```bash
# Option A — start from the included template
cp samples/check_back_template.xlsx output/my_portfolio.xlsx
export CHECK_BACK_XLSX=output/my_portfolio.xlsx

# Option B — build from customer PDFs/screenshots
.venv/bin/python -m src.cli populate \
  --sources ./my-customer-pdfs \
  --template samples/check_back_template.xlsx \
  --out output/my_portfolio.xlsx
export CHECK_BACK_XLSX=output/my_portfolio.xlsx

# Open the dashboard (local HTTP server — required for file upload)
export CHECK_BACK_VENV="$PWD/.venv"
./check-back dashboard
```

The dashboard opens at `http://127.0.0.1:8765/index.html`. Use **📂 Reload spreadsheet** to pick any `.xlsx`, or **🔄 Reload baseline** after syncing the default workbook.

> **Note:** Opening `dashboard/index.html` directly (`file://`) will not work — browsers block local script loading. Always use `./check-back dashboard` or `cd dashboard && ./serve.sh`.

---

## One-command wrapper (`./check-back`)

Point the wrapper at your venv and workbook:

```bash
export CHECK_BACK_VENV="$PWD/.venv"
export CHECK_BACK_XLSX=output/my_portfolio.xlsx   # or output/Check_Back_standardized.xlsx
```

| Command | What it does |
|---------|----------------|
| `./check-back` or `./check-back open` | Sync workbook + prepare dashboard + open Excel + browser |
| `./check-back sync` | Spreadsheet only (slide fields, URLs, subscription dates) |
| `./check-back dashboard` | Rebuild JS bundle + copy xlsx + open browser |
| `./check-back populate …` | PDF/screenshot ingest (passthrough to `python -m src.cli populate`) |
| `./check-back help` | Show all commands |

Default workbook path: `output/Check_Back_standardized.xlsx` (override with `CHECK_BACK_XLSX`).

Python equivalent for sync: `python -m src.cli sync-workbook -i output/my_portfolio.xlsx`

---

## Data pipeline

### Single customer

```bash
.venv/bin/python -m src.cli populate \
  --sources ./path/to/customer-pdfs \
  --account "CUSTOMER NAME" \
  --template samples/check_back_template.xlsx \
  --out output/my_portfolio.xlsx \
  --mode append
```

### Multiple customers

Put each customer in its own subfolder:

```text
sources/
  customer-a/     ← PDFs + screenshots → one Check Back row
  customer-b/     ← PDFs + screenshots → one Check Back row
```

```bash
.venv/bin/python -m src.cli populate \
  --sources ./sources \
  --template samples/check_back_template.xlsx \
  --out output/portfolio_check_back.xlsx
```

### Append to an existing workbook

```bash
.venv/bin/python -m src.cli populate \
  --sources ./path/to/new-customer \
  --template samples/check_back_template.xlsx \
  --mode append \
  --out output/portfolio_updated.xlsx
```

### Validate license math

```bash
.venv/bin/python -m src.cli validate -i output/my_portfolio.xlsx
```

---

## Dashboard

### Local development

```bash
cd dashboard
./build-bundle.sh          # rebuild dashboard.bundle.js after JS changes
./sync-default-workbook.sh # copy CHECK_BACK_XLSX → check_back_default.xlsx
./serve.sh                 # HTTP server (port 8765+)
./open-dashboard.sh        # start/reuse server + open browser
```

### Dashboard modes (auto-detected from upload)

| Upload contains | Mode |
|-----------------|------|
| `Entitled Lic Calling` or `Provisioned/Entitled Lic Calling`, `(G/Y/R)` | **Check Back** — Adoption Health |
| `Collab AOV`, `Renewal Fiscal Qtr` | **Renewal** — full renewal analytics |
| Other | Generic table + KPIs |

### Public demo (GitHub Pages)

Upload a Check Back `.xlsx` in the browser — all processing runs client-side.

- **Hosted demo:** https://konyebin.github.io/GitHub/demos/check-back/index.html  
  (loads a sanitized sample workbook; no real customer data)

To rebuild the static site for Pages:

```bash
cd dashboard
./prepare-github-pages.sh
# Push docs/ to main — GitHub Actions deploys the dashboard
```

---

## Webex bot connector

Share the dashboard link and portfolio KPIs in Webex spaces.

### Prerequisites

- `WEBEX_BOT_TOKEN` (and optionally `WEBEX_WEBHOOK_SECRET`) in a project `.env` file
- `cloudflared` on your PATH
- Baseline workbook at `output/Check_Back_standardized.xlsx` (or set `CHECK_BACK_XLSX`)

```bash
cp .env.example .env
# Edit .env — add WEBEX_BOT_TOKEN=...

bash webex_bot/run-check-back-bot.sh
```

Copy the printed webhook URL, then register it:

```bash
PYTHONPATH=. .venv/bin/python -m webex_bot.register_webhook \
  --url "https://….trycloudflare.com/webhook"
```

Add the bot to a Webex space and send:

| Command | Action |
|---------|--------|
| `help` | List commands |
| `dashboard` | Link to the public dashboard tunnel |
| `summary` / `portfolio` | KPI snapshot from baseline xlsx |
| `refresh` / `sync baseline` | Re-sync baseline into dashboard, then post summary |

Tunnel state: `~/.check-back/bot-tunnel.json`  
Stop the stack: `kill $(cat ~/.check-back/check-back-bot.pids)`

---

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `CHECK_BACK_VENV` | `$PROJECT/.venv` | Python venv for `./check-back` |
| `CHECK_BACK_XLSX` | `output/Check_Back_standardized.xlsx` | Baseline workbook path |
| `WEBEX_BOT_TOKEN` | — | Webex bot API token |
| `WEBEX_WEBHOOK_SECRET` | — | Optional webhook HMAC secret |
| `CHECKBACK_DASHBOARD_PORT` | `8765` | Dashboard HTTP port (bot stack) |
| `CHECKBACK_WEBHOOK_PORT` | `5010` | Flask webhook port (bot stack) |
| `PORT` | `8765` | `serve.sh` port picker |

Copy `.env.example` → `.env` for bot tokens. **Never commit `.env`.**

---

## CLI reference

```bash
.venv/bin/python -m src.cli <command> -h
```

| Command | Purpose |
|---------|---------|
| `populate` | **Main** — PDFs + screenshots → Check Back xlsx |
| `sync-workbook` | Slide fields, Salesforce URLs, subscription dates |
| `ingest-sources` | Staging only → `staging/customers.json` |
| `build-workbook` | Rebuild xlsx from staging JSON |
| `map-install-base` | Install base → JSON rows + gap report |
| `validate` | Check license math / missing org id |
| `export-panels` / `import-panels` | Sidecar panel cache merge |

### Optional: Install Base fields

```bash
.venv/bin/python -m src.cli populate \
  --sources ./customer-pdfs \
  --install-base samples/install_base_sample.xlsx \
  --account-filter "CUSTOMER" \
  --out output/check_back_filled.xlsx
```

---

## Project layout

```text
check-back-intelligence/
├── check-back              # wrapper script
├── src/                    # Python CLI pipeline
├── dashboard/              # static HTML/JS dashboard
├── webex_bot/              # Webex bot + tunnels
├── samples/                # template xlsx, BIA slide PDF
├── config/                 # field mapping YAML
├── tests/
└── output/                 # your workbooks (gitignored — no customer data in repo)
```

---

## What is not in this repo

Customer PDFs, populated workbooks, and staging JSON are **local only** (`.gitignore`). Bring your own sources and xlsx files.

For agent/IDE conventions see [CLAUDE.md](CLAUDE.md).  
For the standalone extraction plan see [docs/superpowers/plans/2026-06-15-standalone-project.md](docs/superpowers/plans/2026-06-15-standalone-project.md).
