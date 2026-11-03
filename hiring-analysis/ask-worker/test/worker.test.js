import test from "node:test";
import assert from "node:assert/strict";
import worker from "../src/index.js";

const ORIGIN = "https://site.example";
const env = (over = {}) => ({
  ALLOWED_ORIGIN: ORIGIN,
  MODEL: "m",
  LIMITER: { limit: async () => ({ success: true }) },
  AI: { run: async () => ({ response: "Answer (F1)." }) },
  ...over
});
const req = (body, headers = {}, method = "POST") =>
  new Request("https://w.example/", { method, headers: { origin: ORIGIN, "content-type": "application/json", ...headers }, body: method === "POST" ? JSON.stringify(body) : undefined });

test("answers a valid question", async () => {
  const r = await worker.fetch(req({ question: "q", context: "c" }), env());
  assert.equal(r.status, 200);
  assert.equal((await r.json()).answer, "Answer (F1).");
  assert.equal(r.headers.get("access-control-allow-origin"), ORIGIN);
});

test("blocks other origins, rate limited callers and bad bodies", async () => {
  assert.equal((await worker.fetch(req({ question: "q", context: "c" }, { origin: "https://evil.example" }), env())).status, 403);
  assert.equal((await worker.fetch(req({ question: "q", context: "c" }), env({ LIMITER: { limit: async () => ({ success: false }) } }))).status, 429);
  assert.equal((await worker.fetch(req({ question: "", context: "c" }), env())).status, 400);
  assert.equal((await worker.fetch(req(null, {}, "GET"), env())).status, 405);
});

test("model failure returns a clean 502", async () => {
  const r = await worker.fetch(req({ question: "q", context: "c" }), env({ AI: { run: async () => { throw new Error("boom"); } } }));
  assert.equal(r.status, 502);
  assert.ok(!JSON.stringify(await r.json()).includes("boom"));
});
