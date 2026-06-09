---
name: lookback
description: |
  OCR dashboard screenshots into a structured Excel spreadsheet.
  Each customer folder becomes one row; every card label and value is
  extracted with confidence scoring and written as merged column headers.
  Built for Webex Control Hub screenshots but works on any card-based UI.
allowed-tools: Bash, Read, Edit, Write, Glob
argument-hint: [customer-folder] [output.xlsx]
---

# Lookback Skill

Converts screenshot folders → Excel. One folder = one customer row.

**Project path:** `~/Documents/GitHub/Lookback/`

---

## Quick-start

```bash
cd ~/Documents/GitHub/Lookback

# GUI mode — file picker opens
bash run.sh

# CLI mode — single folder
.venv/bin/python3 src/screenshot_to_excel.py <customer_folder> <output.xlsx>

# CLI mode — multiple folders into one file
.venv/bin/python3 src/screenshot_to_excel.py folder1 folder2 output.xlsx
```

---

## Stack & entry point

| Item | Detail |
|---|---|
| Language | Python 3.13 |
| GUI | tkinter (stdlib) |
| OCR | Tesseract (system) via `pytesseract` |
| Image processing | Pillow + OpenCV (optional but improves accuracy) |
| Excel output | `openpyxl` |
| Entry point | `src/screenshot_to_excel.py` — all logic in one file |
| Venv | `.venv/` — always activate before running |

---

## How it works

1. User picks one or more customer folders (GUI) or passes them as args (CLI)
2. Every image in each folder is OCR'd via Tesseract
3. Adaptive layout parser groups words into rows/phrases, matches values to labels by x-axis overlap
4. Fields written to Excel with two-row merged header: `SectionName::CardLabel`
5. If the Excel file already exists, rows are upserted by customer name (no duplication)

---

## Output format

- **Row identifier:** folder name → Customer name
- **Column header:** `SectionName::CardLabel` (rendered as merged header in Excel)
- **Confidence:** HIGH / MEDIUM / LOW written alongside each extracted value
- **Output file:** wherever you specify; never overwrites without upsert logic

---

## OpenCV preprocessing pipeline

`grayscale → CLAHE → denoise → upscale`

Binary threshold is only applied to low-contrast (scanned) images. If OpenCV is missing, images go straight to Tesseract unprocessed — lower accuracy but functional.

---

## Setup (first time)

```bash
cd ~/Documents/GitHub/Lookback
brew install tesseract          # OS-level OCR engine (required)
python3.13 -m venv .venv
.venv/bin/pip install pytesseract pillow opencv-python openpyxl
```

---

## Gotchas

- Tesseract must be installed at OS level — `which tesseract` should return a path
- OpenCV is optional; skip it if install is slow, but accuracy drops on noisy screenshots
- Always use `.venv/bin/python3`, not system Python
- `run.sh` handles venv activation automatically for GUI mode
- Folder name becomes the row identifier — rename folders before processing if customer names need fixing
