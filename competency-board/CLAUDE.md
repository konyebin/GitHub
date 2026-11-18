# competency-board

Static, dependency-free drag-and-drop board for sorting Cisco SE skills into core competencies vs nice to haves. Inherits conventions from the root `CLAUDE.md`.

## Run and test

- Run: open `index.html` directly (works from `file://`; scripts are classic, not ES modules, on purpose).
- Unit tests: `node --test "tests/*.test.js"` (pass a glob; passing the directory fails on Node 22).
- E2E: `npm i --no-save playwright-core && CHROME_PATH=... node tests/e2e.js` (not a repo dependency).

## Conventions

- `core.js` is pure and DOM-free; all state rules and validation live there with unit tests. `app.js` only renders and wires events.
- Every state change goes through `commit(mutate)` in `app.js`, which snapshots for undo, persists to `localStorage`, and re-renders. Do not mutate `state` elsewhere.
- Drag and drop uses pointer events, not HTML5 DnD, so touch works. The dragged element itself is the live placeholder; the drop index is its position among sibling cards, which matches the post-removal index semantics of `moveItem` / `moveColumn`.
- Render user text with `textContent` (the `h()` helper does this); never `innerHTML` with user data.
- Form fields named `title` must be read via `form.elements.title` because `form.title` is the HTML `title` attribute.
- Changing the saved shape: bump `SCHEMA_VERSION` and keep `normalize()` tolerant of older files.
