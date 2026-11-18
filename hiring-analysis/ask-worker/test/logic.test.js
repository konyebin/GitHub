import test from "node:test";
import assert from "node:assert/strict";
import { buildMessages, corsHeaders, extractAnswer, parseRequest, scrubIds, MAX_QUESTION } from "../src/logic.js";

test("accepts a valid request and scrubs candidate ids", () => {
  const r = parseRequest({ question: "Who is lenient?", context: "F1 candidate12 and Candidate 7 scored high" });
  assert.equal(r.error, undefined);
  assert.ok(!/candidate\s*\d/i.test(r.context));
});

test("rejects bad input", () => {
  assert.ok(parseRequest(null).error);
  assert.ok(parseRequest({ question: "", context: "x" }).error);
  assert.ok(parseRequest({ question: "x".repeat(MAX_QUESTION + 1), context: "x" }).error);
  assert.ok(parseRequest({ question: "q", context: "" }).error);
  assert.ok(parseRequest({ question: "q", context: "x".repeat(60001) }).error);
});

test("cors only allows the configured origin", () => {
  assert.equal(corsHeaders("https://a.example", "https://a.example")["access-control-allow-origin"], "https://a.example");
  assert.equal(corsHeaders("https://evil.example", "https://a.example")["access-control-allow-origin"], "null");
  assert.equal(corsHeaders(null, "https://a.example")["access-control-allow-origin"], "null");
});

test("messages keep the rules in the system prompt and the question in the user turn", () => {
  const m = buildMessages("Q?", "CTX");
  assert.equal(m[0].role, "system");
  assert.match(m[0].content, /Never recommend hiring or rejecting/);
  assert.match(m[1].content, /CTX[\s\S]*Q\?/);
});

test("extracts answers from the shapes Workers AI models return", () => {
  assert.equal(extractAnswer({ response: " hi " }), "hi");
  assert.equal(extractAnswer({ choices: [{ message: { content: "yo" } }] }), "yo");
  assert.equal(extractAnswer({ response: "<think>x</think>done" }), "done");
  assert.equal(extractAnswer(null), "");
});

test("scrubIds", () => assert.equal(scrubIds("candidate5"), "[candidate]"));
