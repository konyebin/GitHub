# Splitting the monorepo into one repo per project

This folder turns the projects tracked in this repository into standalone repos, keeping each project's git history. It does not change this checkout until you run `cutover.sh`.

## What lives where

| Project | Today | Dependencies found | Outcome |
|---|---|---|---|
| `check-back-intelligence` | `check-back-intelligence/` | Python: openpyxl, pdfplumber, PyYAML, flask, requests, python-dotenv. Nothing outside its folder. | Already its own repo ([konyebin/check-back-intelligence](https://github.com/konyebin/check-back-intelligence)); the copy here is byte-identical to its `main`. Nothing to create. |
| `samuel-ai-309090` | `docs/public/demos/samuel-ai-309090/` | None (static) | Already its own repo; copy here matches it apart from its README and .gitignore. Nothing to create. |
| `quiz-bank` | `docs/public/demos/quiz-bank/` + `quiz-bank/tests` + `quiz-bank/docs` | Tests imported the app through `../../docs/public/demos/quiz-bank/`. The publish form wrote to `konyebin/GitHub` at `docs/public/demos/quiz-bank/quizzes.json`. | New repo. Paths flattened, tests import `../`, publish target is `konyebin/quiz-bank` `quizzes.json`, `npm test` added. |
| `ice-breaker` | `docs/public/demos/ice-breaker/` | None (Node built-in test runner only) | New repo, `npm test` added. |
| `misc-ops-report` | `docs/public/demos/misc-ops-report/` | pandas. Script preferred `~/Documents/GitHub/wxops/.venv`. | New repo. `requirements.txt` added; script uses a local `.venv` or `$PYTHON`. No runtime dependency on wxops. |
| `ai-receptionist`, `ctfmonopoly`, `hiring-analysis`, `influence-skills` | `docs/public/demos/<name>/` | None (static) | New repos. |
| docs hub | `docs/` | VitePress. Embedded and linked the demos above by `/demos/<name>/`. | Stays here. `cutover.sh` points it at each project's own Pages site. |
| Workspace root | `webex_oauth*.py`, `CLAUDE.md`, `AGENTS.md`, `.claude/`, `.cursor/` | Shared tooling for the whole workspace | Stays here. |

`wxops`, `vidcastmcp`, `scrapeweb`, `Lookback`, `my-orchestrator` and `test/device-mcp-server` are referenced by the docs and `CLAUDE.md` but are not tracked in this repository, so there is nothing to split for them.

## Steps

```bash
pip install git-filter-repo
scripts/split-projects/split.sh ../split-repos     # build repos locally, with history
# inspect ../split-repos/*, run `npm test` in quiz-bank and ice-breaker
scripts/split-projects/publish.sh ../split-repos konyebin   # gh repo create + push + enable Pages
# wait for each Pages site to deploy, then:
scripts/split-projects/cutover.sh                  # drop the demos from this repo, repoint docs
git diff && git commit
```

Each new repo gets a README, `.gitignore` and a GitHub Pages workflow (`overlays/_common`), served at `https://konyebin.github.io/<repo>/`.

## Things to know

- Pages for `quiz-bank` publishes via a token you paste in the form, so the token must have contents-write on `konyebin/quiz-bank`.
- `cutover.sh` leaves `check-back-intelligence/` and the `samuel-ai-309090` demo alone. Both already have their own repos; remove them here once you are happy, and drop the "Prepare Check Back dashboard" step from `.github/workflows/deploy-docs.yml` at the same time. `AGENTS.md` and `.cursor/skills/github-pages-dashboard` mention these paths.
- `.env.admin` is tracked at the repo root and holds real Webex credentials (client secret, access and refresh tokens). It is not copied into any split repo, but it is in this repository's history. Rotate those credentials and remove the file from history.
