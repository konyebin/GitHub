# Check Back Customer Adoption Intelligence

## Pipeline (any customer)

1. Drop PDFs and screenshots in a folder (or one subfolder per customer).
2. `python -m src.cli populate --sources <folder> --out output/<name>.xlsx`
3. Upload that xlsx in `dashboard/index.html` or run `./check-back dashboard`.

Dashboard does **not** accept PDFs/images — only the populated Check Back spreadsheet.

## Commands

```bash
cd check-back-intelligence
./check-back setup
./check-back populate -s sources/my-customer --out output/my_portfolio.xlsx
./check-back dashboard
```

## Samples (in repo)

- `samples/check_back_template.xlsx` — header-only Check Back template (`scripts/build_samples.py`)
- `samples/install_base_sample.xlsx` — optional install base mapping demo
- `samples/Lookback-BIA-Slide-Template.pdf` — BIA slide reference

## Webex bot

```bash
cp .env.example .env   # WEBEX_BOT_TOKEN=...
./check-back bot
PYTHONPATH=. python3 -m webex_bot.register_webhook --url "<tunnel>/webhook"
```

Commands in Webex: `dashboard`, `summary`, `refresh`, `help`.
