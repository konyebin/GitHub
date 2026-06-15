# check-back-intelligence

<ClientOnly>
  <DemoPanel slug="check-back-intelligence" />
</ClientOnly>

## What it is

**Customer adoption analytics** — track whether Webex customers use what they pay for. Drop PDFs and screenshots into a folder, populate a Check Back spreadsheet via CLI, then explore adoption health in an interactive dashboard.

## Live dashboard (GitHub Pages)

**[Open Check Back dashboard](https://konyebin.github.io/GitHub/demos/check-back/index.html)** — upload any Check Back `.xlsx` in the browser. A sanitized sample loads by default; your data never leaves the browser.

## When to use it

- Build or refresh Check Back workbooks from customer source documents
- Review adoption health (Green/Yellow/Red) across licenses and accounts
- Prepare renewal analytics and account insight charts
- Match BIA slides to customer data

## Stack and entry points

| Item | Path |
|------|------|
| Project context | `check-back-intelligence/CLAUDE.md` |
| CLI | `python -m src.cli` |
| Wrapper script | `./check-back` |
| Dashboard | `dashboard/index.html`, `dashboard/serve.sh` |
| Sample template | `samples/check_back_template.xlsx` |

## Prerequisites

| Need | Detail |
|------|--------|
| Python | 3.x with `pip install -r requirements.txt` |
| Input | Populated Check Back `.xlsx` (dashboard does not accept PDFs directly) |

## How to run

```bash
cd ~/Documents/GitHub/check-back-intelligence
pip install -r requirements.txt

python -m src.cli populate --sources sources/genuine-parts --out output/gpc.xlsx
python -m src.cli validate -i output/gpc.xlsx

./check-back dashboard
# or: bash dashboard/open-dashboard.sh
```

## Canonical docs

- `~/Documents/GitHub/check-back-intelligence/CLAUDE.md`
- `~/Documents/GitHub/check-back-intelligence/README.md`
