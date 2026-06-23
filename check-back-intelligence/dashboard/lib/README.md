# Dashboard JavaScript modules

The dashboard loads a **concat bundle** (`dashboard.bundle.js`) — no npm build step. Edit files under `lib/`, then run `./build-bundle.sh`.

## Layout

| Module | Responsibility |
|--------|----------------|
| `lib/namespace.js` | `CheckBack.Dashboard` root |
| `lib/constants.js` | Column names, link order, canonical field sets |
| `lib/bia-sanitize.js` | `BiaSanitizer` — field cleanup, health G/Y/R, timelines |
| `lib/html-utils.js` | `DashboardHtml` — escape, kv rows, license bars, org links |
| `lib/note-parser.js` | `NoteParser` — extract PL/WS provisioning from notes columns |
| `lib/license-products.js` | `LicenseProductParser` — PL/WS/WxMS/WxM/WxCC used/entitled pairs |
| `lib/bia-slide-matcher.js` | `BiaSlideMatcher` — org id / alias / fuzzy name matching |
| `lib/bia-workbook-mapper.js` | `BiaWorkbookMapper` — row ↔ slide object mapping |
| `lib/bia-portfolio.js` | `BiaPortfolioService` — merge deck + workbook portfolio |
| `lib/bia-slide-merger.js` | `BiaSlideMerger` — overlay workbook edits on slide view |
| `lib/bia-slide-renderer.js` | `BiaSlideRenderer` — HTML for Business Insight slide |
| `lib/bia-slide-editor.js` | `BiaSlideEditor` — in-slide edit ↔ workbook column sync |
| `bia-template.js` | `BiaTemplate` facade (stable global API) |
| `account-insight.js` | Overlay open/close; delegates to `BiaTemplate` |

## Conventions

- **Classes** for cohesive domains; **static methods** (no instance state in the browser bundle).
- Shared utilities live in `CheckBack.Dashboard.*` — avoid duplicating `esc()` or sanitizers.
- **`BiaTemplate`** global is kept for `index.html` inline handlers; implementation is `BiaTemplateFacade`.
