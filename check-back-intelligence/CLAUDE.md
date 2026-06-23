# Check Back Customer Adoption Intelligence

## Pipeline (any customer)

1. Drop PDFs and screenshots in a folder (or one subfolder per customer).
2. `python -m src.cli populate --sources <folder> --out output/<name>.xlsx`
3. Upload that xlsx in `dashboard/index.html`.

Dashboard does **not** accept PDFs/images — only the populated Check Back spreadsheet.

## Commands

```bash
cd ~/Documents/GitHub/check-back-intelligence
pip install -r requirements.txt

python -m src.cli populate -s sources/genuine-parts --account "GENUINE PARTS COMPANY" \
  -t "$HOME/Downloads/Check Back Initiative Customer Analysis.xlsx" \
  -o "$HOME/Downloads/Check Back Initiative Customer Analysis.xlsx" --mode append
python -m src.cli validate -i output/gpc.xlsx --out staging/validation.json

open ~/Documents/GitHub/check-back-intelligence/dashboard/index.html
```

## Samples

- `samples/check_back_template.xlsx` — header structure (used as template; `fresh` mode clears sample rows)
- `samples/install_base_sample.xlsx` — optional install base mapping source
