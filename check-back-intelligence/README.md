# Check Back Customer Adoption Intelligence

Track whether Webex customers are **using what they pay for**.

## How it works (correct flow)

```text
PDFs + screenshots  →  populate CLI  →  Check Back .xlsx  →  dashboard upload
```

The **dashboard only reads Excel/CSV**. It does not ingest PDFs or images directly. Always run `populate` first (for any customer).

## Quick start

```bash
cd ~/Documents/GitHub/check-back-intelligence
pip install -r requirements.txt

# Any customer: folder with PDFs and/or screenshots
python -m src.cli populate \
  --sources "$HOME/Desktop/Genuine Parts" \
  --account "GENUINE PARTS COMPANY" \
  --out "/Users/konyebin/Downloads/Check Back Initiative Customer Analysis.xlsx" \
  --mode append

cd dashboard && ./open-dashboard.sh
```

### One command (spreadsheet + dashboard)

After you edit the live workbook in Downloads:

```bash
cd ~/Documents/GitHub/check-back-intelligence
./check-back
```

This runs **everything** in order: sync slide columns → subscription dates → Salesforce URLs → copy xlsx for the dashboard → rebuild JS bundle → open Excel → open the browser.

| Command | What it does |
|---------|----------------|
| `./check-back` or `./check-back open` | Full update + open Excel + dashboard |
| `./check-back sync` | Spreadsheet only (no browser) |
| `./check-back dashboard` | Dashboard copy + bundle + browser only |
| `./check-back populate …` | PDF/screenshot ingest (same as `python -m src.cli populate`) |

Python equivalent: `python -m src.cli sync-workbook` (replaces `rebuild-ppt-columns` + `sync-subscription-dates`).

On open, the dashboard loads **`output/Check_Back_standardized.xlsx`** (copied to `dashboard/check_back_default.xlsx`). Edit the baseline in the repo, run `cd dashboard && ./sync-default-workbook.sh`, then **🔄 Reload baseline**. Or use **📂 Reload spreadsheet** to pick any file.

### Multiple customers at once

Put each customer in its own subfolder under `--sources`:

```text
sources/
  wake-county/     ← PDFs + screenshots → one Check Back row
  genuine-parts/   ← PDFs + screenshots → one Check Back row
```

```bash
python -m src.cli populate --sources ./sources --out output/portfolio_check_back.xlsx
```

### Append to an existing portfolio spreadsheet

```bash
python -m src.cli populate \
  --sources "$HOME/Desktop/Genuine Parts" \
  --template samples/check_back_template.xlsx \
  --mode append \
  --out output/portfolio_updated.xlsx
```

## Dashboard modes

| Upload contains | Mode |
|-----------------|------|
| `Entitled Lic Calling`, `(G/Y/R)` | **Check Back** — Adoption Health tab |
| `Collab AOV`, `Renewal Fiscal Qtr` | **Renewal** — full renewal analytics |
| Other | Generic table + KPIs |

## Public dashboard (GitHub Pages)

Anyone can use the dashboard in a browser — no local server required:

**https://konyebin.github.io/GitHub/demos/check-back/index.html**

Upload a Check Back `.xlsx`; processing runs entirely client-side. The hosted demo loads a **sanitized sample workbook** (no real customer data).

To refresh the hosted copy after dashboard changes:

```bash
cd ~/Documents/GitHub/check-back-intelligence/dashboard
chmod +x prepare-github-pages.sh
./prepare-github-pages.sh
# Then push to main — deploy-docs.yml publishes on merge
```

## Optional: Install Base fields

```bash
python -m src.cli populate \
  --sources ./customer-pdfs \
  --install-base samples/install_base_sample.xlsx \
  --account-filter "PHILLIPS" \
  --out output/check_back_filled.xlsx
```

## CLI reference

| Command | Purpose |
|---------|---------|
| `populate` | **Main command** — PDFs + images → Check Back xlsx |
| `ingest-sources` | Staging only → `staging/customers.json` |
| `build-workbook` | Rebuild xlsx from staging JSON |
| `map-install-base` | Install base → JSON rows + gap report |
| `validate` | Check license math / missing org id |
| `sync-workbook` | **Bundled** — slide fields, URLs, subscription dates |

Legacy (still work, use `sync-workbook` instead): `rebuild-ppt-columns`, `sync-subscription-dates`.

See [CLAUDE.md](CLAUDE.md) for paths and details.
