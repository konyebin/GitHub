# Lookback

<ClientOnly>
  <DemoPanel slug="lookback" />
</ClientOnly>

## What it is

**Desktop app (tkinter) + CLI** that OCRs dashboard screenshots (especially Webex Control Hub) and exports labelled metrics to **Excel**, with confidence hints per cell.

## When to use it

- OCR a dashboard screenshot into Excel
- Batch customer folders → one row per folder in a master workbook

## Stack and entry points

| Item | Path |
|------|------|
| Project context | `Lookback/CLAUDE.md` |
| Main script | `Lookback/src/screenshot_to_excel.py` |
| GUI launcher | `Lookback/run.sh` |
| Venv | `Lookback/.venv` (Python **3.13**) |

## Prerequisites

| Need | Detail |
|------|--------|
| Python | **3.13** |
| Packages | `pip install -r requirements.txt` |
| Tesseract | OS install (`brew install tesseract`) |
| Optional | OpenCV for better OCR accuracy |

## How to run

```bash
cd ~/Documents/GitHub/Lookback
bash run.sh
# CLI:
.venv/bin/python3 src/screenshot_to_excel.py <customer_folder> <output.xlsx>
```

## Canonical docs

- `~/Documents/GitHub/Lookback/CLAUDE.md`
