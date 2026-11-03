# ask-worker

Optional Cloudflare Worker behind the dashboard's "Ask the data" page. Without it, that page is a plain search over the findings and nothing leaves the browser. With it, questions are answered by a Workers AI model that sees only the aggregate findings (no candidate ids).

How it stays safe: the Worker accepts POSTs only from `ALLOWED_ORIGIN`, rate limits per origin, caps question and context size, strips anything that looks like a candidate id, and tells the model to answer only from the supplied results and never to recommend hiring or rejecting a person. It stores nothing.

```bash
cd hiring-analysis/ask-worker
npm install
npm test                       # unit tests, no network
npx wrangler login
npx wrangler deploy            # prints https://hiring-analysis-ask.<account>.workers.dev
```

Then set `HIRING_ASK_ENDPOINT=<that url>` in `hiring-analysis/.env` and rebuild the shareable dashboard (`dashboard/build_dashboard.py --mode shareable`). The endpoint is only ever embedded in the shareable build.

Change `ALLOWED_ORIGIN` in `wrangler.jsonc` if the dashboard is hosted somewhere other than https://konyebin.github.io. Workers AI usage is billed to the Cloudflare account that deploys it. The model name is the `MODEL` var; the model response shape handled is `{response}` or OpenAI-style `choices`. Not yet run against live Workers AI.
