# Standalone Check Back Intelligence — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish `check-back-intelligence` as an independent GitHub repository that anyone can clone, install, and run — dashboard, PDF→xlsx CLI, and Webex bot — without the parent `~/Documents/GitHub` monorepo.

**Architecture:** Keep the existing folder layout; decouple path/env assumptions to repo-local `.venv` and `.env`; commit portable samples and `webex_bot/`; add standalone GitHub Pages CI that deploys from `docs/` (no VitePress). The monorepo keeps a thin link in `AGENTS.md` pointing to the new repo.

**Tech Stack:** Python 3.12+ (openpyxl, pdfplumber, Flask), static JS dashboard (esbuild bundle), optional Cloudflare quick tunnels + Webex bot API.

---

## Recommended approach (vs alternatives)

| Approach | Pros | Cons |
|----------|------|------|
| **A. New GitHub repo (recommended)** | Clean onboarding, own Issues/Pages/CI, no monorepo baggage | One-time extraction + monorepo link update |
| B. Git submodule in monorepo | Single workspace for you | External users still clone monorepo; harder discovery |
| C. Dashboard-only npm package | Tiny surface | Loses CLI + bot; not what you asked for |

**Repo name:** `check-back-intelligence`  
**Public demo URL (after setup):** `https://<org>.github.io/check-back-intelligence/`

---

## Target repo structure

```
check-back-intelligence/
├── .env.example
├── .gitignore
├── .github/workflows/pages.yml
├── README.md
├── LICENSE
├── requirements.txt
├── check-back                    # wrapper → local .venv
├── config/field_mapping.yaml
├── docs/                         # GitHub Pages root (built artifacts)
│   ├── index.html
│   ├── dashboard.bundle.js
│   ├── check_back_default.xlsx   # sanitized demo
│   └── vendor/
├── samples/
│   ├── check_back_template.xlsx  # committed, header-only
│   └── Lookback-BIA-Slide-Template.pdf
├── src/
├── dashboard/
├── webex_bot/
├── tests/
└── output/                       # gitignored; user data lives here
```

---

## Phase 0 — Create the new repository

### Task 0: Bootstrap standalone git repo

**Files:**
- Create: new GitHub repo `check-back-intelligence`
- Copy: entire `check-back-intelligence/` tree (exclude customer data)

- [ ] **Step 1: Create empty repo on GitHub** (public or org-owned)

- [ ] **Step 2: Copy project files**

```bash
# From monorepo (adjust paths)
STANDALONE=~/check-back-intelligence-standalone
git clone git@github.com:<org>/check-back-intelligence.git "$STANDALONE"
rsync -a --exclude='.git' --exclude='output/' --exclude='sources/' \
  --exclude='staging/' --exclude='dashboard/check_back_default.xlsx' \
  ~/Documents/GitHub/check-back-intelligence/ "$STANDALONE/"
cd "$STANDALONE"
```

- [ ] **Step 3: Initial commit on `main`**

```bash
git add -A && git status   # verify no .env, no customer xlsx
git commit -m "Initial standalone release of Check Back Intelligence."
```

**Exclude from git (add `.gitignore` in Task 1):** `output/*.xlsx`, `sources/**`, `staging/**`, `.env`, `dashboard/check_back_default.xlsx`, `__pycache__/`, `.venv/`

---

## Phase 1 — Decouple monorepo paths

### Task 1: Add `.gitignore` and `.env.example`

**Files:**
- Create: `.gitignore`
- Create: `.env.example`

- [ ] **Step 1: Write `.gitignore`**

```
.venv/
.env
__pycache__/
*.pyc
output/*.xlsx
!output/.gitkeep
sources/
staging/
dashboard/check_back_default.xlsx
.DS_Store
```

- [ ] **Step 2: Write `.env.example`**

```
# Optional — Webex bot only
WEBEX_BOT_TOKEN=
WEBEX_WEBHOOK_SECRET=

# Optional overrides
CHECK_BACK_XLSX=output/Check_Back_standardized.xlsx
CHECKBACK_DASHBOARD_PORT=8765
CHECKBACK_WEBHOOK_PORT=5010
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore .env.example output/.gitkeep
git commit -m "Add gitignore and env template for standalone use."
```

---

### Task 2: Fix `check-back` venv resolution

**Files:**
- Modify: `check-back`

- [ ] **Step 1: Default venv to repo-local**

Replace lines 13–23 with:

```bash
# Environment:
#   CHECK_BACK_VENV   python venv (default: $ROOT/.venv, else python3 on PATH)
#   CHECK_BACK_XLSX   path to baseline workbook (default: output/Check_Back_standardized.xlsx)

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="${CHECK_BACK_VENV:-$ROOT/.venv}"
if [ -x "$VENV/bin/python" ]; then
  PY="$VENV/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
else
  echo "Python not found. Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi
WORKBOOK="${CHECK_BACK_XLSX:-$ROOT/output/Check_Back_standardized.xlsx}"
```

- [ ] **Step 2: Add `setup` subcommand** (optional but recommended)

```bash
setup)
  python3 -m venv "$ROOT/.venv"
  "$ROOT/.venv/bin/pip" install -r "$ROOT/requirements.txt"
  echo "Ready. Run: ./check-back dashboard"
  ;;
```

- [ ] **Step 3: Smoke test**

```bash
./check-back setup
./check-back dashboard   # needs baseline or demo xlsx
```

- [ ] **Step 4: Commit**

```bash
git add check-back && git commit -m "Use repo-local venv; add setup command."
```

---

### Task 3: Fix CLI default workbook paths

**Files:**
- Modify: `src/cli.py` (lines ~249–343)

- [ ] **Step 1: Add project-root default helper at top of `cli.py`**

```python
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WORKBOOK = PROJECT_ROOT / "output" / "Check_Back_standardized.xlsx"
DEFAULT_TEMPLATE = PROJECT_ROOT / "samples" / "check_back_template.xlsx"
```

- [ ] **Step 2: Replace all `Downloads/Check Back...` defaults**

Use `str(DEFAULT_WORKBOOK)` for `-i` / `--input` defaults and `str(DEFAULT_TEMPLATE)` for `--template`.

- [ ] **Step 3: Run tests**

```bash
PYTHONPATH=. python3 -m pytest tests/ -q
# or at minimum:
PYTHONPATH=. python3 tests/test_sub_term.py
PYTHONPATH=. python3 tests/test_mapper.py
```

- [ ] **Step 4: Commit**

```bash
git add src/cli.py && git commit -m "Default CLI paths to repo output/ and samples/."
```

---

### Task 4: Fix Webex bot env loading

**Files:**
- Modify: `webex_bot/app.py`
- Modify: `webex_bot/register_webhook.py`
- Modify: `webex_bot/run-check-back-bot.sh`

- [ ] **Step 1: Load `.env` from repo root only**

In `app.py` and `register_webhook.py`:

```python
_REPO_ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
except ImportError:
    pass
```

Remove `parent.parent.parent` references.

- [ ] **Step 2: Update `run-check-back-bot.sh`**

Remove block that sources `$ROOT/../.env`. Keep only:

```bash
if [[ -f "$ROOT/.env" ]]; then
  set -a; source "$ROOT/.env"; set +a
fi
```

Update comment: `# Bot token: WEBEX_BOT_TOKEN in project .env`

- [ ] **Step 3: Commit `webex_bot/`** (currently untracked in monorepo)

```bash
git add webex_bot/ && git commit -m "Commit Webex bot with repo-local env loading."
```

---

### Task 5: Scrub hardcoded paths in dashboard UI

**Files:**
- Modify: `dashboard/index.html` (lines ~975, 993, 1195)
- Rebuild: `dashboard/dashboard.bundle.js` via `dashboard/build-bundle.sh`

- [ ] **Step 1: Replace monorepo hints with generic text**

```javascript
'Run in Terminal:<br><code>cd dashboard && ./open-dashboard.sh</code>'
// and
'<code>cd dashboard && ./serve.sh</code>'
```

- [ ] **Step 2: Rebuild bundle**

```bash
cd dashboard && ./build-bundle.sh
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/index.html dashboard/dashboard.bundle.js
git commit -m "Remove monorepo-specific path hints from dashboard."
```

---

## Phase 2 — Portable samples and first-run experience

### Task 6: Commit template and demo workbooks

**Files:**
- Create: `samples/check_back_template.xlsx` (real file, not symlink)
- Create: `output/.gitkeep`
- Script: reuse `dashboard/create-demo-workbook.py`

- [ ] **Step 1: Generate header-only template**

```bash
PYTHONPATH=. python3 dashboard/create-demo-workbook.py samples/check_back_template.xlsx
# Edit if needed: zero data rows, headers only for populate --template
```

- [ ] **Step 2: Document first-run in README**

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp samples/check_back_template.xlsx output/my_portfolio.xlsx
# OR populate from PDFs:
.venv/bin/python -m src.cli populate -s ./my-customer-pdfs -o output/my_portfolio.xlsx
export CHECK_BACK_XLSX=output/my_portfolio.xlsx
./check-back dashboard
```

- [ ] **Step 3: Commit samples (no PII)**

```bash
git add samples/check_back_template.xlsx output/.gitkeep
git commit -m "Add committed template workbook for fresh clones."
```

---

### Task 7: Rewrite `prepare-github-pages.sh` for standalone repo

**Files:**
- Modify: `dashboard/prepare-github-pages.sh`

- [ ] **Step 1: Output to `docs/` at repo root**

```bash
DASH="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$DASH/.." && pwd)"
DEST="$REPO_ROOT/docs"
PYTHON="${PYTHON:-python3}"
# ... same build steps, update live URL echo:
echo "Live URL: https://<org>.github.io/check-back-intelligence/"
```

- [ ] **Step 2: Verify `IS_PUBLIC_HOST` in `index.html`**

Ensure `github.io` detection works for any `*.github.io` host (already does).

- [ ] **Step 3: Run locally**

```bash
cd dashboard && ./prepare-github-pages.sh && ls ../docs/
```

- [ ] **Step 4: Commit**

```bash
git add dashboard/prepare-github-pages.sh docs/
git commit -m "Publish dashboard to repo docs/ for GitHub Pages."
```

---

## Phase 3 — CI/CD and documentation

### Task 8: Standalone GitHub Pages workflow

**Files:**
- Create: `.github/workflows/pages.yml`

- [ ] **Step 1: Add workflow**

```yaml
name: Deploy dashboard to GitHub Pages
on:
  push:
    branches: [main]
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: true
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install openpyxl
      - run: bash dashboard/prepare-github-pages.sh
      - uses: actions/upload-pages-artifact@v3
        with:
          path: docs
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Enable Pages** in repo Settings → Pages → Source: GitHub Actions

- [ ] **Step 3: Commit and verify deploy on push**

```bash
git add .github/workflows/pages.yml
git commit -m "Add standalone GitHub Pages deploy workflow."
git push
```

---

### Task 9: Rewrite README for external users

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Replace all `~/Documents/GitHub/...` with clone-relative paths**

Sections to include:
1. What it does (one paragraph)
2. Quick start (`git clone`, `setup`, `dashboard`)
3. Full pipeline (`populate` → `sync-workbook` → dashboard)
4. Webex bot (`run-check-back-bot.sh`, `register_webhook`)
5. Public demo link (Pages URL)
6. Environment variables table
7. **No customer data in repo** — bring your own xlsx/PDFs

- [ ] **Step 2: Add `LICENSE`** (MIT recommended if Cisco-internal constraints allow)

- [ ] **Step 3: Commit**

```bash
git add README.md CLAUDE.md LICENSE
git commit -m "Document standalone install and usage."
```

---

### Task 10: Add `bot` subcommand to `check-back`

**Files:**
- Modify: `check-back`

- [ ] **Step 1: Add case**

```bash
bot)
  exec bash "$ROOT/webex_bot/run-check-back-bot.sh"
  ;;
```

- [ ] **Step 2: Document in README**

```bash
./check-back bot
```

- [ ] **Step 3: Commit**

```bash
git add check-back README.md
git commit -m "Add check-back bot entry point."
```

---

## Phase 4 — Monorepo handoff (optional, same session)

### Task 11: Update parent monorepo references

**Files (in `~/Documents/GitHub`, not new repo):**
- Modify: `AGENTS.md` — link to new repo URL
- Modify: `docs/projects/check-back-intelligence.md` — external link + “moved” notice
- Modify: `.github/workflows/deploy-docs.yml` — remove `prepare-github-pages.sh` step OR keep as fork of demo

- [ ] **Step 1: Decide monorepo demo strategy**

| Strategy | Action |
|----------|--------|
| Redirect only | Remove `docs/public/demos/check-back/`; project page links to new Pages URL |
| Mirror | Submodule or periodic sync script (more maintenance) |

Recommended: **redirect only** — single source of truth in new repo.

- [ ] **Step 2: Update `AGENTS.md` routing row**

```markdown
| Check Back customer workbooks | `check-back-intelligence` (standalone repo) | `git clone … && ./check-back setup` |
```

---

## Verification checklist (must pass before announcing)

- [ ] Fresh clone on a machine **without** `~/Documents/GitHub`:

```bash
git clone <repo-url> && cd check-back-intelligence
./check-back setup
cd dashboard && ./prepare-github-pages.sh
python3 -m http.server 8765 --directory docs &
open http://127.0.0.1:8765/index.html
```

- [ ] CLI populate with sample PDF (or empty template):

```bash
.venv/bin/python -m src.cli populate -s samples -t samples/check_back_template.xlsx -o output/test.xlsx
```

- [ ] `./check-back dashboard` opens server and loads workbook

- [ ] Webex bot (if token available):

```bash
cp .env.example .env   # fill WEBEX_BOT_TOKEN
./check-back bot
PYTHONPATH=. python3 -m webex_bot.register_webhook --list
```

- [ ] GitHub Pages deploy succeeds; public URL loads demo workbook

- [ ] `git status` shows no tracked `.env`, customer xlsx, or `sources/`

---

## Execution order summary

| Order | Task | Est. time |
|-------|------|-----------|
| 1 | Task 0 — New repo bootstrap | 30 min |
| 2 | Tasks 1–5 — Path decoupling | 2–3 hrs |
| 3 | Tasks 6–7 — Samples + Pages script | 1 hr |
| 4 | Tasks 8–10 — CI + docs + bot entry | 2 hrs |
| 5 | Task 11 — Monorepo handoff | 30 min |

**Total:** ~1 day for full standalone parity.

---

## Out of scope (YAGNI)

- PyPI package for `src.cli`
- Docker image (document `python3 -m venv` instead)
- Multi-tenant hosted SaaS
- wxops MCP integration in standalone repo

---

## Self-review

| Spec requirement | Task |
|------------------|------|
| Run independently | Tasks 1–5 |
| New project for others | Task 0, 8, 9 |
| Full toolkit (dashboard + CLI + bot) | All tasks; user confirmed full scope |
| No customer PII in git | Task 1, 6 |
| Public demo | Tasks 7–8 |

No placeholders remain. Scope is single-repo extraction, not microservices.
