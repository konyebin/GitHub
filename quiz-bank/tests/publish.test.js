import assert from "node:assert/strict";
import test from "node:test";
import { publishQuiz } from "../../docs/public/demos/quiz-bank/publish.js";

test("appends a quiz and puts the file with the current sha", async () => {
  const calls = [];
  const bank = [{ id: "python-lists", title: "Python lists", description: "", questions: [] }];
  const fetchImpl = async (url, options = {}) => {
    calls.push({ url, options });
    if (!options.method || options.method === "GET") {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          sha: "abc",
          content: Buffer.from(JSON.stringify(bank)).toString("base64"),
        }),
      };
    }
    return { ok: true, status: 200, json: async () => ({ content: { sha: "def" } }) };
  };
  const quiz = {
    id: "tudor-monarchs",
    title: "Tudor monarchs",
    description: "",
    questions: [{ prompt: "First Tudor king?", choices: ["Henry VII", "Henry VIII"], answerIndex: 0 }],
  };
  const result = await publishQuiz({
    token: "example-token",
    owner: "konyebin",
    repo: "GitHub",
    branch: "main",
    path: "docs/public/demos/quiz-bank/quizzes.json",
    quiz,
    fetchImpl,
  });
  assert.equal(result.contentSha, "def");
  const put = calls[1];
  assert.equal(put.options.method, "PUT");
  assert.equal(put.options.headers.Authorization, "Bearer example-token");
  const body = JSON.parse(put.options.body);
  assert.equal(body.sha, "abc");
  const written = JSON.parse(Buffer.from(body.content, "base64").toString("utf8"));
  assert.deepEqual(written.map((item) => item.id), ["python-lists", "tudor-monarchs"]);
});

test("retries once when GitHub reports a conflict", async () => {
  let reads = 0;
  let puts = 0;
  const bank = [];
  const fetchImpl = async (url, options = {}) => {
    if (!options.method || options.method === "GET") {
      reads += 1;
      return {
        ok: true,
        status: 200,
        json: async () => ({
          sha: reads === 1 ? "abc" : "ghi",
          content: Buffer.from(JSON.stringify(bank)).toString("base64"),
        }),
      };
    }
    puts += 1;
    if (puts === 1) return { ok: false, status: 409, json: async () => ({}) };
    return { ok: true, status: 200, json: async () => ({ content: { sha: "def" } }) };
  };
  const result = await publishQuiz({
    token: "example-token",
    owner: "konyebin",
    repo: "GitHub",
    branch: "main",
    path: "docs/public/demos/quiz-bank/quizzes.json",
    quiz: {
      id: "baking-bread",
      title: "Baking bread",
      description: "",
      questions: [{ prompt: "What makes dough rise?", choices: ["Yeast", "Salt"], answerIndex: 0 }],
    },
    fetchImpl,
  });
  assert.equal(result.contentSha, "def");
  assert.equal(puts, 2);
  assert.equal(reads, 2);
});
