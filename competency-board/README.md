# Competency Board

A drag-and-drop board for deciding what is a **core competency** and what is merely **nice to have** for a Cisco Systems Engineer role. Add as many columns as you like, fill them with items, and move everything around until the picture is right.

No build step, no dependencies, no server. Open `index.html` in a browser.

```bash
cd competency-board
xdg-open index.html        # or just double-click it
```

## What you can do

- **Columns:** add, rename (click the title), recolor, add a description, duplicate, move left/right, clear, delete. Drag a column by its header to reorder.
- **Items:** type in the box at the bottom of a column and press Enter. Paste a bulleted or numbered list to add one item per line. Each item can carry notes and a tag (tags are auto-colored and filterable).
- **Move:** drag cards between columns or within a column. Works with mouse, pen, and touch (on touch, use the grip handle so the page can still scroll). The board auto-scrolls near the edges while dragging; `Esc` cancels a drag.
- **Keyboard:** focus a card, then `Alt`+arrows to move it, `Enter` to edit, `Delete` to remove, `/` to filter, `Ctrl/Cmd`+`Z` to undo.
- **Undo / redo** for every change, including deletes (toast has an Undo button).
- **Templates:** a Cisco SE starter (Core Competencies, Nice to Have, and a To Sort pool of about 18 candidate skills), a blank Core vs Nice to Have board, or an empty board.
- **Persistence:** saved automatically in the browser (`localStorage`). Export JSON as a backup or to share, import it elsewhere, and export Markdown to paste into a doc or a Webex message.
- Light and dark themes.

## Layout

| File | Purpose |
|------|---------|
| `index.html` | Page shell and dialogs |
| `styles.css` | Theming and layout |
| `core.js` | Pure state logic (columns, items, moves, import validation, history, templates). Also loads under Node for tests |
| `app.js` | Rendering, pointer-based drag and drop, menus, dialogs, persistence |
| `tests/core.test.js` | Unit tests for `core.js` |
| `tests/e2e.js` | Real-browser test of drag and drop, touch, keyboard, persistence, import/export |

## Tests

```bash
node --test "tests/*.test.js"                                  # unit tests, no install needed

npm i --no-save playwright-core                                # e2e needs Playwright + a Chrome binary
CHROME_PATH=/usr/bin/google-chrome node tests/e2e.js
```

## Notes

- Everything user-entered is rendered with `textContent`, and imported files are validated and sanitized by `normalize()` (length limits, hex-only colors, de-duplicated ids), so a hostile JSON file cannot inject markup.
- Data never leaves the browser. Clearing site data clears the board, so export a JSON backup of anything you care about.
