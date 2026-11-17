# Quiz bank

Static multiple-choice quizzes. The page groups similar quizzes into topics each time it loads; a quiz that matches nothing becomes its own topic.

Live: https://konyebin.github.io/quiz-bank/

## Run locally

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

## Test

```bash
npm test        # Node 20+, no dependencies
```

## Publishing a quiz

The "add a quiz" form commits to `quizzes.json` on `main` through the GitHub contents API, using a personal access token you paste into the form (never stored). The token needs write access to **contents** on this repository. The Pages workflow redeploys on push.

`app.js` (`PUBLISH`) holds the owner, repo, branch and path the form writes to.

## Layout

- `index.html`, `app.js`, `style.css` — the page
- `cluster.js`, `validate.js`, `publish.js` — logic, unit-tested in `tests/`
- `quizzes.json` — the quiz bank
- `docs/` — design plan
