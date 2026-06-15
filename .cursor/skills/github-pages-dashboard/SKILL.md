---
name: github-pages-dashboard
description: Publish static HTML/JS dashboards to GitHub Pages via the workspace VitePress site. Use when the user asks for GitHub Pages, host a dashboard publicly, deploy the Check Back dashboard, or browser tools without a local server.
---

# GitHub Pages dashboard (~/Documents/GitHub)

## One site, one workflow

| What | Where |
|------|--------|
| CI | `.github/workflows/deploy-docs.yml` |
| Base URL | `https://konyebin.github.io/GitHub/` (`base: "/GitHub/"` in `docs/.vitepress/config.ts`) |
| Hosted assets | `docs/public/demos/<slug>/` (VitePress `public/` folder — path name is historical) |
| Live dashboard URL | `https://konyebin.github.io/GitHub/demos/<slug>/index.html` |

**Never** add a second Pages workflow unless the user explicitly asks.

## Checklist (every new dashboard)

1. Read `deploy-docs.yml` + `docs/.vitepress/config.ts`
2. Put assets in `docs/public/demos/<slug>/` (relative paths only)
3. Add `prepare-github-pages.sh` in the project if files are generated
4. Add one CI step **before** `npm run docs:build` in `deploy-docs.yml` (or commit built assets directly)
5. In app JS: `const IS_PUBLIC_HOST = /github\.io$/i.test(location.hostname)` — no `~/Downloads` or localhost hints on public host
6. **Never** ship real customer xlsx/PII — use sanitized sample workbook generator
7. Link live URL in `docs/projects/<project>.md`
8. Run prepare script locally (seconds)
9. **Push to `main`** — Pages only deploys from `main`/`master`, not feature branches

## Prepare script template

Adapt from `check-back-intelligence/dashboard/prepare-github-pages.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SRC/../.." && pwd)"
DEST="$REPO_ROOT/docs/public/demos/<slug>"
PYTHON="${PYTHON:-$REPO_ROOT/.venv/bin/python3}"

"$SRC/build-bundle.sh"   # if needed
mkdir -p "$DEST"
"$PYTHON" "$SRC/create-demo-workbook.py" "$DEST/check_back_default.xlsx"  # sanitized sample only
cp "$SRC/index.html" "$DEST/"
cp "$SRC/dashboard.bundle.js" "$DEST/"
```

## CI snippet (deploy-docs.yml)

Before `npm run docs:build`:

```yaml
- name: Prepare Check Back dashboard for GitHub Pages
  run: bash check-back-intelligence/dashboard/prepare-github-pages.sh
```

Add `setup-python` + `pip install openpyxl` only if prepare needs Python.

**Alternative (simpler):** commit `docs/public/demos/<slug>/` directly after running prepare locally — no CI prepare step required.

## Reference: Check Back dashboard

- Source: `check-back-intelligence/dashboard/`
- Prepare: `check-back-intelligence/dashboard/prepare-github-pages.sh`
- Hosted: `docs/public/demos/check-back/`
- Live: `https://konyebin.github.io/GitHub/demos/check-back/index.html`

## Agent rules (avoid hangs)

- Write files with the Write tool — avoid long parallel shell batches
- Run prepare script **alone**, one command
- If shell interrupts, give user the manual command
- Prep takes ~5–15 seconds locally

## 404 troubleshooting

404 means the dashboard files are not on **`main`** at deploy time. Check:

1. `docs/public/demos/<slug>/index.html` exists locally
2. Files are committed on **`main`** (not only a feature branch)
3. GitHub Actions "Deploy docs to GitHub Pages" succeeded after push

```bash
bash ~/Documents/GitHub/check-back-intelligence/dashboard/prepare-github-pages.sh
git checkout main && git pull
git add docs/public/demos/check-back/
git commit -m "Publish Check Back dashboard to GitHub Pages"
git push origin main
```
